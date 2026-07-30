"""Stage 1 — SURVEY. Deterministic. No model.

Reads a repo, emits survey.json: file tree, import edges, entry points, git
churn. Python-only, stdlib `ast` (see CLAUDE.md: `ast` beats tree-sitter here).

Survey is where the project's facts come from, so every number it emits has to
be defensible on stage. Four things in here exist because the obvious version of
them is measurably wrong on the proving-ground repo:

  root discovery   `restored/` has its pyproject at `src/pyproject.toml`, not at
                   the root. Surveyed from `restored/` the longest-prefix
                   resolver finds ONE internal edge out of 782 import
                   statements — a silently empty graph, not an error. The anchor
                   namespace (repo_root) and the module namespace (import_roots)
                   are separate concepts and conflating them costs the map.

  the classifier   An import naming a module with no file on disk is NOT an edge.
                   Measured on `restored/src`: 1854 internal, 706 dangling
                   statements over 14 targets, 1922 external. The bare
                   longest-prefix resolver calls 2557 of them internal, of which
                   700 (27.4%) are phantom edges to files that do not exist.

  the churn probe  Three states, not two. `restored/` sits INSIDE a git work
                   tree and has no tracked history of its own, so a boolean
                   "is there git?" answers yes and then reports the enclosing
                   repository's commits against files that do not exist here.
                   The pathspec `-- .` is what stops that, and it is two argv
                   elements or git exits 128.

  the substitute   With no history, files are ranked by fan-in and every string
                   that carries the ranking says so (decision #18). The page's
                   drawer heading is hard-coded MOST-EDITED FILES, so an
                   unlabelled substitution makes the artifact state a falsehood.

Reading and hashing happen in `textio` and nowhere else. A second reader is a
second sha256 recipe, and every anchor in the bundle dies of it.
"""
import ast
import hashlib
import keyword
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from trailhead.textio import read_source, rel_key

#: Pruned at directory level by name, in place, never rglob-then-filter — one
#: `.venv` is 45,698 entries on this machine and the walk is the only thing
#: standing between survey and it. Plan §3.3, literal.
EXCLUDED_DIRS = frozenset({
    ".git", ".venv", "venv", "env", ".env", "node_modules", "__pycache__",
    "site-packages", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    ".nox", "build", "dist", ".eggs", ".ipynb_checkpoints", "htmlcov",
    ".idea", ".vscode", "target", "vendor", "third_party",
})

#: Suffixes an anchor may point into besides `.py` (decision #6). Line-based
#: anchoring is language-agnostic; `src/pyproject.toml:53` is the single most
#: anchorable fact in the proving-ground repo.
TEXT_SUFFIXES = frozenset({
    ".toml", ".cfg", ".ini", ".yml", ".yaml", ".json", ".md", ".txt",
    ".sh", ".cmd", ".ps1",
})

#: Build files that carry no suffix at all.
TEXT_NAMES = frozenset({"Makefile", "justfile", "Dockerfile"})

#: A file bigger than this is never bundled, so never anchored into.
MAX_TEXT_BYTES = 256 * 1024

#: `evaluation/economic_value.py` is 1439 lines. A def list is an orientation
#: aid, not an index, and 400 of them is already past useful.
MAX_DEFS_PER_FILE = 400

#: Every git call is bounded. A hung git on stage is a dead demo.
GIT_TIMEOUT = 10

#: Constructors that mean "this module is a service entry point" (rule 4).
_APP_FACTORIES = frozenset({"FastAPI", "Flask", "Typer"})

_DOC_SUFFIXES = frozenset({".md", ".rst", ".txt"})


class SourceRootError(Exception):
    """Raised when a repo of real size resolves to zero internal edges.

    This is the failure mode that has no symptom: a wrong import root does not
    crash, it produces an empty graph, a map with no edges and a walkthrough
    that says nothing. The check is `len(py_in_scope) > 50 and internal == 0`,
    and the message names every candidate root that was considered with the
    edge count each one would have produced, because the fix is always to point
    the tool one directory deeper or one directory up.
    """


@dataclass(frozen=True)
class Roots:
    """Where the repo is, and separately, what is on the import path.

    `repo_root` is the ANCHOR namespace — every path key in the bundle is
    relative to it. `import_roots` are sys.path entries and set module names.
    On `restored/` they differ (`restored/` vs `restored/src`) and conflating
    them yields 1 edge out of 782.
    """

    repo_root: Path
    import_roots: list[Path]
    test_roots: list[Path]
    pyproject: Path | None
    declared_packages: list[str]
    rule: str


@dataclass(frozen=True)
class GitState:
    """Three states, not two — plus the error state.

    GIT_OK        history exists for this path
    GIT_UNTRACKED inside a work tree, but nothing here is tracked
    NO_GIT        no work tree, or no git binary
    GIT_ERROR     git ran and failed in a way worth reporting rather than hiding

    `branch` is additive to the plan's five fields and defaults to None so that
    positional construction of the documented shape still works.
    """

    state: str
    toplevel: Path | None
    prefix: str
    head: str | None
    reason: str
    branch: str | None = None


@dataclass(frozen=True)
class ImportRef:
    """One import statement, with `base` ALREADY made absolute.

    Relative resolution happens inside `extract_imports`, so nothing downstream
    needs `roots` to know what `from . import x` meant. `name` is None for a
    plain `import a.b.c` and the imported symbol otherwise — which may be a
    submodule or an attribute, and one file cannot tell the difference. The
    classifier decides, using what is actually on disk.
    """

    base: str
    name: str | None
    level: int
    line: int

    @property
    def dotted(self) -> str:
        return f"{self.base}.{self.name}" if self.name else self.base


# --------------------------------------------------------------------------
# 3.2 Root discovery
# --------------------------------------------------------------------------

def discover_roots(repo_root: Path) -> Roots:
    """The anchor root, the import roots, and where that decision came from.

    A ranked cascade whose terminal case always succeeds, because "this repo
    has no recognisable layout" must still produce a survey. `rule` is carried
    into `survey.json` so the choice is inspectable rather than magic — when the
    map looks wrong, the first question is always which root produced it.
    """
    base = Path(repo_root).resolve()
    pyproject = _shallowest_pyproject(base)

    data: dict = {}
    import_roots: list[Path] = []
    packages: list[str] = []
    rule = ""

    if pyproject is not None:
        data = _load_toml(pyproject)
        import_roots, packages, rule = _declared_roots(pyproject, data)

    if not import_roots:
        import_roots, rule = _cascade_roots(base)

    test_roots = _test_roots(base, pyproject, data, import_roots)

    # A test tree that sits outside every import root is not merely unnamed —
    # it vanishes. Measured: 68 of 161 files on IMC-Prosperity-4 (all 36 tests),
    # 49 of 81 on prediction-markets (all 43 test files). `restored/` only
    # escapes it by luck, because its tests happen to live at `src/tests`.
    for t in test_roots:
        import_roots.append(t.parent)

    import_roots = _dedupe_paths(import_roots)
    if not packages:
        packages = _packages_under(import_roots, test_roots)

    return Roots(
        repo_root=base,
        import_roots=import_roots,
        test_roots=_dedupe_paths(test_roots),
        pyproject=pyproject,
        declared_packages=packages,
        rule=rule,
    )


def _shallowest_pyproject(base: Path) -> Path | None:
    """The pyproject.toml nearest the root, found through the PRUNED walk.

    Never `rglob("**/pyproject.toml")`: on IMC-Prosperity-4 that walks 45,698
    entries under `.venv` before answering, and the answer it finds first is a
    vendored package's, not the project's.
    """
    best: Path | None = None
    best_depth = 10**9
    for dirpath, _dirnames, filenames in _walk(base):
        if "pyproject.toml" not in filenames:
            continue
        cand = dirpath / "pyproject.toml"
        depth = len(cand.relative_to(base).parts)
        if depth < best_depth or (depth == best_depth and best is not None
                                  and cand.as_posix() < best.as_posix()):
            best, best_depth = cand, depth
    return best


