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

#: The template-parity contract. Emitted only when the payload actually carries
#: an @3 surface (glossary, enriched map, stats); a repo with no answers for the
#: new narration units keeps emitting byte-identical @2, which is what makes
#: the extension additive rather than a migration.
CONTRACT_V3 = "trailhead/verified@3"

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

#: The one reason the @3 tour surface can add: a guided-tour step naming a
#: module that is not a node on the board highlights nothing, so it is dropped
#: and counted like any other failed assertion (ledger id `t-<node id>`).
REASON_OFF_BOARD = "tour step names a module not on the board"

#: Composed rather than restated: `resolve.py` owns the eight it can emit, this
#: module owns the rest, which need the disk, the parser or the map. Restating
#: the eight here would be a second copy of a frozen vocabulary, free to drift.
DROP_REASONS = frozenset(resolve.REASONS) | {
    REASON_NO_FILE,
    REASON_HASH,
    REASON_UNPARSEABLE,
    REASON_OFF_BOARD,
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

# --- @3 sanitisation (template-parity spec 1.6) ----------------------------
# The dash policy: no em or en dash in any authored string of the payload.
# Bundled source lines in `files` and command captures are the machine's own
# bytes and are exempt; everything a model or a template sentence produced is
# transliterated here, at assembly time, so the gate's re-scan finds nothing.
# All three patterns use escapes because the house style bars the characters
# themselves from this package's source.

#: An em dash with its surrounding spaces, in authored prose. Replaced with a
#: comma-space, which is the reading the em dash almost always carries.
_EM_DASH = re.compile(r"[ \t]*\u2014[ \t]*")

#: An en dash anywhere in authored prose. Replaced with a plain hyphen, which
#: is what it means in the ranges ("3-5 lines") it actually appears in.
_EN_DASH = "\u2013"

#: Either dash inside a ledger REASON. Reasons keep their frozen wording but
#: the `code <dash> detail` join becomes `code: detail`, which is exactly the
#: legacy colon form `is_known_reason` has always accepted for hash mismatches.
_REASON_DASH = re.compile(r"[ \t]*[\u2014\u2013][ \t]*")

#: The ledger placeholder for "no file was cited". The em dash it replaces
#: would be the one authored dash left in a clean payload.
_NO_FILE = "(none)"

#: Glossary ids are slugs, unique, and the target of `[[id|label]]` markers.
_GLOSS_ID = re.compile(r"^[a-z0-9-]+$")
_SLUG_JUNK = re.compile(r"[^a-z0-9]+")

#: A trailing parenthetical on a glossary term: "realized variance (RV)".
#: Prose writes the bare words, so the id must slug from the bare words too —
#: an id of `realized-variance-rv` leaves every bare `[[realized variance]]`
#: marker dead on screen.
_TERM_PAREN = re.compile(r"\s*\([^()]*\)\s*$")

#: The explicit glossary marker form the renderer expands. A marker whose id
#: is not in the surviving glossary is rewritten to its bare label so the gate
#: never sees a dangling reference; the rewrite is counted in the audit, not
#: the ledger, because it is a formatting downgrade rather than a lie.
_GLOSS_MARKER = re.compile(r"\[\[([a-z0-9-]+)\|([^\]]+)\]\]")

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
    """True if `reason` is vocabulary, or vocabulary plus a detail tail.

    Two joins are accepted for the tail: the em dash the ledger historically
    used, and the `: ` the dash policy (spec 1.6) transliterates it to at
    assembly time. Old payloads keep passing; new ones ship dash-free.
    """
    if not isinstance(reason, str) or not reason.strip():
        return False
    if _OUT_OF_RANGE.match(reason) or reason in _LEGACY_REASONS:
        return True
    return any(reason == r or reason.startswith(r + " \u2014 ")
               or reason.startswith(r + ": ") for r in DROP_REASONS)


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

    # The @3 surfaces anchor evidence outside `tracks`: a glossary entry cites
    # where its term lives, a map node cites one excerpt for its drawer. Both
    # ship lines in `files` and both are re-hashed by the gate, so both belong
    # to this walk. Yielded after the tracks so an @2 payload's `files` map
    # keeps its exact key order.
    for entry in payload.get("glossary") or []:
        if entry.get("anchor"):
            yield entry["anchor"]
    for node in (payload.get("map") or {}).get("nodes") or []:
        if node.get("anchor"):
            yield node["anchor"]


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
        "file": (cite or {}).get("file") or _NO_FILE,
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

    # @3 surfaces cite files too, and forgetting them here is the documented
    # failure mode: the file never enters the snapshot and every glossary or
    # node cite drops as `file does not exist at this commit`.
    for entry in content.get("glossary") or []:
        if isinstance(entry, Mapping):
            take(entry)
    for answer in (content.get("map_answers") or {}).values():
        if isinstance(answer, Mapping):
            take(answer)
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
    """`dur` is a display string; the renderer prints it verbatim.

    The fallback is `n/a` rather than a dash glyph: `dur` reaches the payload
    and the dash policy (spec 1.6) keeps both dash characters out of it.
    """
    try:
        return f"{int(ms) / 1000:.1f} s"
    except (TypeError, ValueError):
        return "n/a"


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
             regen: str | None = None,
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

    `regen` is THIS run's regeneration command, built by the caller from its
    own arguments and emitted verbatim (dash-transliterated) as
    `report.regen`, the ledger footer's provenance line. Absent, the key
    stays off the report and the renderer falls back to a neutral sentence —
    never to a claim of hand-built pedigree.
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
        row.setdefault("file", _NO_FILE)
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

    # --- @3 surfaces: resolved with the same machinery as the claims --------
    # Each degrades to absence, so a content.json without the new keys leaves
    # this whole section a no-op and the payload exactly as @2 emitted it.
    notes: list[str] = []
    glossary = _resolve_glossary(content.get("glossary"), run, snapshot, sources)
    the_map = _map_block(map_json)
    _merge_node_answers(the_map, content.get("map_answers"), run, snapshot,
                        sources, tracks=tracks)
    _apply_tour(the_map, content.get("tour"), run, notes)
    _apply_columns(the_map, content.get("cols"), notes)

    payload = {
        "contract": CONTRACT,
        "repo": _repo_block(content, survey),
        "report": {},
        "map": the_map,
        "files": {},
        "tracks": tracks,
        "dropped": run.dropped,
    }
    if glossary:
        payload["glossary"] = glossary
    payload["files"] = bundle_files(payload, sources)

    # Spec 1.6: authored dashes out, dead glossary markers rewritten. After
    # every resolution (the ledger is complete), before the report is counted.
    marker_rewrites = _sanitise(payload)

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
    if regen and str(regen).strip():
        # The footer prints this as the run's own provenance. A command line
        # reads dashes as flags, so both banned dashes become plain hyphens
        # here rather than the comma join prose gets.
        report["regen"] = (str(regen).strip()
                           .replace("\u2014", "-").replace(_EN_DASH, "-"))
    payload["report"] = report

    # The contract names what the payload carries, decided on the OUTPUT: any
    # @3 surface bumps the version and adds `report.anchors` (glossary and
    # node cites are anchors, not claims, so the claim math above is exactly
    # @2's). A barren repo keeps @2, field for field.
    if _has_v3_surface(payload):
        payload["contract"] = CONTRACT_V3
        report["anchors"] = sum(1 for _ in iter_anchors(payload))

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
        # `[[id|label]]` markers rewritten to their bare label because the id
        # was not in the surviving glossary. A formatting downgrade, counted
        # here rather than in the ledger (spec section 5).
        "glossary_markers_rewritten": marker_rewrites,
        # §9's fired rows arrive from two earlier stages under their own key;
        # the audit log is where all three meet, so the count in the ledger
        # callout can be taken from one place. `notes` carries the @3 surface
        # degradations decided in this stage (tour dropped, labels mismatched).
        "degradations": (list(survey.get("degradations") or [])
                         + list(content.get("degradations") or [])
                         + list(degradations)
                         + notes),
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
    """`map.json`, copied through with the contract tag and diagnostics off.

    Nodes and edges are the `@2` shape and always ship. The `@3` board surfaces
    (`w`/`h` viewBox, `columns`, `note`, `tour`) pass through only when the
    mapper emitted them, so an `@2` map stays byte-identical. Per-node fields
    (`path`, `h`, and later the narrated `role`/`reads`/`feeds`/`key_files`/
    `concepts`/`anchor`) ride inside the node dicts and were never stripped.
    """
    source = map_json or {}
    out = {
        "nodes": copy.deepcopy(list(source.get("nodes", []) or [])),
        "edges": copy.deepcopy(list(source.get("edges", []) or [])),
    }
    for key in ("w", "h", "columns", "note", "tour"):
        if key in source:
            out[key] = copy.deepcopy(source[key])
    return out


# --- @3 surfaces (template-parity spec 1.1, 1.3, section 5) ----------------
# Everything below degrades to absence: a content.json with none of these keys
# produces exactly the @2 payload it always did. The answers arrive from the
# new narration units via the cli driver (`gloss` -> content.glossary,
# `node:<gid>` -> content.map_answers, `tour` -> content.tour, `cols` ->
# content.cols), and every cite in them is resolved and hashed by the same
# `anchor_for` + `_confirm_on_disk` pair a prose claim goes through.


def _slugify(term) -> str:
    """A glossary id: lowercase, `[a-z0-9-]+`, matching the renderer's own
    slug rule for bare `[[Label]]` markers so slug-matching works both ways.

    A trailing parenthetical is stripped before slugging: the model defines
    "realized variance (RV)" but the prose that cites it writes the bare
    `[[realized variance]]`, so the id must be `realized-variance` or the
    marker resolves to nothing and renders as plain text. A term that is ALL
    parenthetical keeps its full slug rather than vanishing. Collisions after
    stripping fall to the caller's dedupe: first spelling wins, ledger
    untouched, exactly as two spellings of one term always have.
    """
    text = str(term or "")
    slug = _SLUG_JUNK.sub("-", _TERM_PAREN.sub("", text).lower()).strip("-")
    if not slug:
        slug = _SLUG_JUNK.sub("-", text.lower()).strip("-")
    return slug


def _resolve_glossary(entries, run: _Run, snap: Snapshot,
                      sources: Mapping[str, Source]) -> list[dict]:
    """Glossary answers -> the payload's top-level `glossary` list.

    A failed cite keeps the DEFINITION and loses only the anchor: a glossary
    popover without evidence is honest (the renderer shows the definition and
    no jump-to-evidence button), so the entry survives while the failure is
    ledgered under `g-<slug>`. Contrast the node answers below, where a failed
    cite discards the narration entirely.
    """
    out: list[dict] = []
    seen: set[str] = set()
    for raw in entries or []:
        if not isinstance(raw, Mapping):
            continue
        term = str(raw.get("term") or "").strip()
        definition = str(raw.get("def") or raw.get("definition") or "").strip()
        if not term or not definition:
            continue
        gid = _slugify(raw.get("id") or term)
        if not gid or gid in seen:
            continue                      # dedupe: first spelling of a term wins
        seen.add(gid)
        entry = {"id": gid, "term": term, "def": definition}

        cite = raw.get("cite")
        pre = raw.get("anchor")
        resolved = why = None
        if cite:
            resolved, why = anchor_for(cite, snap)
            if resolved is not None:
                resolved, why = _confirm_on_disk(resolved, sources)
        elif pre:
            resolved, why = _confirm_on_disk(copy.deepcopy(dict(pre)), sources)
        if resolved is not None:
            entry["anchor"] = resolved
        elif why is not None:
            run.drop({"id": f"g-{gid}", "text": term,
                      "file": ((cite or pre or {}).get("file")) or _NO_FILE,
                      "reason": why})
        out.append(entry)
    return out


def _merge_node_answers(the_map: dict, answers, run: _Run, snap: Snapshot,
                        sources: Mapping[str, Source], *,
                        tracks: Sequence[dict] | None = None) -> None:
    """`node:<gid>` answers -> role/reads/feeds/key_files/concepts on the node.

    The asymmetry with the glossary is deliberate: a node answer is narrated
    prose ABOUT the module, and its cite is the evidence the drawer opens on.
    When that cite fails, shipping the prose anyway would put unanchored
    narration behind a board that looks verified, so the node keeps its
    deterministic `why`/`top` fallback instead and the failure is ledgered
    under the node's own id (`n-<gid>`).

    `tracks` is the verified course: when the anchor resolves, the matching
    dive stop (`dive-<slug(gid)>`) gains the same evidence as an excerpt
    block, because compose could not emit one — at compose time the node had
    no anchor yet. See `_inject_dive_excerpt`.
    """
    if not answers:
        return
    by_id = {n.get("id"): n for n in the_map.get("nodes", []) or []}
    for gid in sorted(answers, key=str):
        answer = answers[gid]
        if not isinstance(answer, Mapping):
            continue
        node = by_id.get(gid) or by_id.get(f"n-{gid}")
        if node is None:
            continue                      # narrated a group that fell off the board

        nid = str(node.get("id") or "")
        ledger_id = nid if nid.startswith("n-") else f"n-{gid}"
        cite = answer.get("cite")
        anchor = None
        if cite:
            anchor, why = anchor_for(cite, snap)
            if anchor is not None:
                anchor, why = _confirm_on_disk(anchor, sources)
            if anchor is None:
                run.drop({"id": ledger_id,
                          "text": str(answer.get("caption")
                                      or node.get("label") or ""),
                          "file": (cite or {}).get("file") or _NO_FILE,
                          "reason": why})
                continue                  # why/top fallback, nothing merged

        role = [str(p).strip() for p in (answer.get("role") or [])
                if isinstance(p, str) and p.strip()]
        if role:
            node["role"] = role
        for key in ("reads", "feeds"):
            value = str(answer.get(key) or "").strip()
            if value:
                node[key] = value
        key_files = [{"file": str(k.get("file")).strip(),
                      "purpose": str(k.get("purpose")).strip()}
                     for k in (answer.get("key_files") or [])
                     if isinstance(k, Mapping)
                     and str(k.get("file") or "").strip()
                     and str(k.get("purpose") or "").strip()]
        if key_files:
            node["key_files"] = key_files
        concepts = [str(c).strip() for c in (answer.get("concepts") or [])
                    if isinstance(c, str) and c.strip()]
        if concepts:
            node["concepts"] = concepts
        if anchor is not None:
            node["anchor"] = anchor
            caption = str(answer.get("caption") or "").strip()
            if caption:
                node["anchor_caption"] = caption
            _inject_dive_excerpt(tracks, gid, anchor, caption)


def _inject_dive_excerpt(tracks: Sequence[dict] | None, gid: str,
                         anchor: Anchor, caption: str) -> None:
    """Put a node's resolved evidence on its own dive stop as an excerpt.

    Compose emits a dive stop's excerpt only when the map node already
    carries an anchor, and at compose time it never does: the anchor is the
    `node:<gid>` answer's cite, resolved here, one stage later. Without this
    the one stop titled "Inside <module>" ships prose about the module and no
    line of it — the evidence exists, hashed and bundled, and only the board
    drawer can open it.

    The anchor handed in is already resolved and disk-confirmed, and
    `iter_anchors` walks excerpt blocks the same as node anchors, so the
    lines are bundled and re-hashed by the gate with no new resolution and no
    new ledger path. The block goes directly after the stop's prose block,
    where compose would have put it, and only when the stop exists and does
    not already carry an excerpt of its own.
    """
    want = f"dive-{_SLUG_JUNK.sub('-', str(gid).lower()).strip('-') or 'group'}"
    for track in tracks or []:
        for stop in track.get("stops") or []:
            if stop.get("id") != want:
                continue
            blocks = stop.get("blocks") or []
            if any(b.get("type") == "excerpt" for b in blocks):
                return
            at = next((i + 1 for i, b in enumerate(blocks)
                       if b.get("type") == "prose"), len(blocks))
            blocks.insert(at, {"type": "excerpt",
                               "anchor": copy.deepcopy(anchor),
                               "caption": caption or ""})
            return


def _apply_tour(the_map: dict, steps, run: _Run, notes: list) -> None:
    """The guided tour, kept only where it can actually guide.

    A step whose id is not a node on the board is dropped and ledgered
    (`t-<id>`); if fewer than three steps survive, the whole tour goes, noted
    in the verification report rather than the ledger because the surviving
    steps asserted nothing false. The answer from the `tour` unit wins over a
    tour the mapper may have carried; both are validated the same way.
    """
    if steps is None:
        steps = the_map.get("tour")
    the_map.pop("tour", None)
    if not steps:
        return
    node_ids = {n.get("id") for n in the_map.get("nodes", []) or []}
    kept: list[dict] = []
    seen: set[str] = set()
    offered = 0
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        sid = str(step.get("id") or "").strip()
        text = str(step.get("text") or "").strip()
        if not sid or not text or sid in seen:
            continue
        seen.add(sid)
        offered += 1
        if sid not in node_ids:
            run.drop({"id": f"t-{sid}", "text": text, "file": _NO_FILE,
                      "reason": REASON_OFF_BOARD})
            continue
        kept.append({"id": sid, "text": text})
    if len(kept) >= 3:
        the_map["tour"] = kept
    elif offered:
        notes.append(f"map tour dropped: only {len(kept)} of {offered} "
                     "steps survived validation (minimum 3)")


def _apply_columns(the_map: dict, labels, notes: list) -> None:
    """`cols` answer -> labels on the mapper's LAYER placeholders, in order.

    Column GEOMETRY is the mapper's and never the model's; the answer renames
    the columns and does nothing else. A count mismatch keeps the placeholders
    and is noted in the verification report: wrong labels on the right columns
    would be a lie about the architecture, placeholders are merely mute.
    """
    columns = the_map.get("columns")
    if labels is None or not isinstance(columns, list) or not columns:
        return
    given = [str(label).strip() for label in (labels or [])
             if isinstance(label, str) and str(label).strip()]
    if len(given) != len(columns):
        notes.append(f"column labels answer had {len(given)} labels for "
                     f"{len(columns)} columns; LAYER placeholders kept")
        return
    for column, label in zip(columns, given):
        if isinstance(column, dict):
            column["label"] = label


def _has_v3_surface(payload: Mapping) -> bool:
    """Does anything in this payload need the @3 contract to describe it?

    Checked on the assembled payload, not the inputs, so an answer that failed
    verification and left no trace does not bump the version. A False here is
    the bit-stability promise: the payload is field-for-field what @2 emitted.
    """
    if payload.get("glossary"):
        return True
    the_map = payload.get("map") or {}
    if any(key in the_map for key in ("w", "h", "columns", "note", "tour")):
        return True
    for node in the_map.get("nodes") or []:
        if any(key in node for key in ("role", "reads", "feeds", "key_files",
                                       "concepts", "anchor", "anchor_caption",
                                       "path", "h")):
            return True
    return any(block.get("type") == "stats"
               for block in iter_blocks(payload.get("tracks") or []))


def _sanitise(payload: dict) -> list[str]:
    """The spec 1.6 pass: dashes out of authored text, dead markers rewritten.

    Runs once, on the assembled payload, after every resolution and before the
    report is computed. Three distinct rules:

      * authored prose (claim text, ledes, callouts, tour text, node role and
        friends, glossary defs, captions): em dash becomes a comma join, en
        dash becomes a hyphen;
      * ledger reasons keep their frozen wording with the dash join replaced
        by a colon, which `is_known_reason` accepts alongside the dash form;
      * explicit `[[id|label]]` markers whose id is not in the surviving
        glossary are rewritten to the bare label, and the rewrite is reported
        in the audit rather than the ledger (a formatting downgrade, not a
        lie).

    Deliberately untouched: `files` (the repo's own bytes; hash integrity
    wins), command captures and banners (real output, non-negotiable #4), and
    checkpoint fields (the shipped key must deep-equal `survey.checkpoints`,
    non-negotiable #6, so cleanliness is the checkpoint builder's job).
    """
    known = {entry.get("id") for entry in payload.get("glossary") or []}
    rewrites: list[str] = []

    def clean(value, markers: bool = False):
        if not isinstance(value, str):
            return value
        value = _EM_DASH.sub(", ", value).replace(_EN_DASH, "-")
        if markers:
            def swap(match):
                if match.group(1) in known:
                    return match.group(0)
                rewrites.append(match.group(1))
                return match.group(2)
            value = _GLOSS_MARKER.sub(swap, value)
        return value

    for track in payload.get("tracks") or []:
        for stop in track.get("stops") or []:
            if isinstance(stop.get("lede"), str):
                stop["lede"] = clean(stop["lede"], markers=True)
            for block in stop.get("blocks") or []:
                kind = block.get("type")
                if kind == "prose":
                    for claim in block.get("claims") or []:
                        claim["text"] = clean(claim.get("text"), markers=True)
                elif kind == "callout":
                    block["title"] = clean(block.get("title"), markers=True)
                    block["text"] = clean(block.get("text"), markers=True)
                elif kind in ("excerpt", "table"):
                    if isinstance(block.get("caption"), str):
                        block["caption"] = clean(block["caption"], markers=True)
                elif kind == "trace":
                    for step in block.get("steps") or []:
                        if isinstance(step.get("claim"), str):
                            step["claim"] = clean(step["claim"], markers=True)
                elif kind == "lineage":
                    # Only the tool-written `downgraded` reason is touched
                    # (colon rule, like the ledger); the narrated fields are
                    # compose's to keep clean at the source.
                    for entity in block.get("entities") or []:
                        for step in entity.get("steps") or []:
                            if isinstance(step.get("downgraded"), str):
                                step["downgraded"] = _REASON_DASH.sub(
                                    ": ", step["downgraded"])

    the_map = payload.get("map") or {}
    note = the_map.get("note")
    if isinstance(note, dict):
        note["title"] = clean(note.get("title"))
        note["text"] = clean(note.get("text"), markers=True)
    for step in the_map.get("tour") or []:
        if isinstance(step, dict):
            step["text"] = clean(step.get("text"), markers=True)
    for column in the_map.get("columns") or []:
        if isinstance(column, dict) and isinstance(column.get("label"), str):
            column["label"] = clean(column["label"])
    for node in the_map.get("nodes") or []:
        if isinstance(node.get("role"), list):
            node["role"] = [clean(p, markers=True) for p in node["role"]]
        for key in ("reads", "feeds"):
            if isinstance(node.get(key), str):
                node[key] = clean(node[key], markers=True)
        for key in ("why", "anchor_caption"):
            if isinstance(node.get(key), str):
                node[key] = clean(node[key])
        for entry in node.get("key_files") or []:
            if isinstance(entry, dict) and isinstance(entry.get("purpose"), str):
                entry["purpose"] = clean(entry["purpose"], markers=True)
        if isinstance(node.get("concepts"), list):
            node["concepts"] = [clean(c) for c in node["concepts"]]
        if isinstance(node.get("top"), list):
            node["top"] = [clean(t) for t in node["top"]]

    for entry in payload.get("glossary") or []:
        entry["term"] = clean(entry.get("term"))
        entry["def"] = clean(entry.get("def"))

    # Ledger rows are mutated in place: the audit dict aliases this exact
    # list, so the verification report comes out as clean as the payload.
    for row in payload.get("dropped") or []:
        if isinstance(row.get("text"), str):
            row["text"] = clean(row["text"])
        if isinstance(row.get("reason"), str):
            row["reason"] = _REASON_DASH.sub(": ", row["reason"])
        path = row.get("file")
        if not isinstance(path, str) or not path.strip() \
                or path.strip() in ("\u2014", "\u2013"):
            row["file"] = _NO_FILE

    return rewrites


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

    # `stats` (@3) passes through like the other deterministic blocks: every
    # number in its tiles is computed by compose from survey.json, never by a
    # model, so there is nothing to resolve; self_police still checks its
    # shape so a malformed tile cannot reach the renderer unchecked.
    if kind in ("graph", "ledger", "callout", "table", "stats"):
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
        # Colon, not a dash: this title is authored text in the payload and
        # the dash policy (spec 1.6) applies to it like any other callout.
        "title": f"Low confidence: {pct}% of claims dropped",
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
        elif kind == "stats":
            # @3. `v` and `of` are interpolated RAW by the renderer (they may
            # carry a `<span>` from nowhere but here), `l`/`s` are escaped;
            # a missing `v` or `l` prints the literal word `undefined`.
            items = block.get("items") or []
            if not items:
                bad.append("stats block with no items")
            for item in items:
                item = item if isinstance(item, Mapping) else {}
                for field in ("v", "l"):
                    if not str(item.get(field) or "").strip():
                        bad.append(f"stats tile has no {field}")
                color = item.get("color")
                if color is not None and color not in ("ok", "inf", "bad"):
                    bad.append(f"stats color {color!r} is not ok|inf|bad")
                for field in ("v", "of"):
                    if isinstance(item.get(field), str):
                        bad.extend(_unescaped(item[field], f"stats.{field}"))
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
        # The required set is @2's, unchanged: every @3 field below is checked
        # only when present, so existing payloads pass exactly as before.
        missing = {"id", "label", "loc", "files", "x", "y", "w", "why", "top"} - set(node)
        if missing:
            bad.append(f"map node {node.get('id')!r} missing {sorted(missing)}")
        if not node.get("top"):
            bad.append(f"map node {node.get('id')!r} has an empty top[]")
        bad.extend(_unescaped(str(node.get("label") or ""), "map node label"))
        node_ids.add(node.get("id"))
        nid = node.get("id")
        if "h" in node and (isinstance(node.get("h"), bool)
                            or not isinstance(node.get("h"), (int, float))):
            bad.append(f"map node {nid!r}: h is not numeric")
        if "role" in node and (
                not isinstance(node.get("role"), list)
                or not node["role"]
                or not all(isinstance(p, str) and p.strip() for p in node["role"])):
            bad.append(f"map node {nid!r}: role is not a non-empty list of "
                       "paragraphs")
        for entry in node.get("key_files") or []:
            entry = entry if isinstance(entry, Mapping) else {}
            if not str(entry.get("file") or "").strip() \
                    or not str(entry.get("purpose") or "").strip():
                bad.append(f"map node {nid!r}: key_files entry missing file "
                           "or purpose")
        # The drawer interpolates the caption into a raw figcaption, exactly
        # like an excerpt block's.
        bad.extend(_unescaped(str(node.get("anchor_caption") or ""),
                              f"map node {nid!r} anchor_caption"))
    for edge in payload["map"].get("edges", []):
        for end in ("a", "b"):
            if edge.get(end) not in node_ids:
                bad.append(f"map edge references unknown node {edge.get(end)!r}")

    # --- @3 board surfaces, all conditional on presence ---------------------
    the_map = payload["map"]
    for column in the_map.get("columns") or []:
        column = column if isinstance(column, Mapping) else {}
        if not str(column.get("label") or "").strip():
            bad.append("map column with no label")
        if isinstance(column.get("x"), bool) \
                or not isinstance(column.get("x"), (int, float)):
            bad.append(f"map column {column.get('label')!r}: x is not numeric")
    note = the_map.get("note")
    if note is not None:
        for field in ("title", "text"):
            if not str((note if isinstance(note, Mapping) else {}).get(field)
                       or "").strip():
                bad.append(f"map.note has no {field}")
    seen_tour: set = set()
    for step in the_map.get("tour") or []:
        step = step if isinstance(step, Mapping) else {}
        sid = step.get("id")
        if sid not in node_ids:
            bad.append(f"map tour step references unknown node {sid!r}")
        if sid in seen_tour:
            bad.append(f"duplicate map tour step id {sid!r}")
        seen_tour.add(sid)
        if not str(step.get("text") or "").strip():
            bad.append(f"map tour step {sid!r} has no text")

    # --- @3 glossary (top level, optional) ----------------------------------
    seen_gloss: set = set()
    for entry in payload.get("glossary") or []:
        entry = entry if isinstance(entry, Mapping) else {}
        gid = entry.get("id")
        if not isinstance(gid, str) or not _GLOSS_ID.match(gid or ""):
            bad.append(f"glossary id {gid!r} is not a lowercase slug")
        if gid in seen_gloss:
            bad.append(f"duplicate glossary id {gid!r}")
        seen_gloss.add(gid)
        for field in ("term", "def"):
            if not str(entry.get(field) or "").strip():
                bad.append(f"glossary {gid!r} has no {field}")

    # `report.anchors` (@3) counts what actually shipped; the anchor walk is
    # the same one `files` was bundled from, so disagreement means the report
    # was computed before the payload stopped changing.
    if "anchors" in report:
        shipped = sum(1 for _ in iter_anchors(payload))
        if report["anchors"] != shipped:
            bad.append(f"report.anchors {report['anchors']!r} != {shipped} "
                       "anchors shipped")

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
