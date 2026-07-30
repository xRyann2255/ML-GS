"""Stage 5 RENDER — `verified.json` into one self-contained HTML file.

Template-splice, not emit-HTML-from-Python (decision #7). `template.html` is a
de-fixtured copy of the browser-tested demo: it earns all 21 of
`tools/check-bundle.js`'s passes — doctype, `lang`, viewport, non-empty title,
`prefers-color-scheme`, `data-theme`, `prefers-reduced-motion`, print styles,
contained scroll, focus-visible, projector mode, localStorage, balanced CSS —
for free, and it already renders all nine block types. Emitting the same HTML
from Python means re-earning every one of those by hand for zero pitch value.

So this module does three things and nothing else:

    check_payload   refuse what would render as a lie or as a blank page
    splice          armour the JSON and drop it between two literal markers
    render          write the result atomically, UTF-8, LF

**No model is reachable from here.** Render is one of the four deterministic
stages; a renderer that asked a model anything would defeat the whole pitch.

The template is found as `Path(__file__).with_name("template.html")` — no
`importlib.resources`, no package-data configuration to get wrong at hour 9.
"""
import json
import os
import re
from pathlib import Path

from trailhead.textio import armour_json

#: The literal strings `tools/verify-contract.js` scrapes the bundle with. It
#: slices between the two DATA markers, finds `const BUNDLES =` inside that
#: slice, brace-matches it and `eval`s the result. All three must survive
#: verbatim and in this order or the gate exits **2** — which reads as "gate
#: crashed", not "generator broken", and costs ten minutes to diagnose.
#:
#: Note for anyone reading plan §7.2: it names `const D = {` and pins the second
#: marker to `RENDER — knows only`. The tool on disk moved to explicit DATA
#: markers precisely so the gate stopped being hostage to the wording of a prose
#: comment. `SCRAPE_MARKER` is still asserted here, because the comment it lives
#: in is what separates data from renderer for a human reading the bundle, and
#: because an em dash landing in the payload is exactly the accident the armour
#: exists to stop.
DATA_START = "/* ==== TRAILHEAD-DATA-START ==== */"
DATA_END = "/* ==== TRAILHEAD-DATA-END ==== */"
BUNDLE_MARKER = "const BUNDLES = {"
SCRAPE_MARKER = "RENDER — knows only"

#: The complete set. The page's dispatch table is `B[block.type]`, so an unknown
#: type is not a missing section — it is `undefined is not a function`, which
#: takes down the whole stop and every stop after it.
BLOCK_TYPES = frozenset({
    "prose", "excerpt", "command", "graph", "table",
    "trace", "checkpoint", "callout", "ledger",
})

CALLOUT_LEVELS = frozenset({"info", "inferred", "broken"})
CLAIM_STATUSES = frozenset({"verified", "inferred"})

#: Seven top-level keys, all required even when empty. The page does
#: `D.tracks.flatMap(...)` and `Object.keys(D.files)` before it draws anything.
TOP_LEVEL = ("contract", "repo", "report", "map", "files", "tracks", "dropped")

_CLAIM_ID = re.compile(r"^c-\d{3,}$")


class RenderError(Exception):
    """A payload or template that must not become an artifact.

    Raised instead of writing, because the two failure modes below are both
    worse than no file at all:

    * a **lie** — a dropped claim on screen, a synthesised exit code, an
      inferred sentence wearing a verified anchor. One of those on a projector
      ends the pitch, and neither gate catches all of them.
    * a **blank page** — a payload missing `repo.generated_at` throws inside
      `shell()` before the first stop is drawn, and **both gates still pass**,
      because neither one executes the page's JavaScript. That is the single
      failure mode nothing else in this project catches.
    """


def template_path() -> Path:
    """Where the shell lives. Beside this module, always."""
    return Path(__file__).with_name("template.html")


def load_template(path: Path | None = None) -> str:
    """Read the shell and prove it is still spliceable before we need it.

    Checking the markers here rather than mid-splice means a template someone
    hand-edited fails with a sentence naming the missing marker, instead of a
    `ValueError: substring not found` from `str.index` forty lines away.
    """
    p = template_path() if path is None else Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise RenderError(f"cannot read the template at {p}: {exc}") from exc
    check_template(text)
    return text


