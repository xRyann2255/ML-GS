"""Stage 3 — NARRATE. The only stage that touches a model.

Orchestration, the narration store, and the parser. The parser is the important
half: it is the boundary where model output stops being model output and becomes
data the rest of the pipeline is allowed to trust, and it **rejects, never
repairs**. A parser that patches a bad response is a model verifying itself with
extra steps — the exact thing non-negotiable #1 forbids — so a cite carrying a
`start` key takes the whole response down instead of quietly becoming an anchor.

The default route is not an API call. `--emit-prompts` writes one self-contained
pack per unit to `.trailhead/prompts/<key>.json`, carrying its own absolute
`out` path; the host coding agent answers each pack into `.trailhead/narration/`;
`StubProvider` replays it. The key is `provider.cache_key`, computed once, in one
place, so the path the pack tells the agent to write is byte-identical to the
path the replay reads. Compute it twice and replay misses every time.

What leaves this module:

    build_units   which units this repo can support, and what was cut
    parse         one response -> (claims, ledger rows).  Rejects, never repairs
    run           the unit loop -> narration, windows, ledger, degradations
    emit_prompts  the agent route

`run` returns `windows` per unit as well as claims. Stage 4 needs them: its
resolver arbitrates a quote against the spans that were actually shown, and
without them a quote that matched a file we never displayed resolves as
verified.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from trailhead import prompts, provider as provider_mod
from trailhead.prompts import Unit, Window
from trailhead.provider import CITE_KEYS, SCHEMA, MissingNarration, cache_key

#: `Unit` and `Window` are re-exported deliberately: a caller wiring stage 3
#: into the pipeline should need one import, and `compose.py` reads the windows
#: this stage recorded.
__all__ = ["Unit", "Window", "Rejected", "build_units", "parse",
           "parse_structured", "schema_for", "run", "emit_prompts", "main",
           "CACHE_DIRNAME", "PROMPTS_DIRNAME", "CODE_UNNARRATED",
           "STRUCTURED_KINDS"]

#: `.trailhead/narration/<key>.json` — record and replay share one directory.
CACHE_DIRNAME = "narration"

#: `.trailhead/prompts/<key>.json` — the agent route's inbox.
PROMPTS_DIRNAME = "prompts"

#: The @3 unit set tops out at 22 (4 claim units, 10 node, 5 dive, gloss,
#: tour, cols), so the default budget clears it with headroom rather than
#: silently cutting the drawers on every big repo.
MAX_UNITS_DEFAULT = 24

#: Reverse priority. Overflow drops from the left, matching §14's stop-cut
#: order. `trace` is last because it carries beat 4 of the pitch. An entry
#: matches a unit id exactly OR as a `<prefix>:` family (`node` matches
#: `node:core`); family members drop one at a time, last-built first, so the
#: smallest groups lose their drawers before the biggest do.
DROP_ORDER = ("cols", "conv", "gloss", "tour", "node", "dive",
              "green", "five", "trace")

#: The @2 claim-shaped kinds. `unit_unnarrated` degradations are scoped to
#: these: for a structured unit, an unanswered pack IS the designed @2
#: fallback (the drawer keeps `why`/`top`, the page keeps no glossary), so
#: labelling it a gap would put noise rows on every partially-answered run.
CORE_KINDS = ("five", "green", "trace", "conventions")

#: Kinds whose answers are structured objects validated by per-kind schemas
#: rather than claim lists. Their narration value is a dict, `{}` on absence.
STRUCTURED_KINDS = ("node", "gloss", "tour", "cols")

#: Claim text rules from §5.5. Backticks and `<` reach a raw-interpolation
#: surface; a newline breaks the one-sentence-per-claim contract the renderer
#: lays out against; `](` is a markdown link the page will never render.
TEXT_MAX_CHARS = 280
TEXT_BANNED = ("`", "\n", "<", "](")

#: The @3 kinds (`node`, `dive`, `gloss`, `tour`, `cols`) render through the
#: template's rich() pipeline, which escapes first and then turns `code`
#: spans and [[glossary]] markers into markup, so backticks are legal there.
#: Angle brackets and markdown links stay banned everywhere.
TEXT_BANNED_MARKUP = ("\n", "<", "](")

#: Unit counts for the @3 packs: top-K on-board map groups get a `node:` unit,
#: top-D get a `dive:` unit as well (both by loc, biggest first).
NODE_UNITS_MAX = 10
DIVE_UNITS_MAX = 5

#: Files fed to a node/dive pack: the group's top fan-in files, plus its
#: package `__init__` and the repo README, all under the prompt line budget.
NODE_TOP_FILES = 6
DIVE_TOP_FILES = 5
GLOSS_TOP_FILES = 5

#: Dive claims mirror `five` (6..8 sentences, cite-or-inferred).
DIVE_MAX_CLAIMS = 8

#: Field caps for the structured answers, enforced in `parse_structured` and
#: stated in each pack's schema. Spec section 4 fixes terms<=14, term<=40,
#: def<=300, tour text<=340, column label<=14; the rest are house numbers
#: sized off the hand-built template payload.
GLOSS_TERMS_MAX = 14
TERM_MAX_CHARS = 40
DEF_MAX_CHARS = 300
TOUR_TEXT_MAX_CHARS = 340
TOUR_STEP_CAP = 12
TOUR_MIN_STEPS = 3
COL_LABEL_MAX_CHARS = 14
NODE_ROLE_MIN = 2
NODE_ROLE_MAX = 3
ROLE_MAX_CHARS = 600
READS_FEEDS_MAX_CHARS = 300
KEY_FILES_MAX = 6
PURPOSE_MAX_CHARS = 200
CONCEPTS_MAX = 6
CONCEPT_MAX_CHARS = 60
CAPTION_MAX_CHARS = 200

#: A quote longer than this cannot become an anchor — `expand_anchor`'s cap is
#: 24 lines and a focus line outside the anchor fails `verify-contract.js:69`.
QUOTE_MAX_LINES = 24

#: One claim per trace hop, and the two counts must be equal or a hop renders
#: `esc(undefined)` inside a `.claim` span. The cap is on the hop list, not the
#: claims: a 40-hop trace is a chain nobody reads and a prompt nobody answers
#: well, so it is truncated before it is asked for.
TRACE_CLAIM_CAP = 12

#: Two of the twelve frozen drop reasons (§6.6) belong to this stage. Detail is
#: appended at the ledger boundary as `f"{code}: {detail}"`, so the vocabulary
#: stays a set of literals while the on-screen row still says what happened.
REASON_UNPARSEABLE = "model returned unparseable output"
REASON_QUOTE_CAP = "quote longer than the anchor cap"

#: §9 has no row for it, so this stage names it: a unit that came back with
#: nothing at all — no claims and no drop rows — while other units of the same
#: run came back with prose. A rejected response already earns a ledger row and
#: shows up in the on-screen drop count; a store miss earns nothing, and the
#: only trace of it was the arithmetic in `model 9 claim(s) from 2/3 unit(s)`.
#: The gap is labelled, never filled: nothing here invents prose.
CODE_UNNARRATED = "unit_unnarrated"


class Rejected(Exception):
    """A response the parser refuses to repair.

    Whole-response, not per-claim: a cite key that is not `file`/`quote`/`focus`
    means the model answered a different schema than the one it was given, and
    the claims either side of it are no more trustworthy than that one.
    """


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------

def build_units(survey: dict, commands: dict | None = None,
                hops: list | None = None, *, map_data: dict | None = None,
                max_units: int = MAX_UNITS_DEFAULT) -> tuple[list[Unit], list[dict]]:
    """-> (units, degradations). Fewer on a thinner repo, more with a map.

    The @2 rule stands: one call per stop-unit, never per claim. What changed
    at @3 is what counts as a stop-unit. Decisions #19 and #26 deleted the old
    `map:<node>` units because they routed unanchored prose onto surfaces with
    no claim marker; the @3 `node:`/`dive:` units are their disciplined
    replacement: dives are ordinary claim units (markers, audit rows, the
    lot), and node drawer text renders on a surface the template marks as
    narrated, with its optional cite resolved by stage 4 exactly like a
    claim's.

    A unit is built only when the repo can support it: `trace` needs a hop
    list, `green` needs a command that actually passed, `node`/`dive`/`tour`/
    `cols` need `map.json` (passed as `map_data`), `gloss` needs at least one
    file worth showing. Every new unit degrades to absence downstream, so an
    unanswered pack costs nothing but the model call that was never made.
    """
    hops = list(hops or [])
    degradations = []
    units = []

    # Six, not five: the @3 shape adds "what is unusual" between the pipeline
    # sentences and the closing inferred "what it is not". The title is a
    # stop name, not a count.
    five_files = _dedupe(_readme_files(survey) + _entry_files(survey)
                         + _top_files(survey, 4))[:6]
    units.append(Unit(
        id="five", kind="five", title="Five sentences", max_claims=6,
        files=tuple(five_files),
    ))

    passing, kind = _passing_command(survey, commands)
    if passing is not None:
        if kind == "test":
            green_files = _test_files(survey, 3) or _top_files(survey, 3)
        else:
            green_files = _dedupe(_entry_files(survey) + _top_files(survey, 2))[:3]
        units.append(Unit(
            id="green", kind="green", title="It runs", max_claims=2,
            files=tuple(green_files), notes=tuple(_command_notes(passing, kind)),
        ))

    # Hops and claims are counted together, never separately: a hop the model
    # was not asked about renders `esc(undefined)` inside a `.claim` span.
    usable = [(hop, region) for hop, region in
              ((h, _hop_region(h)) for h in hops) if region is not None]
    usable = usable[:TRACE_CLAIM_CAP]
    if len(usable) >= 2:
        regions = tuple(region for _, region in usable)
        units.append(Unit(
            id="trace", kind="trace", title="Follow one request",
            max_claims=len(regions),
            files=tuple(_dedupe([r[0] for r in regions])), regions=regions,
            notes=tuple(_hop_notes([hop for hop, _ in usable])),
        ))

    units.append(Unit(
        id="conv", kind="conventions", title="How this codebase is written",
        max_claims=4, files=tuple(_top_files(survey, 4)),
    ))

    units += _map_units(survey, map_data)

    gloss_files = _dedupe(_fanin_files(survey, GLOSS_TOP_FILES)
                          + _readme_files(survey))
    if gloss_files:
        units.append(Unit(
            id="gloss", kind="gloss", title="Glossary",
            max_claims=GLOSS_TERMS_MAX, files=tuple(gloss_files),
        ))

    total = len(units)
    if total > max_units:
        # §9 row 7. Drop from the left of DROP_ORDER until the budget holds;
        # the affected stops fall back to their template blocks and carry no
        # claims, which the audit callout says out loud. A `<prefix>:` family
        # sheds members one at a time, last-built (smallest group) first.
        for victim in DROP_ORDER:
            for unit in reversed(_drop_matches(units, victim)):
                if len(units) <= max_units:
                    break
                units = [u for u in units if u is not unit]
            if len(units) <= max_units:
                break
        degradations.append({
            "code": "narrate_budget",
            "reason": (f"{len(units)} of {total} units narrated. The rest render "
                       f"from templates and carry no claims."),
            "narrated": len(units),
            "units": total,
        })

    return units, degradations


def _drop_matches(units: list, victim: str) -> list:
    """The units a DROP_ORDER entry names: exact id or `<victim>:` family."""
    return [u for u in units
            if u.id == victim or u.id.startswith(victim + ":")]


def _map_units(survey: dict, map_data: dict | None) -> list:
    """The `node:`/`dive:`/`tour`/`cols` units a map makes possible.

    Everything here reads `map.json` defensively: a pipeline run that has not
    produced a map (or an old map without `columns`/`tour_order`) simply
    builds fewer units, which downstream degrades to the exact @2 page.
    """
    out = []
    board = _board_nodes(map_data)

    for node in board[:NODE_UNITS_MAX]:
        gid = _gid(node)
        group_files = _node_files(survey, node, NODE_TOP_FILES)
        if not group_files:
            continue
        label = str(node.get("label") or gid)
        out.append(Unit(
            id=f"node:{gid}", kind="node", title=f"Drawer: {label}",
            max_claims=1,
            files=tuple(_dedupe(group_files + _readme_files(survey))),
            notes=tuple(_node_notes(node, group_files)),
            choices=tuple(_dedupe([_basename(p) for p in group_files])),
        ))

    for node in board[:DIVE_UNITS_MAX]:
        gid = _gid(node)
        group_files = _node_files(survey, node, DIVE_TOP_FILES)
        if not group_files:
            continue
        label = str(node.get("label") or gid)
        out.append(Unit(
            id=f"dive:{gid}", kind="dive", title=f"Inside {label}",
            max_claims=DIVE_MAX_CLAIMS,
            files=tuple(_dedupe(group_files + _readme_files(survey))),
            notes=tuple(_group_note(node)),
        ))

    tour_ids, by_id = _tour_ids(map_data)
    if len(tour_ids) >= TOUR_MIN_STEPS:
        tour_files = _dedupe([f for nid in tour_ids
                              for f in _node_files(survey, by_id[nid], 1)])
        out.append(Unit(
            id="tour", kind="tour", title="Guided tour",
            max_claims=len(tour_ids),
            files=tuple(tour_files[:TOUR_STEP_CAP]),
            notes=tuple(_tour_notes(tour_ids, by_id)),
            choices=tuple(tour_ids),
        ))

    columns = [c for c in ((map_data or {}).get("columns") or [])
               if isinstance(c, dict)]
    if len(columns) >= 2:
        out.append(Unit(
            id="cols", kind="cols", title="Column labels",
            max_claims=len(columns),
            notes=tuple(_cols_notes(map_data, columns, board)),
        ))

    return out


def _entry_files(survey: dict) -> list:
    out = []
    for entry in survey.get("entry_points") or []:
        path = entry.get("file")
        if isinstance(path, str) and path:
            out.append(path)
    return out


def _top_files(survey: dict, limit: int) -> list:
    """The busiest file of each of the biggest modules, largest module first."""
    out = []
    for name, info in prompts.modules_by_loc(survey.get("modules") or {}):
        for item in (info or {}).get("top") or []:
            path = item.get("path") if isinstance(item, dict) else item
            if isinstance(path, str) and path:
                out.append(path)
                break
        if len(out) >= limit:
            break
    return out[:limit]


def _test_files(survey: dict, limit: int) -> list:
    roots = tuple(r for r in ((survey.get("roots") or {}).get("test_roots") or ())
                  if isinstance(r, str) and r)
    if not roots:
        return []
    out = [f.get("path") for f in survey.get("files") or []
           if isinstance(f.get("path"), str)
           and f["path"].startswith(roots)]
    return out[:limit]


def _passing_command(survey: dict, commands: dict | None) -> tuple:
    """The best command that really passed, and its survey `kind`.

    Preference order is §5.7's `green` rule: an admitted test command that
    passed, else any command that passed, else nothing. `exit` is compared to
    the integer 0 — a string "0" is a failing command that renders green, which
    is the single most dishonest thing this page could do.
    """
    runs = (commands or {}).get("runs") or []
    kinds = {}
    for candidate in survey.get("command_candidates") or []:
        kinds[(candidate.get("cmd"), candidate.get("cwd"))] = candidate.get("kind")

    passed = [r for r in runs if r.get("exit") == 0 and not r.get("timed_out")]
    for run_record in passed:
        if kinds.get((run_record.get("cmd"), run_record.get("cwd"))) == "test":
            return run_record, "test"
    if passed:
        key = (passed[0].get("cmd"), passed[0].get("cwd"))
        return passed[0], kinds.get(key)
    return None, None


def _command_notes(run_record: dict, kind: str | None) -> list:
    """Real capture, quoted into the prompt so the sentences describe reality.

    **The duration is deliberately not here.** It is real and it belongs on the
    page — but the cache key is `sha256` over these very bytes, so a command
    that takes 32 ms on one run and 47 ms on the next produces two keys, and the
    answer stored under the first misses on every run afterwards. Measured: the
    `green` packs of four back-to-back builds of the same commit differed by
    exactly that one line, and the stop's prose came and went with it (12/14/12/
    12 claims). Nothing the model is asked to write depends on a millisecond
    count; timings live in `commands.json` and in the rendered command block,
    where they are checkable. Everything else quoted here — cmd, cwd, kind, exit
    code, output — is a function of the repo, so the same repo hashes the same.
    """
    out = ["COMMAND THAT PASSED (real capture; exit code and output are not simulated)",
           f"  cmd: {run_record.get('cmd')}",
           f"  cwd: {run_record.get('cwd')}",
           f"  kind: {kind or 'unclassified'}",
           f"  exit: {run_record.get('exit')}"]
    output = (run_record.get("out") or "").split("\n")[:12]
    if output and any(line.strip() for line in output):
        out.append("  output:")
        out += [f"    {line}" for line in output]
    return out


def _hop_notes(hops: list) -> list:
    out = ["HOPS, in order:"]
    for i, hop in enumerate(hops, 1):
        region = _hop_region(hop)
        where = region[0] if region else hop.get("file", "?")
        what = hop.get("what") or hop.get("label") or hop.get("symbol") or ""
        out.append(f"  {i}. {where}{(': ' + what) if what else ''}")
    return out


def _hop_region(hop: dict) -> tuple | None:
    """(file, start, end) from a hop, whichever of the two shapes it uses.

    `fixtures/trace.*.json` is owned elsewhere and may nest the range under
    `anchor` or carry it flat. Tolerating both here is three lines; guessing
    wrong is eight silently unshown hops on the stop that carries the pitch.
    """
    if not isinstance(hop, dict):
        return None
    anchor = hop.get("anchor") if isinstance(hop.get("anchor"), dict) else hop
    path = anchor.get("file")
    start = anchor.get("start", anchor.get("line"))
    end = anchor.get("end", start)
    if not isinstance(path, str) or not isinstance(start, int) or not isinstance(end, int):
        return None
    return path, start, end


def _dedupe(items: list) -> list:
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] if "/" in path else path


def _dirkey(path) -> str:
    """A directory path normalised for prefix comparison: `/`-separated, no
    leading or trailing slash, `""` for the repo root (`.` included)."""
    key = str(path or "").replace("\\", "/").strip("/")
    return "" if key == "." else key


def _board_nodes(map_data: dict | None) -> list:
    """The on-board map groups, biggest first, ties broken by id.

    The upgraded mapper keeps pure test containers off the board entirely and
    names them in `map.note`; `is_test` is checked anyway so an older map
    cannot put a `node:tests` drawer on the page.
    """
    nodes = (map_data or {}).get("nodes") or []
    kept = [n for n in nodes
            if isinstance(n, dict) and n.get("id") and not n.get("is_test")]
    return sorted(kept, key=lambda n: (-int(n.get("loc") or 0), str(n["id"])))


def _gid(node: dict) -> str:
    """The group id a composite unit id carries: the node id minus its `n-`."""
    nid = str(node.get("id"))
    return nid[2:] if nid.startswith("n-") and len(nid) > 2 else nid


def _group_top_files(survey: dict, node: dict, limit: int) -> list:
    """The group's top fan-in files: every `top` entry of every survey module
    whose directory sits under the node's path, highest fan-in first."""
    gdir = _dirkey(node.get("path"))
    rows = []
    for _, info in sorted((survey.get("modules") or {}).items()):
        mdir = _dirkey((info or {}).get("path"))
        if not (mdir == gdir or (gdir and mdir.startswith(gdir + "/"))):
            continue
        for item in (info or {}).get("top") or []:
            path = item.get("path") if isinstance(item, dict) else item
            if not isinstance(path, str) or not path:
                continue
            fan_in = int(item.get("fan_in") or 0) if isinstance(item, dict) else 0
            rows.append((-fan_in, path))
    rows.sort()
    return _dedupe([path for _, path in rows])[:limit]


