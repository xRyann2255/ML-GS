"""Stage 3 NARRATE — the deterministic half: the stop list and the blocks.

compose runs *inside* stage 3 and never touches a model (decision #13).
`content@1` carries `tracks`, so the course skeleton has to be produced by
stage 3 — but nothing says a *model* produces it. The model fills claims; it
never invents a stop, a title, a lede, a table cell, a command or an answer key.

Three rules shape every line below.

**Ten block types, no eleventh.** The renderer implements exactly `prose`,
`excerpt`, `command`, `graph`, `table`, `trace`, `checkpoint`, `callout`,
`ledger` and, since `@3`, `stats`; its dispatch table has no default arm, so an
unknown type renders *nothing*: a silently blank stop that both gates still
pass. Every block is built by one of the constructors here and `build_course`
re-checks the type of everything a builder hands back.

**Never a blank stop, never a silent omission.** §9's degradation table is
implemented in full: whenever a stop cannot be built as designed it emits a
*labelled* placeholder saying what is missing and why. A labelled gap reads as
a tool that knows what it does not know; a blank stop reads as a bug.

**No model string reaches a surface with no claim marker** (decision #20c).
Ledes, titles, table cells, callouts and the `where` table's purpose column are
deterministic templates over `survey.json` / `map.json`, verified by
construction and re-derivable from the artifacts on disk. Model output only ever
lands in a `prose` claim or a `trace` hop sentence, both of which carry an
anchor and a marker.

What is deliberately *not* here: `command.exit`/`out`/`dur` (the runner's, and
real or the run is a fraud), checkpoint answer keys (survey's — non-negotiable
#6, so a checkpoint block is emitted as a bare `{"type": "checkpoint", "id": …}`
reference that VERIFY substitutes), anchors and line ranges (VERIFY resolves
them from the verbatim quotes emitted here), and §9 row 5's low-confidence
banner (`verify.assemble` computes the drop rate).
"""
import json
import random
import re
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Callable, Sequence

from trailhead import TOOL_VERSION
# The stage that clamped the number is the only honest source for the clamp:
# a second literal `48` in this file drifts from mapper's and the drift surfaces
# as a sentence on the page stating a clamped weight as an import count.
from trailhead.mapper import EDGE_CAP
from trailhead.textio import cell

#: The complete block vocabulary. `excerpt` had no producer before `@3`; the
#: dive stops now emit one when their map node carries an anchor. `stats` is
#: the `@3` tile row, computed here and never narrated.
BLOCK_TYPES = frozenset(
    ["prose", "excerpt", "command", "graph", "table", "trace",
     "checkpoint", "callout", "ledger", "stats"]
)

#: `callout.level` — three, no more (spec §4.7).
CALLOUT_LEVELS = frozenset(["info", "inferred", "broken"])

#: `stats.items[].color` values the renderer maps onto its palette variables.
#: Anything else would silently fall back to the default ink, hiding the typo.
STAT_COLORS = frozenset(["ok", "inf", "bad"])

#: What a stat tile's `v` and `of` may contain. The renderer interpolates both
#: WITHOUT escaping (they are its own numbers), so the constructor refuses
#: anything that is not a plain figure.
_STAT_VALUE = re.compile(r"^[A-Za-z0-9 ,.%+-]+$")

#: How a stop behaves when its precondition is unmet. Only DROP removes it.
PLACEHOLDER, ALTERNATE, DROP = "PLACEHOLDER", "ALTERNATE", "DROP"

#: Track key -> (display title, minutes). `minutes` is a CONSTANT on the track,
#: not the sum of its stops: the shipped fixture has ORIENT at 15 against a stop
#: sum of 18. It is a rounded reading estimate and the rail prints it verbatim.
TRACKS = (
    ("ORIENT", "ORIENT", 15),
    ("RUN", "GET IT RUNNING", 20),
    ("DIVE", "INSIDE THE SYSTEM", 15),
    ("READ", "FOLLOW ONE PATH", 25),
    ("CONV", "CONVENTIONS", 8),
    ("AUDIT", "CLOSE", 6),
)

#: The narrate units compose consumes by name. Deep-dive units are composite,
#: keyed `dive:<gid>` (one per map group narrate chose), and matched by the
#: prefix below, exact-or-prefix and never a substring test, so they are not
#: listed here. Anything else in `ctx.narration` is ignored rather than
#: rendered: a unit with no stop has nowhere to go.
UNITS = ("five", "trace", "conv", "green")

#: The composite-unit prefix for the INSIDE THE SYSTEM track: `dive:core`
#: names a deep dive of map group `core`.
DIVE_UNIT_PREFIX = "dive:"

#: Rail minutes for one dive stop, a rounded reading estimate like the rest.
DIVE_MINUTES = 4

#: Claim-id bases for dive stops: unit i gets DIVE_ID_BASE + i*DIVE_ID_STRIDE.
#: The stride is wider than any dive pack's claim budget, and the whole range
#: sits above every ID_BASE entry and below the 900 fallback, so ids stay
#: unique across the payload without a shared counter.
DIVE_ID_BASE = 201
DIVE_ID_STRIDE = 20

#: The stop that is never skippable and never filterable. Stripping every
#: `ledger` block from the fixture leaves `verify-contract.js` exiting 0, so
#: nothing mechanical stops a ledger-less page. This constant is what does.
AUDIT_STOP = "audit"

#: Claim-id bases, one per producing stop, so ids are unique across the payload
#: without a shared counter that would make a builder untestable alone. VERIFY
#: renumbers with its own run-wide sequence (§6.7); these only have to be unique
#: and to match `^c-\\d{3,}$`.
ID_BASE = {"five": 1, "map": 11, "green": 41, "conv": 101}

#: §9's degradation table: code -> (callout level, title, text template).
#: The words are §9's, verbatim — an unspecified title renders the literal word
#: `undefined` on exactly the stops that carry the honest-degradation story.
#: Case is presentation and matches the shipped fixture's other callouts.
#: Rows 9 and 10 (parse failures, skipped files) emit no callout of their own;
#: they are counted into the audit stop's callout. Row 5 belongs to
#: `verify.assemble`, which is the only place the drop rate exists.
#:
#: Row 1 is ONE row with TWO triggers — "no entry point, **or** trace < 2 hops"
#: — so it has two entries here and two texts. It had one, and that one asserted
#: the no-entry-point half unconditionally; on a repo that plainly does declare
#: entry points the page then said nothing declares one and listed those very
#: entry points as candidates in the next sentence. A generator whose pitch is
#: that it catches a model inventing facts cannot ship a deterministic sentence
#: its own `survey.json` refutes, so the trigger picks the text that is true.
#: Both still record §9 row 1 on the ledger (see `LEDGER_CODE`).
DEGRADATIONS = {
    "no_trace": (
        "broken", "NO TRACEABLE ENTRY POINT FOUND",
        "Nothing in this repo declares a console script, a __main__.py, or a "
        "resolvable if __name__ guard inside an import root. "
        "Candidates considered: {candidates}."),
    "no_trace_hops": (
        "info", "NO HOP PATH WAS SPECIFIED FOR THIS REPO",
        "This repo declares {n} ({candidates}), so the entry point is not what "
        "is missing. The hops for this stop are hand-specified input rather "
        "than generated: a repo carries its chain in {fixture} or it has none, "
        "and this run had {hops}. Fewer than two hops is not a path, so the "
        "stop says so instead of inventing one."),
    "no_test_command": (
        "info", "NO TEST COMMAND DETECTED",
        "Candidates considered: {candidates}."),
    "setup_all_failed": (
        "broken", "THIS REPO DID NOT BUILD DURING GENERATION.",
        "All {n} setup commands failed. Every one is shown below with its real "
        "exit code and output; nothing is hidden."),
    "few_modules": (
        "info", "TOO FEW MODULES TO DRAW A GRAPH",
        "{n} module group(s) found. The table below carries the same "
        "information."),
    "no_churn": (
        "info", "NO GIT HISTORY FOR THIS PATH",
        "{reason} Files are ranked by {substitute} instead; the column header "
        "and every entry say so."),
    "narration_budget": (
        "info", "NARRATION BUDGET REACHED",
        "{n} of {m} units narrated. The rest render from templates and carry "
        "no claims."),
    "stops_dropped": (
        "info", "STOPS NOT GENERATED",
        "{rows}"),
    "no_commands": (
        "info", "NO COMMANDS WERE EXECUTED",
        "The allowlist admitted nothing from this repo. "
        "Candidates considered: {candidates}."),
    "dive_empty": (
        "info", "SUBSYSTEM DIVES NOT GENERATED",
        "Narration for {names} returned no claims that survived filtering, so "
        "those stops were omitted rather than rendered empty."),
}

#: Catalogue key -> the code that reaches `degradations`. A §9 row with more
#: than one trigger needs more than one *text* but must stay one *row*: the
#: ledger is a list of conditions keyed by row, `_needs_trace` asks `_fired`
#: whether row 1 fired at all, and `verification-report.json.degradations` is
#: what §11.3's per-repo golden files compare as an exact set. Splitting row 1
#: into two ledger codes would fix the sentence and silently re-key the
#: contract; splitting only the text fixes the sentence and leaves the contract
#: alone. Keys absent here record under their own name, which is all but one.
LEDGER_CODE = {"no_trace_hops": "no_trace"}


@dataclass(frozen=True)
class Ctx:
    """Everything a builder is allowed to see. No repo path, and no provider.

    A builder that cannot reach the disk cannot invent a line number, and a
    builder that cannot reach a provider cannot smuggle model prose onto an
    unanchored surface. Both are structural, not a matter of discipline.

    `degradations` is the sink for §9's fired rows and is why this frozen
    dataclass holds one mutable field: `build_course` runs the builders in
    STOP_TABLE order and later stops (`audit`) read what earlier stops
    (`trace`, `map`) reported. It is appended to the emitted `content@1` as
    `degradations` by the caller.
    """

    survey: dict
    map: dict
    commands: dict
    narration: dict
    hops: list[dict] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)
    degradations: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class StopSpec:
    """One row of the STOP_TABLE.

    `precondition` returns None when the stop can be built as designed, or the
    reason it cannot. `on_fail` decides what an unmet precondition means:
    PLACEHOLDER and ALTERNATE still build (the builder emits §9's labelled
    substitute), DROP removes the stop from `tracks` entirely and records it for
    the audit callout. Only checkpoint stops DROP — "Checkpoint A unavailable"
    is worse than no checkpoint, and padding a quiz with invented distractors
    puts a fabrication into an artifact whose whole claim is that it has none.
    """

    id: str
    title: str
    track: str
    minutes: int
    kind: str
    precondition: Callable[["Ctx"], str | None]
    build: Callable[["Ctx"], list[dict]]
    on_fail: str
    lede: Callable[["Ctx"], str] | None = None