def check_template(template: str) -> None:
    """Assert the three scrape markers survive, verbatim and in order."""
    for marker in (DATA_START, DATA_END, BUNDLE_MARKER):
        n = template.count(marker)
        if n != 1:
            raise RenderError(
                f"template marker {marker!r} appears {n} times, expected exactly 1 — "
                "verify-contract.js keys off it and exits 2 when it cannot"
            )
    if SCRAPE_MARKER not in template:
        raise RenderError(f"template lost the {SCRAPE_MARKER!r} banner")

    a, b = template.index(DATA_START), template.index(BUNDLE_MARKER)
    c, d = template.index(DATA_END), template.index(SCRAPE_MARKER)
    if not a < b < c < d:
        raise RenderError(
            "template markers are out of order: "
            f"DATA_START@{a} BUNDLE@{b} DATA_END@{c} RENDER@{d}"
        )

    # The placeholder is exactly `{}`, which is why the splice below needs no
    # brace matching: `str.index("}", a)` cannot land anywhere else.
    if template[b + len(BUNDLE_MARKER)] != "}":
        raise RenderError(
            "the template's BUNDLES placeholder is not empty — it must read "
            "`const BUNDLES = {};` so the splice needs no brace matcher"
        )


def check_payload(payload: dict) -> list[str]:
    """Everything neither gate checks, returned as human sentences.

    Deliberately *not* the full §6.7 list: the checks that need `survey.json`
    (checkpoint answer keys deep-equalling the survey, stop kinds, track
    minutes) belong to stage 4, which has the survey in hand. What is here is
    payload-internal and falls into exactly two buckets — things that render a
    lie, and things that render nothing at all. Anything that merely renders
    *ugly* is left alone on purpose: aborting the build at hour 9 over an empty
    drawer would be the more expensive failure.
    """
    out: list[str] = []

    missing = [k for k in TOP_LEVEL if k not in payload]
    if missing:
        return [f"payload is missing top-level key(s): {', '.join(missing)}"]

    repo, report = payload["repo"] or {}, payload["report"] or {}

    # Decision #27's three fields. `shell()` reads all three before the first
    # stop is drawn; a missing one is the blank page that passes both gates.
    for key in ("name", "commit", "generated_at"):
        if not str(repo.get(key) or "").strip():
            out.append(f"repo.{key} is empty — shell() throws and the page renders blank")
    if not str(report.get("tool_version") or "").strip():
        out.append("report.tool_version is empty — shell() throws and the page renders blank")
    if not isinstance(report.get("duration_s"), int):
        out.append("report.duration_s must be an int (decision #27)")

    dropped = payload["dropped"]
    dropped_ids = {d.get("id") for d in dropped}
    ledgers = failing = 0
    claim_ids: list[str] = []

    for track in payload["tracks"]:
        for stop in track.get("stops", []):
            where = stop.get("id", "?")
            blocks = stop.get("blocks") or []
            if not blocks:
                out.append(f"stop {where}: empty blocks array — the renderer TypeErrors on it")
            for block in blocks:
                kind = block.get("type")
                if kind not in BLOCK_TYPES:
                    out.append(f"stop {where}: unknown block type {kind!r} — B[type] is undefined")
                    continue
                if kind == "ledger":
                    ledgers += 1
                elif kind == "command":
                    failing += _check_command(block, where, out)
                elif kind == "prose":
                    _check_prose(block, where, out, claim_ids)
                elif kind == "callout":
                    _check_callout(block, where, out)
                elif kind == "checkpoint":
                    _check_checkpoint(block, where, out)
                elif kind == "trace":
                    for i, step in enumerate(block.get("steps") or [], 1):
                        _check_anchor(step.get("anchor"), f"stop {where} trace hop {i}", out)
                elif kind == "excerpt":
                    _check_anchor(block.get("anchor"), f"stop {where} excerpt", out)

    # Non-negotiable #3. The drop count is on the badge either way, but the
    # ledger block is where the eight deleted sentences are actually listed,
    # and no gate asks for it.
    if not ledgers:
        out.append("no ledger block — the dropped claims would never be shown (non-negotiable #3)")

    dupes = {i for i in claim_ids if claim_ids.count(i) > 1}
    if dupes:
        out.append(
            f"duplicate claim id(s) {sorted(dupes)} — `data-pop` collides and a marker "
            "opens the wrong excerpt"
        )
    both = sorted(dropped_ids & set(claim_ids))
    if both:
        out.append(f"claim id(s) {both} are both rendered and in the ledger")

    # The gate builds its "rendered" set from prose claims only, so a dropped
    # sentence surfacing in a table cell or a trace hop passes it. This is the
    # one failure that would discredit the whole pitch, so it is checked over
    # the serialised tracks — every block type, not just the two.
    serialised = json.dumps(payload["tracks"], ensure_ascii=False)
    for cid in sorted(i for i in dropped_ids if i):
        if cid in serialised and cid not in both:
            out.append(f"dropped claim {cid} appears somewhere in tracks — it must appear only in the ledger")

    for entry in dropped:
        if not str(entry.get("reason") or "").strip():
            out.append(f"dropped claim {entry.get('id')} carries no reason")

    if report.get("dropped") != len(dropped):
        out.append(f"report.dropped is {report.get('dropped')}, the ledger lists {len(dropped)}")
    if report.get("failed") != failing:
        out.append(f"report.failed is {report.get('failed')}, the page renders {failing} failing command(s)")

    return out