def _node_files(survey: dict, node: dict, limit: int) -> list:
    """Top fan-in files plus the package `__init__` for one map group."""
    files = _group_top_files(survey, node, limit)
    gdir = _dirkey(node.get("path"))
    if gdir:
        init = gdir + "/__init__.py"
        if init not in files:
            files.append(init)
    return files


def _readme_files(survey: dict) -> list:
    """Root-level README paths from the survey, or the conventional name.

    `prompts._read_files` skips anything not on disk, so guessing `README.md`
    on a repo without one costs nothing.
    """
    out = [f.get("path") for f in survey.get("files") or []
           if isinstance(f.get("path"), str) and "/" not in f["path"]
           and f["path"].lower().startswith("readme")]
    return out[:2] or ["README.md"]


def _fanin_files(survey: dict, limit: int) -> list:
    """The highest fan-in files repo-wide, from every module's `top` list."""
    rows = []
    for _, info in sorted((survey.get("modules") or {}).items()):
        for item in (info or {}).get("top") or []:
            path = item.get("path") if isinstance(item, dict) else item
            if not isinstance(path, str) or not path:
                continue
            fan_in = int(item.get("fan_in") or 0) if isinstance(item, dict) else 0
            rows.append((-fan_in, path))
    rows.sort()
    return _dedupe([path for _, path in rows])[:limit]