# --------------------------------------------------------------------------
# Block constructors — one per renderable type, and nothing else emits a block.
# --------------------------------------------------------------------------

def prose(claims: Sequence[dict]) -> dict:
    """The only block that carries model sentences, each with a claim marker."""
    return {"type": "prose", "claims": list(claims)}


def excerpt(cite: dict, caption: str = "") -> dict:
    """Standalone code excerpt. Since `@3` the dive stops emit one when their
    map node carries an anchor; VERIFY resolves `cite` into the anchor the
    renderer draws, exactly as it does for a prose claim. `caption` goes
    through `cell` — the renderer interpolates it without escaping.
    """
    return {"type": "excerpt", "cite": dict(cite), "caption": cell(caption)}


def command(cmd: str, cwd: str = ".", hypothesis: str | None = None,
            predict: str | None = None) -> dict:
    """A command REFERENCE. Never an exit code, never output, never a timing.

    Non-negotiable #4 is structural here: this block has no field in which a
    fabricated result could travel. VERIFY merges the real capture from
    `commands.json` on `(cmd, cwd)`; a command with no capture is dropped and
    logged rather than rendered empty. `hypothesis` comes from
    `runner.classify_failure`'s rule table and always renders tagged `inferred`.
    """
    block = {"type": "command", "cmd": cmd, "cwd": cwd}
    if hypothesis:
        block["hypothesis"] = hypothesis
    if predict:
        # No answer field, deliberately: the renderer keys the prediction off
        # the captured exit code, so it cannot disagree with the run below it.
        block["predict"] = predict
    return block


def graph() -> dict:
    """Field-free: it renders the payload's single top-level `map`."""
    return {"type": "graph"}


def table(columns: Sequence[str], rows: Sequence[Sequence[str]],
          caption: str = "", sortable: bool = False) -> dict:
    """A table whose cells the renderer interpolates WITHOUT escaping.

    Callers pass values already through `textio.cell`, which escapes the value
    and re-adds markup from a two-tag whitelist. This constructor enforces the
    one thing the gate checks (`verify-contract.js:146`): every row is exactly
    as long as `columns`. A short row shifts every later cell into the wrong
    column and still renders.
    """
    cols = [str(c) for c in columns]
    out = []
    for i, r in enumerate(rows):
        r = [str(c) for c in r]
        if len(r) != len(cols):
            raise ValueError(
                f"table row {i} has {len(r)} cells, expected {len(cols)}"
            )
        out.append(r)
    return {"type": "table", "caption": caption, "sortable": bool(sortable),
            "columns": cols, "rows": out}


def stats(items: Sequence[dict]) -> dict:
    """A row of stat tiles (`@3`). Every value is computed, never narrated.

    The renderer interpolates `v` and `of` WITHOUT escaping (they are treated
    as the page's own numbers), so both are checked against a plain-figure
    whitelist here; `l` and `s` are escaped by the renderer and pass through
    as text. `color` tints the value and must be one of STAT_COLORS, because
    an unknown color silently falls back to the default ink and the typo
    would never surface.
    """
    out = []
    for i, it in enumerate(items):
        v, label = str(it.get("v") or ""), str(it.get("l") or "")
        if not v or not label:
            raise ValueError(f"stats tile {i} needs a non-empty v and l")
        if not _STAT_VALUE.fullmatch(v):
            raise ValueError(f"stats tile {i} value {v!r} is not a plain figure")
        tile = {"v": v, "l": label}
        if it.get("s"):
            tile["s"] = str(it["s"])
        if it.get("of"):
            of = str(it["of"])
            if not _STAT_VALUE.fullmatch(of):
                raise ValueError(f"stats tile {i} of {of!r} is not a plain figure")
            tile["of"] = of
        if it.get("color"):
            if it["color"] not in STAT_COLORS:
                raise ValueError(
                    f"stats tile {i} color {it['color']!r} not in "
                    f"{sorted(STAT_COLORS)}")
            tile["color"] = it["color"]
        out.append(tile)
    if not out:
        raise ValueError("a stats block needs at least one tile")
    return {"type": "stats", "items": out}


def trace(steps: Sequence[dict]) -> dict:
    """The chain of hops. Every step needs a `claim`, or it renders undefined."""
    return {"type": "trace", "steps": list(steps)}


def checkpoint_ref(cp_id: str) -> dict:
    """A REFERENCE to `survey.checkpoints[id]`, never the answer key itself.

    Non-negotiable #6: the key comes from static analysis, not from a model, and
    there is no model in the page to grade a free-text answer. VERIFY
    substitutes the whole object; an unknown id drops the block and logs it.
    """
    return {"type": "checkpoint", "id": cp_id}


def callout(level: str, title: str, text: str) -> dict:
    """A labelled aside. Both strings are required and both are checked here.

    The renderer emits `<b>${esc(b.title)}</b>` unconditionally, so an empty
    title prints the literal word `undefined` — on exactly the stops that carry
    the honest-degradation story, since those are the stops that emit callouts.
    Both strings are escaped by the renderer, so they are passed as plain text:
    running them through `cell` first would double-escape an ampersand.
    """
    if level not in CALLOUT_LEVELS:
        raise ValueError(f"callout level {level!r} not in {sorted(CALLOUT_LEVELS)}")
    if not title or not text:
        raise ValueError(f"callout {title!r} needs a non-empty title and text")
    return {"type": "callout", "level": level, "title": title, "text": text}


def ledger() -> dict:
    """Field-free: it renders `report` + `dropped`. Non-negotiable #3."""
    return {"type": "ledger"}


def claim(cid: str, text: str, cite: dict | None = None) -> dict:
    """One claim in `content@1` form: a verbatim quote, never a line number.

    An `inferred` claim carries no `cite` at all — an anchor is what makes a
    claim render as verified, so an inferred claim holding one is a lie by
    markup and the gate fails it.
    """
    if cite:
        return {"id": cid, "text": text, "status": "verified", "cite": dict(cite)}
    return {"id": cid, "text": text, "status": "inferred"}


def degradation(code: str, **slots) -> dict:
    """§9's callout for one degradation row, with its slots filled.

    Public because §9 puts row 7's emission in `narrate.build_units`, which is
    the one row compose cannot detect on its own: only the narrator knows how
    many units it decided not to run.
    """
    level, title, text = DEGRADATIONS[code]
    return callout(level, title, text.format(**slots))


# --------------------------------------------------------------------------
# Reading Ctx — every accessor tolerates a missing key rather than raising.
# A generation that dies at hour 9 because `survey.churn` was absent is worse
# than one that renders a labelled gap.
# --------------------------------------------------------------------------

def _repo(ctx: Ctx) -> dict:
    return ctx.survey.get("repo") or {}


def _stats(ctx: Ctx) -> dict:
    return ctx.survey.get("stats") or {}


def _nodes(ctx: Ctx) -> list[dict]:
    return list((ctx.map or {}).get("nodes") or [])


def _runs(ctx: Ctx) -> list[dict]:
    return list((ctx.commands or {}).get("runs") or [])


def _skipped(ctx: Ctx) -> list[dict]:
    return list((ctx.commands or {}).get("skipped") or [])


def _candidates(ctx: Ctx) -> list[dict]:
    return list(ctx.survey.get("command_candidates") or [])


def _churn(ctx: Ctx) -> dict:
    return ctx.survey.get("churn") or {}


def _churn_available(ctx: Ctx) -> bool:
    return bool(_churn(ctx).get("available"))


def _kind_of(ctx: Ctx, run: dict) -> str:
    """The candidate `kind` behind an executed run — `setup`, `test`, `lint`, `run`.

    The runner copies `kind` onto its own record, so that is read first; the
    join back to `survey.command_candidates` is the fallback for a
    `commands.json` written before it did. `cmd` is the one string three
    producers share (survey, runner, verify), so it is the only safe join key,
    and `cwd` is compared only when both sides have one — the runner is free to
    record an absolute cwd.
    """
    if run.get("kind"):
        return str(run["kind"])
    for c in _candidates(ctx):
        if c.get("cmd") != run.get("cmd"):
            continue
        if c.get("cwd") and run.get("cwd") and c["cwd"] != run["cwd"]:
            continue
        return str(c.get("kind") or "")
    return ""


def _fire(ctx: Ctx, code: str, **slots) -> dict:
    """Record a §9 row AND return its callout — one row per condition per run.

    The callout is returned unconditionally. A stop that degrades has to *say
    so* on the page every time it renders, and a suppressed callout is exactly
    the silent omission this module refuses to emit.

    The ledger row is a different object, and there is at most one per code.
    `degradations` is a list of *conditions*, not of the places that noticed
    them, and §9 row 6 alone is detected in three (`survey.git_churn`, `mapper`,
    `build_where`). Survey records its row into `survey.json`;
    `verify.assemble` concatenates that list with this one into
    `verification-report.json.degradations`. Without this guard every repo with
    no git history reports `no_churn` twice — invisible to a set comparison,
    wrong in any count or rendered list, and it reads as the same condition
    having happened twice.

    The row already on the ledger wins, so the reason kept is the one written by
    the stage that *detected* the condition and the artifacts stay consistent:
    the `no_churn` row in `verification-report.json` is byte-identical to the
    one in `survey.json` rather than a compose-flavoured rewrite of it. What
    this stage does with the condition — which column it ranked by — is stated
    on the page, in the callout, where a reader will actually meet it.

    `code` names the CALLOUT, `LEDGER_CODE[code]` names the ROW. They differ
    only where one §9 row has two triggers and therefore two honest texts, and
    the dedupe is on the row: two triggers of one condition are one condition.
    """
    block = degradation(code, **slots)
    code = LEDGER_CODE.get(code, code)
    if _reported(ctx, code):
        return block
    row = {"code": code, "reason": block["text"]}
    if "substitute" in slots:
        row["substitute"] = slots["substitute"]
    ctx.degradations.append(row)
    return block


