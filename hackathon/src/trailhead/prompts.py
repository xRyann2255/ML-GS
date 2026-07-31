"""Stage 3 NARRATE — context packing. Deterministic; nothing here calls a model.

The rule the whole project turns on lives in this file's output:

    Never ask the model for a line number. Ask it to quote.

So every source line goes in behind a fixed-width gutter the model can read but
must not copy, and `pack` hands back the exact `(file, start, end)` set it
showed. That set is the strongest anti-hallucination check available: a quote
that resolves outside what we showed was not copied, and stage 4 drops it with
`snippet resolved outside the excerpt shown to the model`.

Two window sets exist and they are NOT the same set:

    shown      what the model sees, including the head of every file
    quotable   what a quote may resolve inside — the shown set minus lines 1-12

Rule 5 of §5.4 is why. `from __future__ import annotations` / blank /
`import logging` is 3 lines and 44 non-space characters — it clears every
quality floor the resolver has and appears verbatim at lines 1-3 of twenty files
under one package of the proving-ground repo. Showing it is orientation;
allowing it to anchor a claim is a coin flip over which file the claim lands in.

`pack` returns the quotable set. The shown set never leaves this module.
"""
import ast
from dataclasses import dataclass
from pathlib import Path

from trailhead.textio import Source, read_source

#: Total source lines any one prompt may carry (~12k tokens). Whole files are
#: never fed: the largest module of the proving-ground repo is 1477 lines and
#: would swallow the budget on its own while teaching nothing.
MAX_LINES = 900

#: Lines 1..HEAD_LINES of every file are shown but never quotable. See §5.4
#: rule 5 and this module's docstring.
HEAD_LINES = 12

#: A hot window is at least this many contiguous lines, so a quote has room to
#: be three lines long with context either side, and at most HOT_MAX so one
#: greedy function cannot eat the budget.
HOT_MIN = 30
HOT_MAX = 60

#: Signature + docstring + first body lines. Five is the floor at which a
#: skeleton fragment is still quotable at all (the resolver refuses one-liners).
SKELETON_MIN = 5

#: Context either side of a caller-specified region (a trace hop's anchor).
#: The hop's own lines must be quotable, and a quote that starts one line above
#: the anchor is a better quote, not a worse one.
REGION_PAD = 4

#: Ranges closer than this merge, so the rendered file does not become a
#: staircase of two-line fragments separated by more elision markers than code.
MERGE_GAP = 2

#: What the prompt asks for. The resolver's floor is 2 lines (§6.1) — asking
#: for 3 leaves one line of headroom for a model that miscounts its own quote.
ASK_MIN_LINES = 3
ASK_MAX_LINES = 24


@dataclass(frozen=True)
class Window:
    """One quotable span, 1-based inclusive, keyed by repo-relative path."""

    file: str
    start: int
    end: int


@dataclass(frozen=True)
class Unit:
    """One model call's worth of work — a stop-unit, not a module or a claim.

    The claim-shaped kinds are `five`, `trace`, `green`, `conventions` and
    `dive` (one per major map group, claims identical to `five`). The
    structured kinds are `node` (drawer content per map group), `gloss`
    (repo glossary), `tour` (guided map tour) and `cols` (column labels);
    their answers are validated against per-kind schemas, not the claims
    schema. `narrate.build_units` decides which of them the repo supports.

    `kind` drives the task text AND the parser's quarantine: `conventions`
    forces every returned claim to `inferred` in code, so the quarantine holds
    even if the prompt drifts.

    `regions` are caller-specified spans that must appear in the prompt — the
    trace hops. Without them the model is asked to narrate a chain it was never
    shown, every quote resolves outside the windows, and the stop that carries
    the pitch loses all eight claims.

    `choices` is the fixed vocabulary an answer may reference: the node ids a
    tour step may name, or the file names a node's key_files may name. The
    parser and the per-unit schema both enforce it, so the model can only pick
    from what the pack listed, never invent a member.
    """

    id: str
    kind: str
    title: str
    max_claims: int
    files: tuple[str, ...] = ()
    regions: tuple[tuple[str, int, int], ...] = ()
    notes: tuple[str, ...] = ()
    choices: tuple[str, ...] = ()


