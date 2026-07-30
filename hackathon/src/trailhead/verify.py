"""Stage 4 — VERIFY. Deterministic. No model.

This is the machine that checks the model, and it is the only reason the project
has a pitch. It re-reads every anchor stage 3 claimed, resolves each verbatim
quote to a line range in code, recomputes the sha256 with `textio`'s recipe, and
**deletes** whatever does not hold. The deletions are counted on screen.

Nothing in this module may call a provider (non-negotiable #1). A model cannot
verify itself, so every judgement below is ordinary Python over bytes on disk.

    content.json + survey.json + map.json + commands.json + the repo on disk
                                  |
                                  v
              verified.json  +  verification-report.json

Three things here are load-bearing beyond the obvious merge:

  * **The ledger is the product.** A drop needs a reason from the enumerated
    vocabulary (§6.6) that a human reading the audit panel would accept. A
    silent filter defeats non-negotiable #3 more thoroughly than a bug would.
  * **`report` is assembled last, by walking the emitted payload.**
    `report.dropped === dropped.length` and `report.failed ===` the number of
    *rendered* failing command blocks are the two cross-checks
    `tools/verify-contract.js` fails a payload for.
  * **`self_police` catches what neither gate checks.** Neither gate executes
    the renderer, so a payload missing `repo.generated_at` throws inside
    `shell()` before the first stop draws and still passes both gates — a blank
    page with a green light. That failure mode is why this module aborts on its
    own checks rather than trusting the Node ones.
"""
import copy
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping, Sequence

from trailhead import TOOL_VERSION, resolve
from trailhead.textio import Source, read_source, rel_key, sha256_range

#: Re-exported so the widening rule has one implementation and one owner.
#: `resolve.py` hands back the range the QUOTE occupies; this module widens it,
#: adds `focus` and `sha256`, and only then is it a contract anchor.
expand_anchor = resolve.expand_anchor

#: `file -> (lines, quotable windows)`. The lines are the ones the model was
#: SHOWN, which need not be what is on disk now — that difference is what makes
#: `excerpt hash mismatch` a real reason rather than a decorative one.
Snapshot = resolve.Snapshot
Anchor = resolve.Anchor

#: `trailhead/verified@2` — decision #14. `verify-contract.js` asserts the
#: string, so a silent bump is a gate failure rather than a surprise on stage.
CONTRACT = "trailhead/verified@2"

#: The audit log this module writes beside the payload. Not shipped in the
#: bundle and not read by the renderer; it exists so a drop can be explained
#: after the fact without re-running the pipeline.
REPORT_CONTRACT = "trailhead/verification-report@1"

#: Anchor cap, in lines. Best effort — focus containment outranks it (§6.2).
ANCHOR_CAP = 24

#: Focus lines kept per anchor. A 20-line highlight inside a 24-line excerpt
#: highlights nothing.
FOCUS_CAP = 4

#: Above this the page prepends a low-confidence callout and `shell()` turns the
#: badge amber (§9 row 5).
LOW_CONFIDENCE = 0.40

# --- The drop vocabulary (§6.6) -------------------------------------------
# Four frozen in docs/verified-contract.md, eight added by the plan. A reason
# reaching the ledger is either one of these verbatim or one of these followed
# by " — <detail>", so the vocabulary stays a set of literals while the
# on-screen string can still name a match count.

REASON_NOT_FOUND = "snippet not found verbatim in file"
REASON_NO_FILE = "file does not exist at this commit"
REASON_HASH = "excerpt hash mismatch — file changed after narration"
REASON_AMBIGUOUS = "snippet ambiguous"
REASON_AMBIGUOUS_FILES = "snippet ambiguous across files shown to the model"
REASON_WRONG_FILE = "snippet belongs to a different file than the one cited"
REASON_OUTSIDE = "snippet resolved outside the excerpt shown to the model"
REASON_THIN = "quote too thin to be unique"
REASON_SHORT = "quote shorter than two lines"
REASON_LONG = "quote longer than the anchor cap"
REASON_UNPARSEABLE = "model returned unparseable output"

#: Composed rather than restated: `resolve.py` owns the eight it can emit, this
#: module owns the four that need the disk or the parser. Restating the eight
#: here would be a second copy of a frozen vocabulary, free to drift.
DROP_REASONS = frozenset(resolve.REASONS) | {
    REASON_NO_FILE,
    REASON_HASH,
    REASON_UNPARSEABLE,
}

#: The twelfth reason is a template rather than a literal, so it gets a pattern.
_OUT_OF_RANGE = re.compile(r"^lines \d+-\d+ out of range \(file ends at \d+\)$")

#: Accepted on input, never emitted. `fixtures/verified.sample.json` is frozen
#: and gate-green with the colon punctuation this project later standardised to
#: an em dash; a self-police rule that rejects the reference payload is a bug in
#: the rule, not in the payload.
_LEGACY_REASONS = frozenset({"excerpt hash mismatch: file changed after narration"})

#: Claim ids. `^c-\d{3,}$` because the renderer's marker label is
#: `c.id.slice(-3)`: `c-7` renders as `c-7` and `claim-1042` renders as `042`.
_CLAIM_ID = re.compile(r"^c-\d{3,}$")
_NUMERIC_ID = re.compile(r"^c-(\d+)$")

#: The two tags `textio.cell` is allowed to add. Anything else on a surface the
#: renderer interpolates without `esc()` is unescaped markup carried in data.
_WHITELIST_TAGS = re.compile(r"</?(?:code|b)>")

#: `runner.classify_failure`'s rule, mirrored here for the case where a capture
#: arrives without one. See `_derive_broken` for why that is not duplication.
_FAILURE_LINE = re.compile(r"(Error|Exception|error:|FAILED|assert)")

class VerifyError(Exception):
    """Assembly refused to emit a payload.

    Raised only by `self_police`'s violations and by the id-space guard. Every
    one of them is a defect that both Node gates pass and the browser does not,
    so failing loudly here is the whole point of raising at all.
    """


# --- Drop reasons ----------------------------------------------------------


def reason_text(why) -> str:
    """The ledger string for whatever `resolve.py` handed back.

    `resolve.Drop` is a `str` subclass carrying a `detail`, so the frozen
    vocabulary stays a set of literals while the on-screen reason still names
    the match count. Formatting it is the ledger boundary's job, and this
    module is the ledger boundary.
    """
    full = getattr(why, "full", None)
    return full() if callable(full) else str(why)