def _record(ctx: Ctx, code: str, reason: str, **extra) -> None:
    """Record a §9 row that emits no callout of its own (rows 8, 9, 10)."""
    ctx.degradations.append({"code": code, "reason": reason, **extra})


def _fired(ctx: Ctx, code: str) -> bool:
    """Did *this stage* record this §9 row? Preconditions ask exactly that."""
    return any(d.get("code") == code for d in ctx.degradations)


def _reported(ctx: Ctx, code: str) -> bool:
    """Has any stage in this run already put this §9 code on the ledger?

    Both lists are consulted because `verify.assemble` concatenates them:
    `survey.json`'s rows and the ones this stage appends land in the same
    `verification-report.json.degradations`, so "already recorded" cannot mean
    "already recorded *here*". Survey's rows are read, never edited — its
    artifact is on disk before compose starts and a later stage rewriting it in
    memory would put the report and `survey.json` out of step.
    """
    if _fired(ctx, code):
        return True
    return any(isinstance(d, dict) and d.get("code") == code
               for d in (ctx.survey.get("degradations") or []))


def _plural(n: int, word: str, plural: str | None = None) -> str:
    """`1 file`, `2 files`. A page that says "1 modules" reads like a template.

    Every count on screen is interpolated through this, because the degraded
    paths — one failing command, one dangling module — are exactly the ones
    where n is 1, and they are the paths the pitch spends its time on.
    """
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def _claims(ctx: Ctx, unit: str) -> list[dict]:
    """The parsed claims for one narrate unit, in `content@1` claim shape.

    Accepts either the provider envelope (`{"claims": [...]}`) or a bare list,
    because `narrate` holds both shapes at different points and a stub miss
    returns `{"claims": []}`. Anything still malformed after `narrate.parse` has
    had its go is skipped: §5.5 makes a `verified` claim with no quote a *drop*
    with a ledger row, and compose has no ledger to write to.
    """
    raw = ctx.narration.get(unit) if ctx.narration else None
    if isinstance(raw, dict):
        raw = raw.get("claims")
    if not isinstance(raw, list):
        return []
    out = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        text = (c.get("text") or "").strip()
        if not text:
            continue
        cite = c.get("cite") if isinstance(c.get("cite"), dict) else None
        if c.get("status") == "inferred":
            cite = None
        elif not (cite and cite.get("quote")):
            continue
        out.append({"text": text, "cite": cite})
    return out


def _numbered(unit: str, claims: Sequence[dict],
              base: int | None = None) -> list[dict]:
    if base is None:
        base = ID_BASE.get(unit, 900)
    return [claim(f"c-{base + i:03d}", c["text"], c.get("cite"))
            for i, c in enumerate(claims)]


def _narration_note(ctx: Ctx) -> dict:
    """§9 row 7 as compose can see it: which of this course's units narrated.

    Every unnarrated stop calls this and every one of them gets its callout;
    `_fire` records the row once. Two rows for one budget would double-count in
    the degradation list the golden files compare.
    """
    # `wanted` must be the units narrate actually planned, not the whole table.
    # narrate builds `trace` only when it has two or more usable hops (the same
    # threshold row 1 fires on), so counting it here on a repo with no hop file
    # prints a denominator one larger than the run ever attempted.
    wanted = [u for u in UNITS
              if (u != "green" or _green_pick(ctx))
              and (u != "trace" or len(ctx.hops or []) >= 2)]
    # Dive units count exactly when narrate planned them, and a planned unit
    # is one present in `ctx.narration` (a stub miss still keys `{claims: []}`).
    wanted += _dive_units(ctx)
    got = [u for u in wanted if _claims(ctx, u)]
    return _fire(ctx, "narration_budget", n=len(got), m=len(wanted))


# --------------------------------------------------------------------------
# Stop builders — one per STOP_TABLE row.
# --------------------------------------------------------------------------

def build_cover(ctx: Ctx) -> list[dict]:
    """`stats` · `callout` · `table`. Survey-derived; nothing model-written.

    The tile row opens the page with the repo's real size and the run's real
    command record, every value computed from `survey.json` and
    `commands.json` (`@3`, spec §6). The table states the anchor scope on
    screen (decision #6): Python source plus the text files the survey
    admitted, and nothing else was read. Saying it here and in the ledger is
    the difference between a stated limit and an implied capability.
    """
    sv, st = _repo(ctx), _stats(ctx)
    runs = _runs(ctx)
    failed = sum(1 for r in runs if r.get("exit") not in (0, None))
    texts = len(ctx.survey.get("text_files") or [])

    if runs:
        ran = (f"Every command on the GET IT RUNNING track was executed on the "
               f"generation machine: {len(runs)} run, {failed} failing. The exit "
               f"codes, the output and the timings are the real ones.")
    else:
        ran = ("No command was executed during generation, so nothing below "
               "claims to have been run.")

    intro = callout(
        "info", "BEFORE YOU START",
        f"This walkthrough was generated from "
        f"{_plural(st.get('py_files', 0), 'Python file')} and "
        f"{_plural(texts, 'other text file')}. Anchors resolve into those files "
        f"and nowhere else; anything outside that scope is out of scope for "
        f"this page, not absent from the repo. {ran}")

    minutes = sum(m for _, _, m in TRACKS)
    entry = _entry_points(ctx)
    rows = [
        [cell("commit"), cell(sv.get("commit") or "unknown", code=True)],
        [cell("surveyed"), cell(sv.get("surveyed_at") or "unknown")],
        [cell("tool"), cell(f"trailhead {TOOL_VERSION}")],
        [cell("python files"),
         cell(f"{st.get('py_files', 0)} of {st.get('files', 0)} files")],
        [cell("modules"),
         cell(f"{st.get('modules', 0)} in {len(_nodes(ctx))} groups on the map")],
        [cell("entry point"),
         cell(entry[0].get("target") or entry[0].get("name") or "unknown",
              code=True)
         if entry else cell("none declared")],
        [cell("commands executed"), cell(f"{len(runs)} ({failed} failing)")],
        [cell("est. reading time"), cell(f"{minutes} minutes")],
    ]
    return [_cover_stats(ctx), intro,
            table([cell("FIELD"), cell("VALUE")], rows,
                  caption="Generation record")]


def _cover_stats(ctx: Ctx) -> dict:
    """The cover tile row (spec §6). Every value formatted from survey facts.

    The dangling tile appears only when the survey found imports with no file
    on disk, coloured `inf` so it reads as the caveat it is. No model comes
    anywhere near these numbers.
    """
    st = _stats(ctx)
    runs = _runs(ctx)
    failed = sum(1 for r in runs if r.get("exit") not in (0, None))
    tiles = [
        {"v": f"{st.get('loc', 0):,}", "l": "LINES OF CODE"},
        {"v": f"{st.get('py_files', 0):,}", "l": "PYTHON FILES",
         "of": f"{st.get('files', 0):,}"},
        {"v": f"{st.get('modules', 0):,}", "l": "MODULES",
         "s": (f"{_plural(len(_nodes(ctx)), 'group')} on the map"
               if _nodes(ctx) else "")},
        {"v": f"{_test_file_count(ctx):,}", "l": "TEST FILES"},
        {"v": f"{len(runs):,}", "l": "COMMANDS RUN", "s": f"{failed} failing"},
    ]
    dangling = ctx.survey.get("dangling") or []
    if dangling:
        n = sum(int(d.get("n") or 0) for d in dangling)
        tiles.append({"v": f"{len(dangling):,}", "l": "MISSING MODULES",
                      "s": f"{_plural(n, 'import statement')} cannot resolve",
                      "color": "inf"})
    return stats(tiles)


def _test_file_count(ctx: Ctx) -> int:
    """Files under a declared test root, straight off `survey.roots`.

    Component-safe containment, not a substring test: `src/tests_extra` is
    not under `src/tests`. No declared test root means zero, which is an
    honest tile on a repo the survey found no test directory in.
    """
    roots = [str(r).replace("\\", "/").strip("/")
             for r in ((ctx.survey.get("roots") or {}).get("test_roots") or [])
             if r]
    if not roots:
        return 0
    n = 0
    for f in ctx.survey.get("files") or []:
        p = str(f.get("path") or "")
        if any(p == r or p.startswith(r + "/") for r in roots):
            n += 1
    return n


def build_five(ctx: Ctx) -> list[dict]:
    """`prose` (5 model claims) · `callout`.

    Claim 5 is expected to come back `inferred` — "what it is not" is an absence
    and an absence cannot be anchored to a line. The callout says so in the same
    breath rather than letting the amber mark look like a failure.
    """
    claims = _numbered("five", _claims(ctx, "five"))
    if not claims:
        return [_narration_note(ctx)]

    if any(c["status"] == "inferred" for c in claims):
        note = callout(
            "inferred", "WHY AN AMBER SENTENCE IS AMBER",
            "An absence cannot be anchored to a line of code. Where this tool "
            "searched and found nothing, it reports that as inferred rather "
            "than dressing it up as verified. Every amber mark in this "
            "document means the same thing: plausible, unproven.")
    else:
        note = callout(
            "info", "EVERY SENTENCE ABOVE IS ANCHORED",
            "Click a claim marker to see the exact lines it was checked "
            "against. Each range was re-read and hash-matched after the "
            "sentence was written; the ones that failed are in the ledger.")
    return [prose(claims), note]


