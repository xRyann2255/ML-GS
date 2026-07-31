"""Stage 1 SURVEY — import resolution.

Survey is deterministic and pure, so it is test-driven. These tests are the
contract for what MAP consumes and what checkpoint answer keys are derived from
(non-negotiable #6: keys come from survey.json, never from the model).

Four of them guard failures that have no symptom, which is why they exist at all
rather than being caught by looking at the output:

  a wrong import root produces an EMPTY graph, not an error — measured, 1 edge
  of 782 on the proving-ground repo surveyed one directory too high;

  an import of a module that does not exist resolves, under a longest-prefix
  resolver, to a real-looking edge to its nearest existing ancestor — 700
  phantom edges, 27.4% of everything that resolver calls internal;

  a CRLF file read naively hashes differently from the same logical lines in an
  LF file, and every anchor in it dies silently at verify time;

  `git log … -- .` written as one argv element exits 128, which a
  returncode-blind caller reads as "no history" — so a repo with real churn
  reports none and falls back to fan-in without saying so.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_survey -v
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from trailhead import survey, textio


class ParseImports(unittest.TestCase):
    def test_plain_import_yields_dotted_name(self):
        src = "import os\nimport pkg.sub\n"

        self.assertEqual(
            survey.parse_imports(src, module="pkg.mod"),
            ["os", "pkg.sub"],
        )

    def test_from_import_qualifies_each_name(self):
        # `thing` may be a submodule or a symbol inside pkg.sub — we cannot tell
        # from one file. Emit the most specific candidate and let edge
        # resolution pick the longest prefix that is a real module.
        src = "from pkg.sub import thing, other\n"

        self.assertEqual(
            survey.parse_imports(src, module="pkg.mod"),
            ["pkg.sub.thing", "pkg.sub.other"],
        )

    def test_single_dot_relative_resolves_against_own_package(self):
        src = "from . import sibling\nfrom .helpers import fn\n"

        self.assertEqual(
            survey.parse_imports(src, module="pkg.sub.mod"),
            ["pkg.sub.sibling", "pkg.sub.helpers.fn"],
        )

    def test_multi_dot_relative_climbs_one_package_per_dot(self):
        src = "from .. import cousin\nfrom ..other import fn\n"

        self.assertEqual(
            survey.parse_imports(src, module="pkg.sub.mod"),
            ["pkg.cousin", "pkg.other.fn"],
        )


class ResolveImport(unittest.TestCase):
    KNOWN = {"pkg", "pkg.sub", "pkg.sub.helpers", "pkg.other"}

    def test_picks_the_longest_known_prefix(self):
        # pkg.sub.helpers.fn -> fn is a symbol, pkg.sub.helpers is the module.
        self.assertEqual(
            survey.resolve_import("pkg.sub.helpers.fn", self.KNOWN),
            "pkg.sub.helpers",
        )

    def test_exact_match_resolves_to_itself(self):
        self.assertEqual(survey.resolve_import("pkg.other", self.KNOWN), "pkg.other")

    def test_third_party_import_resolves_to_nothing(self):
        # An external dependency is not a node on the map.
        self.assertIsNone(survey.resolve_import("os.path", self.KNOWN))
        self.assertIsNone(survey.resolve_import("fastapi", self.KNOWN))

    def test_unknown_submodule_falls_back_to_its_known_parent(self):
        self.assertEqual(
            survey.resolve_import("pkg.sub.missing.deep", self.KNOWN),
            "pkg.sub",
        )


class ExtractImports(unittest.TestCase):
    def test_a_relative_import_inside_a_package_init_resolves_to_the_package_itself(self):
        # `from . import engine` in pkg/__init__.py means pkg.engine. Treating
        # the init like an ordinary module strips a level and yields `engine`,
        # which is then dangling or, worse, someone else's top-level module.
        refs = survey.extract_imports("from . import engine\n", "pkg", is_init=True)

        self.assertEqual([r.dotted for r in refs], ["pkg.engine"])

    def test_the_same_statement_in_a_module_climbs_to_the_parent(self):
        refs = survey.extract_imports("from . import engine\n", "pkg.mod", is_init=False)

        self.assertEqual([r.dotted for r in refs], ["pkg.engine"])

    def test_every_ref_carries_the_line_it_was_written_on(self):
        # Entry-point and dangling-site provenance is a file:line or it is
        # nothing; a ref with no lineno cannot be cited.
        refs = survey.extract_imports("import os\n\n\nfrom pkg import x\n", "m")

        self.assertEqual([r.line for r in refs], [1, 4])


class ClassifyImport(unittest.TestCase):
    KNOWN = {"volforecast", "volforecast.data", "volforecast.data.ohlcv",
             "volforecast.cli"}

    def ref(self, base, name=None, level=0):
        return survey.ImportRef(base, name, level, 1)

    def test_an_import_of_a_module_that_does_not_exist_is_dangling_not_internal(self):
        # `volforecast/constants.py` genuinely does not exist in the proving
        # ground; 60 statements import it. A longest-prefix resolver reports an
        # edge to `volforecast`, inventing a dependency that is not there.
        kind, target = survey.classify_import(
            self.ref("volforecast.constants", "FUTURES_SYMBOLS"),
            module="volforecast.cli", is_init=False, known=self.KNOWN)

        self.assertEqual((kind, target), ("dangling", "volforecast.constants"))

    def test_a_symbol_imported_from_a_real_module_is_an_edge_to_that_module(self):
        kind, target = survey.classify_import(
            self.ref("volforecast.data.ohlcv", "save_ohlcv_cache"),
            module="volforecast.cli", is_init=False, known=self.KNOWN)

        self.assertEqual((kind, target), ("internal", "volforecast.data.ohlcv"))

    def test_a_submodule_imported_by_name_beats_the_symbol_reading(self):
        # `from volforecast.data import ohlcv` — ohlcv is a real module, so the
        # edge points at it and not at the package above it.
        kind, target = survey.classify_import(
            self.ref("volforecast.data", "ohlcv"),
            module="volforecast.cli", is_init=False, known=self.KNOWN)

        self.assertEqual((kind, target), ("internal", "volforecast.data.ohlcv"))

    def test_a_third_party_import_reports_its_distribution_root(self):
        kind, target = survey.classify_import(
            self.ref("pandas.api", "types"),
            module="volforecast.cli", is_init=False, known=self.KNOWN)

        self.assertEqual((kind, target), ("external", "pandas"))


class Tmp(unittest.TestCase):
    """Base for tests that need a real tree on disk — survey reads files."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name).resolve()
        self.addCleanup(self._dir.cleanup)

    def write(self, rel: str, text: str = "") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def write_bytes(self, rel: str, data: bytes) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def graph(self, roots=None):
        """Run the deterministic half of the stage and hand back the pieces."""
        roots = roots or survey.discover_roots(self.root)
        walked = survey.walk_files(roots, None)
        files = [
            survey.extract_module(
                self.root.joinpath(*rel.split("/")), rel,
                *(lambda m, _r, i: (m, i))(*survey.module_name(rel, roots)))
            for rel in walked["py_in_scope"]
        ]
        index, known = survey.build_module_index(files, roots)
        return roots, walked, files, index, known, survey.build_edges(files, index, known)