def _tour_ids(map_data: dict | None) -> tuple[list, dict]:
    """-> (tour step ids in order, node id -> node). Empty list without a map.

    `tour_order` is the mapper's pipeline ordering; an older map without it
    falls back to reading order (left to right, top to bottom), which is the
    same thing computed the crude way. Ids not on the board are dropped here,
    so the pack can promise every id it fixes.
    """
    nodes = _board_nodes(map_data)
    by_id = {n["id"]: n for n in nodes}
    order = [i for i in ((map_data or {}).get("tour_order") or []) if i in by_id]
    if not order:
        order = [n["id"] for n in sorted(
            nodes, key=lambda n: (int(n.get("x") or 0), int(n.get("y") or 0),
                                  str(n["id"])))]
    return order[:TOUR_STEP_CAP], by_id


def _group_note(node: dict) -> list:
    """One orientation line naming the group a node/dive pack is about."""
    label = node.get("label") or _gid(node)
    where = node.get("path") or "(repo root)"
    return [f"GROUP: {label} at {where}: "
            f"{node.get('files', '?')} files, {node.get('loc', '?')} loc."]


def _node_notes(node: dict, group_files: list) -> list:
    """The group facts plus the fixed key_files vocabulary, names first."""
    out = _group_note(node)
    out.append("FILES you may name in key_files (copy the name exactly):")
    for path in group_files:
        out.append(f"  - {_basename(path)} ({path})")
    return out