SYSTEM = """You are the narration stage of Trailhead, a tool that generates a \
walkthrough of an unfamiliar Python repository for a new joiner.

Everything you write is checked afterwards by ordinary deterministic code. Every
quote you return is searched for verbatim in the file on disk; anything that is
not found exactly is deleted and counted on screen. You cannot talk your way
past the checker, so do not try: an honest "inferred" sentence survives, an
invented quote does not.

Rules, all enforced in code after you answer:

1. Reply with JSON matching the schema and nothing else.
2. NEVER return a line number. The gutter (`  123| `) is orientation for you
   only. It is not part of any line and must not appear inside a quote.
3. `cite.quote` is a VERBATIM, CONTIGUOUS copy of {min}-{max} lines from ONE file,
   lines joined with newlines. Copy the leading indentation exactly, character
   for character. Do not reflow, re-indent, elide, or add an ellipsis.
4. Quote only code you were shown below. Quoting something you inferred exists
   is the single most expensive thing you can do here.
5. `cite.focus` is an array of exact substrings of your own `cite.quote`, the
   one or two lines that actually carry the point.
6. If you cannot support a sentence with a quote, set `"status": "inferred"` and
   omit `cite` entirely. That is a legitimate, visible answer, not a failure.
7. `text` is one plain sentence, at most 280 characters. No backticks, no
   newlines, no markdown links, no `<`. Use commas instead of dashes.
8. Say what the system DOES in its own domain's terms. When the README or a
   package docstring states the project's purpose, that purpose is the story;
   argument parsing, CLI wiring, and directory layout are never what a repo
   is for.
9. Write for someone who has never opened this repo. Name real symbols and real
   paths. Never say "this codebase appears to", say what it does.
""".replace("{min}", str(ASK_MIN_LINES)).replace("{max}", str(ASK_MAX_LINES))

#: The `dive` variant: claims-shaped like SYSTEM, but the renderer gives dive
#: prose the rich-text treatment, so backticks and glossary markers are legal.
#: Derived by replacement so the two cannot drift apart silently; the assert
#: below fails the import the moment the anchor text is edited without this.
SYSTEM_DIVE = SYSTEM.replace(
    "7. `text` is one plain sentence, at most 280 characters. No backticks, no\n"
    "   newlines, no markdown links, no `<`. Use commas instead of dashes.",
    "7. `text` is one plain sentence, at most 280 characters. Backticks may mark\n"
    "   code identifiers and [[term]] or [[id|label]] may mark a glossary term.\n"
    "   No newlines, no markdown links, no `<`. Use commas instead of dashes.")
assert SYSTEM_DIVE != SYSTEM, "SYSTEM rule 7 drifted; update the SYSTEM_DIVE replacement"

#: The structured kinds (`node`, `gloss`, `tour`, `cols`) answer per-kind
#: schemas rather than the claims schema, so their rules talk about fields,
#: not sentences. Same verification framing: quotes are re-resolved, unknown
#: keys discard the whole answer, and honesty beats decoration.
SYSTEM_INFO = """You are the narration stage of Trailhead, a tool that \
generates a verified walkthrough of an unfamiliar Python repository for a new \
joiner.

Everything you write is checked afterwards by ordinary deterministic code. Any
quote you return is searched for verbatim in the file on disk; anything not
found exactly is deleted and counted on screen. Fields that fail their checks
are dropped, and a malformed answer is discarded whole, so answer the schema
exactly.

Rules, all enforced in code after you answer:

1. Reply with JSON matching the schema and nothing else. An unknown key
   anywhere discards the whole answer.
2. NEVER return a line number. The gutter (`  123| `) is orientation for you
   only. It is not part of any line and must not appear inside a quote.
3. Where the schema allows a `cite`, its `quote` is a VERBATIM, CONTIGUOUS copy
   of {min}-{max} lines from ONE file shown below, lines joined with newlines,
   indentation copied exactly. `focus` is an array of exact substrings of your
   own quote. A cite is optional: omitting one is honest, inventing one is not.
4. Prose fields are plain sentences. Backticks may mark code identifiers and
   [[term]] or [[id|label]] may mark a glossary term. No newlines inside a
   field, no markdown links, no `<`. Use commas instead of dashes.
5. State substantive domain facts: what a thing is FOR, what flows through it,
   what would surprise a newcomer. Never restate code mechanics the reader can
   see, and never present argument parsing or CLI wiring as a purpose. When the
   README or a package docstring states the purpose, that purpose is the story.
6. Write for someone who has never opened this repo. Name real symbols and real
   paths. Never say "appears to", say what it is.
""".replace("{min}", str(ASK_MIN_LINES)).replace("{max}", str(ASK_MAX_LINES))