class DiscoverRoots(Tmp):
    def test_a_pyproject_one_level_down_wins_over_the_repo_root(self):
        # The proving-ground layout: pyproject at restored/src/pyproject.toml,
        # nothing at the root. Surveyed from the root with a path-derived module
        # namespace the whole graph collapses to one edge out of 782.
        self.write("src/pyproject.toml",
                   '[tool.hatch.build.targets.wheel]\npackages = ["pkg"]\n')
        self.write("src/pkg/__init__.py")
        self.write("src/pkg/mod.py")

        roots = survey.discover_roots(self.root)

        self.assertEqual(roots.pyproject, self.root / "src" / "pyproject.toml")
        self.assertEqual(roots.import_roots, [self.root / "src"])
        self.assertEqual(roots.declared_packages, ["pkg"])
        self.assertEqual(survey.module_name("src/pkg/mod.py", roots)[0], "pkg.mod")

    def test_the_shallowest_pyproject_wins_when_there_are_several(self):
        # A vendored or example pyproject deeper in the tree must never win —
        # its packages are not this project's.
        self.write("pyproject.toml", '[project]\nname = "top"\n')
        self.write("examples/demo/pyproject.toml", '[project]\nname = "demo"\n')
        self.write("app/__init__.py")

        roots = survey.discover_roots(self.root)

        self.assertEqual(roots.pyproject, self.root / "pyproject.toml")

    def test_import_roots_include_the_parent_of_every_test_root(self):
        # Standard src-layout puts tests/ outside the declared import root.
        # Measured: without this, 68 of 161 files vanish on IMC-Prosperity-4,
        # including all 36 test files.
        self.write("pyproject.toml",
                   '[tool.setuptools.packages.find]\nwhere = ["src"]\n')
        self.write("src/pkg/__init__.py")
        self.write("tests/test_pkg.py")

        roots = survey.discover_roots(self.root)

        self.assertIn(self.root, roots.import_roots)
        self.assertIn(self.root / "src", roots.import_roots)
        self.assertEqual(survey.module_name("tests/test_pkg.py", roots)[0],
                         "tests.test_pkg")

    def test_a_bare_directory_of_scripts_still_produces_module_names(self):
        # The terminal fallback. `qrt` is 7 loose .py with no __init__.py
        # anywhere and it is a named acceptance repo.
        self.write("a.py", "import os\n")
        self.write("b.py", "import os\n")

        roots = survey.discover_roots(self.root)

        self.assertEqual(roots.import_roots, [self.root])
        self.assertEqual(survey.module_name("a.py", roots)[0], "a")

    def test_an_init_maps_to_its_package_not_to_pkg_dunder_init(self):
        self.write("pkg/__init__.py")

        roots = survey.discover_roots(self.root)

        self.assertEqual(survey.module_name("pkg/__init__.py", roots),
                         (("pkg"), self.root, True))