def is_known_reason(reason: str) -> bool:
    """True if `reason` is vocabulary, or vocabulary plus a ` — detail` tail."""
    if not isinstance(reason, str) or not reason.strip():
        return False
    if _OUT_OF_RANGE.match(reason) or reason in _LEGACY_REASONS:
        return True
    return any(reason == r or reason.startswith(r + " — ") for r in DROP_REASONS)


def reason_out_of_range(start: int, end: int, end_of_file: int) -> str:
    """The one templated reason, built in one place so it stays greppable."""
    return f"lines {start}-{end} out of range (file ends at {end_of_file})"


# --- Payload walkers (§6.5) ------------------------------------------------


def iter_blocks(tracks: Sequence[dict]) -> Iterator[dict]:
    """Every block of every stop of every track, in document order."""
    for track in tracks or []:
        for stop in track.get("stops", []):
            for block in stop.get("blocks", []):
                yield block


def iter_anchors(payload: Mapping) -> Iterator[Anchor]:
    """Every anchor in the ASSEMBLED payload — claims, trace steps, excerpts.

    `files` is built from this walk and never from the claim list.
    `verify-contract.js` runs its full anchor check on every trace step and on
    every excerpt block, not only on prose claims, and trace anchors are survey-derived, so a
    `files` map built from claim anchors alone fails every trace hop with
    `file not bundled` — on the stop that carries the pitch.
    """
    for block in iter_blocks(payload.get("tracks", [])):
        kind = block.get("type")
        if kind == "prose":
            for claim in block.get("claims", []):
                if claim.get("anchor"):
                    yield claim["anchor"]
        elif kind == "trace":
            for step in block.get("steps", []):
                if step.get("anchor"):
                    yield step["anchor"]
        elif kind == "excerpt":
            if block.get("anchor"):
                yield block["anchor"]
        elif kind == "lineage":
            # `@2`'s tenth block type anchors its steps and its failure mode the
            # same way a claim does, and the gate runs the same `anchor()` over
            # both. Missing them here bundles no lines for either and fails
            # every one of them with `file not bundled`.
            for entity in block.get("entities", []) or []:
                for step in entity.get("steps", []) or []:
                    if step.get("anchor"):
                        yield step["anchor"]
                failure = entity.get("failure_mode") or {}
                if failure.get("anchor"):
                    yield failure["anchor"]


# --- Anchors (§6.2, §6.3) --------------------------------------------------


def anchor_for(cite: Mapping, snap: Snapshot) -> tuple[Anchor | None, str | None]:
    """One cite -> a contract anchor, or a reason it could not become one.

    `resolve.arbitrate` decides *where* the quote is — including the two
    cross-file rows, whose precedence is fixed there. This function turns that
    match range into the thing the payload ships: widened to a readable window,
    with `focus` placed inside it and the sha256 taken over the same lines the
    bundle will carry. Splitting it that way keeps the resolver free of the
    disk, the hash and the ledger, which is why it can be tested from two lists
    of strings.
    """
    span, why = resolve.arbitrate(dict(cite), _normalised(snap))
    if span is None:
        return None, reason_text(why)

    path, ms, me = span["file"], span["start"], span["end"]
    lines = _lines_of(snap[path])
    start, end = resolve.expand_anchor(lines, ms, me, cap=ANCHOR_CAP,
                                       python=str(path).endswith(".py"))
    if not (start <= ms and me <= end):  # pragma: no cover - true by construction
        raise VerifyError(f"anchor {start}-{end} does not contain its match {ms}-{me}")

    focus = [n for n in resolve.focus_lines(cite.get("quote") or "",
                                            cite.get("focus"), ms, cap=FOCUS_CAP)
             if start <= n <= end]
    return {
        "file": path,
        "start": start,
        "end": end,
        "focus": focus,
        "sha256": sha256_range(lines, start, end),
    }, None


def _normalised(snap: Snapshot) -> dict:
    """Snapshot values as the `(lines, windows)` pairs `resolve` unpacks.

    A caller holding only the text — the common case, since narrate and verify
    usually run minutes apart against the same bytes — may pass a bare line
    list. Coercing here means that convenience never reaches `resolve.py`,
    which is entitled to assume the documented shape.
    """
    out = {}
    for path, entry in snap.items():
        if isinstance(entry, (tuple, list)) and len(entry) == 2 and \
                not isinstance(entry[0], str):
            out[path] = (list(entry[0]), entry[1])
        else:
            out[path] = (list(entry), None)
    return out


def _lines_of(entry) -> list[str]:
    """The line list out of a snapshot value, whichever shape it arrived in."""
    if isinstance(entry, (tuple, list)) and len(entry) == 2 and \
            not isinstance(entry[0], str):
        return list(entry[0])
    return list(entry)


def verify_claim(claim: Mapping, snap: Snapshot,
                 sources: Mapping[str, Source]) -> tuple[dict | None, dict | None]:
    """-> (kept_claim_with_anchor, None) or (None, ledger_row). Never both.

    The two-source shape is deliberate. `snap` is what the model was shown;
    `sources` is the file as it is on disk now. Resolving against the snapshot
    is what makes the window check meaningful, and re-hashing against disk is
    what catches a file edited between narration and verification — the
    `excerpt hash mismatch` row. When they agree, which is the normal case, the
    digest is the same number computed twice.
    """
    out = copy.deepcopy(dict(claim))
    cite = out.pop("cite", None)
    out.pop("anchor", None)
    status = out.get("status") or ("inferred" if not cite else "verified")

    if status == "inferred":
        # NN2: an anchor is what makes a claim render as verified, so an
        # inferred claim carrying one is a lie by markup. Delete the key — not
        # blank it, not null it: the gate's `if (c.anchor)` is
        # and that is true for `{}`.
        out["status"] = "inferred"
        out.pop("anchor", None)
        return out, None

    if status != "verified":
        return None, _ledger_row(out, cite,
                                 f"{REASON_UNPARSEABLE} — unknown claim status "
                                 f"{status!r}")

    if not cite or not str(cite.get("quote") or "").strip():
        return None, _ledger_row(
            out, cite, f"{REASON_UNPARSEABLE} — verified claim carries no quote")

    path = cite.get("file")
    if not isinstance(path, str) or not path.strip():
        return None, _ledger_row(
            out, cite, f"{REASON_UNPARSEABLE} — cite names no file")
    if path not in sources:
        return None, _ledger_row(out, cite, REASON_NO_FILE)

    anchor, why = anchor_for(cite, snap)
    if anchor is None:
        return None, _ledger_row(out, cite, why or REASON_NOT_FOUND)

    disk = sources[path].lines
    if anchor["end"] > len(disk):
        return None, _ledger_row(
            out, cite, reason_out_of_range(anchor["start"], anchor["end"], len(disk)))

    digest = sha256_range(disk, anchor["start"], anchor["end"])
    if digest != anchor["sha256"]:
        return None, _ledger_row(out, cite, REASON_HASH)

    anchor["sha256"] = digest
    for line in anchor["focus"]:
        assert anchor["start"] <= line <= anchor["end"], "focus escaped its anchor"
    out["status"] = "verified"
    out["anchor"] = anchor
    return out, None