def system_for(kind: str) -> str:
    """The system prompt for one unit kind. Three texts, chosen in one place.

    `pack` calls this, so the cache key follows the kind automatically: editing
    any of the three invalidates exactly the stores of the kinds it serves.
    """
    if kind == "dive":
        return SYSTEM_DIVE
    if kind in ("node", "gloss", "tour", "cols"):
        return SYSTEM_INFO
    return SYSTEM


def number(lines, start: int, end: int) -> str:
    """Render `lines[start-1:end]` behind the fixed-width gutter.

    `f"{n:5d}| {line}"` — five columns, a pipe, one space, then the line
    byte-for-byte including its indentation. Indentation is the main
    disambiguator between two otherwise identical bodies, so it must survive
    the round trip; a prompt that re-indents its own evidence produces quotes
    that cannot be found in the file they came from.

    Out-of-range input is clamped rather than raised: this is display, and the
    hash recipe that must never guess is `textio.sha256_range`, not this.
    """
    start = max(1, start)
    end = min(len(lines), end)
    return "\n".join(f"{n:5d}| {lines[n - 1]}" for n in range(start, end + 1))


def facts(survey: dict) -> str:
    """The deterministic facts block — true by construction, never quotable.

    Everything here is already verified: it came out of `survey.json`, which no
    model touched. The model may rely on it and must not quote it, which is why
    it carries no gutter and no line numbers at all. Entry points are named
    without their `file:line` for the same reason — the prompt should not
    contain a single line number outside the gutter.

    Every lookup is defensive. `survey.json` grows additively (§2), an unknown
    repo fires degradations that empty half of it, and a narration stage that
    KeyErrors on a repo with no git history is worse than one that says so.
    """
    repo = survey.get("repo") or {}
    stats = survey.get("stats") or {}
    roots = survey.get("roots") or {}
    modules = survey.get("modules") or {}

    out = ["FACTS (from survey.json, deterministic). Rely on these; never quote them."]
    out.append(f"repo: {repo.get('name', '(unnamed)')} @ {repo.get('commit', '(no commit)')}")
    out.append(
        "size: {files} files, {py} python files, {loc} loc, {mods} modules".format(
            files=stats.get("files", "?"), py=stats.get("py_files", "?"),
            loc=stats.get("loc", "?"), mods=stats.get("modules", len(modules) or "?"),
        )
    )

    if roots.get("import_roots"):
        out.append("import roots: " + ", ".join(str(r) for r in roots["import_roots"]))
    if roots.get("declared_packages"):
        out.append("declared packages: " + ", ".join(str(p) for p in roots["declared_packages"]))
    if roots.get("test_roots"):
        out.append("test roots: " + ", ".join(str(r) for r in roots["test_roots"]))

    deps = stats.get("external_deps") or []
    if deps:
        out.append("external dependencies: " + ", ".join(str(d) for d in deps[:12]))

    fan_in = _fan_in(survey)
    if modules:
        out.append("modules (largest first, fan-in = how many modules import it):")
        for name, info in modules_by_loc(modules)[:10]:
            out.append(
                "  {name}: {files} files, {loc} loc, fan-in {fi}".format(
                    name=name, files=(info or {}).get("files", "?"),
                    loc=(info or {}).get("loc", "?"), fi=fan_in.get(name, 0),
                )
            )

    entries = survey.get("entry_points") or []
    if entries:
        out.append("entry points:")
        for e in entries[:6]:
            out.append(
                "  {kind}: {name} -> {target} (in {file})".format(
                    kind=e.get("kind", "?"), name=e.get("name", "?"),
                    target=e.get("target", "?"), file=e.get("file", "?"),
                )
            )

    dangling = survey.get("dangling") or []
    if dangling:
        stmts = sum(int(d.get("n") or 0) for d in dangling)
        out.append(
            f"dangling imports: {len(dangling)} module name(s) imported by this repo "
            f"have no file on disk, across {stmts} import statements: "
            + ", ".join(str(d.get("target")) for d in dangling[:5])
        )

    churn = survey.get("churn") or {}
    if churn:
        if churn.get("available"):
            out.append("git history: available; files are ranked by commit count")
        else:
            out.append(
                "git history: unavailable ({reason}); files are ranked by "
                "{sub} instead".format(
                    reason=churn.get("reason", "no reason recorded"),
                    sub=churn.get("substitute", "fan-in"),
                )
            )

    failures = survey.get("parse_failures") or []
    if failures:
        out.append(f"parse failures: {len(failures)} file(s) do not parse")

    return "\n".join(out)