def build_map(ctx: Ctx) -> list[dict]:
    """`graph` · `prose`, or §9 row 4's ALTERNATE: `callout` · `table`.

    The prose here is survey-derived and therefore emitted `inferred`: it is
    true by construction but it is not anchored to a line, and in this document
    "verified" means exactly one thing — an anchor that re-read and hash-matched.
    Decision #19 cut per-node model narration; `node.why` is a template in
    `mapper`.
    """
    nodes = _nodes(ctx)
    if len(nodes) < 3:
        note = _fire(ctx, "few_modules", n=len(nodes))
        rows = [[cell(n.get("label", "?"), code=True),
                 cell(n.get("files", 0)),
                 cell(f"{n.get('loc', 0):,}"),
                 cell(_edge_count(ctx, n.get("id")))] for n in nodes]
        if not rows:
            return [note]
        # IMPORTS sums clamped edge weights, so the caption states the clamp on
        # the repos where it bites (§4.1: state the cap in the map stop). A
        # table cell has no claim marker and nothing downstream re-checks it.
        caption = "The module groups the survey found."
        if _edges_clamped(ctx):
            caption += (f" IMPORTS sums edge weights, and the map clamps every "
                        f"edge at {EDGE_CAP}, so a row at or above that is a "
                        f"floor rather than a count.")
        return [note, table([cell("PATH"), cell("FILES"), cell("LOC"),
                             cell("IMPORTS")], rows, caption=caption)]

    st, diag = _stats(ctx), (ctx.map or {}).get("diagnostics") or {}
    big = max(nodes, key=lambda n: n.get("loc", 0))
    said = [
        f"{st.get('modules', len(nodes))} modules collapse into "
        f"{len(nodes)} groups on this map; the largest is "
        f"{big.get('label', '?')} at {big.get('loc', 0):,} lines across "
        f"{big.get('files', 0)} files.",
    ]
    edges = (ctx.map or {}).get("edges") or []
    if edges:
        # By node LABEL, never by node id: `n-cli` is a slug the reader has
        # never seen, and the label is what the map draws.
        label = {n.get("id"): n.get("label", n.get("id")) for n in nodes}
        said.append(_heaviest_edge(edges, label))
    back = diag.get("edges_dropped_backward")
    if back:
        said.append(
            f"Backward edges, {back} of them, are counted but not drawn: a "
            f"right-to-left edge crosses the whole canvas and reads as a band "
            f"rather than as a dependency.")
    return [graph(), prose(_numbered("map", [{"text": s} for s in said[:3]]))]


def build_where(ctx: Ctx) -> list[dict]:
    """`table` (PATH/PURPOSE/FILES/LOC/metric[/committers]).

    Decision #20: the purpose cell is the package `__init__.py` docstring's
    first sentence, or an honest gap. Never model prose — a table cell has no claim
    marker, no anchor, and `verify-contract.js` never walks one, so a model
    sentence in a cell is an unverified factual claim on the stop a joiner reads
    second. Prose about the layout goes in the `map` stop above.

    The metric column prints the metric itself — the real commit count, the
    fan-in, the loc — never the row's 1..n rank. A rank under a COMMITS
    header reads as commit numbers the history does not contain, which is a
    fabrication in everything but authorship, on the one page whose pitch is
    that it fabricates nothing.

    §9 row 6: with no git history the metric column is relabelled in place.
    The committers column exists only when some row actually has a committer:
    a snapshot repo has git history but no per-module committers, and a
    column of `n/a` repeated down every row is dropped rather than padded.
    """
    rows_src = _where_rows(ctx)
    if not rows_src:
        return [callout("info", "NO MODULE GROUPS FOUND",
                        "The survey found no importable package under an "
                        "import root, so there is nothing to list here.")]

    label = _rank_label(ctx)
    ranked = sorted(rows_src, key=lambda r: (-r["rank_by"], r["path"]))
    committers = _churn_available(ctx) and any(r["committers"] for r in ranked)

    columns = [cell("PATH"), cell("PURPOSE"), cell("FILES"), cell("LOC"),
               cell(label.upper())]
    if committers:
        columns.append(cell("RECENT COMMITTERS"))

    rows = []
    for r in ranked:
        row = [cell(r["path"] + "/", code=True), cell(r["purpose"]),
               cell(r["files"]), cell(f"{r['loc']:,}"),
               cell(f"{r['rank_by']:,}")]
        if committers:
            row.append(cell(", ".join(r["committers"][:2]) or "n/a"))
        rows.append(row)

    caption = ("Sortable. Purpose is each package's __init__ docstring, not a "
               "description of it.")
    blocks = [table(columns, rows, caption=caption, sortable=True)]
    if not _churn_available(ctx):
        # The callout is emitted here whatever survey did — the reader meets the
        # condition on this stop, not in `survey.json`. The ledger row is
        # `_fire`'s call: survey detected the same condition and already
        # recorded it, so this appends nothing and `no_churn` appears once.
        blocks.insert(0, _fire(
            ctx, "no_churn",
            reason=_churn(ctx).get("reason")
            or "This path has no tracked history in the enclosing repository.",
            substitute=label.lower()))
    return blocks


def build_cp(ctx: Ctx, ids: Sequence[str]) -> list[dict]:
    """`checkpoint` × n — references only, resolved by VERIFY from survey.

    Bound to its ids with `functools.partial` in the STOP_TABLE, because both
    checkpoint stops share this builder and a builder cannot know which row it
    was called for.
    """
    keys = ctx.survey.get("checkpoints") or {}
    return [checkpoint_ref(i) for i in ids if i in keys]


def build_setup(ctx: Ctx) -> list[dict]:
    """`command` × n · `callout`. §9 row 3 when every setup command failed.

    A failing command is shown failing, in full, with its real exit code and its
    real output. That is the whole point of the stop: the alternative is a page
    that tells a new joiner to run something that has never worked.
    """
    green = _green_pick(ctx)
    runs = [r for r in _runs(ctx) if r is not green]
    blocks: list[dict] = []

    setups = [r for r in runs if _kind_of(ctx, r) == "setup"]
    if setups and all(r.get("exit") not in (0, None) for r in setups):
        blocks.append(_fire(ctx, "setup_all_failed", n=len(setups)))

    for i, r in enumerate(runs):
        predict = None
        if i == 0:
            predict = (f"Before you look: on a clean checkout of this repo, "
                       f"does {r.get('cmd', 'this command')} pass?")
        blocks.append(command(r.get("cmd", ""), r.get("cwd", "."),
                              hypothesis=r.get("hypothesis"), predict=predict))

    skipped = _skipped(ctx)
    if skipped:
        blocks.append(callout("info", "NOT EXECUTED", _skipped_text(skipped)))

    if not runs:
        # `runs` excludes whatever the green stop took. Fire no_commands on what
        # the RUNNER did, not on what is left after that pick — otherwise a repo
        # whose single admitted command went to the green stop reads
        # "no commands were executed" on the stop directly above a command block
        # showing that command exiting 0. A page contradicting itself is the one
        # defect this project cannot ship.
        if _runs(ctx):
            blocks.append(callout(
                "info", "NOTHING ADDITIONAL TO SHOW HERE",
                "The one command the allowlist admitted for this repo is shown "
                "under “Your first green test”."))
        else:
            blocks.append(_fire(ctx, "no_commands",
                                candidates=_candidate_list(ctx) or "none found"))
        return blocks + _restore_ledger(ctx)

    failed = sum(1 for r in runs if r.get("exit") not in (0, None))
    if failed:
        blocks.append(callout(
            "broken", "WHAT THE FAILURES ABOVE MEAN FOR YOU",
            f"{failed} of {_plural(len(runs), 'command')} failed during "
            f"generation, on a clean checkout. Do not spend your first morning "
            f"believing you broke them. Nothing above was written by a model: "
            f"the exit codes, the output and the timings are the captured "
            f"ones."))
    else:
        blocks.append(callout(
            "info", "EVERY COMMAND ABOVE WAS EXECUTED",
            f"Every command above ({_plural(len(runs), 'command')}) ran during "
            f"generation and passed. The output shown is the captured output, "
            f"not an example of what it should look like."))
    return blocks + _restore_ledger(ctx)


def _restore_ledger(ctx: Ctx) -> list[dict]:
    """The missing-modules table and callout (`@3`, spec §6), or `[]`.

    When `survey.dangling` is non-empty the setup stop closes with the RESTORE
    LEDGER: every module the repo imports that has no file on disk at this
    commit, ranked by import statements, capped at 20 rows. The wording is
    generic on purpose ("at this commit"): a dangling import is a fact about
    the tree, not a story about how the tree got that way. All of it is
    survey-derived and the callout names the top offenders because those are
    the ModuleNotFoundErrors a new joiner will hit first.
    """
    dangling = [d for d in (ctx.survey.get("dangling") or [])
                if isinstance(d, dict) and d.get("target")]
    if not dangling:
        return []

    ranked = sorted(dangling,
                    key=lambda d: (-int(d.get("n") or 0), str(d.get("target"))))
    rows = []
    for d in ranked[:20]:
        sites = [str(s.get("file")) for s in (d.get("sites") or [])
                 if isinstance(s, dict) and s.get("file")]
        files = list(dict.fromkeys(sites))
        if files:
            shown = ", ".join(files[:2])
            rest = len(files) - 2
            frm = f"{shown}, and {rest} more" if rest > 0 else shown
        else:
            frm = "unknown"
        rows.append([cell(str(d.get("target")), code=True), cell(frm),
                     cell(f"{int(d.get('n') or 0):,}")])

    caption = ("Missing at this commit: modules imported somewhere in this "
               "repo that have no file on disk. IMPORT SITES counts import "
               "statements.")
    if len(ranked) > 20:
        caption += (f" Showing the top 20 of {len(ranked)} by import "
                    f"statement count.")
    tbl = table([cell("MISSING MODULE"), cell("IMPORTED FROM"),
                 cell("IMPORT SITES")], rows, caption=caption, sortable=True)

    total = sum(int(d.get("n") or 0) for d in dangling)
    top = ", ".join(
        f"{d.get('target')} ({_plural(int(d.get('n') or 0), 'import')})"
        for d in ranked[:3])
    note = callout(
        "broken", "MISSING AT THIS COMMIT",
        f"The survey counted {_plural(len(dangling), 'imported module')} with "
        f"no file on disk at this commit, across "
        f"{_plural(total, 'import statement')}. The heaviest: {top}. Code "
        f"paths that reach these imports fail with ModuleNotFoundError until "
        f"the modules are restored.")
    return [tbl, note]