def _load_toml(path: Path) -> dict:
    """Parse a TOML file, or return {} — a malformed pyproject is not fatal."""
    try:
        return tomllib.loads(read_source(path).text())
    except (OSError, tomllib.TOMLDecodeError, ValueError):
        return {}


def _declared_roots(pyproject: Path, data: dict) -> tuple[list[Path], list[str], str]:
    """Import roots the project itself declares, in build-backend order.

    Each entry names a directory relative to the pyproject's parent. The case
    that matters is hatch's bare `packages = ["volforecast"]`, which has no
    directory component at all — the import root is then the pyproject's own
    directory, which is exactly why `restored/src` and not `restored/` is right.
    """
    parent = pyproject.parent
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return [], [], ""

    st = tool.get("setuptools", {})
    if isinstance(st, dict):
        find = st.get("packages", {})
        where = find.get("find", {}).get("where") if isinstance(find, dict) else None
        if isinstance(where, list) and where:
            roots = [parent / str(w) for w in where if isinstance(w, str)]
            return roots, [], "pyproject [tool.setuptools.packages.find] where"
        if isinstance(find, list) and find:
            names = [str(p).split(".")[0] for p in find]
            return [parent], sorted(set(names)), "pyproject [tool.setuptools] packages"
        pkg_dir = st.get("package-dir")
        if isinstance(pkg_dir, dict) and "" in pkg_dir:
            return ([parent / str(pkg_dir[""])], [],
                    "pyproject [tool.setuptools] package-dir")

    wheel = (tool.get("hatch", {}).get("build", {})
                 .get("targets", {}).get("wheel", {}))
    packages = wheel.get("packages") if isinstance(wheel, dict) else None
    if isinstance(packages, list) and packages:
        roots, names = _split_package_paths(parent, [str(p) for p in packages])
        return roots, names, "pyproject [tool.hatch.build.targets.wheel] packages"

    poetry = tool.get("poetry", {})
    packages = poetry.get("packages") if isinstance(poetry, dict) else None
    if isinstance(packages, list) and packages:
        roots, names = [], []
        for entry in packages:
            if not isinstance(entry, dict):
                continue
            frm = entry.get("from")
            roots.append(parent / str(frm) if frm else parent)
            include = entry.get("include")
            if include:
                names.append(str(include).split("/")[0])
        if roots:
            return _dedupe_paths(roots), sorted(set(names)), \
                "pyproject [tool.poetry] packages"

    return [], [], ""


def _split_package_paths(parent: Path, entries: list[str]) -> tuple[list[Path], list[str]]:
    """`["src/volforecast"]` -> root `src`, package `volforecast`."""
    roots, names = [], []
    for raw in entries:
        pp = PurePosixPath(raw.replace("\\", "/"))
        names.append(pp.name)
        roots.append(parent.joinpath(*pp.parts[:-1]) if len(pp.parts) > 1 else parent)
    return _dedupe_paths(roots), sorted(set(names))


def _cascade_roots(base: Path) -> tuple[list[Path], str]:
    """No declaration — infer, in the order that is right most often.

    The terminal case is the one that matters for the acceptance repos: a bag
    of loose scripts with no `__init__.py` anywhere still has to produce module
    names, and when a directory and its parent both hold `.py` files the
    SHALLOWEST wins, or `module_name` has two answers for one file.
    """
    src = base / "src"
    if src.is_dir():
        if not (src / "__init__.py").exists():
            return [src], "src/ layout — src holds no __init__.py"
        return [base], "src/ is itself a package"

    for child in sorted(p for p in base.iterdir() if p.is_dir()):
        if child.name in EXCLUDED_DIRS:
            continue
        if (child / "__init__.py").exists():
            return [base], "a top-level directory is a package"

    with_py = []
    for dirpath, _dirnames, filenames in _walk(base):
        if any(f.endswith(".py") for f in filenames):
            with_py.append(dirpath)
    roots = [d for d in with_py
             if not any(d != o and _within(d, o) for o in with_py)]
    if roots:
        return _dedupe_paths(roots), "no packages found — every directory holding .py is a root"
    return [base], "no .py found — repo root used as the import root"


def _test_roots(base: Path, pyproject: Path | None, data: dict,
                import_roots: list[Path]) -> list[Path]:
    """Declared `testpaths` if there are any, else the conventional names.

    The conventional search covers the repo base and the pyproject's directory
    as well as the import roots. Under a standard src-layout `tests/` sits
    OUTSIDE the import root by design, so searching only inside the roots finds
    nothing and the whole test tree loses its module names — which is the exact
    42% file loss this rule exists to prevent.
    """
    if pyproject is not None:
        paths = (data.get("tool", {}).get("pytest", {})
                     .get("ini_options", {}).get("testpaths"))
        if isinstance(paths, str):
            paths = [paths]
        if isinstance(paths, list) and paths:
            found = [pyproject.parent / str(p) for p in paths]
            found = [p for p in found if p.is_dir()]
            if found:
                return found

    out = []
    places = list(import_roots) + [base]
    if pyproject is not None:
        places.append(pyproject.parent)
    for place in _dedupe_paths(places):
        for name in ("tests", "test"):
            cand = place / name
            if cand.is_dir():
                out.append(cand)
    return _dedupe_paths(out)


def _packages_under(import_roots: list[Path], test_roots: list[Path]) -> list[str]:
    """Importable top-level package names, when nothing declares them.

    A test root is excluded even when it carries an `__init__.py`. It is a
    package by construction and not by intent, and admitting it produces a
    `python -c "import tests"` command candidate that proves nothing — observed
    on IMC-Prosperity-4, whose `tests/` sits directly under the repo root.
    """
    skip = {t.as_posix() for t in test_roots}
    names = set()
    for root in import_roots:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_dir() and child.name not in EXCLUDED_DIRS \
                    and child.as_posix() not in skip \
                    and (child / "__init__.py").exists():
                names.add(child.name)
    return sorted(names)


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """Order-stable dedupe, then sorted — walk order must not set behaviour."""
    seen, out = set(), []
    for p in paths:
        key = p.as_posix()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return sorted(out, key=lambda p: p.as_posix())


# --------------------------------------------------------------------------
# 3.3 The walk
# --------------------------------------------------------------------------

def _walk(base: Path):
    """`os.walk` with in-place prune and sorted names.

    Sorting before descending is what makes walk order — and therefore every
    id, tie-break and ranking built on it — identical on two machines.
    """
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if not _excluded_dir(d))
        filenames.sort()
        yield Path(dirpath), dirnames, filenames


def _excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIRS or name.endswith(".egg-info")