def pack(unit: Unit, survey: dict, root) -> tuple[str, str, tuple[Window, ...]]:
    """-> (system, user, QUOTABLE windows).

    Quotable ⊂ shown: rule 5 excludes lines 1-12 of every file, which are still
    SHOWN for orientation.

    A file that is missing, binary or unreadable contributes nothing and does
    not raise. Genericity is the whole point of the tool, and a repo where one
    listed path has been deleted since the survey must still narrate the rest.
    """
    root = Path(root)
    sources = _read_files(unit, root)
    shown = _select(unit, sources)

    body = _render(shown, sources)
    user = "\n\n".join(part for part in (facts(survey), body, task(unit)) if part)

    windows = []
    for path in shown:
        for start, end in shown[path]:
            quotable_start = max(start, HEAD_LINES + 1)
            if quotable_start <= end:
                windows.append(Window(path, quotable_start, end))
    return system_for(unit.kind), user, tuple(windows)


def task(unit: Unit) -> str:
    """The per-unit instruction. One shape per `unit.kind`, all deterministic."""
    lines = [f"TASK: {unit.title}"]

    if unit.kind == "five":
        lines += [
            f"Write exactly {unit.max_claims} sentences that tell a new joiner what this repo",
            "is. Follow this shape, one sentence each, in this order:",
            "  1. What the system IS, in its domain's own words: the problem it exists",
            "     to solve, taken from the README or a package docstring when one",
            "     states it.",
            "  2. What it CONSUMES: the real inputs, data sources, or upstream systems.",
            "  3. How QUALITY is judged: the metric, test, or comparison that decides",
            "     whether the output is good.",
            "  4. What the OUTPUTS FEED: who or what consumes the results.",
            "  5. What is UNUSUAL about this repo, the thing a newcomer would not guess.",
            "  6. What this repo is NOT: the thing a newcomer would reasonably assume",
            "     and be wrong about. Mark that one 'inferred'; an absence has no line",
            "     to cite.",
            "Domain first: parser setup, CLI plumbing, and directory layout are never",
            "the story when a README or docstring states a purpose.",
        ]
    elif unit.kind == "dive":
        lines += [
            f"Write 6 to {unit.max_claims} sentences that take a new joiner INSIDE this",
            "part of the repo: what it is for in domain terms, what flows in and out,",
            "the mechanism that makes it work, how you can tell it is correct, and",
            "anything a newcomer would not guess. Substantive facts only; never",
            "restate code mechanics the reader can see in the excerpt.",
            "Quote from the files shown above wherever a sentence can be anchored,",
            "and mark honest readings 'inferred'. One inferred sentence about what",
            "this part does NOT do is welcome.",
        ]
    elif unit.kind == "node":
        lines += [
            "Fill the drawer for this module group. Return a JSON object with:",
            "  role: 2 or 3 short paragraphs saying what this group IS and DOES in",
            "        domain terms, and what is distinctive about how it does it.",
            "  reads: one sentence, what this group consumes and where it comes from.",
            "  feeds: one sentence, what depends on this group's output.",
            "  key_files: 3 to 6 entries; 'file' is copied exactly from the FILES",
            "        list below and 'purpose' is one line saying why a newcomer",
            "        would open that file.",
            "  concepts: 3 to 6 short terms a newcomer should recognise here.",
            f"  cite (optional): one verbatim quote of {ASK_MIN_LINES}-{ASK_MAX_LINES} contiguous lines from",
            "        the source shown above that best captures this group, with an",
            "        optional one-line caption.",
        ]
    elif unit.kind == "gloss":
        lines += [
            f"Identify up to {unit.max_claims} terms of art a newcomer to this repo",
            "must know: domain concepts, internal names, systems, metrics. For each,",
            "return 'term' (at most 40 characters, spelled the way the codebase",
            "spells it) and 'def' (one or two plain sentences, at most 300",
            "characters, that teach the concept rather than the code). Add a 'cite'",
            "with a verbatim quote where the repo defines or computes the thing,",
            "when the source shown above contains one.",
            "Prefer terms the repo's own README, docstrings, and file names use.",
            "Skip generic programming vocabulary.",
        ]
    elif unit.kind == "tour":
        lines += [
            f"Write the guided tour of the module map: exactly {unit.max_claims} steps,",
            "one per node id listed below, in the order given. Each step is 'id'",
            "(copied exactly from the list) and 'text' (at most 340 characters):",
            "what the reader is looking at, why it matters, and why it comes next.",
            "Name real files and symbols.",
        ]
    elif unit.kind == "cols":
        lines += [
            f"Name the layers of the module map: exactly {unit.max_claims} labels, one",
            "per column, in the order given below. Each label is at most 14",
            "characters, ALL UPPERCASE, and says what the column's groups have in",
            "common (for example INTERFACE, DATA, MODELS, OUTPUT). No two labels",
            "alike.",
        ]
    elif unit.kind == "trace":
        lines += [
            f"Below is one real call chain through this repo, {unit.max_claims} hops long.",
            f"Write exactly {unit.max_claims} sentences, one per hop, in the order given.",
            "Each sentence says what happens at that hop and what it hands to the next.",
            "Quote from the hop's own file; the lines you need are shown above.",
        ]
    elif unit.kind == "green":
        lines += [
            f"Write exactly {unit.max_claims} sentences about what the command below actually",
            "proves about this repo, and what it does not prove. Be precise about the",
            "difference between 'it imports' and 'it is tested'.",
        ]
    elif unit.kind == "conventions":
        lines += [
            f"Write exactly {unit.max_claims} sentences about the conventions and habits of",
            "this codebase: how errors are handled, how modules are laid out, what the",
            "authors clearly cared about.",
            "These are readings, not facts. Every one of them will be marked inferred and",
            "shown as such; do not stretch for a quote to make one look verified.",
        ]
    else:
        lines += [f"Write at most {unit.max_claims} anchored sentences about this repo."]

    if unit.notes:
        lines.append("")
        lines += list(unit.notes)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# window selection