def _ledger_row(claim: Mapping, cite: Mapping | None, reason: str) -> dict:
    """One row of the on-screen audit ledger: id, text, file, reason.

    The renderer's ledger table reads all four; the gate checks only `reason`,
    which is exactly why the other three are filled in here rather than left to
    render as `undefined` in front of an audience.
    """
    return {
        "id": claim.get("id"),
        "text": claim.get("text") or claim.get("claim") or "",
        "file": (cite or {}).get("file") or "—",
        "reason": reason,
    }


# --- Snapshot construction -------------------------------------------------


def cited_files(content: Mapping) -> set[str]:
    """Every path `content.json` points at, whether by quote or by anchor.

    Anchors are collected as well as cites because a lineage step may arrive
    already resolved from survey data. Stage 4 re-reads it regardless — "the
    machine that checks the model" checks everything it ships, not only the
    parts a model wrote — and it cannot re-read a file it never opened.
    """
    out: set[str] = set()

    def take(node) -> None:
        for key in ("cite", "anchor"):
            path = ((node or {}).get(key) or {}).get("file")
            if path:
                out.add(path)

    for block in iter_blocks(content.get("tracks", [])):
        kind = block.get("type")
        if kind == "prose":
            for claim in block.get("claims", []):
                take(claim)
        elif kind == "trace":
            for step in block.get("steps", []):
                take(step)
        elif kind == "excerpt":
            take(block)
        elif kind == "lineage":
            for entity in block.get("entities", []) or []:
                for step in entity.get("steps", []) or []:
                    take(step)
                take({"cite": (entity.get("failure_mode") or {}).get("cite"),
                      "anchor": (entity.get("failure_mode") or {}).get("anchor")})
    return out


def build_snapshot(content: Mapping, root: Path, *,
                   windows: Mapping[str, Sequence[tuple[int, int]]] | None = None
                   ) -> tuple[dict, dict]:
    """-> (snap, sources), both keyed by repo-relative forward-slash path.

    Used when the caller has no narration-time snapshot to hand, which is the
    normal case: narrate and verify run minutes apart in one process, so the
    file the model saw and the file on disk are the same bytes.

    A path that `rel_key` cannot round-trip — absolute, backslashed, or escaping
    the root via `..` or a junction — is left out of both maps and drops as
    `file does not exist at this commit`. That is the only place a traversal
    could reach the bundle, and it is closed by construction rather than by a
    denylist.
    """
    root = Path(root)
    snap: dict = {}
    sources: dict[str, Source] = {}
    for rel in sorted(cited_files(content)):
        candidate = root / rel
        try:
            same = rel_key(candidate, root) == rel and candidate.is_file()
        except OSError:
            same = False
        if not same:
            continue
        source = read_source(candidate)
        sources[rel] = source
        # `None` and `()` mean different things to the resolver: "do not scope"
        # against "nothing in this file was quotable". A file with no recorded
        # windows is the first, not the second — the second would drop every
        # claim in the run as `resolved outside the excerpt shown`, which is a
        # total, silent loss dressed up as a verification result.
        window = tuple(tuple(w) for w in (windows or {}).get(rel, ())) or None
        snap[rel] = (source.lines, window)
    return snap, sources


# --- Block merges (§6.4) ---------------------------------------------------


def substitute_checkpoint(block: Mapping, survey: Mapping) -> tuple[dict | None, str | None]:
    """Replace a `{type, id}` reference with the full survey answer key.

    The substitution is **total** — nothing from `content.json` survives except
    the id — so "the shipped key equals the survey key" is true by construction.
    It is self-policed anyway (§6.7): that assertion is all that stands in for
    acceptance test 6, and non-negotiable #6 is the reason there is no model in
    the page to grade a free-text answer.
    """
    key = block.get("id")
    keys = survey.get("checkpoints") or {}
    if key not in keys:
        return None, f"no such checkpoint in survey.json: {key!r}"
    merged = copy.deepcopy(dict(keys[key]))
    merged["type"] = "checkpoint"
    merged["id"] = key
    return merged, None


def index_commands(commands: Mapping) -> dict[tuple[str, str], dict]:
    """`(cmd, cwd) -> run`. One string, three producers, so normalise once."""
    out: dict[tuple[str, str], dict] = {}
    for run in (commands or {}).get("runs", []):
        out[_command_key(run.get("cmd"), run.get("cwd"))] = run
    return out


def _command_key(cmd, cwd) -> tuple[str, str]:
    return (str(cmd or "").strip(), (str(cwd or ".").strip() or "."))


def merge_command(block: Mapping, runs: Mapping[tuple[str, str], dict],
                  env: str) -> tuple[dict | None, str | None]:
    """Merge a real capture into a command block, or refuse to emit one.

    Non-negotiable #4 made mechanical: there is no path here that invents
    `exit`, `out` or `dur`. A block with no matching run is dropped and logged;
    a run whose `exit` is not an integer is treated as no capture at all,
    because `"0"` renders FAILING and `null` renders PASSING while
    the gate demands a banner for the second (`failing command with no
    BROKEN banner`) — a
    self-contradictory page that still passes one gate.
    """
    key = _command_key(block.get("cmd"), block.get("cwd"))
    run = runs.get(key)
    if run is None:
        return None, f"no captured run for {key[0]!r} in {key[1]!r}"

    code = run.get("exit")
    if isinstance(code, bool) or not isinstance(code, int):
        return None, f"capture for {key[0]!r} carries no integer exit code"

    # `(no output)` is the one blessed placeholder in a command block (§8.3): it
    # describes an absence rather than inventing content, and `exit` and `dur`
    # stay real. the gate fails an empty `out` (`no captured output`), so the
    # alternative is not "show nothing" but "fail the gate".
    captured = str(run.get("out") or "").strip() or "(no output)"
    merged = {
        "type": "command",
        "cmd": key[0],
        "cwd": key[1],
        "exit": code,
        "dur": str(run.get("dur") or _dur_from_ms(run.get("dur_ms"))),
        "out": captured,
        "env": str(run.get("env") or env or "").strip(),
    }

    if code != 0:
        merged["broken"] = str(run.get("broken") or _derive_broken(captured, code))
    hypothesis = run.get("hypothesis") or block.get("hypothesis")
    if hypothesis:
        # Always rendered tagged `inferred`, whatever produced it (decision #26).
        merged["hypothesis"] = str(hypothesis)
    if block.get("predict") is not None:
        merged["predict"] = block["predict"]
    return merged, None