class Walk(Tmp):
    def test_pycache_and_venv_are_pruned_at_directory_level(self):
        # Pruned in place, never rglob-then-filter: one .venv is 45,698 entries.
        self.write("pkg/__init__.py")
        self.write("pkg/real.py")
        self.write("pkg/__pycache__/real.py")
        self.write(".venv/Lib/site-packages/numpy/core.py")

        _roots, walked, *_ = self.graph()

        self.assertEqual(walked["py_in_scope"], ["pkg/__init__.py", "pkg/real.py"])
        self.assertGreaterEqual(walked["walk"]["excluded_dirs"], 2)

    def test_a_png_named_dot_py_is_skipped_as_not_text(self):
        # It must never reach ast.parse, and it is not a parse failure either —
        # §9 counts "skipped, not text" on a different row from "did not parse".
        self.write("pkg/__init__.py")
        self.write_bytes("pkg/image.py", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

        sv = survey.survey(self.root)

        self.assertIn({"path": "pkg/image.py", "reason": "not text"},
                      sv["walk"]["skipped"])
        self.assertEqual(sv["parse_failures"], [])

    def test_an_extensionless_shebang_script_is_anchorable_and_a_binary_is_not(self):
        # This clause is what admits `restored/vol`, a 22 KB bash script that
        # carries the best platform-claim anchor in the repo.
        self.write("vol", "#!/usr/bin/env bash\necho hi\n")
        self.write_bytes("blob", b"\x00\x01\x02\x03")

        _roots, walked, *_ = self.graph()

        self.assertIn("vol", walked["text_files"])
        self.assertNotIn("blob", walked["text_files"])

    def test_the_output_bundle_is_excluded_from_its_own_next_run(self):
        self.write("pkg/__init__.py")
        out = self.write("trailhead.html", "<html></html>")

        walked = survey.walk_files(survey.discover_roots(self.root), out)

        self.assertNotIn("trailhead.html", walked["files_all"])


class Reading(Tmp):
    """Encoding hazards. `restored/` is LF-only and BOM-free — it will never
    surface any of this, and CRLF is the majority checkout on this machine."""

    BODY = 'def handle(args):\n    """Do the thing."""\n    return 1\n'

    def test_crlf_and_lf_files_hash_identically(self):
        # A surviving \r makes a model's verbatim quote unfindable and every
        # digest wrong: a 100% claim-drop rate on the majority of repos here.
        lf = self.write_bytes("lf.py", self.BODY.encode("utf-8"))
        crlf = self.write_bytes("crlf.py",
                                self.BODY.replace("\n", "\r\n").encode("utf-8"))

        a = survey.extract_module(lf, "lf.py", "lf", False)
        b = survey.extract_module(crlf, "crlf.py", "crlf", False)

        self.assertEqual(a["sha1"], b["sha1"])
        self.assertEqual(a["loc"], b["loc"])
        self.assertEqual(
            textio.sha256_range(textio.read_source(lf).lines, 1, 3),
            textio.sha256_range(textio.read_source(crlf).lines, 1, 3))

    def test_bom_is_stripped_and_the_text_still_parses(self):
        path = self.write_bytes("bom.py", b"\xef\xbb\xbfimport os\n\n" +
                                self.BODY.encode("utf-8"))

        rec = survey.extract_module(path, "bom.py", "bom", False)

        self.assertTrue(rec["parsed"])
        self.assertEqual([r.dotted for r in rec["imports"]], ["os"])
        # The BOM is gone from line 1, so a quote of it is findable.
        self.assertEqual(textio.read_source(path).lines[0], "import os")

    def test_form_feed_in_a_docstring_does_not_split_a_line(self):
        # str.splitlines() breaks on \x0c and seven other characters, which
        # desynchronises the line index from ast.lineno for the whole file.
        path = self.write_bytes(
            "ff.py", 'x = 1\n"""a\x0cb"""\ndef after():\n    pass\n'.encode("utf-8"))

        rec = survey.extract_module(path, "ff.py", "ff", False)

        self.assertEqual(rec["loc"], 4)
        self.assertEqual([d["start"] for d in rec["defs"]], [3])

    def test_a_file_that_does_not_parse_is_counted_and_never_fatal(self):
        self.write("pkg/__init__.py")
        self.write("pkg/broken.py", "def (:\n")

        sv = survey.survey(self.root)

        self.assertEqual(len(sv["parse_failures"]), 1)
        self.assertEqual(sv["parse_failures"][0]["path"], "pkg/broken.py")
        self.assertEqual(sv["parse_failures"][0]["line"], 1)
        # The file keeps its record, so its loc still counts toward the repo.
        self.assertIn("pkg/broken.py", [f["path"] for f in sv["files"]])


class Edges(Tmp):
    def test_a_real_import_becomes_an_edge_between_directory_groups(self):
        self.write("pkg/__init__.py")
        self.write("pkg/api/__init__.py")
        self.write("pkg/api/app.py", "from pkg.core.engine import price\n")
        self.write("pkg/core/__init__.py")
        self.write("pkg/core/engine.py", "def price():\n    return 1\n")

        *_, graph = self.graph()

        self.assertEqual(graph["internal"], 1)
        self.assertEqual(graph["edges"], [{"a": "pkg.api", "b": "pkg.core", "n": 1}])
        self.assertEqual(graph["file_edges"], 1)
        self.assertEqual(graph["fan_in"]["pkg/core/engine.py"], 1)

    def test_an_import_of_a_missing_module_is_recorded_with_its_sites(self):
        self.write("pkg/__init__.py")
        self.write("pkg/app.py", "import os\nfrom pkg.config import SETTINGS\n")

        *_, graph = self.graph()

        self.assertEqual(graph["edges"], [])
        self.assertEqual(graph["dangling"], [{
            "target": "pkg.config", "n": 1,
            "sites": [{"file": "pkg/app.py", "line": 2}]}])

    def test_the_known_set_is_scoped_per_import_root(self):
        # `restored/skills/SECDB_INSPECT/src/inspect.py` is the module `inspect`
        # for files under its own root and must never shadow stdlib `inspect`
        # for the rest of the repo.
        self.write("a/alpha.py", "import beta\n")
        self.write("b/beta.py", "x = 1\n")

        roots, _walked, _files, _index, known, graph = self.graph()

        self.assertEqual(len(roots.import_roots), 2)
        self.assertEqual(len(known), 2)
        self.assertEqual(graph["internal"], 0)
        self.assertEqual(graph["external"], 1)

    def test_no_internal_edges_on_a_large_repo_raises_source_root_error(self):
        # The failure with no symptom: a wrong root gives an empty graph and a
        # walkthrough that says nothing, at exit 0.
        self.write("src/pkg/__init__.py")
        for i in range(60):
            self.write(f"src/pkg/mod{i}.py", "import os\n")

        with self.assertRaises(survey.SourceRootError) as caught:
            survey.survey(self.root)

        message = str(caught.exception)
        self.assertIn("no internal import edges", message)
        self.assertIn("candidate roots", message)
        self.assertIn("src", message)


class Churn(Tmp):
    """The three-state git probe. `GIT_UNTRACKED` is the DEFAULT path for the
    proving-ground repo, not an edge case."""

    def setUp(self):
        super().setUp()
        if shutil.which("git") is None:
            self.skipTest("git is not on PATH")

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.root), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=30)

    def init_repo(self):
        self.git("init", "-q", "-b", "main")
        self.write("tracked.py", "import os\n")
        self.git("add", "tracked.py")
        self.git("-c", "user.email=t@t", "-c", "user.name=T",
                 "commit", "-q", "-m", "first")

    def test_the_churn_argv_passes_dashdash_and_dot_as_two_elements(self):
        # `"-- ."` as one element gives rc=128, which a returncode-blind caller
        # reads as "no history" — so every repo with real churn silently falls
        # back to fan-in. And the pathspec itself is mandatory: without it,
        # git answers with the ENCLOSING repository's history at exit 0.
        argv = survey.churn_argv(Path("C:/repo"), 365)

        self.assertEqual(argv[-2:], ["--", "."])
        self.assertIn("core.quotepath=false", argv)
        self.assertIn("--since=365.days", argv)

    def test_a_repo_with_history_reports_its_real_commits(self):
        self.init_repo()

        st = survey.git_state(self.root)
        churn = survey.git_churn(self.root, st, 3650)

        self.assertEqual(st.state, "GIT_OK")
        self.assertEqual(st.branch, "main")
        self.assertTrue(churn["available"])
        self.assertEqual(churn["by_file"]["tracked.py"]["commits"], 1)
        self.assertIsNone(churn["substitute"])

    def test_an_untracked_subdirectory_reports_unavailable_with_a_reason(self):
        # Exactly `restored/`: inside a work tree, nothing here tracked. A
        # two-state probe answers "git available" and then attributes the
        # enclosing repository's commits to files that do not exist here.
        self.init_repo()
        self.write("sub/mod.py", "import os\n")

        st = survey.git_state(self.root / "sub")
        churn = survey.git_churn(self.root / "sub", st, 3650)

        self.assertEqual(st.state, "GIT_UNTRACKED")
        self.assertFalse(churn["available"])
        self.assertEqual(churn["substitute"], "fan_in")
        self.assertIn("no tracked history", churn["reason"])
        self.assertEqual(churn["by_file"], {})

    def test_no_git_at_all_is_a_state_and_not_an_exception(self):
        st = survey.git_state(self.root)

        self.assertEqual(st.state, "NO_GIT")
        self.assertFalse(survey.git_churn(self.root, st, 365)["available"])

    def test_the_no_history_commit_id_changes_when_the_tree_changes(self):
        # localStorage is keyed trailhead:<name>:<commit>. An id that does not
        # move leaves a reader's old progress on a regenerated walkthrough.
        self.write("pkg/__init__.py")
        self.write("pkg/mod.py", "x = 1\n")
        before = survey.survey(self.root)["repo"]["commit"]

        self.write("pkg/mod.py", "x = 2\n")
        after = survey.survey(self.root)["repo"]["commit"]

        self.assertTrue(before.startswith("nogit-"))
        self.assertNotEqual(before, after)