def walk_files(roots: Roots, out_path: Path | None) -> dict:
    """Every file in scope, in two scopes, plus the census the ledger shows.

    `py_in_scope` is `.py` under an import root — the only files parsed, named,
    mapped or anchored. `files_all` is everything else the walk saw, which is
    what makes the extension census and the doc-only-directory list honest.

    The `--out` path is excluded explicitly. Without that, a second run surveys
    the 76 KB HTML the first run wrote into the repo it is surveying.

    `skipped` records only files we actually tried to read — a NUL-sniffed
    binary named `.py`, or a path that escapes the root through a junction.
    Claiming to have classified 12.6 MB of files we never opened would be the
    kind of unearned number this tool exists to catch.
    """
    base = roots.repo_root
    out_resolved = out_path.resolve() if out_path is not None else None

    files_all: list[str] = []
    py_in_scope: list[str] = []
    text_files: list[str] = []
    skipped: list[dict] = []
    by_ext: dict[str, int] = {}
    excluded_dirs = 0
    dirs_seen: dict[str, dict] = {}

    for raw_dir, dirnames, filenames in os.walk(base):
        kept = sorted(d for d in dirnames if not _excluded_dir(d))
        excluded_dirs += len(dirnames) - len(kept)
        dirnames[:] = kept
        filenames.sort()
        dirpath = Path(raw_dir)

        stats = {"files": 0, "py": 0, "doc": 0}
        for name in filenames:
            path = dirpath / name
            rel = rel_key(path, base)
            if rel is None:
                skipped.append({"path": str(path), "reason": "outside root"})
                continue
            if out_resolved is not None and _same_file(path, out_resolved):
                continue

            files_all.append(rel)
            ext = path.suffix.lower().lstrip(".") or "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + 1
            stats["files"] += 1

            if name.endswith(".py"):
                stats["py"] += 1
                if any(_within(path, r) for r in roots.import_roots):
                    py_in_scope.append(rel)
                continue
            if path.suffix.lower() in _DOC_SUFFIXES:
                stats["doc"] += 1
            if _text_candidate(path):
                src = read_source(path)
                if src.note == "not text":
                    skipped.append({"path": rel, "reason": "not text"})
                elif not src.degraded and _admits_anchor(path, src):
                    text_files.append(rel)

        dirs_seen[rel_key(dirpath, base) or "."] = stats

    return {
        "files_all": sorted(files_all),
        "py_in_scope": sorted(py_in_scope),
        "text_files": sorted(text_files),
        "walk": {
            "scanned": len(files_all),
            "py_in_scope": len(py_in_scope),
            "excluded_dirs": excluded_dirs,
            "skipped": skipped,
            "by_ext": dict(sorted(by_ext.items(), key=lambda kv: (-kv[1], kv[0]))),
            "doc_only_dirs": _doc_only_dirs(dirs_seen),
        },
    }


def _same_file(path: Path, resolved_out: Path) -> bool:
    try:
        return path.resolve() == resolved_out
    except OSError:
        return False


def _text_candidate(path: Path) -> bool:
    """The §2 predicate, minus the decode check the caller performs.

    The extensionless clause is what admits `restored/vol`, a 22 KB bash script
    with a `#!` line that carries the best platform-claim anchor in the repo.
    """
    try:
        if path.stat().st_size >= MAX_TEXT_BYTES:
            return False
    except OSError:
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    if path.name in TEXT_NAMES:
        return True
    return not path.suffix


def _admits_anchor(path: Path, src) -> bool:
    """The decode half of the predicate: a suffix we trust, or a `#!` line."""
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
        return True
    return bool(src.lines) and src.lines[0].startswith("#!")


def _doc_only_dirs(dirs_seen: dict[str, dict]) -> list[str]:
    """Shallowest directories whose subtree is prose, not code.

    Useful orientation — `memory/`, `workspace/docs/`, `.github/` are 40% of
    `restored` by file count and none of it is the codebase. Only the shallowest
    qualifying directory is reported, or the list is a hundred rows of noise.
    """
    doc_only = set()
    for key, stats in dirs_seen.items():
        if key == ".":
            continue
        sub = [(k, v) for k, v in dirs_seen.items() if k == key or k.startswith(key + "/")]
        if any(v["py"] for _k, v in sub):
            continue
        if not any(v["doc"] for _k, v in sub):
            continue
        doc_only.add(key)
    shallow = [k for k in doc_only
               if not any(k != o and k.startswith(o + "/") for o in doc_only)]
    return sorted(shallow)[:20]


# --------------------------------------------------------------------------
# 3.4 Module mapping and the import classifier
# --------------------------------------------------------------------------

def module_name(rel_path: str, roots: Roots) -> tuple[str | None, Path | None, bool]:
    """-> (dotted | None, import_root | None, is_init)

    The LONGEST matching import root wins, so a file under both `base` and
    `base/src` is named from `src` and gets the short, importable name. A path
    part that is not an identifier (`2020-report.py`, `my-pkg/`) makes the file
    unnameable, not unlisted: it keeps its `loc` and its file record and simply
    cannot be an edge endpoint.

    `__init__.py` maps to its PACKAGE's dotted name, never `pkg.__init__` —
    `import pkg` must find it or every package in the repo reads as dangling.
    """
    path = roots.repo_root.joinpath(*rel_path.split("/"))
    best: tuple[Path, Path] | None = None
    for root in roots.import_roots:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if best is None or len(root.parts) > len(best[0].parts):
            best = (root, rel)
    if best is None:
        return None, None, False

    root, rel = best
    parts = list(rel.parts)
    is_init = parts[-1] == "__init__.py"
    parts = parts[:-1] if is_init else parts[:-1] + [parts[-1][:-3]]
    if not parts or not all(_is_name(p) for p in parts):
        return None, root, is_init
    return ".".join(parts), root, is_init


def _is_name(part: str) -> bool:
    return part.isidentifier() and not keyword.iskeyword(part)


def build_module_index(files: list[dict], roots: Roots) -> tuple[dict[str, str], dict[str, set[str]]]:
    """-> (dotted -> relpath, str(import_root) -> known-set). `known` is PER ROOT.

    Per-root scoping is not fussiness. `restored/skills/SECDB_INSPECT/src/inspect.py`
    is the module `inspect` — for files under its own root, and never anywhere
    else. One global set would shadow stdlib `inspect` across the whole repo and
    silently turn every `import inspect` into an internal edge.

    Also STAMPS `import_root`, `root_key`, `group` and `group_path` onto each
    file dict. `build_edges` needs the per-file root (to pick the right `known`
    set) and the directory rollup key, its signature takes no `roots`, and
    recomputing the mapping twice is how the two halves drift apart.
    """
    index: dict[str, str] = {}
    known: dict[str, set[str]] = {}

    for f in files:
        module, root, _is_init = module_name(f["path"], roots)
        f["import_root"] = rel_key(root, roots.repo_root) if root is not None else None
        f["root_key"] = str(root) if root is not None else ""
        f["group"], f["group_path"] = _group_of(f["path"], root, roots)
        if module is None or root is None:
            continue
        # First writer wins, deterministically, because `files` is path-sorted.
        # Dotted names DO collide — `inspect` appears twice in `restored` — and
        # node ids derive from the path for exactly that reason.
        index.setdefault(module, f["path"])
        known.setdefault(str(root), set()).add(module)

    return index, known


def _group_of(rel_path: str, root: Path | None, roots: Roots) -> tuple[str | None, str | None]:
    """The directory-level rollup key for one file, and that directory's path.

    `modules` in the contract is keyed by the containing PACKAGE, not by the
    file's own dotted name: `src/volforecast/data/ohlcv.py` rolls up under
    `volforecast.data`. A file sitting directly in an import root has no package
    above it, so its group is `"."` — which is also the label the map draws for
    a flat repo like `ryanatron-v2`.
    """
    if root is None:
        return None, None
    path = roots.repo_root.joinpath(*rel_path.split("/"))
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None, None
    parts = list(rel.parts[:-1])
    if not parts:
        return ".", rel_key(root, roots.repo_root)
    if not all(_is_name(p) for p in parts):
        return None, None
    return ".".join(parts), rel_key(root.joinpath(*parts), roots.repo_root)


def parse_imports(source, module):
    """Every module this source depends on, as absolute dotted names.

    `module` is the dotted name of the file being parsed, needed to resolve
    relative imports. Names are emitted at their most specific — a
    `from pkg import thing` yields `pkg.thing` whether `thing` is a submodule or
    a symbol, because one file cannot tell the difference. Edge resolution picks
    the longest prefix that is a real module.

    Now a projection of `extract_imports` so there is exactly one ast walk and
    one relative-import rule. The contract and the four tests are unchanged.
    """
    return [ref.dotted for ref in extract_imports(source, module)]