def _check_prose(block: dict, where: str, out: list[str], claim_ids: list[str]) -> None:
    """An inferred claim must not wear an anchor, and vice versa.

    An anchor is the only thing that makes a sentence render as verified. An
    inferred claim carrying one is a lie by markup — non-negotiable #2 — and a
    verified claim without one renders a marker whose popover is empty.
    """
    for claim in block.get("claims") or []:
        cid = claim.get("id")
        claim_ids.append(cid)
        if cid and not _CLAIM_ID.match(str(cid)):
            # Not fatal — the marker label is `id.slice(-3)` — but worth saying.
            out.append(f"stop {where}: claim id {cid!r} is not of the form c-001")
        status = claim.get("status")
        if status not in CLAIM_STATUSES:
            out.append(f"stop {where}: claim {cid} has status {status!r}")
        elif status == "inferred":
            if claim.get("anchor") is not None:
                out.append(f"claim {cid} is inferred but carries an anchor — it would render as verified")
        else:
            _check_anchor(claim.get("anchor"), f"claim {cid}", out)


def _check_anchor(anchor: dict | None, who: str, out: list[str]) -> None:
    """Anchors are the gate's business — except the one it cannot report well.

    `verify-contract.js` does an exact-string lookup into `files`, so a single
    backslash in `anchor.file` reports "file not bundled" for every anchor in
    that file and says nothing about why. Catching it here names the cause.
    """
    if not anchor:
        out.append(f"{who}: verified but carries no anchor")
        return
    path = anchor.get("file") or ""
    if "\\" in path:
        out.append(f"{who}: anchor.file {path!r} contains a backslash — use textio.rel_key")
    if not anchor.get("sha256"):
        out.append(f"{who}: anchor carries no sha256 — nothing to verify it against")


def _check_command(block: dict, where: str, out: list[str]) -> int:
    """Non-negotiable #4, made checkable. Returns 1 if this command failed.

    `exit` is type-checked rather than truth-checked because the page tests
    truthiness: `null` renders a green PASSING pill and the string `"0"` renders
    a red one. Both are fabrications of a result, which is the one thing this
    project promises never to do. `bool` is excluded explicitly — `True == 1`
    in Python and would sail through an `isinstance(x, int)` on its own.
    """
    code = block.get("exit")
    cmd = block.get("cmd", "?")
    if isinstance(code, bool) or not isinstance(code, int):
        out.append(f"stop {where}: command {cmd!r} has exit {code!r} — must be a real int")
        code = None
    for key in ("cmd", "cwd", "out", "dur", "env"):
        if not str(block.get(key) or "").strip():
            out.append(f"stop {where}: command {cmd!r} has no {key}")
    if code not in (None, 0) and not str(block.get("broken") or "").strip():
        out.append(f"stop {where}: command {cmd!r} failed with no BROKEN banner")
    return 1 if code not in (None, 0) else 0


def _check_callout(block: dict, where: str, out: list[str]) -> None:
    """The renderer emits `<b>${esc(b.title)}</b>` unconditionally.

    A missing title therefore prints the literal word "undefined" — on the
    honest-degradation stops, which are the ones a judge reads most closely.
    """
    if block.get("level") not in CALLOUT_LEVELS:
        out.append(f"stop {where}: callout level {block.get('level')!r} is not one of {sorted(CALLOUT_LEVELS)}")
    for key in ("title", "text"):
        if not str(block.get(key) or "").strip():
            out.append(f"stop {where}: callout has no {key} — the page would print 'undefined'")


