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
__all__ = ["Unit", "Window", "Rejected", "build_units", "parse", "run",
           "emit_prompts", "main", "CACHE_DIRNAME", "PROMPTS_DIRNAME",
           "CODE_UNNARRATED"]

#: `.trailhead/narration/<key>.json` — record and replay share one directory.
CACHE_DIRNAME = "narration"

#: `.trailhead/prompts/<key>.json` — the agent route's inbox.
PROMPTS_DIRNAME = "prompts"

MAX_UNITS_DEFAULT = 12

#: Reverse priority. Overflow drops from the left, matching §14's stop-cut
#: order. `trace` is last because it carries beat 4 of the pitch.
DROP_ORDER = ("conv", "green", "five", "trace")

#: Claim text rules from §5.5. Backticks and `<` reach a raw-interpolation
#: surface; a newline breaks the one-sentence-per-claim contract the renderer
#: lays out against; `](` is a markdown link the page will never render.
TEXT_MAX_CHARS = 280
TEXT_BANNED = ("`", "\n", "<", "](")

#: A quote longer than this cannot become an anchor — `expand_anchor`'s cap is
#: 24 lines and a focus line outside the anchor fails `verify-contract.js:69`.
QUOTE_MAX_LINES = 24

#: One claim per trace hop, and the two counts must be equal or a hop renders
#: `esc(undefined)` inside a `.claim` span. The cap is on the hop list, not the
#: claims: a 40-hop trace is a chain nobody reads and a prompt nobody answers
#: well, so it is truncated before it is asked for.
TRACE_CLAIM_CAP = 12