def _dur_from_ms(ms) -> str:
    """`dur` is a display string; the renderer prints it verbatim."""
    try:
        return f"{int(ms) / 1000:.1f} s"
    except (TypeError, ValueError):
        return "—"


def _derive_broken(out: str, code: int) -> str:
    """The banner for a failing command, taken verbatim from its real output.

    `runner.classify_failure` is the producer (decision #26) and its value wins
    whenever it is present. This exists because `verify-contract.js` fails
    **every** failing command that reaches the page without a banner, and a
    capture from an older runner, a re-used `commands.json` or a hand-written
    fixture would otherwise take the whole gate down. It quotes the output; it
    never invents a diagnosis.
    """
    lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    for line in reversed(lines):
        if _FAILURE_LINE.search(line):
            return line
    if lines:
        return lines[-1]
    return f"exited {code} with no output"


# --- Assembly (§6.7) -------------------------------------------------------


class _Run:
    """Mutable bookkeeping for one assemble() call.

    Ids are one monotonic counter across the whole run — kept and dropped claims
    draw from the same sequence — but ids that arrived from stage 3 are
    preserved, because the ledger's cross-reference to `content.json` is what
    makes a drop auditable after the fact.
    """

    def __init__(self, content: Mapping):
        self.dropped: list[dict] = []
        self.blocks_dropped: list[dict] = []
        self.stops_dropped: list[dict] = []
        self.stripped_anchors: list[str] = []
        self.kept_verified = 0
        self.kept_inferred = 0
        self._next = self._first_free(content)

    @staticmethod
    def _first_free(content: Mapping) -> int:
        used = [0]
        for block in iter_blocks(content.get("tracks", [])):
            for claim in block.get("claims", []) or []:
                match = _NUMERIC_ID.match(str(claim.get("id") or ""))
                if match:
                    used.append(int(match.group(1)))
        for row in content.get("dropped", []) or []:
            match = _NUMERIC_ID.match(str(row.get("id") or ""))
            if match:
                used.append(int(match.group(1)))
        return max(used) + 1

    def mint(self) -> str:
        n = self._next
        self._next += 1
        if n >= 100000:
            raise VerifyError(
                f"claim id space exhausted at {n}; ids must stay short enough "
                "for the renderer's slice(-3) marker to remain distinct")
        return f"c-{n:03d}"

    def drop(self, row: dict) -> None:
        if not row.get("id"):
            row["id"] = self.mint()
        self.dropped.append(row)


def assemble(content: Mapping, survey: Mapping, map_json: Mapping | None,
             commands: Mapping | None, root: Path | str | None = None, *,
             t0: float | None = None,
             snapshot: Snapshot | None = None,
             sources: Mapping[str, Source] | None = None,
             windows: Mapping[str, Sequence[tuple[int, int]]] | None = None,
             run_stats: Mapping[str, int] | None = None,
             degradations: Sequence[str] = ()) -> tuple[dict, dict]:
    """content + survey + map + commands + the repo on disk -> (payload, report).

    `payload` is `verified.json`, ready for `render.py` and for
    `node tools/verify-contract.js` **unmodified**. `report` is
    `verification-report.json`, the audit log that never ships in the bundle.

    `t0` is `time.monotonic()` taken at the top of stage 1; `report.duration_s`
    is a wall clock over stages 1–5, not over this function.

    Pass `snapshot`/`sources` when narration-time text differs from what is on
    disk — that is the only way the `excerpt hash mismatch` row can ever fire.
    Otherwise both are built from `root`.

    `run_stats` carries the counts only earlier stages know, and it is how
    `report` stays deliberately larger than what the page renders — that gap is
    the point of the pitch. Two keys are read: `commands`, the number of
    commands actually run, and `extra_claims`, claims the narrate parser
    discarded before they ever reached `content.json`.
    """
    if snapshot is None or sources is None:
        if root is None:
            raise VerifyError("assemble needs either a repo root or a prepared "
                              "snapshot and sources")
        built_snap, built_sources = build_snapshot(content, Path(root), windows=windows)
        snapshot = built_snap if snapshot is None else snapshot
        sources = built_sources if sources is None else sources

    survey = survey or {}
    run = _Run(content)

    for row in content.get("dropped", []) or []:
        row = dict(row)
        row.setdefault("file", "—")
        row.setdefault("text", "")
        run.drop(row)

    commands = commands or {}
    runs = index_commands(commands)
    env = str(commands.get("env") or "")

    tracks = []
    for track in content.get("tracks", []):
        stops = []
        for stop in track.get("stops", []):
            built = _verify_stop(stop, run, snapshot, sources, survey, runs, env)
            if built is not None:
                stops.append(built)
        if stops:
            merged = {k: v for k, v in track.items() if k != "stops"}
            merged["stops"] = stops
            if merged.get("minutes") is None:
                # The rail prints `${t.minutes}m` unconditionally. A track that
                # lost a stop to verification should not also lose its estimate
                # to `undefinedm`; the sum of what survived is the only
                # defensible number available here.
                merged["minutes"] = sum(int(s.get("minutes") or 0) for s in stops)
            tracks.append(merged)

    payload = {
        "contract": CONTRACT,
        "repo": _repo_block(content, survey),
        "report": {},
        "map": _map_block(map_json),
        "files": {},
        "tracks": tracks,
        "dropped": run.dropped,
    }
    payload["files"] = bundle_files(payload, sources)

    claims_run = (run.kept_verified + run.kept_inferred + len(run.dropped)
                  + int((run_stats or {}).get("extra_claims", 0)))
    report = {
        "claims": claims_run,
        "verified": run.kept_verified,
        "dropped": len(run.dropped),
        "inferred": run.kept_inferred,
        "commands": int((run_stats or {}).get("commands", len(commands.get("runs", []) or []))),
        "failed": sum(1 for b in iter_blocks(tracks)
                      if b.get("type") == "command" and b.get("exit") != 0),
        "tool_version": TOOL_VERSION,
        "duration_s": max(0, round(time.monotonic() - t0)) if t0 is not None else 0,
    }
    payload["report"] = report

    rate = report["dropped"] / max(report["claims"], 1)
    if rate > LOW_CONFIDENCE:
        _flag_low_confidence(payload, rate)

    violations = self_police(payload, survey)
    if violations:
        raise VerifyError("verified.json failed self-police:\n  - "
                          + "\n  - ".join(violations))

    audit = {
        "contract": REPORT_CONTRACT,
        "generated_at": payload["repo"]["generated_at"],
        "tool_version": TOOL_VERSION,
        "duration_s": report["duration_s"],
        "repo": dict(payload["repo"]),
        "counts": dict(report),
        "drop_rate": round(rate, 4),
        "low_confidence": rate > LOW_CONFIDENCE,
        "anchors": sum(1 for _ in iter_anchors(payload)),
        "files_bundled": len(payload["files"]),
        "files_skipped": sorted(cited_files(content) - set(sources)),
        "files_not_text": sorted(k for k, s in sources.items() if s.note == "not text"),
        "dropped": run.dropped,
        "blocks_dropped": run.blocks_dropped,
        "stops_dropped": run.stops_dropped,
        "anchors_stripped_from_inferred": run.stripped_anchors,
        # §9's fired rows arrive from two earlier stages under their own key;
        # the audit log is where all three meet, so the count in the ledger
        # callout can be taken from one place.
        "degradations": (list(survey.get("degradations") or [])
                         + list(content.get("degradations") or [])
                         + list(degradations)),
    }
    return payload, audit