def build_green(ctx: Ctx) -> list[dict]:
    """`command` · `prose` · `callout`, per §5.7's three rules.

    Rule 2 is the honest reading of spec stop 6 and the better demo beat: show a
    green command and say in the same breath that it is not the thing you
    wanted. A repo with no runnable test suite gets §9 row 2's callout naming
    every candidate that was considered and why each was denied.
    """
    pick = _green_pick(ctx)
    is_test = bool(pick) and _kind_of(ctx, pick) == "test"
    blocks: list[dict] = []

    if not is_test:
        blocks.append(_fire(ctx, "no_test_command",
                            candidates=_test_candidates(ctx)))
    if not pick:
        return blocks

    blocks.append(command(
        pick.get("cmd", ""), pick.get("cwd", "."),
        hypothesis=pick.get("hypothesis"),
        predict=f"Before you look: does {pick.get('cmd', 'this command')} pass "
                f"on this machine?"))

    claims = _numbered("green", _claims(ctx, "green"))
    if claims:
        blocks.append(prose(claims))

    if is_test:
        blocks.append(callout(
            "info", "IF THIS PASSES, YOUR ENVIRONMENT IS CORRECT",
            "This is the repo's own test command, executed during generation. "
            "If it passes for you too, stop configuring things and start "
            "reading."))
    else:
        blocks.append(callout(
            "info", "THIS IS A SMOKE CHECK, NOT A TEST SUITE",
            f"{pick.get('cmd', 'The command above')} proves the package "
            f"imports from the source root the survey resolved. It does not "
            f"run a single test, and this page will not pretend otherwise."))
    return blocks


def _dive_units(ctx: Ctx) -> list[str]:
    """Every `dive:<gid>` unit in this run's narration, in map order.

    Map order is the mapper's left-to-right pipeline order, so the dive track
    reads in the same direction as the board above it. Units whose gid matches
    no node sort after the matched ones, then alphabetically, so the order
    stays deterministic even on a map that has moved since narration.
    """
    units = [u for u in (ctx.narration or {})
             if isinstance(u, str) and u.startswith(DIVE_UNIT_PREFIX)
             and len(u) > len(DIVE_UNIT_PREFIX)]
    return sorted(units, key=lambda u: (
        _dive_node(ctx, u[len(DIVE_UNIT_PREFIX):])[1], u))


def _dive_node(ctx: Ctx, gid: str) -> tuple[dict | None, int]:
    """The map node a dive gid names, and its index in the node order.

    Narrate keys dive units by map group; the join tolerates the node id with
    or without its `n-` prefix and falls back to label and path, because the
    two stages have different owners and a silent join miss would quietly
    demote every dive stop to prose-only. A total miss returns `(None, N)` so
    unmatched units sort last and still render under their own name.
    """
    nodes = _nodes(ctx)
    for probe in (lambda n: n.get("id") == gid,
                  lambda n: n.get("id") == f"n-{gid}",
                  lambda n: n.get("label") == gid,
                  lambda n: n.get("path") == gid):
        for i, n in enumerate(nodes):
            if probe(n):
                return n, i
    return None, len(nodes)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s or "group"


def _build_dives(ctx: Ctx) -> list[dict]:
    """The INSIDE THE SYSTEM stops: one per `dive:<gid>` unit that came back.

    Blocks per stop: `prose` (the dive claims), an `excerpt` when the map node
    carries an anchor, and a `stats` tile row computed from the node and the
    map edges. A unit with no surviving claims produces NO stop: a dive with
    nothing to say is omitted, and the omission is recorded once via `_fire`
    under `dive_empty`. The callout `_fire` returns here has no stop to sit
    on, so it is dropped and `build_audit` re-emits an identical one from the
    recorded row, on the close track, where a reader looks for what the page
    did not do.
    """
    stops: list[dict] = []
    used: set[str] = set()
    for i, unit in enumerate(_dive_units(ctx)):
        gid = unit[len(DIVE_UNIT_PREFIX):]
        node, _ = _dive_node(ctx, gid)
        label = str((node or {}).get("label") or gid)
        claims = _claims(ctx, unit)
        if not claims:
            # An unanswered dive unit is indistinguishable here from one that
            # was never planned: absence-by-default (spec section 4) means a
            # cold run must produce the exact @2 course, so the omission is
            # silent. Answers the parser refused already sit in the ledger.
            continue

        base = DIVE_ID_BASE + DIVE_ID_STRIDE * i
        blocks = [prose(_numbered(unit, claims, base=base))]
        anchor = (node or {}).get("anchor")
        if isinstance(anchor, dict) and anchor:
            blocks.append(excerpt(
                anchor, str((node or {}).get("anchor_caption") or "")))
        if node:
            blocks.append(_group_stats(ctx, node))

        want = f"dive-{_slug(gid)}"
        sid, k = want, 2
        while sid in used:
            sid, k = f"{want}-{k}", k + 1
        used.add(sid)
        stops.append({"id": sid, "title": f"Inside {label}", "kind": "stop",
                      "minutes": DIVE_MINUTES, "blocks": blocks,
                      "lede": _lede_dive(label, len(stops))})
    return stops


def _group_stats(ctx: Ctx, node: dict) -> dict:
    """One dive stop's tile row: group size and coupling, all from `map.json`.

    Fan counts are distinct group edges on the emitted map, which is the same
    graph the reader is looking at; self edges never count.
    """
    nid = node.get("id")
    edges = (ctx.map or {}).get("edges") or []
    fan_in = sum(1 for e in edges
                 if e.get("b") == nid and e.get("a") != nid)
    fan_out = sum(1 for e in edges
                  if e.get("a") == nid and e.get("b") != nid)
    return stats([
        {"v": f"{int(node.get('loc') or 0):,}", "l": "LINES OF CODE"},
        {"v": f"{int(node.get('files') or 0):,}", "l": "FILES"},
        {"v": f"{fan_in:,}", "l": "FAN-IN",
         "s": "groups that import this one"},
        {"v": f"{fan_out:,}", "l": "FAN-OUT",
         "s": "groups this one imports"},
    ])


#: The dive-stop lede templates, dealt by stop position on the DIVE track so
#: adjacent stops never open with the same sentence. One sentence stamped
#: across every dive reads as the template it is; four rotated ones read as a
#: written page while staying exactly as deterministic (#20c): the rotation is
#: keyed by position, never by a random draw, so a cold rerun deals the same
#: lede to the same stop. Every template states only what is true of every
#: dive stop — the claim-marker contract — because a lede has no claim marker
#: and cannot promise blocks (an excerpt, a tile row) a given stop may lack.
DIVE_LEDES = (
    "A closer read of {label}. The claims here are checked the same way as "
    "everywhere else on this page, and anything marked INFERRED could not be "
    "anchored to a line and says so.",
    "What {label} actually does, read from its own source. Each sentence "
    "carries a claim marker, and the sentences that failed their re-check "
    "are in the ledger rather than on this stop.",
    "A few minutes inside {label}. The rules are the same here as on every "
    "other stop: a sentence is either anchored to a real line range or "
    "marked as unproven on its face.",
    "The shape of {label}, up close. Nothing below asks to be taken on "
    "trust; every claim marker opens the evidence behind its sentence, or "
    "says plainly that there is none.",
)


def _lede_dive(label: str, index: int) -> str:
    """One of DIVE_LEDES, dealt by the stop's position on the DIVE track.

    `index` counts emitted stops, not narration units, so a dive that came
    back empty and was omitted does not leave a hole in the rotation: the
    stops that do render still cycle through the templates in order, and two
    neighbours can never share one.
    """
    return DIVE_LEDES[index % len(DIVE_LEDES)].format(label=label)


def build_trace(ctx: Ctx) -> list[dict]:
    """`trace` · `callout`, from the hand-specified hops (decision #25).

    Every hop is ONE contiguous window with its focus lines inside it, because
    an anchor is a single `start..end` range: a hop specified as three scattered
    linenos is not expressible and fails the gate. The anchors are survey-derived
    and the sentences are the model's, one per hop — a mismatch in those two
    counts renders `esc(undefined)` inside a claim span, so a missing sentence
    falls back to the hop's own deterministic one rather than going blank.

    §9 row 1: fewer than two hops, or no entry point at all, and the stop
    becomes a labelled callout — which also drops `cp-c`, whose answer key is
    hop 7's file.

    **The two triggers get two texts.** The entry-point half is a fact about the
    repo; the hops half is a fact about what this run was given, since decision
    #25 makes the chain hand-specified input. One text for both meant a repo
    with five entry points was told it had none, immediately above a list of
    those five — a deterministic sentence contradicted by the `survey.json`
    sitting beside it, on a page whose whole claim is that it deletes sentences
    like that. Which trigger fired is checked first and the text follows it.
    """
    hops = list(ctx.hops or [])
    entries = _entry_points(ctx)
    if not entries:
        return [_fire(ctx, "no_trace",
                      candidates=_entry_list(ctx) or "none found")]
    if len(hops) < 2:
        return [_fire(ctx, "no_trace_hops",
                      n=_plural(len(entries), "entry point"),
                      candidates=_entry_list(ctx),
                      fixture=_hops_fixture_name(ctx),
                      hops=_plural(len(hops), "hop"))]

    said = _claims(ctx, "trace")
    predicts = _trace_predicts(hops)
    steps = []
    for i, h in enumerate(hops):
        nxt = hops[i + 1] if i + 1 < len(hops) else None
        step = {
            "claim": _hop_claim(h, said[i] if i < len(said) else None),
            "cite": {"file": h["file"], "quote": h["quote"],
                     "focus": list(h.get("focus") or [])},
            "next": (f"{nxt['symbol']} in {nxt['file']}" if nxt else None),
        }
        if predicts[i]:
            step["predict"] = (
                f"This hop ends in {h['file'].split('/')[-1]}. Which file does "
                f"the path reach next?")
        steps.append(step)

    dangling = ctx.survey.get("dangling") or []
    if dangling:
        names = ", ".join(str(d.get("target")) for d in dangling[:2])
        tail = (f" The deterministic stage also found "
                f"{_plural(len(dangling), 'imported module')} with no file on "
                f"disk ({names}), so parts of this path cannot run as written.")
    else:
        tail = ""
    note = callout(
        "inferred", "WHAT THIS TRACE DOES NOT PROVE",
        f"The hops above are a static read of the source: each anchor was "
        f"re-read and hash-matched, but nothing was executed along this path "
        f"during generation.{tail}")
    return [trace(steps), note]