class EntryPoints(Tmp):
    def test_project_scripts_outranks_main_module_which_outranks_if_name_main(self):
        self.write("pyproject.toml",
                   '[tool.hatch.build.targets.wheel]\npackages = ["pkg"]\n\n'
                   '[project.scripts]\nrun-me = "pkg.__main__:main"\n')
        self.write("pkg/__init__.py")
        self.write("pkg/__main__.py", "def main():\n    return 0\n")
        self.write("pkg/tool.py",
                   'import argparse\n\nif __name__ == "__main__":\n    pass\n')

        _roots, _walked, files, _index, _known, graph = self.graph()
        found = survey.entry_points(survey.discover_roots(self.root), files,
                                    graph["fan_in"])

        self.assertEqual([e["kind"] for e in found],
                         ["console_script", "module_main", "main_guard"])
        # Every one of them is citable, which is the point of ranking them.
        self.assertEqual(found[0]["file"], "pyproject.toml")
        self.assertEqual(found[0]["line"], 5)
        self.assertEqual(found[2]["line"], 3)

    def test_toml_line_finds_the_key_inside_its_own_table(self):
        # tomllib returns no line numbers, and an anchor without one is not an
        # anchor. Verified against the proving-ground pyproject: packages :50,
        # [project.scripts] :52-53, testpaths :79.
        lines = ["[project]", 'name = "x"', "", "[project.scripts]",
                 'run-me = "pkg:main"']

        self.assertEqual(survey.toml_line(lines, "project.scripts", "run-me"), 5)
        self.assertEqual(survey.toml_line(lines, "project.scripts"), 4)
        self.assertIsNone(survey.toml_line(lines, "tool.poetry", "x"))

    def test_a_key_that_is_absent_reports_the_table_and_never_a_guess(self):
        lines = ["[project.scripts]", 'other = "pkg:main"']

        self.assertEqual(survey.toml_line(lines, "project.scripts", "run-me"), 1)