def _check_checkpoint(block: dict, where: str, out: list[str]) -> None:
    """A bare-numeric checkpoint id makes CHECK navigate instead of grade.

    The id is used as a DOM hook and shares a namespace with stop indices, so
    `"12"` sends the reader to stop 12 rather than marking their answer. It is
    silent, it looks like a UI bug, and no gate catches it.
    """
    cid = str(block.get("id") or "")
    if not cid:
        out.append(f"stop {where}: checkpoint has no id")
    elif cid.isdigit():
        out.append(f"stop {where}: checkpoint id {cid!r} is all digits — CHECK would navigate, not grade")
    for key in ("provenance", "explanation"):
        if not str(block.get(key) or "").strip():
            out.append(f"checkpoint {cid}: no {key} — the answer key must say where it came from")


def splice(template: str, payload: dict) -> str:
    """Drop one armoured payload into the template's `{}` placeholder.

    No brace matching is needed on this side: the placeholder is exactly `{}`,
    so the first `}` after the marker is the right one. `tools/inline-fixture.js`
    carries a string-aware matcher only because it re-splices an *already
    populated* demo.

    The payload is wrapped as `{repo.name: payload}` because the shell reads a
    map of repo to walkthrough. A generated artifact always has exactly one
    entry; the wrapper is what lets the same renderer serve a two-repo demo
    without shipping two near-identical files.
    """
    check_template(template)
    name = (payload.get("repo") or {}).get("name")
    if not name:
        raise RenderError("payload has no repo.name — there is nothing to key the bundle on")

    # ensure_ascii=False keeps the payload readable and small; the armour is
    # what makes that safe. Compute nothing from the armoured text — sha256s
    # were taken over the pre-armour lines and the gate re-hashes the decoded
    # `files` map.
    body = armour_json(json.dumps({name: payload}, ensure_ascii=False, separators=(",", ":")))

    a = template.index(BUNDLE_MARKER)
    end = template.index("}", a)
    out = template[:a] + "const BUNDLES = " + body + template[end + 1:]

    # The armour removes every `/` from the payload, so a bundled source line
    # can never forge either DATA marker. Assert it rather than assume it: a
    # forged end marker truncates the gate's slice and the gate exits 2.
    for marker in (DATA_START, DATA_END):
        if out.count(marker) != 1:
            raise RenderError(
                f"the spliced payload duplicated the marker {marker!r} — the armour is not doing its job"
            )
    return out


def render(payload: dict, out_path: Path, *, template: str | None = None) -> Path:
    """Write the finished bundle. Returns the resolved path actually written.

    **This does not refuse to write inside the repo, deliberately.** The ledger
    prints `trailhead build . --out trailhead.html` on screen as the regeneration
    command, and it is copy-paste correct from the repo root. Refusing writes
    inside the repo would make the one command shown to the audience the one
    command the tool rejects. The output is kept out of its own walkthrough the
    other way round: the resolved path returned here is what `survey.walk_files`
    takes as `out_path` and excludes (§3.3).

    Atomic (`tmp` + `os.replace`) so an interrupted run leaves the previous
    good bundle in place rather than a half-written one — on stage, a truncated
    HTML file that still opens is worse than an old one.
    """
    out = Path(out_path).expanduser().resolve()

    problems = check_payload(payload)
    if problems:
        raise RenderError(
            "refusing to render a payload that would lie or render blank:\n  - "
            + "\n  - ".join(problems)
        )

    html = splice(load_template() if template is None else template, payload)

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(html, encoding="utf-8", newline="\n")
    os.replace(tmp, out)
    return out


def main(argv: list[str] | None = None) -> int:
    """`py -3.11 -m trailhead.render --payload P --out O`.

    Stage 5 alone, for rebuilding the demo from the frozen fixture without
    going near `cli.py` or any other stage. `cli.py` owns the real surface;
    this exists so render stays runnable while the rest of the pipeline is
    still being built.
    """
    import argparse

    ap = argparse.ArgumentParser(prog="trailhead.render", description="stage 5 — splice a verified.json into one HTML file")
    ap.add_argument("--payload", required=True, type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ns = ap.parse_args(argv)

    payload = json.loads(ns.payload.read_text(encoding="utf-8"))
    try:
        written = render(payload, ns.out)
    except RenderError as exc:
        print(f"trailhead render: {exc}")
        return 1
    print(f"wrote {written}  {written.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