def build_conv(ctx: Ctx) -> list[dict]:
    """`callout` · `prose`, every claim forced `inferred` in code.

    Spec §3 stop 13 quarantines this stop: the most useful content is the least
    checkable, so rather than diluting the verified stops it is marked once,
    loudly. The override is here and in the parser, not in the prompt, so the
    quarantine holds even if the prompt drifts.
    """
    note = callout(
        "inferred", "THIS ENTIRE STOP IS UNVERIFIED",
        "Nothing below could be anchored to a line. It is a read of the "
        "codebase, quarantined here and marked once rather than mixed into the "
        "verified material and diluting it.")
    quarantined = [{"text": c["text"]} for c in _claims(ctx, "conv")]
    if not quarantined:
        return [note, _narration_note(ctx)]
    return [note, prose(_numbered("conv", quarantined))]


def build_audit(ctx: Ctx) -> list[dict]:
    """`callout` · `ledger`. Never cut, never filtered, always last.

    §9 rows 8, 9 and 10 land here: a dropped stop is named in a callout and
    never in `dropped[]`, because `report.dropped === dropped.length` is a hard
    gate cross-check and stuffing stop-skips there inflates the one number the
    whole pitch turns on.
    """
    blocks = [callout(
        "info", "WHY THIS PAGE EXISTS",
        "Anyone can generate confident documentation. The only useful question "
        "is which parts to trust. The claims below were written by a model and "
        "then deleted by ordinary code because their anchors did not resolve. "
        "They are shown, not swept up.")]

    scope = _scope_text(ctx)
    if scope:
        blocks.append(callout("info", "WHAT THIS PAGE DID NOT READ", scope))

    dropped = [d for d in ctx.degradations if d.get("code") == "stop_dropped"]
    if dropped:
        rows = "; ".join(f"{d.get('stop')}: {d.get('reason')}" for d in dropped)
        blocks.append(degradation("stops_dropped", rows=rows))

    # Dive units that came back empty were omitted from the DIVE track, so
    # their `_fire` callout had no stop to sit on. The row is on the ledger;
    # this re-emits its callout here, where a reader looks for omissions.
    empty_dives = [d for d in ctx.degradations if d.get("code") == "dive_empty"]
    if empty_dives:
        blocks.append(callout("info", DEGRADATIONS["dive_empty"][1],
                              empty_dives[0]["reason"]))

    blocks.append(ledger())
    return blocks


# --------------------------------------------------------------------------
# Ledes — one per stop, and every one a deterministic template (#20c).
#
# A lede is a factual sentence on a surface with no claim marker, so it must
# stay true on the degraded path too: "8 hops, each one a real line range" over
# a stop that is one callout because no entry point was found is exactly the
# kind of small lie that costs the whole pitch its credibility.
# --------------------------------------------------------------------------

def _lede_cover(ctx: Ctx) -> str:
    r = _repo(ctx)
    return (f"A generated walkthrough of {r.get('name', 'this repo')} at "
            f"{r.get('commit', 'an unknown commit')}. Every factual sentence "
            f"below is anchored to a line range in this repo and re-checked "
            f"after it was written. Claims whose anchors failed were deleted, "
            f"not softened, and the count is in the top bar.")


def _lede_five(ctx: Ctx) -> str:
    if not _claims(ctx, "five"):
        return ("This stop had no narration in this run, so it renders from "
                "templates and carries no claims. The callout says so.")
    return ("If you read nothing else, read these. Anything marked INFERRED "
            "could not be anchored to a line, and says so rather than hoping "
            "you do not check.")


def _lede_map(ctx: Ctx) -> str:
    if len(_nodes(ctx)) < 3:
        return ("Too few module groups to draw a graph worth reading. The "
                "table below carries the same information.")
    # The guided tour is promised only when the map actually carries one:
    # inviting a click on a button that is not there is a small lie on a
    # surface with no claim marker.
    if (ctx.map or {}).get("tour"):
        act = "Click any module, or take the guided tour."
    else:
        act = "Click any module."
    return (f"Derived from the real import graph, not from a description of "
            f"it. Node area is lines of code and edge weight is import count; "
            f"{_map_caveat(ctx)} {act}")


def _lede_where(ctx: Ctx) -> str:
    # The lede promises only what the table below it shows. "Ranked by
    # commits" over a column of identical counts describes a ranking that
    # does not exist, so the degenerate-churn mode gets its own sentence.
    rows = _where_rows(ctx)
    if not rows:
        return ("The survey found no importable package under an import root, "
                "so there is nothing to list here.")
    if _churn_available(ctx) and _churn_degenerate(rows):
        return ("The same information as the map, as a list, for the people "
                "who prefer lists. The commit counts shown are real but "
                "identical for every module, which is what a tree committed "
                "in one snapshot looks like, so the rows are ordered by path "
                "rather than by history. The purpose column is each package's "
                "own __init__ docstring.")
    return (f"The same information as the map, as a list, for the people who "
            f"prefer lists. Ranked by {_rank_label(ctx).lower()}, and the "
            f"purpose column is each package's own __init__ docstring.")


def _lede_setup(ctx: Ctx) -> str:
    if not _runs(ctx):
        return ("Nothing in this repo was executed during generation, so this "
                "stop makes no claim about what runs. The callout says which "
                "candidates were considered.")
    return ("Every command here was executed on the generation machine. The "
            "output is real, the timings are real, and so are the failures.")


def _lede_green(ctx: Ctx) -> str:
    if not _green_pick(ctx):
        return ("Nothing this tool was allowed to run passed, so there is no "
                "green command to show you. That is the repo's current state, "
                "not an omission.")
    return ("One command. If this passes, your environment is correct and you "
            "can stop configuring things.")


def _lede_trace(ctx: Ctx) -> str:
    # Two triggers, two ledes, for the reason given in `build_trace`: a lede
    # carries no claim marker, so the degraded one has to be as true as the
    # callout it sits above. Telling a repo with entry points that it has none
    # would be the same lie twice on one stop.
    hops = ctx.hops or []
    if not _entry_points(ctx):
        return ("This repo has no traceable entry point, so there is no chain "
                "to follow. The callout below names what was considered.")
    if len(hops) < 2:
        return (f"The hops for this stop are hand-specified input, and this run "
                f"had {_plural(len(hops), 'hop')} for this repo. Fewer than two "
                f"is not a chain to follow, so the callout below says what was "
                f"and was not found instead.")
    return (f"{_plural(len(hops), 'hop')}, each one a real line range in this "
            f"repo, from the entry point to where the work actually happens. "
            f"This is the path to hold in your head.")


def _lede_conv(ctx: Ctx) -> str:
    return ("Everything on this page is inferred from patterns in the code. "
            "None of it is verified against a written standard, because this "
            "repo does not have one. Treat it as a strong hint, not a rule.")


def _lede_audit(ctx: Ctx) -> str:
    return ("What the tool claimed, what survived, and what it deleted. The "
            "deleted rows are the interesting ones.")


# --------------------------------------------------------------------------
# Preconditions
# --------------------------------------------------------------------------

def _always(ctx: Ctx) -> str | None:
    """Stops that degrade inside their own builder never fail a precondition."""
    return None


def _needs_checkpoints(ids: Sequence[str], ctx: Ctx) -> str | None:
    """Both keys present and each offering at least four real options.

    §9 row 8. Never render a placeholder quiz: "Checkpoint A unavailable" is
    worse than no checkpoint, and padding the options with invented distractors
    puts a fabrication into an artifact whose entire claim is that it has none.
    """
    keys = ctx.survey.get("checkpoints") or {}
    missing = [i for i in ids if i not in keys]
    if missing:
        return f"no survey answer key for {', '.join(missing)}"
    thin = [i for i in ids if len(keys[i].get("options") or []) < 4]
    if thin:
        return f"fewer than four real options for {', '.join(thin)}"
    return None


def _needs_trace(ctx: Ctx) -> str | None:
    """`cp-c2`'s answer is hop 7's file, so no trace means no checkpoint C.

    Asking `_fired` about the ROW and not about either trigger is why row 1 kept
    one ledger code: this precondition wants "did the trace stop degrade", which
    is one question however many ways there are to reach it. The REASON follows
    the trigger, though: the entry-point half is a fact about the repo, the
    hops half is a fact about what this run was given, and each fixture repo's
    `expect.json` pins the half that is true for it. One text for both meant
    a repo with entry points was told it had none, the same wording defect
    `build_trace` fixed in its callout.
    """
    if _fired(ctx, "no_trace"):
        if not _entry_points(ctx):
            return ("no traceable entry point, so the trace stop was not "
                    "generated")
        return ("fewer than two hops were specified, so the trace stop was "
                "not generated")
    return _needs_checkpoints(("cp-c1", "cp-c2"), ctx)


# --------------------------------------------------------------------------
# THE STOP TABLE — decision #13. Deterministic, and the only place a stop
# exists. Genericity is a data question here, not a control-flow question.
# --------------------------------------------------------------------------

STOP_TABLE = (
    StopSpec("cover", "What you are looking at", "ORIENT", 2, "stop",
             _always, build_cover, PLACEHOLDER, _lede_cover),
    StopSpec("five", "Five sentences", "ORIENT", 4, "stop",
             _always, build_five, PLACEHOLDER, _lede_five),
    StopSpec("map", "The map", "ORIENT", 5, "stop",
             _always, build_map, ALTERNATE, _lede_map),
    StopSpec("where", "Where the code lives", "ORIENT", 4, "stop",
             _always, build_where, ALTERNATE, _lede_where),
    StopSpec("cp-a", "Checkpoint A", "ORIENT", 3, "cp",
             partial(_needs_checkpoints, ("cp-a1", "cp-a2")),
             partial(build_cp, ids=("cp-a1", "cp-a2")), DROP),
    StopSpec("setup", "Prerequisites and setup", "RUN", 8, "stop",
             _always, build_setup, PLACEHOLDER, _lede_setup),
    StopSpec("green", "Your first green test", "RUN", 4, "stop",
             _always, build_green, PLACEHOLDER, _lede_green),
    StopSpec("trace", "One path, end to end", "READ", 12, "stop",
             _always, build_trace, ALTERNATE, _lede_trace),
    StopSpec("cp-c", "Checkpoint C", "READ", 4, "cp",
             _needs_trace, partial(build_cp, ids=("cp-c1", "cp-c2")), DROP),
    StopSpec("conv", "Conventions and gotchas", "CONV", 8, "stop",
             _always, build_conv, PLACEHOLDER, _lede_conv),
    StopSpec("audit", "The ledger", "AUDIT", 6, "stop",
             _always, build_audit, PLACEHOLDER, _lede_audit),
)