def _tour_notes(tour_ids: list, by_id: dict) -> list:
    """The fixed step ids in order, with enough facts to write against."""
    out = ["TOUR NODES, in order. One step per id, ids copied exactly:"]
    for i, nid in enumerate(tour_ids, 1):
        node = by_id.get(nid) or {}
        label = node.get("label") or _gid(node) or nid
        where = node.get("path") or "(repo root)"
        out.append(f"  {i}. {nid}: {label} at {where}, {node.get('loc', '?')} loc")
    return out


def _cols_notes(map_data: dict | None, columns: list, board: list) -> list:
    """The columns in order, each with the groups that sit in it.

    Membership comes from the mapper's own `diagnostics.columns` when it is
    published, else from nearest column center x: both deterministic, neither
    trusted to exist.
    """
    diag = ((map_data or {}).get("diagnostics") or {}).get("columns") or {}
    xs = [c.get("x") for c in columns]
    have_x = bool(xs) and all(isinstance(x, (int, float)) for x in xs)

    members: dict[int, list] = {}
    for node in board:
        idx = diag.get(node["id"])
        if not isinstance(idx, int) or not (0 <= idx < len(columns)):
            if have_x:
                center = int(node.get("x") or 0) + int(node.get("w") or 0) / 2
                idx = min(range(len(xs)), key=lambda i: abs(xs[i] - center))
            else:
                idx = 0
        members.setdefault(idx, []).append(str(node.get("label") or _gid(node)))

    out = ["COLUMNS of the module map, left to right. One label per column, "
           "in this order:"]
    for i in range(len(columns)):
        names = ", ".join(members.get(i, [])) or "(no groups)"
        out.append(f"  {i + 1}. holds: {names}")
    return out


# ---------------------------------------------------------------------------
# the parser
# ---------------------------------------------------------------------------

def parse(raw, unit: Unit) -> tuple[list[dict], list[dict]]:
    """-> (claims, ledger rows). Raises `Rejected` for a whole-response failure.

    The claims come back in `content@1` shape minus their ids, which `run`
    stamps from one monotonic counter so kept and dropped claims share a
    sequence (§6.7).

    Per-claim rules, all from §5.5, none of them repairs:

      * over `unit.max_claims` -> truncated, never an error
      * empty / over-long / markup-bearing `text` -> dropped, one ledger row
      * `inferred` -> `cite` discarded outright, whatever came back
      * `verified` with no usable cite -> dropped, one ledger row
      * a `focus` string that is not a substring of `quote` -> focus dropped,
        claim kept
      * `unit.kind == "conventions"` -> every status forced to `inferred`

    A claim never appears in both lists. `verify-contract.js:131` cross-checks
    exactly that, and the contract doc calls a claim in `tracks` *and* `dropped`
    the failure that would discredit the entire pitch.
    """
    if isinstance(raw, dict) and raw.get("_stop_reason"):
        # §9 row 11 — HTTP 200 with content that cannot satisfy the schema.
        raise Rejected(f"stop_reason={raw['_stop_reason']}")
    if not isinstance(raw, dict):
        raise Rejected("response is not a JSON object")

    claims = raw.get("claims")
    if not isinstance(claims, list):
        raise Rejected("response carries no claims array")

    # Scan the WHOLE response for a cite key that is not one of the three, before
    # keeping anything. Scoped to key names, as `check-fixtures.js:80` is: a
    # digit scan over quote text would reject most true responses, since
    # `argv[1]`, `timeout=60` and `version = "0.3.1"` are all legitimate code.
    for claim in claims:
        if isinstance(claim, dict) and isinstance(claim.get("cite"), dict):
            extra = sorted(set(claim["cite"]) - CITE_KEYS)
            if extra:
                raise Rejected("cite carries " + ", ".join(repr(k) for k in extra))

    kept, ledger = [], []
    for index, claim in enumerate(claims[: unit.max_claims], 1):
        if not isinstance(claim, dict):
            ledger.append(_row(f"claim {index} of unit {unit.id} was not an object",
                               "", _reason(REASON_UNPARSEABLE, "claim is not an object")))
            continue

        text = claim.get("text")
        bad_text = _text_problem(text, _banned_for(unit.kind))
        if bad_text is not None:
            ledger.append(_row(_ledger_text(text, unit, index), _cite_file(claim),
                               _reason(REASON_UNPARSEABLE, bad_text)))
            continue

        status = "inferred" if unit.kind == "conventions" else claim.get("status")
        if status not in ("verified", "inferred"):
            ledger.append(_row(text, _cite_file(claim),
                               _reason(REASON_UNPARSEABLE, f"status {status!r}")))
            continue

        if status == "inferred":
            # Forced, not asked. The quarantine holds even if the prompt drifts,
            # and an inferred claim carries no anchor at all — not a blank one,
            # not a null one, none.
            kept.append({"text": text, "status": "inferred"})
            continue

        cite, problem = _clean_cite(claim.get("cite"))
        if problem is not None:
            ledger.append(_row(text, _cite_file(claim), problem))
            continue

        kept.append({"text": text, "status": "verified", "cite": cite})

    return kept, ledger


def _banned_for(kind: str) -> tuple:
    """Which character set a kind's prose must clear.

    The @2 kinds keep the full ban (their claims render through `esc()` paths
    that never grew rich-text). The @3 kinds render through the template's
    rich() pipeline, so backticks are content there, not markup injection.
    """
    if kind in ("dive",) + STRUCTURED_KINDS:
        return TEXT_BANNED_MARKUP
    return TEXT_BANNED