#: Two of the twelve frozen drop reasons (§6.6) belong to this stage. Detail is
#: appended at the ledger boundary as `f"{code} — {detail}"`, so the vocabulary
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
                hops: list | None = None, *,
                max_units: int = MAX_UNITS_DEFAULT) -> tuple[list[Unit], list[dict]]:
    """-> (units, degradations). Four units at most; fewer on a thinner repo.

    One call per stop-unit, never per module and never per claim: decisions #19
    and #26 deleted the ten `map:<node>` units and the three `hyp:` units, which
    were 13 of 17 calls and routed unanchored prose onto surfaces with no claim
    marker on them.

    A unit is built only when the repo can support it — `trace` needs a hop
    list, `green` needs a command that actually passed. Building a unit whose
    stop will render from a template anyway spends a call to produce claims
    nobody will see.
    """
    hops = list(hops or [])
    degradations = []
    units = []

    five_files = _dedupe(_entry_files(survey) + _top_files(survey, 4))[:4]
    units.append(Unit(
        id="five", kind="five", title="Five sentences", max_claims=5,
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

    total = len(units)
    if total > max_units:
        # §9 row 7. Drop from the left of DROP_ORDER until the budget holds;
        # the affected stops fall back to their template blocks and carry no
        # claims, which the audit callout says out loud.
        for victim in DROP_ORDER:
            if len(units) <= max_units:
                break
            units = [u for u in units if u.id != victim]
        degradations.append({
            "code": "narrate_budget",
            "reason": (f"{len(units)} of {total} units narrated. The rest render "
                       f"from templates and carry no claims."),
            "narrated": len(units),
            "units": total,
        })

    return units, degradations


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
    out = ["COMMAND THAT PASSED (real capture — exit code and output are not simulated)",
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
        out.append(f"  {i}. {where}{(' — ' + what) if what else ''}")
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
        bad_text = _text_problem(text)
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


def _text_problem(text) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "claim text is empty"
    if len(text) > TEXT_MAX_CHARS:
        return f"claim text is {len(text)} chars, cap is {TEXT_MAX_CHARS}"
    for banned in TEXT_BANNED:
        if banned in text:
            return f"claim text contains {banned!r}"
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
    """`f"{code} — {detail}"`, so the frozen vocabulary stays a set of literals."""
    return f"{code} — {detail}"


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
# the unit loop
# ---------------------------------------------------------------------------

def run(survey: dict, root, prov, *, work=None, commands: dict | None = None,
        hops: list | None = None, max_units: int = MAX_UNITS_DEFAULT,
        offline: bool = False, verbose: bool = False) -> dict:
    """Narrate one repo. Serial, cached, and the only place `prov` is touched.

    Serial on purpose: a thread pool buys ~90 seconds once, on a run the disk
    cache makes free for every rehearsal afterwards, in exchange for
    partial-failure handling, result ordering and Ctrl-C behaviour.

    Returns, all keyed by unit id where it matters:

        narration      unit id -> claims, in `content@1` shape, ids stamped
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
    units, degradations = build_units(survey, commands, hops, max_units=max_units)
    store = _store(work)

    counter = _Counter()
    narration, windows, ledger, records = {}, {}, [], []
    empty = []
    calls = hits = 0

    for unit in units:
        system, user, unit_windows = prompts.pack(unit, survey, root)
        key = cache_key(system, user)
        windows[unit.id] = [{"file": w.file, "start": w.start, "end": w.end}
                            for w in unit_windows]

        raw = _read_store(store, key)
        source = "cache"
        if raw is None:
            if offline:
                raise MissingNarration(
                    f"no narration for unit {unit.id} (key {key}) and --offline is set"
                )
            raw = prov.complete(system, user, SCHEMA)
            calls += 1
            source = "provider"
            _write_store(store, key, raw)
        else:
            hits += 1

        try:
            claims, rows = parse(raw, unit)
        except Rejected as first:
            # One retry, and only when the answer came from a provider — a
            # second read of the same cache entry returns the same bytes and
            # fails the same way, so retrying it is a slower way to lose.
            claims, rows, detail = [], [], str(first)
            if source == "provider":
                retry = prov.complete(system, user, SCHEMA)
                calls += 1
                try:
                    claims, rows = parse(retry, unit)
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

        narration[unit.id] = claims
        ledger += rows
        records.append({
            "id": unit.id, "kind": unit.kind, "title": unit.title,
            "max_claims": unit.max_claims, "files": list(unit.files),
            "key": key, "source": source,
            "claims": len(claims), "dropped": len(rows),
        })
        if not claims and not rows:
            empty.append((unit, key, source))
        if verbose:
            sys.stderr.write(
                f"narrate {unit.id}: {len(claims)} claims, {len(rows)} dropped "
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
                 hops: list | None = None,
                 max_units: int = MAX_UNITS_DEFAULT) -> list[dict]:
    """Write one prompt pack per unit and return the packs as written.

    Each pack carries its OWN absolute `out` path, computed here from the same
    `cache_key` the replay will use. That is the point of the design: the agent
    answering a pack never computes a sha256 by hand, never gets it wrong, and
    never produces a store the stub cannot find.

    The pack is self-describing — schema included — so answering one needs
    nothing but the file.
    """
    root = Path(root)
    store = _store(work)
    inbox = Path(work) / PROMPTS_DIRNAME
    inbox.mkdir(parents=True, exist_ok=True)
    store.mkdir(parents=True, exist_ok=True)

    units, _ = build_units(survey, commands, hops, max_units=max_units)
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
            "schema": SCHEMA,
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


def _write_store(store: Path, key: str, raw) -> None:
    """Record a real answer. A stub miss is never written.

    Writing `{"claims": []}` would poison the store: the next run would replay
    the empty answer as a hit and the unit could never recover, which is the
    opposite of what a cache is for.
    """
    if not isinstance(raw, dict) or not raw.get("claims"):
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

    if args.emit_prompts:
        packs = emit_prompts(survey, root, args.work, commands=commands, hops=hops,
                             max_units=args.max_units)
        for pack in packs:
            sys.stderr.write(f"{pack['unit']:6s} -> {pack['pack']}\n")
        sys.stderr.write(f"{len(packs)} pack(s) written. Answer each into its own 'out' path.\n")
        return 0

    prov = provider_mod.build(args.provider, _store(args.work), offline=args.offline)
    result = run(survey, root, prov, work=args.work, commands=commands, hops=hops,
                 max_units=args.max_units, offline=args.offline, verbose=args.verbose)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