def build_gloss(glossary: Sequence[dict] | None) -> dict | None:
    """The CLOSE track's glossary stop (`@3`, spec §6), or None to omit it.

    The entries are the payload `glossary` the verify stage attaches: term and
    definition survive verification even when an entry's anchor fails (only
    the anchor is dropped), so every surviving entry is listable here. No
    glossary, no stop, which is what keeps a no-glossary run rendering
    exactly as `@2` did. Terms are the popover targets of the page's dotted
    `[[...]]` markers; the table is the same content as a flat list.
    """
    entries = [g for g in (glossary or [])
               if isinstance(g, dict)
               and str(g.get("term") or "").strip()
               and str(g.get("def") or "").strip()]
    if not entries:
        return None
    rows = [[cell(str(g["term"]).strip(), bold=True),
             cell(str(g["def"]).strip())] for g in entries]
    tbl = table([cell("TERM"), cell("DEFINITION")], rows,
                caption=("Click any dotted term in the prose to open the "
                         "same definition in place."),
                sortable=True)
    return {"id": "gloss", "title": "The glossary", "kind": "stop",
            "minutes": 2, "blocks": [tbl],
            "lede": ("Every dotted term on this page, in one table. The "
                     "definitions travel with the page and open in place "
                     "when you click a term.")}


def _typed(stop_id: str, blocks: Sequence[dict]) -> list[dict]:
    """The closed-vocabulary check, shared by table stops and dive stops."""
    blocks = list(blocks)
    for b in blocks:
        if b.get("type") not in BLOCK_TYPES:
            raise ValueError(
                f"stop {stop_id} emitted block type {b.get('type')!r}, "
                f"which the renderer has no arm for")
    return blocks


def build_course(ctx: Ctx, glossary: list[dict] | None = None) -> list[dict]:
    """`tracks[]` for `content@1`: the whole course, preconditions applied.

    Runs the table in order, because later stops read what earlier ones
    reported: `cp-c`'s precondition asks whether `trace` degraded, and `audit`
    lists every stop that dropped. The `audit` stop is hard-guarded — verified
    by experiment, stripping every ledger block from the fixture still leaves
    `verify-contract.js` exiting 0 with ALL CHECKS PASS, so nothing mechanical
    stops a ledger-less page.

    `@3` additions, both absent-by-default so a bare `@2` run is unchanged:
    the DIVE track is assembled first (so `build_audit`, which runs last,
    sees any `dive_empty` row), and `glossary` is the verified glossary the
    caller wants listed on the CLOSE track; None or empty means no stop.
    """
    built: dict[str, list[dict]] = {}

    dives = _build_dives(ctx)
    for s in dives:
        _typed(s["id"], s["blocks"])
    if dives:
        built["DIVE"] = dives

    for spec in STOP_TABLE:
        reason = spec.precondition(ctx)
        if reason and spec.on_fail == DROP and spec.id != AUDIT_STOP:
            _record(ctx, "stop_dropped", reason, stop=spec.id)
            continue

        blocks = _typed(spec.id, spec.build(ctx))
        if spec.kind == "cp" and not any(b["type"] == "checkpoint" for b in blocks):
            # A checkpoint stop with no checkpoint would auto-tick itself
            # complete and teach nothing. Drop it and say so in the audit.
            _record(ctx, "stop_dropped", "no checkpoint block survived",
                    stop=spec.id)
            continue
        if not blocks:
            # Never a blank stop: the renderer and the gate both walk
            # `stop.blocks` unconditionally, and a labelled gap reads as a tool
            # that knows what it does not know.
            blocks = [callout("info", "NOTHING TO SHOW HERE",
                              f"{spec.id} had no content to render and was not "
                              f"silently omitted.")]

        stop = {"id": spec.id, "title": spec.title, "kind": spec.kind,
                "minutes": spec.minutes, "blocks": blocks}
        if spec.kind == "stop":
            # `lede` is required on a stop and omitted on a cp — that is what
            # the frozen fixture does and the renderer treats it as optional.
            stop["lede"] = spec.lede(ctx) if spec.lede else spec.title
        built.setdefault(spec.track, []).append(stop)

    gloss = build_gloss(glossary)
    if gloss:
        # Before the audit stop, which stays last on the page (AUDIT is the
        # final track and `audit` is appended by the loop above).
        _typed(gloss["id"], gloss["blocks"])
        built.setdefault("AUDIT", []).insert(0, gloss)

    return [{"title": title, "minutes": minutes, "stops": built[key]}
            for key, title, minutes in TRACKS if built.get(key)]


# --------------------------------------------------------------------------
# The hand-specified trace (decision #25)
# --------------------------------------------------------------------------

#: `chain.py` was cut at hour 0, not hour 5: extracting a call chain generically
#: is a day of work and the hops for the demo repo are already known. This file
#: is the pivot-rule safety net, so it is checked in and tested against disk.
HOPS_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "trace.restored.json"


def load_hops(path: Path | None = None) -> list[dict]:
    """The hop list for `Ctx.hops`, or `[]` when there is none for this repo.

    A missing file is not an error: an unknown repo simply has no hand-specified
    trace, and §9 row 1 turns that into a labelled callout instead of a stop
    full of invented hops.
    """
    p = Path(path) if path else HOPS_FIXTURE
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as fh:
        return list(json.load(fh).get("hops") or [])


def _trace_predicts(hops: Sequence[dict]) -> list[bool]:
    """Which hops may ask the reader to predict the next file.

    Three conditions, and all three are load-bearing. The first two are
    `verify-contract.js:110`: the last hop has no next anchor to key against,
    and a next hop in the same file makes the question trivial. The third is the
    renderer, which keys prediction state as `pid = "pt:" + s.anchor.file`, so
    two predicts in one file collide on one localStorage slot and answering the
    first silently answers the second.
    """
    seen: set[str] = set()
    out = []
    for i, h in enumerate(hops):
        ask = (i + 1 < len(hops)
               and hops[i + 1].get("file") != h.get("file")
               and h.get("file") not in seen)
        if ask:
            seen.add(h["file"])
        out.append(ask)
    return out


def _hop_claim(hop: dict, said: dict | None) -> str:
    """The model's sentence for this hop, or the hop's own deterministic one.

    The model sentence is used only when the model was demonstrably looking at
    this hop's file: the anchor is hand-specified, so a sentence citing some
    other file is describing something else and would render as verified against
    code it never saw. The fallback keeps the hop's anchor and swaps the
    sentence, which is why a trace hop is never blank and never carries an
    unverifiable sentence dressed as verified.
    """
    if said and said.get("text"):
        cite = said.get("cite") or {}
        if not cite.get("file") or cite.get("file") == hop.get("file"):
            return said["text"]
    return hop.get("claim") or f"{hop.get('symbol', 'This hop')} in {hop['file']}."


# --------------------------------------------------------------------------
# Small survey-derived helpers
# --------------------------------------------------------------------------

def _entry_points(ctx: Ctx) -> list[dict]:
    return list(ctx.survey.get("entry_points") or [])


def _entry_list(ctx: Ctx) -> str:
    """The entry points, at most four, and *saying so* when it is not all.

    The callout that reads this states the real count in the same sentence, so
    a list silently cut at four reads as the complete set and quietly makes the
    count look wrong. Naming the remainder costs four words.
    """
    eps = _entry_points(ctx)
    if not eps:
        return ""
    shown = ", ".join(f"{e.get('kind')} {e.get('name')}" for e in eps[:4])
    rest = len(eps) - 4
    return f"{shown}, and {rest} more" if rest > 0 else shown


def _hops_fixture_name(ctx: Ctx) -> str:
    """Where this repo's chain would have to live, named on the page.

    `load_hops` and `HOPS_FIXTURE` are this module's, and the CLI looks the file
    up by `survey.repo.name` against the same directory, so this is compose
    describing its own input rather than guessing at another stage's layout.
    Naming the file is what turns "no trace here" from a shrug into something a
    reader can act on, and it is the same sentence the build already prints.
    A repo with no usable name gets the generic phrase instead of a path that
    would not resolve.
    """
    name = str(_repo(ctx).get("name") or "")
    if not name or name in (".", "..") or name != Path(name).name:
        return f"a {HOPS_FIXTURE.parent.name}/trace.<repo>.json"
    return f"{HOPS_FIXTURE.parent.name}/trace.{name}.json"


def _candidate_list(ctx: Ctx) -> str:
    return "; ".join(
        f"{c.get('cmd')} ({c.get('source', 'no source')})"
        for c in _candidates(ctx)[:4])


def _test_candidates(ctx: Ctx) -> str:
    """Every test candidate considered, with the truthful reason it is not green.

    Naming the denied candidate is the difference between "no tests here" and
    "pytest is not importable under the resolved interpreter" — one is a
    statement about the repo and the other is a statement about this machine.

    The runner's record outranks everything above it. A candidate that WAS
    executed is described by its real result, never as "not executed": the
    setup stop is about to render that exact command with its real exit code,
    and a callout contradicting the command block one screen away is the one
    defect this project cannot ship. Only candidates with no run record keep
    the not-executed wording.
    """
    seen: dict[str, str] = {}
    for c in _candidates(ctx):
        if c.get("kind") != "test":
            continue
        seen[str(c.get("cmd"))] = c.get("deny_reason") or (
            "not on the execution allowlist" if c.get("allowed") is False
            else "not executed")
    for s in _skipped(ctx):
        # The runner is the better authority on why a command did not run, so
        # it overwrites the survey's guess rather than appearing twice. A
        # skipped lint or setup candidate is not evidence about tests and stays
        # out of this callout.
        if s.get("kind") in ("test", "", None):
            seen[str(s.get("cmd"))] = str(s.get("reason", "skipped"))
    # Executed candidates become a whole sentence rather than a "cmd: reason"
    # pair, because the honest statement is about the result, not the denial.
    # `cmd` is the one join key three producers share (see `_kind_of`).
    ran: dict[str, str] = {}
    for r in _runs(ctx):
        cmd = str(r.get("cmd"))
        if cmd not in seen or r.get("exit") is None:
            continue
        if r.get("timed_out"):
            ran[cmd] = (f"{cmd} was executed and timed out, so there is no "
                        f"green test command to hand you")
        elif r.get("exit") == 0:
            ran[cmd] = (f"{cmd} was executed and passed, but the runner did "
                        f"not record it as a test run")
        else:
            ran[cmd] = (f"{cmd} was executed and failed with exit "
                        f"{r['exit']}, so there is no green test command to "
                        f"hand you")
    bits = [ran.get(cmd) or f"{cmd}: {why}" for cmd, why in seen.items()]
    return "; ".join(bits[:4]) or "none found in this repo"