def _repo_block(content: Mapping, survey: Mapping) -> dict:
    """`repo`, including the `generated_at` that `shell()` throws without.

    Emitted as `…Z` rather than `…+00:00`: the renderer builds its meta line as
    `.replace("T"," ").replace("Z"," UTC")`, so an offset-suffixed timestamp
    renders as `+00:00` beside the word UTC's absence. The contract doc's own
    example is Z-suffixed.
    """
    repo = dict(survey.get("repo") or {})
    repo.update({k: v for k, v in (content.get("repo") or {}).items() if v})
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "name": repo.get("name") or "repo",
        "commit": repo.get("commit") or "unknown",
        "generated_at": stamp.replace("+00:00", "Z"),
    }


def _map_block(map_json: Mapping | None) -> dict:
    """`map.json`'s nodes and edges, copied through with the contract tag off."""
    source = map_json or {}
    return {
        "nodes": copy.deepcopy(list(source.get("nodes", []) or [])),
        "edges": copy.deepcopy(list(source.get("edges", []) or [])),
    }


def _verify_stop(stop: Mapping, run: _Run, snap: Snapshot,
                 sources: Mapping[str, Source], survey: Mapping,
                 runs: Mapping[tuple[str, str], dict], env: str) -> dict | None:
    """One stop's blocks, verified. None if nothing survived.

    An empty stop is never emitted — the renderer and the gate both TypeError on
    one rather than degrading — except that the `audit` stop is hard-guarded
    upstream by `build_course`. A labelled gap reads as a tool that knows what
    it does not know; a blank stop reads as a bug.
    """
    blocks = []
    for block in stop.get("blocks", []):
        built, why = _verify_block(block, run, snap, sources, survey, runs, env)
        if built is None:
            run.blocks_dropped.append({
                "stop": stop.get("id"),
                "type": block.get("type"),
                "id": block.get("id") or block.get("cmd"),
                "reason": why,
            })
            continue
        blocks.append(built)

    if not blocks:
        run.stops_dropped.append({
            "stop": stop.get("id"),
            "reason": "every block on this stop failed verification",
        })
        return None

    out = {k: v for k, v in stop.items() if k != "blocks"}
    out["blocks"] = blocks

    # `kind` is a pure function of the surviving blocks, so it is derived here
    # rather than demanded of stage 3 — and it is load-bearing: a stop not
    # marked `cp` is auto-marked complete the instant it is drawn.
    has_checkpoint = any(b.get("type") == "checkpoint" for b in blocks)
    if not out.get("kind"):
        out["kind"] = "cp" if has_checkpoint else "stop"
    if out["kind"] == "cp":
        if not has_checkpoint:
            # §9 row 8: a checkpoint whose precondition is unmet DROPs its stop.
            # Never render a placeholder quiz — "Checkpoint A unavailable" is
            # worse than no checkpoint.
            run.stops_dropped.append({
                "stop": stop.get("id"),
                "reason": "no checkpoint on this stop resolved to a survey answer key",
            })
            return None
        out.pop("lede", None)
    return out


def _verify_block(block: Mapping, run: _Run, snap: Snapshot,
                  sources: Mapping[str, Source], survey: Mapping,
                  runs: Mapping[tuple[str, str], dict],
                  env: str) -> tuple[dict | None, str | None]:
    """Dispatch one block by type. Unknown types are dropped, never passed on."""
    kind = block.get("type")

    if kind == "prose":
        claims = []
        for claim in block.get("claims", []):
            claim = dict(claim)
            if not claim.get("id"):
                claim["id"] = run.mint()
            if claim.get("status") == "inferred" and (claim.get("cite") or claim.get("anchor")):
                run.stripped_anchors.append(claim["id"])
            kept, row = verify_claim(claim, snap, sources)
            if kept is None:
                run.drop(row)
                continue
            if kept.get("status") == "inferred":
                run.kept_inferred += 1
            else:
                run.kept_verified += 1
            claims.append(kept)
        if not claims:
            return None, "every claim in this prose block failed verification"
        return {"type": "prose", "claims": claims}, None

    if kind == "trace":
        return _verify_trace(block, run, snap, sources)

    if kind == "excerpt":
        cite = block.get("cite") or {}
        anchor, why = anchor_for(cite, snap) if cite else (None, REASON_UNPARSEABLE)
        if anchor is not None:
            anchor, why = _confirm_on_disk(anchor, sources)
        if anchor is None:
            run.drop(_ledger_row({"id": run.mint(),
                                  "text": block.get("caption") or ""}, cite, why))
            return None, why
        out = {k: v for k, v in block.items() if k != "cite"}
        out["anchor"] = anchor
        return out, None

    if kind == "checkpoint":
        return substitute_checkpoint(block, survey)

    if kind == "command":
        return merge_command(block, runs, env)

    if kind == "lineage":
        return _verify_lineage(block, run, snap, sources)

    if kind in ("graph", "ledger", "callout", "table"):
        return copy.deepcopy(dict(block)), None

    return None, f"unknown block type: {kind!r}"