def _text_problem(text, banned: tuple = TEXT_BANNED) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "claim text is empty"
    if len(text) > TEXT_MAX_CHARS:
        return f"claim text is {len(text)} chars, cap is {TEXT_MAX_CHARS}"
    for item in banned:
        if item in text:
            return f"claim text contains {item!r}"
    return None


def _prose_problem(text, max_chars: int, banned: tuple) -> str | None:
    """None, or why this structured-answer string cannot ship."""
    if not isinstance(text, str) or not text.strip():
        return "text is empty"
    if len(text) > max_chars:
        return f"text is {len(text)} chars, cap is {max_chars}"
    for item in banned:
        if item in text:
            return f"text contains {item!r}"
    return None


def _clean_cite(cite) -> tuple[dict | None, str | None]:
    """-> (cite, None) or (None, ledger reason). Focus problems never drop a claim."""
    if not isinstance(cite, dict):
        return None, _reason(REASON_UNPARSEABLE, "verified claim carries no cite")

    path = cite.get("file")
    quote = cite.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        return None, _reason(REASON_UNPARSEABLE, "verified claim carries an empty quote")
    if not isinstance(path, str) or not path.strip():
        # Without a cited file there is no cross-file precedence to apply, and
        # §6.1 row 2 — the best-reading row the ledger can produce — becomes
        # unexpressible. Drop it here rather than let stage 4 invent a file.
        return None, _reason(REASON_UNPARSEABLE, "cite names no file")

    lines = quote.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) > QUOTE_MAX_LINES:
        return None, _reason(REASON_QUOTE_CAP, f"{len(lines)} lines")

    out = {"file": path, "quote": quote}
    focus = [f for f in (cite.get("focus") or [])
             if isinstance(f, str) and f and f in quote]
    if focus:
        out["focus"] = focus
    return out, None


def _reason(code: str, detail: str) -> str:
    """`f"{code}: {detail}"`, so the frozen vocabulary stays a set of literals.

    A colon, not the historical em dash: these rows land verbatim in the
    payload's audit table, the @3 dash policy bans em and en dashes from every
    authored string that can reach the artifact, and `verify.is_known_reason`
    accepts exactly this join (plus the legacy dash for old payloads).
    """
    return f"{code}: {detail}"


def _row(text: str, path: str, reason: str) -> dict:
    """One ledger row, minus its id. The audit table reads all four fields."""
    return {"text": text, "file": path, "reason": reason}


def _cite_file(claim: dict) -> str:
    cite = claim.get("cite")
    if isinstance(cite, dict) and isinstance(cite.get("file"), str):
        return cite["file"]
    return ""


def _ledger_text(text, unit: Unit, index: int) -> str:
    if isinstance(text, str) and text.strip():
        return text[:TEXT_MAX_CHARS]
    return f"claim {index} of unit {unit.id} arrived with no usable text"


# ---------------------------------------------------------------------------
# the structured parsers (@3 kinds)
# ---------------------------------------------------------------------------

def parse_structured(raw, unit: Unit) -> tuple[dict, list[dict]]:
    """One `node`/`gloss`/`tour`/`cols` response -> (answer, ledger rows).

    Same law as `parse`: reject, never repair. An unknown key anywhere, a
    malformed required field, or a mismatched positional count raises
    `Rejected` and the whole answer is discarded; a bad OPTIONAL slot (one
    glossary term, one tour step, a cite) is dropped and the rest ships.
    `{}` means absence, and absence is the designed @2 fallback, so a stub
    miss (`{"claims": []}`) parses to `({}, [])` rather than an error.

    No ledger rows are minted here today: structured answers are not claims,
    their drop accounting belongs to stage 4's `n-<gid>`/`g-<slug>`/`t-<id>`
    ledger ids, and a whole-response rejection earns its one row in `run`
    exactly as a claim unit's does. The rows slot in the signature keeps the
    two parsers interchangeable at the call site.
    """
    if isinstance(raw, dict) and raw.get("_stop_reason"):
        raise Rejected(f"stop_reason={raw['_stop_reason']}")
    if not isinstance(raw, dict):
        raise Rejected("response is not a JSON object")
    if raw == {"claims": []}:
        # The stub's miss sentinel: no answer exists. Absence, not failure.
        return {}, []

    if unit.kind == "node":
        return _parse_node(raw, unit), []
    if unit.kind == "gloss":
        return _parse_gloss(raw, unit), []
    if unit.kind == "tour":
        return _parse_tour(raw, unit), []
    if unit.kind == "cols":
        return _parse_cols(raw, unit), []
    raise Rejected(f"unit kind {unit.kind!r} has no structured parser")


def _reject_extra(mapping: dict, allowed: frozenset, where: str) -> None:
    extra = sorted(set(mapping) - allowed)
    if extra:
        raise Rejected(f"{where} carries " + ", ".join(repr(k) for k in extra))


def _clean_optional_cite(raw: dict, out: dict, banned: tuple) -> None:
    """Attach a validated cite (and its caption) to `out`, or neither.

    Unknown cite keys reject the whole answer, exactly as they do for a
    claim: a cite carrying `start` is the model answering a different schema.
    A cite that is merely unusable (empty quote, over the anchor cap) is
    dropped; the drawer then keeps its deterministic `why` fallback, which is
    the honest degradation, and a caption without a cite captions nothing.
    """
    cite = raw.get("cite")
    if not isinstance(cite, dict):
        return
    _reject_extra(cite, CITE_KEYS, "cite")
    clean, problem = _clean_cite(cite)
    if problem is not None:
        return
    out["cite"] = clean
    caption = raw.get("caption")
    if caption is not None and _prose_problem(caption, CAPTION_MAX_CHARS,
                                              banned) is None:
        out["caption"] = caption


_NODE_KEYS = frozenset({"role", "reads", "feeds", "key_files", "concepts",
                        "cite", "caption"})