def resolve_import(dotted, known):
    """The internal module a dotted import name refers to, or None if external.

    Walks prefixes longest-first, so `pkg.sub.helpers.fn` lands on the module
    `pkg.sub.helpers` rather than the package `pkg`. Anything with no known
    prefix is a third-party dependency and is not a node on the map.

    Kept for its stated contract and its tests. Survey itself uses
    `classify_import`, because "longest known prefix" re-points an import of a
    module that does not exist at its nearest existing ancestor — 700 phantom
    edges on `restored`, 27.4% of everything it calls internal.
    """
    parts = dotted.split(".")
    for n in range(len(parts), 0, -1):
        candidate = ".".join(parts[:n])
        if candidate in known:
            return candidate
    return None


def extract_imports(source: str, module: str, is_init: bool = False) -> list[ImportRef]:
    """Every import statement in one file, with relative levels already resolved.

    For a package's `__init__.py`, `level=1` means the package ITSELF, not its
    parent — `from . import x` inside `pkg/__init__.py` is `pkg.x`, and treating
    it like a module would make it `x`. `restored/` has 2560 ImportFrom nodes
    and every one is `level == 0`, so nothing in the demo exercises this and the
    unit tests are the only guard there will ever be.
    """
    out: list[ImportRef] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(ImportRef(alias.name, None, 0, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = module.split(".")
                if not is_init:
                    parts = parts[:-1]
                if node.level > 1:
                    parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join(parts + ([base] if base else []))
            for alias in node.names:
                out.append(ImportRef(base, alias.name, node.level, node.lineno))
    return out


def classify_import(ref: ImportRef, module: str, is_init: bool,
                    known: set[str]) -> tuple[str, str | None]:
    """-> ('internal'|'dangling'|'external', target_module_or_root)

    Dangling is the whole reason this function exists instead of
    `resolve_import`. An import whose top-level name belongs to this repo but
    whose module has no file on disk is a broken reference, and calling it an
    edge to the nearest existing ancestor invents a dependency that is not
    there. On `restored` that is 706 statements across 14 targets — and it is
    also the most interesting true fact the tool finds about the repo.
    """
    dotted = ref.dotted
    if dotted in known:
        return "internal", dotted

    if ref.name is not None and ref.base in known:
        # `from a.b import c` where a.b exists and c is a symbol, not a module.
        return "internal", ref.base

    target = ref.base if ref.name is not None else dotted
    root = target.split(".")[0]
    if root in known:
        return "dangling", target
    return "external", root


# --------------------------------------------------------------------------
# 3.5 Per-file extraction — one walk, everything at once
# --------------------------------------------------------------------------

def extract_module(path: Path, rel_path: str, module: str, is_init: bool) -> dict:
    """One `ast.parse`, everything survey will ever need from this file.

    A file that will not parse is COUNTED, not fatal: `parsed=False`, the error
    recorded with its line and offset, `loc` and the file record kept. A repo
    with one bad file still gets a walkthrough — and the bad file becomes a
    visible fact in the ledger instead of a stack trace at hour 9.
    """
    src = read_source(path)
    text = src.text()
    rec = {
        "path": rel_path,
        "module": module,
        "is_init": is_init,
        "loc": len(src.lines),
        "size": len(text.encode("utf-8")),
        "sha1": hashlib.sha1(text.encode("utf-8")).hexdigest(),
        "encoding": src.encoding,
        "degraded": src.degraded,
        "parsed": False,
        "doc": None,
        "defs": [],
        "all": None,
        "main_guard": None,
        "argparse_lines": [],
        "subcommands": [],
        "app_objects": [],
        "imports": [],
        "error": None,
        # Churn fills these in later, or leaves them null and says why.
        "commits": None,
        "last_commit": None,
        "authors": [],
    }

    if src.note == "not text":
        rec["error"] = {"path": rel_path, "line": 0, "offset": 0, "msg": "not text"}
        return rec

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        rec["error"] = {"path": rel_path, "line": exc.lineno or 0,
                        "offset": exc.offset or 0, "msg": exc.msg}
        return rec
    except ValueError as exc:
        # `source code string cannot contain null bytes`, and friends.
        rec["error"] = {"path": rel_path, "line": 0, "offset": 0, "msg": str(exc)}
        return rec

    rec["parsed"] = True
    doc = ast.get_docstring(tree)
    if doc:
        rec["doc"] = doc.strip().split("\n")[0][:200]
    rec["defs"] = _defs(tree)
    rec["all"] = _dunder_all(tree)
    rec["imports"] = extract_imports(text, module or "", is_init)
    rec["main_guard"] = _main_guard(tree)
    rec["argparse_lines"], rec["subcommands"] = _argparse_signals(tree)
    rec["app_objects"] = _app_objects(tree)
    return rec


def _defs(tree: ast.Module) -> list[dict]:
    """Top-level and one-level-nested defs. Not a call graph, deliberately.

    One nesting level is what makes methods visible without making the list a
    parse tree. `start` includes decorators, because an anchor that opens at
    `def handle(` when line 107 is `@register` shows the reader half a fact.
    """
    out: list[dict] = []

    def record(node, owner):
        start = node.lineno
        for dec in getattr(node, "decorator_list", []):
            start = min(start, dec.lineno)
        kind = ("class" if isinstance(node, ast.ClassDef)
                else "method" if owner
                else "async function" if isinstance(node, ast.AsyncFunctionDef)
                else "function")
        doc = ast.get_docstring(node)
        out.append({
            "name": node.name,
            "kind": kind,
            "start": start,
            "end": getattr(node, "end_lineno", node.lineno) or node.lineno,
            "doc": doc.strip().split("\n")[0][:200] if doc else None,
            "public": not node.name.startswith("_"),
            "args": [a.arg for a in getattr(getattr(node, "args", None), "args", [])],
            "class": owner,
        })

    holders = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in tree.body:
        if not isinstance(node, holders):
            continue
        record(node, None)
        if len(out) >= MAX_DEFS_PER_FILE:
            break
        for child in node.body:
            if isinstance(child, holders):
                record(child, node.name)
                if len(out) >= MAX_DEFS_PER_FILE:
                    break
        if len(out) >= MAX_DEFS_PER_FILE:
            break
    return out[:MAX_DEFS_PER_FILE]


def _dunder_all(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            continue
        if isinstance(node.value, (ast.List, ast.Tuple)):
            return [e.value for e in node.value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return None


def _main_guard(tree: ast.Module) -> int | None:
    """The lineno of a module-level `if __name__ == "__main__":`."""
    for node in tree.body:
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        left = node.test.left
        comparators = node.test.comparators
        if isinstance(left, ast.Name) and left.id == "__name__" and comparators:
            right = comparators[0]
            if isinstance(right, ast.Constant) and right.value == "__main__":
                return node.lineno
    return None


def _argparse_signals(tree: ast.Module) -> tuple[list[int], list[str]]:
    """ArgumentParser construction sites, and every literal `add_parser("…")`.

    The subcommand names are the generic version of this repo's
    `def register(subparsers)` convention: 22 real subcommands here, and the
    same code works on any argparse project.
    """
    lines, subs = [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else \
            func.id if isinstance(func, ast.Name) else None
        if name == "ArgumentParser":
            lines.append(node.lineno)
        elif name == "add_parser" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                subs.append(first.value)
    return sorted(set(lines)), subs


def _app_objects(tree: ast.Module) -> list[dict]:
    """Module-level `app = FastAPI()` and friends — entry-point rule 4."""
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        framework = None
        if isinstance(func, ast.Name) and func.id in _APP_FACTORIES:
            framework = func.id
        elif isinstance(func, ast.Attribute):
            if func.attr in _APP_FACTORIES:
                framework = func.attr
            elif func.attr == "Group" and isinstance(func.value, ast.Name) \
                    and func.value.id == "click":
                framework = "click"
        if framework is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                out.append({"name": target.id, "line": node.lineno,
                            "framework": framework})
    return out


# --------------------------------------------------------------------------
# 3.4 (cont.) Edges
# --------------------------------------------------------------------------

def build_edges(files: list[dict], index: dict[str, str],
                known_by_root: dict[str, set[str]]) -> dict:
    """-> {"edges", "internal", "dangling", "external", …}

    `internal` counts import STATEMENTS and is what the §3.2 self-check reads.
    `edges` are between directory-level groups, which is what the contract's
    `modules` keys are; self-edges are dropped because the map drops them and
    an intra-package import is not an architectural fact about the repo.

    `fan_in` is per FILE and counts distinct importing files — 588 distinct
    file-level edges on `restored`, `registry.py` at 70. It is the churn
    substitute (decision #18) and the ranking behind every `top[]` string.
    """
    internal = external = self_edges = 0
    dangling: dict[str, dict] = {}
    externals: dict[str, int] = {}
    pairs: set[tuple[str, str]] = set()
    weights: dict[tuple[str, str], int] = {}
    group_path: dict[str, str] = {}

    by_path = {f["path"]: f for f in files}
    for f in files:
        if f.get("group") and f.get("group_path"):
            group_path.setdefault(f["group"], f["group_path"])

    for f in files:
        known = known_by_root.get(f.get("root_key", ""), set())
        for ref in f["imports"]:
            kind, target = classify_import(ref, f["module"] or "", f["is_init"], known)
            if kind == "external":
                external += 1
                if target:
                    externals[target] = externals.get(target, 0) + 1
                continue
            if kind == "dangling":
                entry = dangling.setdefault(target, {"target": target, "n": 0, "sites": []})
                entry["n"] += 1
                entry["sites"].append({"file": f["path"], "line": ref.line})
                continue

            internal += 1
            dst = index.get(target)
            if dst is None or dst == f["path"]:
                continue
            pairs.add((f["path"], dst))
            a, b = f.get("group"), by_path[dst].get("group")
            if not a or not b:
                continue
            if a == b:
                self_edges += 1
                continue
            weights[(a, b)] = weights.get((a, b), 0) + 1

    fan_in: dict[str, int] = {}
    fan_out: dict[str, int] = {}
    for src, dst in pairs:
        fan_in[dst] = fan_in.get(dst, 0) + 1
        fan_out[src] = fan_out.get(src, 0) + 1

    edges = [{"a": a, "b": b, "n": n} for (a, b), n in
             sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))]

    return {
        "edges": edges,
        "internal": internal,
        "external": external,
        "self_edges": self_edges,
        "dangling": sorted(dangling.values(), key=lambda d: (-d["n"], d["target"])),
        "external_deps": sorted(name for name in externals
                                if name not in sys.stdlib_module_names),
        "external_counts": externals,
        "fan_in": fan_in,
        "fan_out": fan_out,
        "file_edges": len(pairs),
        "group_path": group_path,
    }


# --------------------------------------------------------------------------
# 3.6 Git churn — three states, literal argv
# --------------------------------------------------------------------------

def _git(argv: list[str]) -> tuple[int | None, str]:
    """Run one git command. Bytes in, utf-8/replace out, returncode checked.

    `rc is None` means git never ran — no binary, or it hung past the timeout.
    That is a different fact from "git ran and said no", and the state machine
    below needs to tell them apart.
    """
    try:
        proc = subprocess.run(argv, shell=False, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=GIT_TIMEOUT)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None, ""
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def git_state(repo_root: Path) -> GitState:
    """Which of the four git worlds this path lives in.

    `GIT_UNTRACKED` is not an edge case — it is the DEFAULT path for the
    proving-ground repo, which sits inside the ML-GS work tree with zero tracked
    files of its own. Verified: `rev-parse --is-inside-work-tree` says `true`,
    `log -1 -- .` is empty, `ls-files -- .` is empty. A two-state probe reports
    "git available" here and then attributes the enclosing repository's history
    to files that do not exist in this directory.
    """
    root = str(repo_root)

    rc, _ = _git(["git", "-C", root, "rev-parse", "--is-inside-work-tree"])
    if rc is None:
        return GitState("NO_GIT", None, "", None,
                        "git is not on PATH, or did not answer within "
                        f"{GIT_TIMEOUT}s")
    if rc != 0:
        return GitState("NO_GIT", None, "", None,
                        "the target path is not inside a git work tree")

    rc, out = _git(["git", "-C", root, "rev-parse", "--show-toplevel"])
    if rc != 0:
        return GitState("GIT_ERROR", None, "", None,
                        f"git rev-parse --show-toplevel exited {rc}")
    toplevel = Path(out.strip()) if out.strip() else None

    rc, out = _git(["git", "-C", root, "rev-parse", "--show-prefix"])
    prefix = out.strip() if rc == 0 else ""

    rc_branch, branch_out = _git(["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_out.strip() if rc_branch == 0 else ""
    if branch in ("", "HEAD"):
        branch = None

    rc, out = _git(["git", "-C", root, "log", "-1", "--format=%H", "--", "."])
    if rc != 0:
        return GitState("GIT_UNTRACKED", toplevel, prefix, None,
                        "the repository has no commits yet", branch)
    head = out.strip() or None
    if head is None:
        rc_ls, ls = _git(["git", "-C", root, "ls-files", "-z", "--", "."])
        tracked = len([p for p in ls.split("\0") if p]) if rc_ls == 0 else 0
        return GitState("GIT_UNTRACKED", toplevel, prefix, None,
                        "target path has no tracked history in the enclosing "
                        f"repository ({tracked} tracked files)", branch)

    return GitState("GIT_OK", toplevel, prefix, head,
                    "git history available for this path", branch)


def churn_argv(repo_root: Path, since_days: int) -> list[str]:
    """The churn command, as the exact argv list that was verified to work.

    Three things about it, each learned by running the wrong version:

    1. `"--"` and `"."` are two SEPARATE elements. `"-- ."` as one element gives
       `rc=128, fatal: unrecognized argument: -- .`, which a returncode-blind
       caller reads as "no history" — so every repo with real git history
       silently falls back to fan-in.
    2. The pathspec is MANDATORY. Without it, running inside `restored/` returns
       the enclosing ML-GS repository's history at exit 0, naming files that do
       not exist under the target. For a tool whose pitch is that the machine
       checks the facts, that is the worst available failure.
    3. `-c core.quotepath=false` is MANDATORY. quotepath defaults to true and is
       unset on this machine, so any path with a non-ASCII byte comes back
       C-quoted (`"caf\\303\\251.py"`), fails the existence check, and vanishes
       from the ranking without a word.
    """
    return ["git", "-c", "core.quotepath=false", "-C", str(repo_root), "log",
            f"--since={since_days}.days", "--pretty=format:%x01%h%x02%an",
            "--name-only", "--", "."]


def git_churn(repo_root: Path, st: GitState, since_days: int) -> dict:
    """Commits per file, or an honest statement of why there are none.

    When history is unavailable the substitute is fan-in (decision #18) and the
    caller must label it as such everywhere it surfaces — the page's drawer
    heading is hard-coded MOST-EDITED FILES, so an unlabelled fan-in ranking
    makes the artifact assert something false about the repo.

    `last_commit` is null even under GIT_OK: the plan pins the pretty-format to
    `%x01%h%x02%an`, which carries no date, and inventing one from a second
    traversal is a cost with no consumer. The field stays in the contract and
    stays honest.
    """
    base = {
        "state": st.state,
        "available": False,
        "reason": st.reason,
        "substitute": "fan_in",
        "by_file": {},
        "committers": {},
        "discarded_paths": 0,
        "since_days": since_days,
    }
    if st.state != "GIT_OK":
        return base

    rc, out = _git(churn_argv(repo_root, since_days))
    if rc != 0:
        base["state"] = "GIT_ERROR"
        base["reason"] = f"git log exited {rc} for this path"
        return base

    by_file: dict[str, dict] = {}
    committers: dict[str, int] = {}
    discarded = 0
    author = None
    seen_commit = set()

    for line in out.split("\n"):
        if line.startswith("\x01"):
            head, _, author = line[1:].partition("\x02")
            if head not in seen_commit:
                seen_commit.add(head)
                committers[author] = committers.get(author, 0) + 1
            continue
        path = line.strip()
        if not path:
            continue
        # Every path git prints is relative to the TOP of the work tree, not to
        # the directory we asked about. Re-anchor, then require the file to
        # still exist — which is what drops deletes and rename ghosts.
        if st.prefix and not path.startswith(st.prefix):
            discarded += 1
            continue
        rel = path[len(st.prefix):] if st.prefix else path
        if not (repo_root / rel).exists():
            discarded += 1
            continue
        entry = by_file.setdefault(rel, {"commits": 0, "last_commit": None,
                                         "authors": []})
        entry["commits"] += 1
        if author and author not in entry["authors"]:
            entry["authors"].append(author)

    base.update({
        "available": bool(by_file),
        "substitute": None if by_file else "fan_in",
        "by_file": dict(sorted(by_file.items())),
        "committers": dict(sorted(committers.items(), key=lambda kv: (-kv[1], kv[0]))),
        "discarded_paths": discarded,
    })
    if not by_file:
        base["reason"] = ("git history exists but no commit in the last "
                          f"{since_days} days touched a file under this path")
    return base


def repo_id(st: GitState, files: list[dict]) -> dict:
    """The identity half of the `repo` block — `commit` and `branch`.

    `name`, `root` and `surveyed_at` are added by `survey()`, which is the only
    thing that knows the path the user pointed at.

    With no usable history the commit is `nogit-<8 hex>` over every in-scope
    file's (path, size, content hash). It MUST change when the tree changes:
    the page keys localStorage `trailhead:<name>:<commit>`, so a stale id leaves
    a reader's old progress sitting on a regenerated walkthrough.

    `branch` goes null with it. `restored/` sits inside a work tree checked out
    on `main`, but `main` is the enclosing repository's branch and nothing in
    this directory is on it — printing it beside a `nogit-` commit would be the
    tool asserting a fact it does not have.
    """
    if st.state == "GIT_OK" and st.head:
        return {"commit": st.head[:7], "branch": st.branch}

    digest = hashlib.sha1()
    for f in sorted(files, key=lambda r: r["path"]):
        digest.update(f"{f['path']}\0{f['size']}\0{f['sha1']}\n".encode("utf-8"))
    return {"commit": "nogit-" + digest.hexdigest()[:8], "branch": None}


def repo_name(roots: Roots) -> str:
    """What the project calls ITSELF, falling back to the directory name.

    The directory a repo happens to be checked out into is an accident of the
    reader's disk, not a fact about the project. On the proving-ground repo the
    checkout is `restored/` while `src/pyproject.toml` declares
    `name = "volforecast"` and every module under it is `volforecast.*` — so the
    directory name puts a word on the cover page that appears nowhere else in
    the walkthrough and reads as an unfilled placeholder.

    A declared name is a fact with a file and a line behind it, which is the
    standard everything else here is held to, so it wins whenever one exists.
    `[project] name` (PEP 621) first, then poetry's, then the directory —
    which is still correct for the large number of repos that declare nothing.
    """
    if roots.pyproject is not None:
        data = _load_toml(roots.pyproject)
        for path in (["project", "name"], ["tool", "poetry", "name"]):
            declared = _dig(data, path)
            if isinstance(declared, str) and declared.strip():
                return declared.strip()
    # A drive root (`C:/`) has an empty `.name`; nothing is better than the
    # path itself there, and an empty repo name breaks the localStorage key.
    return roots.repo_root.name or roots.repo_root.as_posix()


# --------------------------------------------------------------------------
# 3.7 Entry points
# --------------------------------------------------------------------------

def toml_line(lines: list[str], table: str, key: str | None = None) -> int | None:
    """The 1-based line of `[table]`, or of `key = …` inside it.

    `tomllib` returns no line numbers and an anchor without a line number is not
    an anchor. Scanning the normalised lines for the header and then for the
    key is exact for every pyproject shape that matters; when it finds nothing
    the caller emits the claim as `inferred` with NO anchor rather than guessing
    a plausible number, which is the one failure this whole tool exists to stop.
    """
    header = "[" + table + "]"
    start = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            start = i
            break
    if start is None:
        return None
    if key is None:
        return start + 1

    pattern = re.compile(r"^\s*(?:\"%s\"|'%s'|%s)\s*=" % ((re.escape(key),) * 3))
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            break
        if pattern.match(lines[j]):
            return j + 1
    return start + 1


def entry_points(roots: Roots, files: list[dict], fan_in: dict[str, int]) -> list[dict]:
    """Every way into this repo, ranked, each one citable.

    Scoping is what makes rule 5 usable. Unscoped, `if __name__ == "__main__"`
    reports 91 candidates on `restored` — 36 in `skills/`, 48 in `workspace/`,
    40 of those using `sys.path.insert` and statically unresolvable. Scoped to
    the import roots it reports the correct 6, ranked by fan-in and capped at 5.

    Call this AFTER `build_module_index`, which is what stamps `import_root` on
    the file records; without it rule 5 has nothing to scope against and
    silently reports no main guards at all.
    """
    out: list[dict] = []
    by_path = {f["path"]: f for f in files}

    pyproject_rel = rel_key(roots.pyproject, roots.repo_root) if roots.pyproject else None
    if roots.pyproject is not None:
        src = read_source(roots.pyproject)
        data = _load_toml(roots.pyproject)
        for table in ("project.scripts", "project.gui-scripts", "tool.poetry.scripts"):
            scripts = _dig(data, table.split("."))
            if not isinstance(scripts, dict):
                continue
            for name, target in sorted(scripts.items()):
                out.append({
                    "kind": "console_script",
                    "name": name,
                    "file": pyproject_rel,
                    "line": toml_line(src.lines, table, name),
                    "target": str(target),
                    "confidence": "high",
                    "provenance": f"{pyproject_rel} [{table}]",
                })

    setup = roots.repo_root / "setup.py"
    if setup.is_file():
        lines = read_source(setup).lines
        for i, line in enumerate(lines):
            m = re.match(r"""^\s*['"]([\w.-]+)\s*=\s*([\w.]+:[\w.]+)['"]""", line)
            if m:
                out.append({
                    "kind": "console_script",
                    "name": m.group(1),
                    "file": rel_key(setup, roots.repo_root),
                    "line": i + 1,
                    "target": m.group(2),
                    "confidence": "medium",
                    "provenance": f"setup.py:{i + 1}",
                })

    for pkg in roots.declared_packages:
        for root in roots.import_roots:
            main = root / pkg / "__main__.py"
            if not main.is_file():
                continue
            rel = rel_key(main, roots.repo_root)
            out.append({
                "kind": "module_main",
                "name": f"python -m {pkg}",
                "file": rel,
                "line": 1,
                "target": f"{pkg}.__main__",
                "confidence": "high",
                "provenance": f"{rel} exists — python -m {pkg} runs it",
            })

    for path in sorted(by_path):
        for app in by_path[path]["app_objects"]:
            out.append({
                "kind": "http_route",
                "name": f"{app['name']} = {app['framework']}()",
                "file": path,
                "line": app["line"],
                "target": app["name"],
                "confidence": "medium",
                "provenance": f"{path}:{app['line']}",
            })

    guards = [f for f in files if f["main_guard"] and f.get("import_root")]
    guards.sort(key=lambda f: (-fan_in.get(f["path"], 0), f["path"]))
    for f in guards[:5]:
        out.append({
            "kind": "main_guard",
            "name": f["path"],
            "file": f["path"],
            "line": f["main_guard"],
            "target": f["module"] or f["path"],
            "confidence": "low",
            "provenance": f"{f['path']}:{f['main_guard']}",
        })

    return out


def _dig(data: dict, path: list[str]):
    node = data
    for part in path:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


# --------------------------------------------------------------------------
# 3.8 Command discovery — candidates only, nothing is executed here
# --------------------------------------------------------------------------

def resolve_interpreter(repo_root: Path) -> str:
    """The python that will actually run, resolved ONCE per repo.

    Never bare `python`: on this box `where python3` answers with the Microsoft
    Store alias in `…/AppData/Local/Microsoft/WindowsApps/`, which is not an
    interpreter — it exits without running anything, or opens the Store. The
    plan's cascade lands on it here, so the alias directory is filtered out by
    name and the search continues. A repo-local venv wins outright, because a
    repo carrying a venv is a repo whose dependencies are inside it.
    """
    for rel in (".venv/Scripts/python.exe", ".venv/bin/python"):
        cand = repo_root.joinpath(*rel.split("/"))
        if cand.is_file():
            return str(cand)
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and "windowsapps" not in found.replace("\\", "/").lower():
            return found
    return sys.executable


def command_candidates(roots: Roots, files: list[dict], text_files: list[str],
                       interp: str) -> list[dict]:
    """Commands this repo says it supports. NOTHING is run here.

    `cmd` is canonical and load-bearing: `commands.json` records runs by it and
    `verify.py` merges command blocks by `(cmd, cwd)`. One string, three
    producers — so `argv` is derived FROM `cmd`, never the reverse, and the
    display string keeps saying `python` while argv carries the real path.
    """
    out: list[dict] = []
    pyproject_rel = rel_key(roots.pyproject, roots.repo_root) if roots.pyproject else None
    data = _load_toml(roots.pyproject) if roots.pyproject else {}
    lines = read_source(roots.pyproject).lines if roots.pyproject else []

    import_root_rel = (rel_key(roots.import_roots[0], roots.repo_root)
                       if roots.import_roots else ".")

    for pkg in roots.declared_packages[:2]:
        line = (toml_line(lines, "tool.hatch.build.targets.wheel", "packages")
                or toml_line(lines, "project", "name"))
        out.append(_candidate(
            f'python -c "import {pkg}"', "run", import_root_rel,
            f"{pyproject_rel}:{line}" if pyproject_rel and line else "package layout",
            "high", interp))

    scripts = _dig(data, ["project", "scripts"]) or {}
    if isinstance(scripts, dict):
        for name, target in sorted(scripts.items()):
            pkg = str(target).split(".")[0].split(":")[0]
            if not pkg:
                continue
            line = toml_line(lines, "project.scripts", name)
            out.append(_candidate(
                f"python -m {pkg} --help", "run", import_root_rel,
                f"{pyproject_rel}:{line}" if pyproject_rel and line else "pyproject",
                "high", interp))

    if roots.test_roots:
        cwd = (rel_key(roots.pyproject.parent, roots.repo_root)
               if roots.pyproject else ".")
        rels = []
        for t in roots.test_roots:
            base = roots.pyproject.parent if roots.pyproject else roots.repo_root
            try:
                rels.append(t.relative_to(base).as_posix())
            except ValueError:
                rels.append(rel_key(t, roots.repo_root) or ".")
        line = toml_line(lines, "tool.pytest.ini_options", "testpaths")
        cand = _candidate(
            "python -m pytest --collect-only -q " + " ".join(rels), "test",
            cwd or ".",
            f"{pyproject_rel}:{line}" if pyproject_rel and line else "tests/ exists",
            "high", interp)
        if not _importable(interp, "pytest"):
            cand["allowed"] = False
            cand["deny_reason"] = "pytest not importable under the resolved interpreter"
        out.append(cand)

    for rel in text_files:
        if not rel.endswith(".pre-commit-config.yaml"):
            continue
        # A line regex, not a YAML parse: PyYAML is a dependency and parsing
        # destroys the line numbers that the provenance string and the anchor
        # both need.
        src = read_source(roots.repo_root.joinpath(*rel.split("/")))
        hook = None
        for i, line in enumerate(src.lines):
            m_id = re.match(r"^\s*-?\s*id:\s*(.+)$", line)
            if m_id:
                hook = m_id.group(1).strip()
            m_entry = re.match(r"^\s*entry:\s*(.+)$", line)
            if m_entry:
                out.append(_candidate(
                    m_entry.group(1).strip(), "lint", ".",
                    f"{rel}:{i + 1} hook {hook or '?'} entry", "medium", interp))

    return out


def _candidate(cmd: str, kind: str, cwd: str, source: str, confidence: str,
               interp: str) -> dict:
    """One candidate, with argv derived from the canonical `cmd` string."""
    try:
        argv = shlex.split(cmd, posix=True)
    except ValueError:
        argv = cmd.split()
    if argv and argv[0] in ("python", "python3"):
        argv[0] = interp
    return {
        "cmd": cmd,
        "kind": kind,
        "cwd": cwd or ".",
        "source": source,
        "confidence": confidence,
        "argv": argv,
        "allowed": True,
        "deny_reason": None,
    }


def _importable(interp: str, module: str) -> bool:
    """Can the resolved interpreter import this? Verified, never assumed.

    `py -3.11` on this machine has torch and no pytest; `py -3.12` has pytest
    and no torch. Emitting a test command that cannot possibly run, and then
    showing it fail with ModuleNotFoundError, would be a self-inflicted red.
    """
    try:
        proc = subprocess.run([interp, "-c", f"import {module}"], shell=False,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


# --------------------------------------------------------------------------
# The stage
# --------------------------------------------------------------------------

def survey(repo_root: Path, *, since_days: int = 365,
           out_path: Path | None = None) -> dict:
    """Run stage 1 and return `survey.json` as a dict. Writing it is the CLI's job.

    Everything here is deterministic and re-runnable: read + `ast.parse` over
    all 455 files of `restored` is 917 ms, so there is no cache, no parallelism
    and no incremental mode to be wrong about. Treat the output as disposable.

    `checkpoints` is emitted EMPTY on purpose. §2 splits answer-key derivation
    into two passes and the second one needs `map.json`, so `checkpoints.py`
    owns both passes and rewrites this file after stage 2. Non-negotiable #6
    still holds either way — the map is deterministic code and no model is
    involved in either pass.
    """
    started = datetime.now(timezone.utc)
    root = Path(repo_root).resolve()
    roots = discover_roots(root)
    walked = walk_files(roots, out_path)

    files: list[dict] = []
    for rel in walked["py_in_scope"]:
        module, _root, is_init = module_name(rel, roots)
        files.append(extract_module(root.joinpath(*rel.split("/")), rel, module, is_init))

    index, known_by_root = build_module_index(files, roots)
    graph = build_edges(files, index, known_by_root)

    # The one check that catches a wrong source root. A wrong root does not
    # crash — it produces an empty graph and a walkthrough that says nothing.
    if len(files) > 50 and graph["internal"] == 0:
        raise SourceRootError(_root_error_message(root, roots, files, walked))

    # Per-FILE fan-in rides on the file record because nothing downstream can
    # recover it: `edges` are between directory groups, and `cp-a1`'s answer
    # key is a single file (`volforecast.registry`, fan-in 70) picked out of a
    # repo-wide ranking. Recomputing it in checkpoints.py would be a second
    # implementation of the classifier.
    for f in files:
        f["fan_in"] = graph["fan_in"].get(f["path"], 0)
        f["fan_out"] = graph["fan_out"].get(f["path"], 0)

    st = git_state(root)
    churn = git_churn(root, st, since_days)
    for f in files:
        entry = churn["by_file"].get(f["path"])
        if entry:
            f["commits"] = entry["commits"]
            f["last_commit"] = entry["last_commit"]
            f["authors"] = list(entry["authors"])

    modules = _rollup(files, graph, churn)
    ident = repo_id(st, files)
    interp = resolve_interpreter(root)

    degradations = []
    if not churn["available"]:
        degradations.append({
            "code": "no_churn",
            "reason": churn["reason"],
            "substitute": "fan-in",
        })

    # A PNG named `.py` is not a parse failure — it is a file we declined to
    # read, and §9 counts those on a different row. Keeping them apart is what
    # stops "1 parse failure" appearing in the ledger for a repo whose Python
    # all parses.
    parse_failures = []
    for f in files:
        if not f["error"]:
            continue
        if f["error"]["msg"] == "not text":
            walked["walk"]["skipped"].append({"path": f["path"], "reason": "not text"})
        else:
            parse_failures.append(f["error"])
    stdlib_shadowed = sorted({
        m.split(".")[0] for names in known_by_root.values() for m in names
        if m.split(".")[0] in sys.stdlib_module_names
    })

    return {
        "contract": "trailhead/survey@1",
        "repo": {
            "name": repo_name(roots),
            # Additive, and the reason it exists: `name` is no longer the
            # checkout's directory name, so anything that keyed off the
            # directory — a per-repo fixture looked up by name, a cache dir —
            # needs the directory back under its own key rather than guessing
            # which of the two `name` currently means.
            "dir": root.name,
            "root": root.as_posix(),
            "commit": ident["commit"],
            "branch": ident["branch"],
            "surveyed_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "stats": {
            "files": walked["walk"]["scanned"],
            "py_files": walked["walk"]["by_ext"].get("py", 0),
            "loc": sum(f["loc"] for f in files),
            "modules": len(index),
            "external_deps": graph["external_deps"],
        },
        "roots": {
            "repo_root": root.as_posix(),
            "import_roots": [rel_key(p, root) for p in roots.import_roots],
            "test_roots": [rel_key(p, root) for p in roots.test_roots],
            "pyproject": rel_key(roots.pyproject, root) if roots.pyproject else None,
            "declared_packages": roots.declared_packages,
            "rule": roots.rule,
        },
        "walk": walked["walk"],
        "files": [_file_record(f) for f in files],
        "modules": modules,
        "edges": graph["edges"],
        "dangling": graph["dangling"],
        "parse_failures": parse_failures,
        "churn": churn,
        "stdlib_shadowed": stdlib_shadowed,
        "text_files": walked["text_files"],
        "entry_points": entry_points(roots, files, graph["fan_in"]),
        "argparse_sites": [{"file": f["path"], "line": n}
                           for f in files for n in f["argparse_lines"]],
        "command_candidates": command_candidates(
            roots, files, walked["text_files"], interp),
        "interpreter": interp,
        "checkpoints": {},
        "degradations": degradations,
        "counts": {
            "internal_imports": graph["internal"],
            "dangling_imports": sum(d["n"] for d in graph["dangling"]),
            "dangling_targets": len(graph["dangling"]),
            "external_imports": graph["external"],
            "file_edges": graph["file_edges"],
            "parse_failures": len(parse_failures),
        },
    }


def _file_record(f: dict) -> dict:
    """The JSON-safe projection of one file.

    `imports` and `known` stay in memory: ImportRef is a dataclass, `known` is a
    set, and neither survives `json.dump`. Everything a downstream stage needs —
    the defs a prompt window is cut from, the linenos an entry point cites — is
    here.
    """
    keep = ("path", "module", "loc", "commits", "last_commit", "authors",
            "is_init", "parsed", "doc", "defs", "all", "main_guard",
            "argparse_lines", "subcommands", "app_objects", "sha1", "size",
            "encoding", "degraded", "import_root", "group", "group_path",
            "fan_in", "fan_out")
    return {k: f.get(k) for k in keep}


def _rollup(files: list[dict], graph: dict, churn: dict) -> dict:
    """The directory-level `modules` map, with `top[]` labelled for its source.

    `top` is never empty. Rank, drop sub-20-loc `__init__.py` files, and if that
    empties the list fall back to the unfiltered ranking — the group keyed
    `volforecast` on `restored` is one 8-line `__init__.py` with the highest
    fan-in in the repo (92), it sits at the far right of the map where it is the
    first node anyone clicks, and a bare exclusion renders it with an empty
    MOST-EDITED FILES heading.
    """
    available = churn["available"]
    label = "commits" if available else "fan_in"
    out: dict[str, dict] = {}

    for f in files:
        group = f.get("group")
        if not group:
            continue
        entry = out.setdefault(group, {
            "path": f.get("group_path") or group,
            "files": 0, "loc": 0, "commits": 0 if available else None,
            "top": [], "_members": [],
        })
        entry["files"] += 1
        entry["loc"] += f["loc"]
        if available:
            entry["commits"] += f["commits"] or 0
        entry["_members"].append(f)

    for entry in out.values():
        members = entry.pop("_members")
        ranked = sorted(
            members,
            key=lambda f: (-(f["commits"] or 0) if available
                           else -graph["fan_in"].get(f["path"], 0),
                           -f["loc"], f["path"]),
        )
        filtered = [f for f in ranked
                    if not (f["is_init"] and f["loc"] < 20)] or ranked
        entry["top"] = [
            {"path": f["path"],
             label: (f["commits"] or 0) if available
             else graph["fan_in"].get(f["path"], 0)}
            for f in filtered[:3]
        ]

    return dict(sorted(out.items()))


def _root_error_message(root: Path, roots: Roots, files: list[dict],
                        walked: dict) -> str:
    """Name every candidate root and the edge count each would have produced.

    The fix for this error is always "point it one directory deeper" or "one
    directory up", so the message has to make that choice for the reader instead
    of asserting that something went wrong.
    """
    candidates = [root, root / "src"]
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name not in EXCLUDED_DIRS and child not in candidates:
            candidates.append(child)

    lines = [
        f"no internal import edges among {len(files)} Python files under "
        f"{root.as_posix()}",
        f"  import roots tried: "
        f"{[rel_key(p, root) for p in roots.import_roots]}  (rule: {roots.rule})",
        "  candidate roots and the internal import statements each would give:",
    ]
    for cand in candidates[:8]:
        if not cand.is_dir():
            continue
        lines.append(f"    {rel_key(cand, root) or '.'}: "
                     f"{_probe_internal(cand, root, files)} internal statements")
    lines.append("  pass the directory that is on sys.path, not the directory "
                 "that contains it")
    return "\n".join(lines)


def _probe_internal(candidate: Path, root: Path, files: list[dict]) -> int:
    """How many already-parsed imports would resolve under a different root.

    Cheap because nothing is re-read or re-parsed: the ImportRefs are in hand
    and only the module NAMES change with the root. Relative imports stay as
    they were resolved under the surveyed root, which is stated in the message
    rather than papered over.
    """
    probe_roots = Roots(root, [candidate], [], None, [], "probe")
    known, owned = set(), []
    for f in files:
        module, _r, _i = module_name(f["path"], probe_roots)
        if module is not None:
            known.add(module)
            owned.append((f, module))
    total = 0
    for f, module in owned:
        for ref in f["imports"]:
            kind, _target = classify_import(ref, module, f["is_init"], known)
            if kind == "internal":
                total += 1
    return total