# ---------------------------------------------------------------------------

def _read_files(unit: Unit, root: Path) -> dict:
    """Repo-relative path -> Source, in `unit.files` order, existing files only.

    Region files are read even when they are not in `unit.files`, because a
    trace hop names its own file and a hop shown without its anchor is a hop
    whose claim cannot survive verification.
    """
    wanted = list(unit.files) + [r[0] for r in unit.regions]
    sources = {}
    for rel in wanted:
        if rel in sources:
            continue
        path = root / rel
        try:
            if not path.is_file():
                continue
            src = read_source(path)
        except OSError:
            continue
        if src.note == "not text" or not src.lines:
            continue
        sources[rel] = src
    return sources


def _select(unit: Unit, sources: dict) -> dict:
    """Path -> merged shown ranges, filled in three tiers under one budget.

    Tier order is the priority order: caller-specified regions (the trace
    anchors) first, then one hot window per file, then skeletons. Every file
    gets its hot window before any file gets a skeleton, so a five-file unit
    does not spend its whole budget on the first file's helper functions.
    """
    picked = {path: [] for path in sources}

    for tier in (_head_ranges, _region_ranges, _hot_ranges, _skeleton_ranges):
        for path, src in sources.items():
            for start, end in tier(unit, path, src, sources):
                start = max(1, start)
                end = min(len(src.lines), end)
                if end < start:
                    continue
                trial = dict(picked)
                trial[path] = _merge(picked[path] + [(start, end)])
                if _count(trial) <= MAX_LINES:
                    picked = trial

    return {path: ranges for path, ranges in picked.items() if ranges}