def _skipped_text(skipped: Sequence[dict]) -> str:
    """§8.4's "Not executed" callout: the candidate, its source, its reason."""
    bits = []
    for s in skipped[:4]:
        where = f" (from {s['source']})" if s.get("source") else ""
        bits.append(f"{s.get('cmd')}{where}: {s.get('reason', 'skipped')}")
    more = len(skipped) - len(bits)
    return ("These candidates were found but never executed: "
            + "; ".join(bits)
            + (f"; and {more} more." if more > 0 else "."))


def _green_pick(ctx: Ctx) -> dict | None:
    """The one command the `green` stop shows, per §5.7's rules 1 then 2.

    Pure and cheap on purpose: `build_setup` calls it to know which run *not* to
    render, so the same command never appears twice on the page.
    """
    runs = _runs(ctx)
    for r in runs:
        if r.get("exit") == 0 and _kind_of(ctx, r) == "test":
            return r
    for r in runs:
        if r.get("exit") == 0:
            return r
    return None


def _edge_count(ctx: Ctx, node_id: str | None) -> int:
    edges = (ctx.map or {}).get("edges") or []
    return sum(e.get("n", 0) for e in edges if e.get("a") == node_id)


def _edges_clamped(ctx: Ctx) -> bool:
    """Is any drawn edge sitting AT the clamp, and therefore not a count?

    Read off the emitted weights rather than off `diagnostics.edge_cap_hits`:
    that counter is incremented in `collapse`, before `build_map` drops the
    backward edges, so a clamped edge that is counted but never drawn leaves the
    counter positive with nothing on the map to explain — and, the other way
    round, an edge whose raw total was exactly `EDGE_CAP` is indistinguishable
    from a clamped one here and has to be described the same cautious way.
    """
    return any(int(e.get("n") or 0) >= EDGE_CAP
               for e in ((ctx.map or {}).get("edges") or []))


def _edge_name(label: dict, e: dict) -> str:
    """`cli to data` — by label, with the id as the fallback, never `None`."""
    a, b = e.get("a"), e.get("b")
    return f"{label.get(a, a)} to {label.get(b, b)}"


def _heaviest_edge(edges: Sequence[dict], label: dict) -> str:
    """The heaviest-edge sentence: honest about the clamp and about ties.

    This sentence is survey-derived and therefore renders `inferred`, so it
    carries no anchor and nothing downstream re-reads it. Both ways it used to
    go wrong were invisible to every gate.

    **A clamped weight is not an import count.** `mapper` stores
    `min(raw, EDGE_CAP)`; on the demo repo eight edges are stored at exactly 48
    and their real totals are 48 *or more*, unknowable from `map.json`. Printing
    48 as "48 import statements" is exactly the kind of confident wrong number
    this tool deletes when a model writes it — writing it deterministically
    instead does not make it true.

    **`max` over a tie picks arbitrarily.** Whichever of those eight edges the
    mapper happened to emit first was named "the heaviest edge drawn" and the
    other seven disappeared. When more than one edge holds the top weight the
    sentence says how many, and names the first few in sorted order so a
    re-run on an unchanged repo produces an unchanged page.
    """
    top = max(int(e.get("n") or 0) for e in edges)
    tied = sorted((e for e in edges if int(e.get("n") or 0) == top),
                  key=lambda e: (str(e.get("a")), str(e.get("b"))))
    names = [_edge_name(label, e) for e in tied[:3]]
    rest = len(tied) - len(names)
    listed = ", ".join(names) + (f", and {rest} more" if rest > 0 else "")

    if top >= EDGE_CAP:
        weight = f"at least {_plural(EDGE_CAP, 'import statement')}"
        why = (f" Edge weights are clamped at {EDGE_CAP} on this map, so that "
               f"is a floor and not a count.")
    else:
        weight, why = _plural(top, "import statement"), ""

    if len(tied) == 1:
        return f"The heaviest edge drawn is {listed}, {weight}.{why}"
    return (f"{_plural(len(tied), 'edge')} tie for the heaviest weight drawn, "
            f"{weight} each: {listed}.{why}")


def _map_caveat(ctx: Ctx) -> str:
    diag = (ctx.map or {}).get("diagnostics") or {}
    back = diag.get("edges_dropped_backward") or 0
    hits = diag.get("edge_cap_hits") or 0
    bits = []
    if back:
        bits.append(f"{back} backward edges are counted but not drawn")
    if hits:
        bits.append(f"{hits} edge weights are capped")
    return (", ".join(bits) + ".") if bits else "every edge found is drawn."


def _churn_degenerate(rows: Sequence[dict]) -> bool:
    """A churn "ranking" with no information in it.

    A tree committed as one snapshot gives every module the same commit
    count. The counts are still printed — they are real — but a column of
    identical numbers is not a ranking, and the lede must stop calling it
    one. A single-row table is exempt: one row is not a ranking claim.
    """
    return len(rows) > 1 and len({r["rank_by"] for r in rows}) == 1


def _rank_label(ctx: Ctx) -> str:
    """What the rank column actually ranks by — decision #18, made visible.

    Never label fan-in as churn. The drawer heading in the renderer is
    hard-coded MOST-EDITED FILES, so the substitution has to be visible inside
    the data or the page states a falsehood on every node drawer.
    """
    if _churn_available(ctx):
        return "commits"
    mods = ctx.survey.get("modules") or {}
    if any(t.get("fan_in") is not None
           for m in mods.values() for t in (m.get("top") or [])):
        return "fan-in (no git history)"
    return "lines of code (no git history)"


def _first_sentence(doc: str, limit: int = 90) -> str:
    doc = " ".join(str(doc).split())
    head = doc.split(". ")[0].rstrip(".")
    if len(head) > limit:
        head = head[:limit - 1].rstrip() + "…"
    return head


def _purpose(ctx: Ctx, path: str) -> str:
    """The package `__init__.py` docstring's first sentence, or `no docstring`.

    Decision #20. An honest gap is a better cell than a plausible sentence
    nobody checked: this column has no claim marker and the gate never walks
    it. The gap used to be an em dash; `@3`'s dash policy bans that glyph on
    every authored surface, and `purpose` is on the scanned list, so the gap
    is now spelled out.
    """
    want = f"{path}/__init__.py"
    for f in ctx.survey.get("files") or []:
        if f.get("path") != want:
            continue
        for key in ("doc", "docstring", "module_doc", "summary"):
            if f.get(key):
                return _first_sentence(f[key])
    return "no docstring"


def _module_for(node: dict, mods: dict) -> dict:
    """Join a map node back to its survey module rollup.

    The node carries a label relative to the import root and the rollup carries
    a repo-relative path, so the join is by path when the node offers one and by
    path tail otherwise. A miss returns `{}` and the row falls back to the
    node's own numbers rather than dropping out of the table.
    """
    if node.get("path"):
        for m in mods.values():
            if m.get("path") == node["path"]:
                return m
    label = node.get("label") or ""
    for m in mods.values():
        p = m.get("path") or ""
        if p == label or p.endswith("/" + label):
            return m
    return {}


def _where_rows(ctx: Ctx) -> list[dict]:
    """One row per map node, falling back to the survey's module rollup."""
    mods = ctx.survey.get("modules") or {}
    nodes = _nodes(ctx)
    pairs: list[tuple[dict, dict]] = [(n, _module_for(n, mods)) for n in nodes]
    if not pairs:
        pairs = [({}, m) for m in sorted(
            mods.values(), key=lambda m: -(m.get("loc") or 0))[:14]]

    committers = _churn(ctx).get("committers") or {}
    rows = []
    for node, m in pairs:
        path = m.get("path") or node.get("label") or "?"
        loc = m.get("loc") or node.get("loc") or 0
        files = m.get("files") or node.get("files") or 0
        top = (m.get("top") or [{}])[0]
        if _churn_available(ctx):
            rank_by = m.get("commits") or top.get("commits") or 0
        elif top.get("fan_in") is not None:
            rank_by = top.get("fan_in") or 0
        else:
            rank_by = loc
        who = committers.get(path) or committers.get(m.get("path")) or []
        rows.append({"path": path, "purpose": _purpose(ctx, path), "loc": loc,
                     "files": files, "rank_by": rank_by,
                     "committers": [str(x) for x in who]})
    return rows


def _scope_text(ctx: Ctx) -> str:
    """§9 rows 9 and 10, plus decision #6's language scope, stated on screen.

    Written as counted nouns rather than sentences with verbs, because every
    one of these numbers is 0 or 1 on a healthy repo and "1 files were skipped"
    on the audit stop undermines the one page whose subject is rigour.
    """
    walk = ctx.survey.get("walk") or {}
    bits = [
        "This tool reads Python with the standard library's ast, and anchors "
        "into any UTF-8 text file the survey listed. Nothing else was read. "
        f"Files that failed to parse: {len(ctx.survey.get('parse_failures') or [])}. "
        f"Files skipped as not text or outside the repo root: "
        f"{len(walk.get('skipped') or [])}. "
        f"Directories excluded by name: {walk.get('excluded_dirs', 0)}."
    ]
    dangling = ctx.survey.get("dangling") or []
    if dangling:
        n = sum(int(d.get("n") or 0) for d in dangling)
        bits.append(f"The survey also counted "
                    f"{_plural(len(dangling), 'import target')} with no file on "
                    f"disk, across {_plural(n, 'import statement')}; none of "
                    f"them is a node or an edge on the map.")
    return " ".join(bits)