def _verify_lineage(block: Mapping, run: _Run, snap: Snapshot,
                    sources: Mapping[str, Source]) -> tuple[dict | None, str | None]:
    """Resolve each lineage step's quote, downgrading rather than deleting.

    A trace hop that fails resolution is dropped: the chain is the point, and a
    hop with no evidence is noise. A lineage step is different. SOURCE → ... →
    OUTCOME is a fixed shape, and deleting the middle of it would misrepresent
    the flow rather than shorten it — a reader would see INGESTION feeding
    CONSUMER directly and believe no transform happened. So an unresolvable step
    keeps its place, loses its anchor and is marked `inferred`. That is the rule
    the project already states for prose: cut or downgrade, and say which on
    screen. The drop is still recorded in the ledger either way.
    """
    entities = []
    for ent in block.get("entities", []):
        steps = []
        for step in ent.get("steps", []):
            out = {k: v for k, v in step.items() if k != "cite"}
            cite = step.get("cite") or {}
            if not cite:
                # No quote offered. An anchor that arrived pre-resolved from
                # survey data is still re-read and re-hashed here — stage 4
                # checks everything it ships, not only what a model wrote — and
                # one that no longer holds is downgraded like any other.
                if out.get("status") == "inferred":
                    out.pop("anchor", None)
                elif out.get("anchor"):
                    fixed, why = _confirm_on_disk(dict(out["anchor"]), sources)
                    if fixed is None:
                        run.drop(_ledger_row(
                            {"id": step.get("id") or run.mint(),
                             "text": step.get("description") or step.get("label") or ""},
                            {"file": out["anchor"].get("file")}, why))
                        out.pop("anchor", None)
                        out["status"] = "inferred"
                        out["downgraded"] = why
                    else:
                        out["anchor"] = fixed
                steps.append(out)
                continue
            anchor, why = anchor_for(cite, snap)
            if anchor is not None:
                anchor, why = _confirm_on_disk(anchor, sources)
            if anchor is None:
                run.drop(_ledger_row(
                    {"id": step.get("id") or run.mint(),
                     "text": step.get("description") or step.get("label") or ""},
                    cite, why))
                out.pop("anchor", None)
                out["status"] = "inferred"
                out["downgraded"] = why
                steps.append(out)
                continue
            out["anchor"] = anchor
            if out.get("status") != "derived":
                out["status"] = "verified"
            run.kept_verified += 1
            steps.append(out)

        if not steps:
            continue

        merged = {k: v for k, v in ent.items() if k != "steps"}
        merged["steps"] = steps

        fail = ent.get("failure_mode")
        if fail and fail.get("cite"):
            fm = {k: v for k, v in fail.items() if k != "cite"}
            anchor, why = anchor_for(fail["cite"], snap)
            if anchor is not None:
                anchor, why = _confirm_on_disk(anchor, sources)
            if anchor is None:
                run.drop(_ledger_row({"id": run.mint(), "text": fail.get("text") or ""},
                                     fail["cite"], why))
                fm.pop("anchor", None)
                fm["status"] = "inferred"
            else:
                fm["anchor"] = anchor
                fm["status"] = "verified"
            merged["failure_mode"] = fm

        # A boundary is what could not be established from this repository.
        # Verified is not a state it can be in, whatever the input said.
        bound = ent.get("boundary")
        if bound and bound.get("status") == "verified":
            merged["boundary"] = {**bound, "status": "inferred"}

        entities.append(merged)

    if not entities:
        return None, "every entity in this lineage block failed verification"

    out = {k: v for k, v in block.items() if k != "entities"}
    out["entities"] = entities
    return out, None


def _verify_trace(block: Mapping, run: _Run, snap: Snapshot,
                  sources: Mapping[str, Source]) -> tuple[dict | None, str | None]:
    """Resolve every hop, then repair the prediction rules the gate enforces.

    Dropping a hop moves the last hop and can leave a `predict` keyed against a
    hop that is no longer there, or against the same file — `verify-contract.js`
    fails both. The repair is done after the drops for exactly that reason.
    """
    steps = []
    for step in block.get("steps", []):
        cite = step.get("cite") or {}
        anchor, why = anchor_for(cite, snap) if cite else (None, REASON_UNPARSEABLE)
        if anchor is not None:
            anchor, why = _confirm_on_disk(anchor, sources)
        if anchor is None:
            run.drop(_ledger_row({"id": step.get("id") or run.mint(),
                                  "text": step.get("claim") or ""}, cite, why))
            continue
        out = {k: v for k, v in step.items() if k != "cite"}
        out["anchor"] = anchor
        steps.append(out)
        run.kept_verified += 1

    if not steps:
        return None, "every hop in this trace failed verification"

    steps[-1]["next"] = None
    steps[-1].pop("predict", None)
    seen_files: set[str] = set()
    for i, step in enumerate(steps[:-1]):
        same = steps[i + 1]["anchor"]["file"] == step["anchor"]["file"]
        if same or step["anchor"]["file"] in seen_files:
            step.pop("predict", None)
        if "predict" in step:
            seen_files.add(step["anchor"]["file"])

    out = {k: v for k, v in block.items() if k != "steps"}
    out["steps"] = steps
    return out, None


def _confirm_on_disk(anchor: Anchor,
                     sources: Mapping[str, Source]) -> tuple[Anchor | None, str | None]:
    """Re-hash a resolved anchor against the file as it is on disk now."""
    path = anchor["file"]
    if path not in sources:
        return None, REASON_NO_FILE
    disk = sources[path].lines
    if anchor["end"] > len(disk):
        return None, reason_out_of_range(anchor["start"], anchor["end"], len(disk))
    digest = sha256_range(disk, anchor["start"], anchor["end"])
    if digest != anchor["sha256"]:
        return None, REASON_HASH
    anchor["sha256"] = digest
    return anchor, None


def bundle_files(payload: Mapping, sources: Mapping[str, Source]) -> dict:
    """The sparse `files` map, built from the FINAL anchor set.

    Keys are canonical decimal integers as strings — no zero-padding. Verified
    in Node: `Object.keys({'058':1,'58':1})` is `['58','058']`, out of numeric
    order, and the gate's `Math.min(...Object.keys(f).map(Number))` reads both.

    Contiguous within each range because the gate requires every line of
    `[start, end]` to be present; sparse across disjoint ranges because that is
    allowed and dropped claims should cost no bytes.
    """
    files: dict[str, dict[str, str]] = {}
    for anchor in iter_anchors(payload):
        path = anchor["file"]
        lines = sources[path].lines
        into = files.setdefault(path, {})
        into.update({str(n): lines[n - 1] for n in range(anchor["start"], anchor["end"] + 1)})
    return files