def _head_ranges(unit: Unit, path: str, src: Source, sources: dict):
    """Lines 1..HEAD_LINES of every file, always shown and never quotable.

    Twelve lines is the imports, the module docstring and the copyright banner —
    the cheapest orientation in the file and the reason the reader can tell
    `data/ohlcv.py` from `cli/ohlcv.py` at a glance. It is excluded from the
    quotable set in `pack`, not here: the model needs to SEE it.
    """
    yield 1, min(HEAD_LINES, len(src.lines))


def _region_ranges(unit: Unit, path: str, src: Source, sources: dict):
    for rel, start, end in unit.regions:
        if rel == path:
            yield start - REGION_PAD, end + REGION_PAD


def _hot_ranges(unit: Unit, path: str, src: Source, sources: dict):
    """One window of >= HOT_MIN lines centred on the file's busiest public def.

    "Busiest" is call sites across the files in this prompt — a local fan-in
    proxy, and deliberately a crude one: survey counts imports between modules,
    not calls between functions, and inventing a call graph here would be a
    second analysis stage hiding inside the prompt builder. Ties break on the
    earlier line, so the choice is stable across runs.

    A file that does not parse (or is not Python at all — `pyproject.toml`, a
    bare shell script) falls back to its head, which is where a config file
    keeps the interesting part anyway.
    """
    defs = _top_level_defs(src)
    if not defs:
        yield 1, min(len(src.lines), HOT_MAX)
        return

    text = "\n".join(s.text() for s in sources.values())
    public = [d for d in defs if not d[0].startswith("_")] or defs
    hot = max(public, key=lambda d: (text.count(d[0] + "("), -d[1]))

    name, lineno, end_lineno = hot
    start = max(1, lineno - HOT_MIN // 3)
    end = max(start + HOT_MIN - 1, min(end_lineno, start + HOT_MAX - 1))
    yield start, end


def _skeleton_ranges(unit: Unit, path: str, src: Source, sources: dict):
    """Signature + docstring + first body lines for every other top-level def."""
    for name, lineno, end_lineno in _top_level_defs(src):
        start = lineno
        end = max(lineno + SKELETON_MIN - 1, min(end_lineno, lineno + 8))
        yield start, min(end, end_lineno)


def _top_level_defs(src: Source) -> list:
    """(name, first line, last line) for each module-level def/class.

    The first line is the first decorator when there is one: a claim about a
    route is a claim about `@router.post(...)`, and a window that starts below
    the decorator cannot quote it.
    """
    try:
        tree = ast.parse(src.text())
    except (SyntaxError, ValueError, RecursionError):
        return []

    out = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        first = min([node.lineno] + [d.lineno for d in node.decorator_list])
        out.append((node.name, first, node.end_lineno or node.lineno))
    return out


def _merge(ranges: list) -> list:
    """Sort and coalesce ranges closer than MERGE_GAP."""
    out = []
    for start, end in sorted(ranges):
        if out and start <= out[-1][1] + MERGE_GAP + 1:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _count(picked: dict) -> int:
    return sum(end - start + 1 for ranges in picked.values() for start, end in ranges)


def _render(shown: dict, sources: dict) -> str:
    """The numbered source block, one section per file.

    Disjoint ranges are separated by a bare `   ...` so the model can see that
    code was elided rather than believing line 40 follows line 12.
    """
    if not shown:
        return ""

    out = ["SOURCE (line numbers are a gutter, not part of any line; never quote them)"]
    for path, ranges in shown.items():
        out.append("")
        out.append(f"--- {path} ---")
        for i, (start, end) in enumerate(ranges):
            if i:
                out.append("   ...")
            out.append(number(sources[path].lines, start, end))
    return "\n".join(out)


def _fan_in(survey: dict) -> dict:
    """Module -> how many distinct modules import it, from `survey.edges`."""
    counts = {}
    for edge in survey.get("edges") or []:
        target = edge.get("b")
        if target:
            counts[target] = counts.get(target, 0) + 1
    return counts


def modules_by_loc(modules: dict) -> list:
    """(name, info) sorted by loc descending, name ascending — stable ordering.

    Public because `narrate.build_units` picks its files off the same ordering:
    two orderings of the same modules would mean the prompt's facts block and
    the prompt's source windows disagree about which module is the big one.
    """
    return sorted(
        modules.items(),
        key=lambda kv: (-int((kv[1] or {}).get("loc") or 0), kv[0]),
    )