class SurveyOutput(Tmp):
    """The emitted contract. Everything downstream reads exactly these keys."""

    def build(self):
        self.write("src/pyproject.toml",
                   '[tool.hatch.build.targets.wheel]\npackages = ["pkg"]\n\n'
                   '[project.scripts]\npkg = "pkg.__main__:main"\n')
        self.write("src/pkg/__init__.py")
        self.write("src/pkg/__main__.py", "def main():\n    return 0\n")
        self.write("src/pkg/core/__init__.py")
        self.write("src/pkg/core/engine.py", "def price():\n    return 1\n")
        self.write("src/pkg/api/__init__.py")
        self.write("src/pkg/api/app.py",
                   "from pkg.core.engine import price\nimport requests\n")
        self.write("README.md", "# demo\n")
        return survey.survey(self.root)

    def test_every_edge_endpoint_is_a_key_in_modules(self):
        # The gate's rule, and the reason mapper can trust the rollup.
        sv = self.build()

        for edge in sv["edges"]:
            self.assertIn(edge["a"], sv["modules"])
            self.assertIn(edge["b"], sv["modules"])

    def test_every_path_is_repo_relative_with_forward_slashes(self):
        # verify-contract.js does an exact-string dict lookup: one backslash
        # reports `file not bundled` for every anchor in that file.
        sv = self.build()

        for f in sv["files"]:
            self.assertNotIn("\\", f["path"])
            self.assertFalse(f["path"].startswith("/"))
            self.assertTrue((self.root / f["path"]).exists())
        for entry in sv["modules"].values():
            self.assertNotIn("\\", entry["path"])
        for cand in sv["command_candidates"]:
            self.assertNotIn("\\", cand["cwd"])

    def test_the_contract_keys_survey_promises_are_all_present(self):
        sv = self.build()

        self.assertEqual(sv["contract"], "trailhead/survey@1")
        for key in ("repo", "stats", "files", "modules", "edges", "entry_points",
                    "command_candidates", "checkpoints", "roots", "walk",
                    "dangling", "parse_failures", "churn", "stdlib_shadowed",
                    "text_files", "degradations"):
            self.assertIn(key, sv)
        for key in ("name", "root", "commit", "branch", "surveyed_at"):
            self.assertIn(key, sv["repo"])

    def test_external_dependencies_exclude_the_standard_library(self):
        sv = self.build()

        self.assertIn("requests", sv["stats"]["external_deps"])
        self.assertNotIn("os", sv["stats"]["external_deps"])

    def test_no_churn_fires_a_degradation_row_naming_its_substitute(self):
        # §9 row 6. The page's drawer heading is hard-coded MOST-EDITED FILES,
        # so the substitution has to be visible in the data or the artifact
        # states a falsehood on every node drawer.
        sv = self.build()

        self.assertEqual([d["code"] for d in sv["degradations"]], ["no_churn"])
        self.assertEqual(sv["degradations"][0]["substitute"], "fan-in")
        self.assertTrue(all("fan_in" in entry["top"][0]
                            for entry in sv["modules"].values()))

    def test_every_file_carries_the_fan_in_a_checkpoint_key_is_built_from(self):
        # cp-a1's answer is one FILE out of a repo-wide fan-in ranking, and
        # `edges` are between directory groups — so without this, checkpoints.py
        # would have to re-implement the classifier to find its own answer key.
        sv = self.build()

        by_path = {f["path"]: f for f in sv["files"]}
        self.assertEqual(by_path["src/pkg/core/engine.py"]["fan_in"], 1)
        self.assertEqual(by_path["src/pkg/api/app.py"]["fan_out"], 1)
        self.assertEqual(by_path["src/pkg/api/app.py"]["fan_in"], 0)

    def test_every_module_group_reports_at_least_one_top_file(self):
        # `top` is never empty: the group keyed `volforecast` on the proving
        # ground is one 8-line __init__.py with the highest fan-in in the repo,
        # and it sits where a judge clicks first.
        sv = self.build()

        for name, entry in sv["modules"].items():
            self.assertGreaterEqual(len(entry["top"]), 1, name)

    def test_the_survey_is_json_serialisable_as_emitted(self):
        # ImportRef and the per-root `known` sets are working state and must not
        # reach the file — json.dump would raise at hour 9 if they did.
        import json

        json.dumps(self.build())


if __name__ == "__main__":
    unittest.main()