def _flag_low_confidence(payload: dict, rate: float) -> None:
    """Prepend §9 row 5's callout to `cover` and `audit`.

    The amber badge itself needs no new field — `shell()` derives it from
    `report.dropped / report.claims`. What it cannot do is say so in prose on
    the two stops a reader actually stops at.
    """
    pct = round(100 * rate)
    callout = {
        "type": "callout",
        "level": "broken",
        "title": f"Low confidence — {pct}% of claims dropped",
        "text": (f"{payload['report']['dropped']} of {payload['report']['claims']} "
                 "generated claims failed verification and were deleted. Every one "
                 "is listed in the audit ledger."),
    }
    stops = [s for t in payload["tracks"] for s in t["stops"]]
    if not stops:
        return
    wanted = [s for s in stops if s.get("id") in ("cover", "audit")]
    if not wanted:
        wanted = [stops[0]]
    for stop in wanted:
        stop["blocks"].insert(0, copy.deepcopy(callout))


# --- Self-police (§6.7) ----------------------------------------------------


def self_police(payload: Mapping, survey: Mapping | None = None) -> list[str]:
    """Everything neither Node gate checks. Returns violations, worst first.

    The gates read the artifact; neither executes the renderer. A payload
    missing `repo.generated_at` therefore passes both and throws inside
    `shell()` before the first stop draws — a blank page with a green light,
    which the plan calls the worst outcome in the document. Every rule below is
    one of those, or one the gate checks only on a subset of block types.

    `survey` is optional: acceptance test 6 (a checkpoint block deep-equals its
    survey answer key) can only run when the survey is to hand.
    """
    bad: list[str] = []
    tracks = payload.get("tracks") or []
    blocks = list(iter_blocks(tracks))
    stops = [s for t in tracks for s in t.get("stops", [])]

    for key in ("contract", "repo", "report", "map", "files", "tracks", "dropped"):
        if key not in payload:
            bad.append(f"top-level key missing: {key}")
    if bad:
        return bad

    repo, report = payload["repo"], payload["report"]
    for key in ("name", "commit", "generated_at"):
        if not str(repo.get(key) or "").strip():
            bad.append(f"repo.{key} is empty — shell() throws before a stop renders")
    if not str(report.get("tool_version") or "").strip():
        bad.append("report.tool_version is empty — shell() renders 'trailhead undefined'")
    if not isinstance(report.get("duration_s"), int) or report["duration_s"] < 0:
        bad.append("report.duration_s is not a non-negative integer")

    dropped_ids = {row.get("id") for row in payload["dropped"]}
    for row in payload["dropped"]:
        if not str(row.get("reason") or "").strip():
            bad.append(f"{row.get('id')}: dropped with no reason")
        elif not is_known_reason(row["reason"]):
            bad.append(f"{row.get('id')}: drop reason outside the vocabulary: "
                       f"{row['reason']!r}")
    if report.get("dropped") != len(payload["dropped"]):
        bad.append(f"report.dropped {report.get('dropped')} != ledger length "
                   f"{len(payload['dropped'])}")

    failing = sum(1 for b in blocks if b.get("type") == "command" and b.get("exit") != 0)
    if report.get("failed") != failing:
        bad.append(f"report.failed {report.get('failed')} != {failing} rendered "
                   "failing command blocks")

    if not any(b.get("type") == "ledger" for b in blocks):
        bad.append("no ledger block — the audit panel is on the never-cut list")

    seen_stops: set[str] = set()
    for stop in stops:
        sid = stop.get("id")
        if sid in seen_stops:
            bad.append(f"duplicate stop id: {sid}")
        seen_stops.add(sid)
        if not stop.get("blocks"):
            bad.append(f"stop {sid}: empty blocks array")
        has_cp = any(b.get("type") == "checkpoint" for b in stop.get("blocks", []))
        kind = stop.get("kind")
        if kind not in ("stop", "cp"):
            bad.append(f"stop {sid}: kind {kind!r} is not stop|cp")
        elif (kind == "cp") != has_cp:
            bad.append(f"stop {sid}: kind {kind!r} disagrees with its blocks")
        if stop.get("minutes") is None:
            bad.append(f"stop {sid}: no minutes — the rail shows 'undefinedm'")
        if kind == "stop" and not str(stop.get("lede") or "").strip():
            bad.append(f"stop {sid}: kind=stop with no lede")
        if kind == "cp" and stop.get("lede"):
            bad.append(f"stop {sid}: kind=cp carries a lede")
    for track in tracks:
        if track.get("minutes") is None:
            bad.append(f"track {track.get('title')!r}: no minutes")

    claim_ids: list[str] = []
    cp_ids: list[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "prose":
            for claim in block.get("claims", []):
                cid = claim.get("id")
                claim_ids.append(cid)
                if not _CLAIM_ID.match(str(cid)):
                    bad.append(f"claim id {cid!r} does not match ^c-\\d{{3,}}$")
                if claim.get("status") not in ("verified", "inferred"):
                    bad.append(f"{cid}: status {claim.get('status')!r} is not "
                               "verified|inferred")
                if claim.get("status") == "inferred" and "anchor" in claim:
                    bad.append(f"{cid}: inferred claim carries an anchor key")
        elif kind == "checkpoint":
            cid = str(block.get("id") or "")
            cp_ids.append(cid)
            if not cid or cid.isdigit():
                bad.append(f"checkpoint id {cid!r} is all digits — CHECK would "
                           "navigate to a stop instead of grading")
            if survey is not None:
                expect = (survey.get("checkpoints") or {}).get(cid)
                got = {k: v for k, v in block.items() if k not in ("type", "id")}
                if expect is None:
                    bad.append(f"checkpoint {cid}: no such key in survey.json")
                elif got != dict(expect):
                    bad.append(f"checkpoint {cid}: shipped key differs from "
                               "survey.checkpoints — acceptance test 6")
            for option in block.get("options", []):
                bad.extend(_unescaped(option, f"checkpoint {cid} option"))
        elif kind == "callout":
            if block.get("level") not in ("info", "inferred", "broken"):
                bad.append(f"callout level {block.get('level')!r} is not "
                           "info|inferred|broken")
            for field in ("title", "text"):
                if not str(block.get(field) or "").strip():
                    bad.append(f"callout has no {field} — the renderer emits "
                               "the literal word 'undefined'")
                else:
                    bad.extend(_unescaped(block[field], f"callout.{field}"))
            # `@2` links. The renderer whitelists the scheme at paint time and
            # draws a visible refusal chip for anything else, so a bad href here
            # is not a security hole — it is a red "unsafe href" chip on stage.
            for link in block.get("links") or []:
                if not str(link.get("label") or "").strip():
                    bad.append("callout link with no label")
                if not re.match(r"^https?://", str(link.get("href") or ""), re.I):
                    bad.append(f"callout link href {link.get('href')!r} is not "
                               "http(s) — the renderer would refuse it on screen")
            if block.get("linknote") is not None and not block.get("links"):
                bad.append("callout carries a linknote with no links")
        elif kind == "command":
            if isinstance(block.get("exit"), bool) or not isinstance(block.get("exit"), int):
                bad.append(f"{block.get('cmd')!r}: exit is not an int "
                           f"({block.get('exit')!r})")
            elif block["exit"] != 0 and not str(block.get("broken") or "").strip():
                bad.append(f"{block.get('cmd')!r}: failing command with no banner")
            if not str(block.get("env") or "").strip():
                bad.append(f"{block.get('cmd')!r}: no environment note")
            if not str(block.get("out") or "").strip():
                bad.append(f"{block.get('cmd')!r}: no captured output")
        elif kind == "table":
            columns = block.get("columns") or []
            for column in columns:
                bad.extend(_unescaped(column, "table column"))
            for row in block.get("rows") or []:
                if len(row) != len(columns):
                    bad.append("table row/column length mismatch")
                for cell_text in row:
                    bad.extend(_unescaped(cell_text, "table cell"))
        elif kind == "excerpt":
            bad.extend(_unescaped(block.get("caption") or "", "excerpt.caption"))
        elif kind == "lineage":
            # The downgrade path in `_verify_lineage` has exactly two ways to be
            # wrong, and both render a step as evidenced when it is not. The
            # gate checks the same two; catching them here means the error names
            # the entity rather than arriving as a Node exit code.
            for entity in block.get("entities", []) or []:
                who = f"lineage {entity.get('id')!r}"
                if not entity.get("steps"):
                    bad.append(f"{who}: entity has no steps")
                for step in entity.get("steps", []) or []:
                    where = f"{who}/{step.get('stage')}"
                    if step.get("status") not in ("verified", "derived", "inferred"):
                        bad.append(f"{where}: status {step.get('status')!r} is not "
                                   "verified|derived|inferred")
                    if step.get("status") == "inferred" and "anchor" in step:
                        bad.append(f"{where}: inferred step carries an anchor — "
                                   "it would render as evidenced")
                    if (step.get("status") == "verified"
                            and step.get("evidence_type") != "runtime"
                            and not step.get("anchor")):
                        bad.append(f"{where}: verified step carries no anchor")
                if (entity.get("boundary") or {}).get("status") == "verified":
                    bad.append(f"{who}: a repository boundary cannot be verified — "
                               "it is by definition what could not be established")

    if len(set(claim_ids)) != len(claim_ids):
        bad.append("duplicate claim ids in tracks")
    if len(set(cp_ids)) != len(cp_ids):
        bad.append("duplicate checkpoint block ids")
    overlap = dropped_ids & set(claim_ids)
    if overlap:
        bad.append(f"dropped ids also rendered: {sorted(overlap)}")

    for stray in _strings(tracks):
        if stray in dropped_ids:
            bad.append(f"dropped id {stray} appears inside tracks")

    files = payload["files"]
    for anchor in iter_anchors(payload):
        path = anchor.get("file", "")
        where = f"{path}:{anchor.get('start')}-{anchor.get('end')}"
        if "\\" in path:
            bad.append(f"{where}: backslash in anchor.file")
        if not str(anchor.get("sha256") or "").strip():
            bad.append(f"{where}: anchor carries no sha256")
        bundled = files.get(path)
        if bundled is None:
            bad.append(f"{where}: file not bundled")
            continue
        missing = [n for n in range(anchor["start"], anchor["end"] + 1)
                   if str(n) not in bundled]
        if missing:
            bad.append(f"{where}: lines {missing[:3]} missing from files")
        for line in anchor.get("focus", []):
            if not anchor["start"] <= line <= anchor["end"]:
                bad.append(f"{where}: focus line {line} outside the anchor")

    node_ids = set()
    for node in payload["map"].get("nodes", []):
        missing = {"id", "label", "loc", "files", "x", "y", "w", "why", "top"} - set(node)
        if missing:
            bad.append(f"map node {node.get('id')!r} missing {sorted(missing)}")
        if not node.get("top"):
            bad.append(f"map node {node.get('id')!r} has an empty top[]")
        bad.extend(_unescaped(str(node.get("label") or ""), "map node label"))
        node_ids.add(node.get("id"))
    for edge in payload["map"].get("edges", []):
        for end in ("a", "b"):
            if edge.get(end) not in node_ids:
                bad.append(f"map edge references unknown node {edge.get(end)!r}")

    return bad


def _unescaped(text, where: str) -> list[str]:
    """Flag markup that the renderer will either execute or print verbatim.

    `textio.cell` escapes the value and re-adds markup from a two-tag whitelist,
    so anything still containing `<` or `>` after the whitelist is stripped
    either skipped `cell()` or is carrying markup in the data. On a surface the
    renderer interpolates raw (table cells, checkpoint options) that is an
    injection point with no claim marker on it; on one it escapes (callout
    title and text) it is a tag printed at the reader. Both are defects, and
    the same check finds them.
    """
    if not isinstance(text, str):
        return []
    stripped = _WHITELIST_TAGS.sub("", text)
    if "<" in stripped or ">" in stripped:
        return [f"{where}: unescaped markup in {text[:60]!r}"]
    return []


def _strings(node) -> Iterator[str]:
    """Every string anywhere in a nested structure, for the dropped-id sweep.

    Exact equality, not substring: the gate builds its `rendered` set from prose
    claims only — its `rendered` set filters on `type === 'prose'` — so a
    dropped id surfacing inside
    a trace step, a table cell or a checkpoint option would pass it.
    """
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _strings(value)


# --- Convenience -----------------------------------------------------------


def write_json(path: Path, payload: Mapping) -> Path:
    """Atomic UTF-8 write with LF endings, so a half-written file never ships."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    tmp.replace(path)
    return path


def run_contract_gate(path: Path, tools: Path) -> subprocess.CompletedProcess:
    """`node tools/verify-contract.js <path>` — the Node half of the check.

    Kept here so stage 4 is gateable before any HTML exists; the gate already
    accepts a bare `verified.json`. Never used to *decide* anything at
    generation time — self-police is the decision — only to report.
    """
    return subprocess.run(
        ["node", str(Path(tools) / "verify-contract.js"), str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