def _parse_node(raw: dict, unit: Unit) -> dict:
    """`{role, reads, feeds, key_files, concepts, cite?, caption?}`, checked.

    Required fields are strict: a drawer with one role paragraph or a prose
    `reads` full of markup is a failed answer, not a thin one. The two list
    fields filter per item but must keep at least one survivor, and a
    `key_files.file` must be one of the names the pack listed; the model
    picks from the vocabulary, it does not extend it.
    """
    _reject_extra(raw, _NODE_KEYS, "node answer")
    banned = TEXT_BANNED_MARKUP

    role = raw.get("role")
    if not isinstance(role, list) or not (NODE_ROLE_MIN <= len(role) <= NODE_ROLE_MAX):
        raise Rejected(f"role must be a list of {NODE_ROLE_MIN} to "
                       f"{NODE_ROLE_MAX} paragraphs")
    for para in role:
        problem = _prose_problem(para, ROLE_MAX_CHARS, banned)
        if problem is not None:
            raise Rejected(f"role paragraph: {problem}")
    out = {"role": list(role)}

    for field in ("reads", "feeds"):
        value = raw.get(field)
        problem = _prose_problem(value, READS_FEEDS_MAX_CHARS, banned)
        if problem is not None:
            raise Rejected(f"{field}: {problem}")
        out[field] = value

    items = raw.get("key_files")
    if not isinstance(items, list):
        raise Rejected("key_files is not a list")
    allowed_names = set(unit.choices)
    kept_files, seen = [], set()
    for item in items[:KEY_FILES_MAX]:
        if not isinstance(item, dict):
            continue
        _reject_extra(item, frozenset({"file", "purpose"}), "key_files entry")
        name = item.get("file")
        base = _basename(name) if isinstance(name, str) else ""
        if base not in allowed_names or base in seen:
            continue
        if _prose_problem(item.get("purpose"), PURPOSE_MAX_CHARS, banned) is not None:
            continue
        seen.add(base)
        kept_files.append({"file": base, "purpose": item["purpose"]})
    if not kept_files:
        raise Rejected("no key_files entry names a listed file")
    out["key_files"] = kept_files

    concepts = raw.get("concepts")
    if not isinstance(concepts, list):
        raise Rejected("concepts is not a list")
    kept_concepts = _dedupe(
        [c for c in concepts
         if _prose_problem(c, CONCEPT_MAX_CHARS, banned) is None])[:CONCEPTS_MAX]
    if not kept_concepts:
        raise Rejected("concepts carries no usable term")
    out["concepts"] = kept_concepts

    _clean_optional_cite(raw, out, banned)
    return out


def _parse_gloss(raw: dict, unit: Unit) -> dict:
    """`{terms: [{term, def, cite?}]}`. Bad terms drop; bad shape rejects."""
    _reject_extra(raw, frozenset({"terms"}), "gloss answer")
    terms = raw.get("terms")
    if not isinstance(terms, list):
        raise Rejected("terms is not a list")

    banned = TEXT_BANNED_MARKUP
    kept, seen = [], set()
    for item in terms[: unit.max_claims]:
        if not isinstance(item, dict):
            continue
        _reject_extra(item, frozenset({"term", "def", "cite"}), "glossary term")
        term, definition = item.get("term"), item.get("def")
        if _prose_problem(term, TERM_MAX_CHARS, banned) is not None:
            continue
        if _prose_problem(definition, DEF_MAX_CHARS, banned) is not None:
            continue
        key = term.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        entry = {"term": term, "def": definition}
        _clean_optional_cite(item, entry, banned)
        entry.pop("caption", None)          # terms carry no caption field
        kept.append(entry)
    return {"terms": kept} if kept else {}


def _parse_tour(raw: dict, unit: Unit) -> dict:
    """`{steps: [{id, text}]}`, ids fixed by the pack, output in pack order.

    A step naming an id off the fixed list is the tour equivalent of a quote
    outside the shown windows: dropped, and stage 4 would drop it again
    (`t-<id>`) if it slipped through. Order is normalised to the pack's,
    because the board walks the pipeline, not the model's whim.
    """
    _reject_extra(raw, frozenset({"steps"}), "tour answer")
    steps = raw.get("steps")
    if not isinstance(steps, list):
        raise Rejected("steps is not a list")

    by_id = {}
    for step in steps:
        if not isinstance(step, dict):
            continue
        _reject_extra(step, frozenset({"id", "text"}), "tour step")
        sid = step.get("id")
        if sid not in unit.choices or sid in by_id:
            continue
        if _prose_problem(step.get("text"), TOUR_TEXT_MAX_CHARS,
                          TEXT_BANNED_MARKUP) is not None:
            continue
        by_id[sid] = {"id": sid, "text": step["text"]}

    ordered = [by_id[sid] for sid in unit.choices if sid in by_id]
    return {"steps": ordered} if ordered else {}


def _parse_cols(raw: dict, unit: Unit) -> dict:
    """`{labels: [...]}`: positional, so the count must match exactly."""
    _reject_extra(raw, frozenset({"labels"}), "cols answer")
    labels = raw.get("labels")
    if not isinstance(labels, list):
        raise Rejected("labels is not a list")
    if len(labels) != unit.max_claims:
        raise Rejected(f"expected {unit.max_claims} labels, got {len(labels)}")
    for label in labels:
        problem = _prose_problem(label, COL_LABEL_MAX_CHARS, TEXT_BANNED_MARKUP)
        if problem is not None:
            raise Rejected(f"label: {problem}")
        if label != label.upper():
            raise Rejected(f"label {label!r} is not uppercase")
    return {"labels": list(labels)}


def _parse_unit(raw, unit: Unit) -> tuple[list, dict | None, list]:
    """-> (claims, structured answer or None, ledger rows), by unit kind."""
    if unit.kind in STRUCTURED_KINDS:
        answer, rows = parse_structured(raw, unit)
        return [], answer, rows
    claims, rows = parse(raw, unit)
    return claims, None, rows


def _answer_items(kind: str, answer: dict | None) -> int:
    """How much content a structured answer carries, for the unit record."""
    if not answer:
        return 0
    if kind == "node":
        return 1
    key = {"gloss": "terms", "tour": "steps", "cols": "labels"}.get(kind, "")
    return len(answer.get(key) or []) if key else 1


# ---------------------------------------------------------------------------
# per-unit response schemas
# ---------------------------------------------------------------------------

def _cite_schema() -> dict:
    """A fresh copy of the cite schema, so callers can embed it safely."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "file": {"type": "string"},
            "quote": {"type": "string"},
            "focus": {"type": "array", "items": {"type": "string"}},
        },
    }


def schema_for(unit: Unit) -> dict:
    """The response schema THIS unit's answer must satisfy.

    The claim kinds share `provider.SCHEMA` verbatim; the structured kinds
    each get their own, built per unit so the fixed vocabularies (`tour` step
    ids, `key_files` names) are enums the provider can enforce before the
    parser re-checks them in code. Both `run` and `emit_prompts` route
    through here, so the schema the live API constrains against and the
    schema a pack shows the answering agent are the same object shape.
    """
    if unit.kind == "node":
        file_schema = {"type": "string"}
        if unit.choices:
            file_schema["enum"] = list(unit.choices)
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["role", "reads", "feeds", "key_files", "concepts"],
            "properties": {
                "role": {"type": "array", "minItems": NODE_ROLE_MIN,
                         "maxItems": NODE_ROLE_MAX,
                         "items": {"type": "string", "maxLength": ROLE_MAX_CHARS}},
                "reads": {"type": "string", "maxLength": READS_FEEDS_MAX_CHARS},
                "feeds": {"type": "string", "maxLength": READS_FEEDS_MAX_CHARS},
                "key_files": {
                    "type": "array", "minItems": 1, "maxItems": KEY_FILES_MAX,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["file", "purpose"],
                        "properties": {
                            "file": file_schema,
                            "purpose": {"type": "string",
                                        "maxLength": PURPOSE_MAX_CHARS},
                        },
                    },
                },
                "concepts": {"type": "array", "minItems": 1,
                             "maxItems": CONCEPTS_MAX,
                             "items": {"type": "string",
                                       "maxLength": CONCEPT_MAX_CHARS}},
                "cite": _cite_schema(),
                "caption": {"type": "string", "maxLength": CAPTION_MAX_CHARS},
            },
        }
    if unit.kind == "gloss":
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["terms"],
            "properties": {
                "terms": {
                    "type": "array", "maxItems": unit.max_claims,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["term", "def"],
                        "properties": {
                            "term": {"type": "string",
                                     "maxLength": TERM_MAX_CHARS},
                            "def": {"type": "string",
                                    "maxLength": DEF_MAX_CHARS},
                            "cite": _cite_schema(),
                        },
                    },
                },
            },
        }
    if unit.kind == "tour":
        id_schema = {"type": "string"}
        if unit.choices:
            id_schema["enum"] = list(unit.choices)
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["steps"],
            "properties": {
                "steps": {
                    "type": "array", "minItems": unit.max_claims,
                    "maxItems": unit.max_claims,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "text"],
                        "properties": {
                            "id": id_schema,
                            "text": {"type": "string",
                                     "maxLength": TOUR_TEXT_MAX_CHARS},
                        },
                    },
                },
            },
        }
    if unit.kind == "cols":
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["labels"],
            "properties": {
                "labels": {"type": "array", "minItems": unit.max_claims,
                           "maxItems": unit.max_claims,
                           "items": {"type": "string",
                                     "maxLength": COL_LABEL_MAX_CHARS}},
            },
        }
    return SCHEMA


# ---------------------------------------------------------------------------
# the unit loop
# ---------------------------------------------------------------------------

def run(survey: dict, root, prov, *, work=None, commands: dict | None = None,
        hops: list | None = None, map_data: dict | None = None,
        max_units: int = MAX_UNITS_DEFAULT,
        offline: bool = False, verbose: bool = False) -> dict:
    """Narrate one repo. Serial, cached, and the only place `prov` is touched.

    Serial on purpose: a thread pool buys ~90 seconds once, on a run the disk
    cache makes free for every rehearsal afterwards, in exchange for
    partial-failure handling, result ordering and Ctrl-C behaviour.

    Returns, all keyed by unit id where it matters:

        narration      unit id -> claims (claim kinds, `content@1` shape, ids
                       stamped) OR the validated structured answer dict for
                       `node:`/`gloss`/`tour`/`cols` units, `{}` on absence
        windows        unit id -> the quotable spans the model was shown
        ledger         drop rows the parser produced, ids from the same counter
        degradations   §9 row 7, plus `unit_unnarrated` for a silent gap
        model          provider, model, calls, cache hits, duration
        units          one record per unit, including its cache key

    A unit whose response is rejected twice contributes zero claims and one
    ledger row; its stop then renders from template blocks. That is a thinner
    page, not a broken one, which is the whole reason the fallback exists.

    A unit that comes back **empty** — no claims, no drop rows — is the other
    shape of the same thing and used to be invisible, so it now appends a
    `unit_unnarrated` degradation. See `_unnarrated_degradations` for why that
    fires on a partly-answered store and not on a cold one.
    """
    started = time.monotonic()
    units, degradations = build_units(survey, commands, hops,
                                      map_data=map_data, max_units=max_units)
    store = _store(work)

    counter = _Counter()
    narration, windows, ledger, records = {}, {}, [], []
    empty = []
    calls = hits = 0

    for unit in units:
        system, user, unit_windows = prompts.pack(unit, survey, root)
        key = cache_key(system, user)
        schema = schema_for(unit)
        structured = unit.kind in STRUCTURED_KINDS
        windows[unit.id] = [{"file": w.file, "start": w.start, "end": w.end}
                            for w in unit_windows]

        raw = _read_store(store, key)
        source = "cache"
        if raw is None:
            if offline:
                raise MissingNarration(
                    f"no narration for unit {unit.id} (key {key}) and --offline is set"
                )
            raw = prov.complete(system, user, schema)
            calls += 1
            source = "provider"
            _write_store(store, key, raw)
        else:
            hits += 1

        try:
            claims, answer, rows = _parse_unit(raw, unit)
        except Rejected as first:
            # One retry, and only when the answer came from a provider: a
            # second read of the same cache entry returns the same bytes and
            # fails the same way, so retrying it is a slower way to lose.
            claims, answer, rows = [], ({} if structured else None), []
            detail = str(first)
            if source == "provider":
                retry = prov.complete(system, user, schema)
                calls += 1
                try:
                    claims, answer, rows = _parse_unit(retry, unit)
                    _write_store(store, key, retry)
                    detail = None
                except Rejected as second:
                    detail = f"{first}; retry: {second}"
            if detail is not None:
                source = "rejected"
                rows = [_row(f"{unit.title}: the model's response could not be parsed",
                             unit.files[0] if unit.files else "",
                             _reason(REASON_UNPARSEABLE, detail))]

        for claim in claims:
            claim["id"] = counter.next()
        for row in rows:
            row["id"] = counter.next()

        narration[unit.id] = answer if structured else claims
        content = _answer_items(unit.kind, answer) if structured else len(claims)
        ledger += rows
        records.append({
            "id": unit.id, "kind": unit.kind, "title": unit.title,
            "max_claims": unit.max_claims, "files": list(unit.files),
            "key": key, "source": source,
            "claims": content, "dropped": len(rows),
        })
        if not content and not rows and unit.kind in CORE_KINDS:
            # Only the claim-shaped @2 units can go SILENTLY missing: an
            # unanswered structured unit is the designed @2 fallback, not a
            # gap on a page that looks narrated.
            empty.append((unit, key, source))
        if verbose:
            sys.stderr.write(
                f"narrate {unit.id}: {content} item(s), {len(rows)} dropped "
                f"({source}, key {key[:12]})\n"
            )

    degradations += _unnarrated_degradations(empty, records)

    return {
        "narration": narration,
        "windows": windows,
        "ledger": ledger,
        "degradations": degradations,
        "units": records,
        "model": {
            "provider": getattr(prov, "name", "unknown"),
            "model": getattr(prov, "model", "unknown"),
            "calls": calls,
            "cache_hits": hits,
            "duration_s": round(time.monotonic() - started, 3),
        },
    }


def _unnarrated_degradations(empty: list, records: list) -> list:
    """One row per unit that produced nothing while its siblings produced prose.

    The condition is deliberately *partial*, not *any*:

      * **Nothing narrated at all** is the cold-store case. Every stop renders
        from its template, the page carries no claims whatsoever, and the CLI
        already says so in one sentence — "every sentence on the page is a
        deterministic template". Nobody mistakes that page for a narrated one,
        and firing a row per unit there would rewrite the degradation vocabulary
        that §11.3's four per-repo golden files compare as an exact set, on
        every repo, for a condition those files were written to describe as
        normal.
      * **Some narrated, one did not** is the silent case, and it is the one
        that reaches a stage. The page looks narrated, the drop count reads 0
        because nothing was dropped — nothing was ever produced — and the only
        trace is arithmetic in `model 9 claim(s) from 2/3 unit(s)`. Measured on
        `restored`: one stop lost its entire prose to a nondeterministic cache
        key and every artifact reported success.

    A unit whose response was *rejected* is excluded by construction: it carries
    a ledger row, so it is already on screen in the audit table and already in
    the dropped count. Empty means empty.

    The row labels the gap. It never fills it — synthesising prose for a unit
    the model never answered is the one thing this project exists not to do.
    """
    narrated = sum(1 for record in records if record["claims"])
    if not empty or not narrated:
        return []

    rows = []
    for unit, key, source in empty:
        rows.append({
            "code": CODE_UNNARRATED,
            "unit": unit.id,
            "key": key,
            "source": source,
            "reason": (f"{unit.title}: the narration store had no answer for this "
                       f"unit's prompt (key {key[:12]}), so its stop renders from "
                       f"templates and carries no claims. "
                       f"{narrated} of {len(records)} units narrated."),
        })
        # Not gated on --verbose. A unit that vanished is exactly the thing the
        # operator must not learn from the page during the pitch.
        # ASCII: the console this is demoed on is cp1252 and an em dash arrives
        # there as a replacement character, on the one line whose job is to be
        # read (`cli._read` makes the same call for the same reason).
        sys.stderr.write(
            f"narrate: unit {unit.id} produced NO claims and NO drops "
            f"({source}, key {key[:12]}) - its stop renders from templates\n"
        )
    return rows


class _Counter:
    """`c-001`, `c-002`, … one sequence for kept AND dropped claims (§6.7).

    Globally unique ids are what let the gate assert that no dropped id appears
    anywhere in `tracks`; the renderer's marker label is `id.slice(-3)`, so the
    three-digit zero-padding is what stops `c-7` rendering as `c-7`.
    """

    def __init__(self, start: int = 1):
        self.n = start

    def next(self) -> str:
        if self.n >= 1000:
            raise ValueError("claim ids exhausted: more than 999 claims in one run")
        out = f"c-{self.n:03d}"
        self.n += 1
        return out


# ---------------------------------------------------------------------------
# the agent route
# ---------------------------------------------------------------------------

def emit_prompts(survey: dict, root, work, *, commands: dict | None = None,
                 hops: list | None = None, map_data: dict | None = None,
                 max_units: int = MAX_UNITS_DEFAULT) -> list[dict]:
    """Write one prompt pack per unit and return the packs as written.

    Each pack carries its OWN absolute `out` path, computed here from the same
    `cache_key` the replay will use. That is the point of the design: the agent
    answering a pack never computes a sha256 by hand, never gets it wrong, and
    never produces a store the stub cannot find.

    The pack is self-describing (schema included, and since @3 the schema is
    the UNIT's schema, not the claims schema), so answering one needs nothing
    but the file.
    """
    root = Path(root)
    store = _store(work)
    inbox = Path(work) / PROMPTS_DIRNAME
    inbox.mkdir(parents=True, exist_ok=True)
    store.mkdir(parents=True, exist_ok=True)

    units, _ = build_units(survey, commands, hops, map_data=map_data,
                           max_units=max_units)
    packs = []
    for unit in units:
        system, user, windows = prompts.pack(unit, survey, root)
        key = cache_key(system, user)
        pack = {
            "unit": unit.id,
            "kind": unit.kind,
            "title": unit.title,
            "max_claims": unit.max_claims,
            "key": key,
            "system": system,
            "user": user,
            "windows": [{"file": w.file, "start": w.start, "end": w.end}
                        for w in windows],
            "schema": schema_for(unit),
            "out": str((store / f"{key}.json").resolve()),
            "pack": str((inbox / f"{key}.json").resolve()),
        }
        _write_json(inbox / f"{key}.json", pack)
        packs.append(pack)
    return packs


def _store(work) -> Path:
    """The narration store. One directory, shared by record and replay."""
    return Path(work) / CACHE_DIRNAME if work is not None else Path(CACHE_DIRNAME)


def _read_store(store: Path, key: str):
    path = store / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # A corrupt entry is a miss, not a crash: the run continues and the
        # unit either calls out again or falls back to its template.
        return None


#: A stored answer must carry at least one of these, non-empty. `claims` is
#: the @2 shape; the rest are the structured @3 answers. Anything else is a
#: miss dressed up as an answer and must never enter the store.
_STORE_CONTENT_KEYS = ("claims", "role", "terms", "steps", "labels")


def _write_store(store: Path, key: str, raw) -> None:
    """Record a real answer. A stub miss is never written.

    Writing `{"claims": []}` (or `{"terms": []}`) would poison the store: the
    next run would replay the empty answer as a hit and the unit could never
    recover, which is the opposite of what a cache is for.
    """
    if not isinstance(raw, dict) or not any(raw.get(k) for k in _STORE_CONTENT_KEYS):
        return
    store.mkdir(parents=True, exist_ok=True)
    _write_json(store / f"{key}.json", raw)


def _write_json(path: Path, data) -> None:
    """Atomic UTF-8 write with LF endings — tmp then `os.replace` (§10)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# `py -3.11 -m trailhead.narrate` — the stage, on its own
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Run stage 3 alone, for building the narration store and for debugging.

    The real pipeline goes through `cli.py`; this exists so the stage can be
    driven before the CLI lands and so `--emit-prompts` can be run by hand.
    """
    parser = argparse.ArgumentParser(prog="trailhead.narrate", description=__doc__.split("\n")[0])
    parser.add_argument("survey", help="path to survey.json")
    parser.add_argument("--root", help="repo root (default: survey.repo.root)")
    parser.add_argument("--work", default=".trailhead", help="work dir (default .trailhead)")
    parser.add_argument("--commands", help="path to commands.json")
    parser.add_argument("--hops", help="path to a trace hop fixture")
    parser.add_argument("--map", dest="map_path",
                        help="path to map.json (enables the node/dive/tour/cols units)")
    parser.add_argument("--provider", choices=("stub", "claude"), default="stub")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--emit-prompts", action="store_true",
                        help="write one prompt pack per unit and exit")
    parser.add_argument("--max-units", type=int, default=MAX_UNITS_DEFAULT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    survey = json.loads(Path(args.survey).read_text(encoding="utf-8"))
    root = args.root or (survey.get("repo") or {}).get("root") or "."
    commands = (json.loads(Path(args.commands).read_text(encoding="utf-8"))
                if args.commands else None)
    hops = json.loads(Path(args.hops).read_text(encoding="utf-8")) if args.hops else None
    if isinstance(hops, dict):
        hops = hops.get("hops") or hops.get("steps") or []
    map_data = (json.loads(Path(args.map_path).read_text(encoding="utf-8"))
                if args.map_path else None)

    if args.emit_prompts:
        packs = emit_prompts(survey, root, args.work, commands=commands, hops=hops,
                             map_data=map_data, max_units=args.max_units)
        for pack in packs:
            sys.stderr.write(f"{pack['unit']:6s} -> {pack['pack']}\n")
        sys.stderr.write(f"{len(packs)} pack(s) written. Answer each into its own 'out' path.\n")
        return 0

    prov = provider_mod.build(args.provider, _store(args.work), offline=args.offline)
    result = run(survey, root, prov, work=args.work, commands=commands, hops=hops,
                 map_data=map_data, max_units=args.max_units,
                 offline=args.offline, verbose=args.verbose)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
