"""The command line — the argparse surface and the stage driver (plan §10).

This module owns two things and deliberately no more: the flags, and the order
the stages run in. Every stage's *logic* lives in its own module; what lives
here is the wiring, the on-disk artifacts, and the exit code.

    repo -> 1 survey -> survey.json -> 2 map -> map.json
                 |                        |
                 +-> runner -> commands.json
                 |                        |
                 +---------> 3 narrate + compose -> content.json
                                          |
                              4 verify <--+
                                          |
                    verified.json + verification-report.json
                                          |
                                     5 render -> trailhead.html

**The runner runs before narrate** (decision #12). Narrate can then see which
commands really failed, and every degradation decision is made once, in one
deterministic place, before a single sentence is written.

Every stage reads its input from disk and writes its output to disk. That is
what makes `--from-stage` real rather than a promise: narrate is the only slow
or networked stage, so `--from-stage verify` re-renders in under a second when
you spot a typo mid-rehearsal, and if the endpoint dies during the pitch you
run the whole thing off the last `content.json` and nobody notices.

Exit codes: `0` ok · `1` generation failed · `2` usage · `3` gates failed.
Three, not two, because "the bundle is wrong" and "the arguments were wrong"
are different problems and a rehearsal script needs to tell them apart.

Run it:

    cd hackathon
    PYTHONPATH=src py -3.11 -m trailhead build restored -o out/restored.html \
        --provider stub --run-commands safe --gate
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from trailhead import checkpoints as checkpoints_mod
from trailhead import compose as compose_mod
from trailhead import mapper as mapper_mod
from trailhead import narrate as narrate_mod
from trailhead import provider as provider_mod
from trailhead import render as render_mod
from trailhead import runner as runner_mod
from trailhead import survey as survey_mod
from trailhead import verify as verify_mod

#: Stage order, and the vocabulary of `--from-stage`. The index of a value in
#: this tuple is how far the driver skips: everything at or after the index
#: runs, everything before it is read back off disk.
STAGES = ("survey", "map", "commands", "narrate", "verify", "render")

#: What each stage leaves in `<work>`. `verification-report.json` is not here
#: because nothing reads it back — it is the audit log, written and kept.
ARTIFACTS = {
    "survey": "survey.json",
    "map": "map.json",
    "commands": "commands.json",
    "narrate": "content.json",
    "verify": "verified.json",
}

#: The Node gates. `hackathon/tools/` — this file is `src/trailhead/cli.py`.
TOOLS = Path(__file__).resolve().parents[2] / "tools"

#: `--gate` runs the two gates that READ AN ARTIFACT. `check-fixtures.js`
#: hard-codes `../fixtures`, takes no argv and says nothing about generated
#: output — it is a repo invariant, not a build gate.
GATES = ("check-bundle.js", "verify-contract.js")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_GATE = 3


class UsageError(Exception):
    """An argument combination argparse cannot express. Exits 2, never 1."""


def build_parser() -> argparse.ArgumentParser:
    """The surface of plan §10, and nothing else.

    Fourteen of the recon's twenty flags are cut (cut-list item 7). Each one is
    argparse plumbing plus a code path plus a way to be wrong on stage; cutting
    `--seed` in particular is why the one seed is pinned to `repo.commit`, so
    two runs of the same commit produce the same checkpoint option order.

    `--emit-prompts` is the one addition, and it is what replaced the project's
    last third-party dependency: it writes one self-describing prompt pack per
    unit for the host coding agent to answer, and the agent writes its answer
    straight into the narration store the stub replays from.
    """
    ap = argparse.ArgumentParser(
        prog="trailhead",
        description="Generate one self-contained HTML walkthrough of a repo, "
                    "with every factual sentence anchored to a file:line and "
                    "re-checked after it was written.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="generate one walkthrough")
    b.add_argument("repo", nargs="?",
                   help="repo to walk. Required except with --from-stage render.")
    b.add_argument("-o", "--out", type=Path, default=Path("trailhead.html"),
                   help="output HTML bundle (default: trailhead.html)")
    b.add_argument("--work", type=Path, default=None,
                   help="intermediate artifacts (default: <out-parent>/.trailhead)")
    b.add_argument("--payload", type=Path, default=None,
                   help="verified.json to render (default: <work>/verified.json). "
                        "Only meaningful with --from-stage render.")
    b.add_argument("--provider", choices=("stub", "claude"), default="stub",
                   help="stub replays the narration store; claude is opt-in and live")
    b.add_argument("--offline", action="store_true",
                   help="a narration-cache miss is an error instead of an empty unit")
    b.add_argument("--run-commands", dest="run_commands",
                   choices=("safe", "none"), default="safe",
                   help="safe executes the allowlisted candidates; none runs nothing")
    b.add_argument("--from-stage", dest="from_stage", choices=STAGES, default="survey",
                   help="skip the stages before this one and read their artifacts")
    b.add_argument("--emit-prompts", dest="emit_prompts", action="store_true",
                   help="write one prompt pack per narrate unit and stop")
    b.add_argument("--max-units", dest="max_units", type=int,
                   default=narrate_mod.MAX_UNITS_DEFAULT,
                   help=f"narrate at most N units (default {narrate_mod.MAX_UNITS_DEFAULT})")
    b.add_argument("--max-nodes", dest="max_nodes", type=int,
                   default=mapper_mod.MAP_CAP,
                   help=f"collapse the map to at most N nodes (default {mapper_mod.MAP_CAP})")
    b.add_argument("--gate", action="store_true",
                   help="run check-bundle.js and verify-contract.js on the output")
    b.add_argument("-v", "--verbose", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    """Parse, dispatch, and turn every expected failure into an exit code.

    A traceback is the right output for a bug in this code and the wrong output
    for a repo the tool cannot survey — so the exceptions the stages raise on
    purpose (`SourceRootError`, `LayoutError`, `VerifyError`, `RenderError`,
    `MissingNarration`) are caught here and printed as one line, and everything
    else is left to propagate with its stack intact.
    """
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return build(args)
    except UsageError as exc:
        sys.stderr.write(f"trailhead: {exc}\n")
        return EXIT_USAGE
    except (survey_mod.SourceRootError, mapper_mod.LayoutError,
            verify_mod.VerifyError, render_mod.RenderError,
            provider_mod.MissingNarration, FileNotFoundError) as exc:
        sys.stderr.write(f"trailhead: {type(exc).__name__}: {exc}\n")
        return EXIT_FAILED
    except KeyboardInterrupt:
        sys.stderr.write("\ntrailhead: interrupted\n")
        return EXIT_FAILED


def build(args) -> int:
    """Run the pipeline from `--from-stage` to the end. The whole driver.

    Written as one flat sequence rather than a stage registry with a dependency
    graph: there are six stages, they run in one order, and a table of callables
    would hide the one thing a reader needs to see here, which is what each
    stage is handed.
    """
    t0 = time.monotonic()
    out = Path(args.out).expanduser().resolve()
    work = (Path(args.work).expanduser().resolve() if args.work
            else out.parent / ".trailhead")
    start = STAGES.index(args.from_stage)

    if args.repo is None and args.from_stage != "render":
        raise UsageError("a repo path is required except with --from-stage render")
    root = Path(args.repo).expanduser().resolve() if args.repo else None
    if root is not None and not root.is_dir():
        raise UsageError(f"not a directory: {root}")
    work.mkdir(parents=True, exist_ok=True)

    say = _talker(args.verbose)
    sv = mp = cmds = content = None

    # --- stage 1 SURVEY ---------------------------------------------------
    # `out_path` is passed so the walk excludes the bundle it is about to
    # write. Without it a second run surveys its own 400 KB of output.
    if start <= STAGES.index("survey"):
        say(f"survey  {root}")
        sv = survey_mod.survey(root, out_path=out)
        # Pass one of the answer keys: cp-a1 and cp-a2 need only survey.json,
        # and emitting them now means `--from-stage map` still has them.
        sv.setdefault("checkpoints", {}).update(
            checkpoints_mod.build_checkpoints(sv))
        verify_mod.write_json(work / ARTIFACTS["survey"], sv)
        say(f"        {sv['stats']['py_files']} py files, "
            f"{sv['stats']['loc']} loc, {len(sv['files'])} in scope")
    elif start <= STAGES.index("verify"):
        sv = _read(work / ARTIFACTS["survey"], "survey")

    root = _root_of(root, sv)
    hops, hops_note = _hops_for(sv) if sv else ([], None)
    if hops_note:
        say(hops_note)

    # --- stage 2 MAP ------------------------------------------------------
    if start <= STAGES.index("map"):
        say("map")
        mp = mapper_mod.build_map(sv, cap=args.max_nodes)
        verify_mod.write_json(work / ARTIFACTS["map"], mp)
        # Pass two: cp-c1 reads the map's column index and cp-c2 the hop list,
        # so the keys are completed here and survey.json is rewritten. The
        # seeds are derived from `repo.commit + cp_id`, so re-deriving cp-a
        # cannot move an answer index that pass one already published.
        sv.setdefault("checkpoints", {}).update(
            checkpoints_mod.build_checkpoints(sv, mp, hops=hops))
        verify_mod.write_json(work / ARTIFACTS["survey"], sv)
        say(f"        {len(mp['nodes'])} nodes, {len(mp['edges'])} edges, "
            f"render={mp['render']}")
    elif start <= STAGES.index("verify"):
        mp = _read(work / ARTIFACTS["map"], "map")

    # --- the runner (before narrate, decision #12) ------------------------
    if start <= STAGES.index("commands"):
        say(f"runner  policy={args.run_commands}")
        cmds = runner_mod.run_commands(
            sv, root, policy=args.run_commands,
            out_path=work / ARTIFACTS["commands"])
        say(f"        {len(cmds['runs'])} run, {len(cmds['skipped'])} skipped")
    elif start <= STAGES.index("verify"):
        cmds = _read(work / ARTIFACTS["commands"], "commands")

    # --- stage 3 NARRATE + compose ---------------------------------------
    if start <= STAGES.index("narrate"):
        if args.emit_prompts:
            return _emit_prompts(sv, mp, root, work, cmds, hops, args)
        content = _narrate(sv, mp, cmds, hops, root, work, args, say)
        verify_mod.write_json(work / ARTIFACTS["narrate"], content)
    elif start <= STAGES.index("verify"):
        content = _read(work / ARTIFACTS["narrate"], "narrate")

    # --- stage 4 VERIFY ---------------------------------------------------
    if start <= STAGES.index("verify"):
        say("verify")
        payload, audit = verify_mod.assemble(
            content, sv, mp, cmds, root, t0=t0,
            windows=_windows(content),
            run_stats={"commands": len((cmds or {}).get("runs") or [])},
            regen=_regen_line(args))
        verify_mod.write_json(work / ARTIFACTS["verify"], payload)
        verify_mod.write_json(work / "verification-report.json", audit)
        r = payload["report"]
        say(f"        {r['verified']} verified, {r['inferred']} inferred, "
            f"{r['dropped']} dropped of {r['claims']}")
    else:
        payload = _read(args.payload or work / ARTIFACTS["verify"], "verify")

    # --- stage 5 RENDER ---------------------------------------------------
    written = render_mod.render(payload, out)
    print(f"wrote {written}  {written.stat().st_size / 1024:.1f} KB")
    _summarise(payload, _provenance(hops_note, content))

    if args.gate:
        return run_gates(written)
    return EXIT_OK


# ---------------------------------------------------------------------------
# Stage 3, which is two things: the model call and the deterministic course.
# ---------------------------------------------------------------------------

def _narrate(sv: dict, mp: dict, cmds: dict, hops: list, root: Path,
             work: Path, args, say) -> dict:
    """Narrate the units, then compose the course around whatever came back.

    The two halves are deliberately not interchangeable. `narrate.run` is the
    only code in this project that reaches a provider; `compose.build_course`
    is a deterministic table of stops that the model never sees and cannot add
    to. A unit that returns nothing — the normal case with an empty narration
    store — costs its stop its claims and nothing else: the stop still renders
    from its template blocks, which is exactly the degradation path §9
    promises, exercised for free on every cold run.
    """
    store = Path(work) / narrate_mod.CACHE_DIRNAME
    prov = provider_mod.build(args.provider, store, offline=args.offline)
    say(f"narrate provider={prov.name} store={store}")

    result = narrate_mod.run(sv, root, prov, work=work, commands=cmds,
                             hops=hops, max_units=args.max_units,
                             offline=args.offline, verbose=args.verbose,
                             map_data=mp)
    model = result["model"]
    say(f"        {len(result['units'])} units, {model['calls']} call(s), "
        f"{model['cache_hits']} cache hit(s), {len(result['ledger'])} parser drop(s)")

    ctx = compose_mod.Ctx(
        survey=sv, map=mp, commands=cmds or {}, narration=result["narration"],
        hops=hops,
        # The one seed, pinned to the commit (there is no `--seed`): the same
        # commit always shuffles the checkpoint options the same way, so a
        # rehearsal and the run on stage are the same page.
        rng=random.Random((sv.get("repo") or {}).get("commit") or sv.get("repo", {}).get("name", "")),
        degradations=[])
    # The glossary stop lists term + definition, both of which survive
    # verification unconditionally (only anchors can drop), so composing it
    # from the raw gloss answer cannot disagree with the verified payload.
    gloss_answer = (result["narration"].get("gloss") or {})
    tracks = compose_mod.build_course(
        ctx, glossary=list(gloss_answer.get("terms") or []))
    say(f"compose {len(tracks)} track(s), "
        f"{sum(len(t['stops']) for t in tracks)} stop(s)")

    content = {
        "contract": "trailhead/content@1",
        "repo": {"name": (sv.get("repo") or {}).get("name"),
                 "commit": (sv.get("repo") or {}).get("commit")},
        "model": model,
        "tracks": tracks,
        # The parser's own drops. They are claims the model produced and the
        # generator refused, so they belong in the ledger on screen exactly
        # like a failed anchor — losing them here would flatter the drop count.
        "dropped": result["ledger"],
        "degradations": list(ctx.degradations) + list(result["degradations"]),
        # Additive over content@1, and load-bearing: these are the spans the
        # model was actually shown. Without them the resolver cannot refuse a
        # quote that resolved outside the excerpt, and `--from-stage verify`
        # would silently verify against the whole file instead.
        "windows": _file_windows(result["windows"]),
        "units": result["units"],
    }
    # The @3 unit answers (glossary terms, per-node narration, tour text,
    # column labels) ride in content.json beside the tracks so that
    # `--from-stage verify` replays them from disk like everything else.
    # Absent units contribute nothing and the keys stay off the file.
    content.update(_unit_answers(result))
    return content


def _emit_prompts(sv: dict, mp: dict, root: Path, work: Path,
                  cmds: dict | None, hops: list, args) -> int:
    """Write the prompt packs and stop, printing what to do with them.

    Stopping is the point. The host agent answers each pack into the `out` path
    the pack itself carries, and the next run — `--from-stage narrate` — replays
    them through `StubProvider` with no model in the loop at all.
    """
    packs = narrate_mod.emit_prompts(sv, root, work, commands=cmds, hops=hops,
                                     max_units=args.max_units, map_data=mp)
    for pack in packs:
        print(f"{pack['unit']:>6}  {pack['pack']}")
    print(f"\n{len(packs)} prompt pack(s) in {Path(work) / narrate_mod.PROMPTS_DIRNAME}.")
    print("Answer each into its own \"out\" path, then re-run with "
          "--from-stage narrate.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Reading artifacts back, and the two conversions between stage vocabularies.
# ---------------------------------------------------------------------------

def _read(path: Path, stage: str) -> dict:
    """Load an artifact a skipped stage should have left behind.

    The error names the stage to re-run rather than the missing file, because
    "no such file: .trailhead/map.json" at hour 9 is a puzzle and "run
    --from-stage map first" is an instruction. ASCII only: the Windows console
    this is demoed on is cp1252, and an em dash arrives there as a replacement
    character on the one line whose whole job is to be read.
    """
    path = Path(path)
    if not path.is_file():
        raise UsageError(
            f"{path} is missing - --from-stage needs it. "
            f"Run with --from-stage {stage} (or earlier) first.")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _file_windows(unit_windows) -> dict:
    """`{unit: [{file,start,end}]}` -> `{file: [[start,end], …]}`.

    Narrate records windows per unit because a unit is what it packed; the
    resolver scopes per file because a quote is resolved against one file's
    lines. Two units that showed the same file contribute both spans — the
    union is correct, since the model saw both.
    """
    out: dict[str, set] = {}
    for spans in (unit_windows or {}).values():
        for w in spans or ():
            try:
                out.setdefault(str(w["file"]), set()).add(
                    (int(w["start"]), int(w["end"])))
            except (KeyError, TypeError, ValueError):
                continue
    return {f: [list(s) for s in sorted(spans)] for f, spans in out.items()}


def _unit_answers(result: dict) -> dict:
    """The @3 unit answers, lifted out of the narration for content.json.

    Unit ids are matched exact-or-prefix on the colon: `gloss`, `tour` and
    `cols` are exact, `node:<gid>` carries its map group id after the colon
    (the claim-bearing `five` and `dive:<gid>` units are compose's business
    and are deliberately not lifted here). Each answer is accepted either as
    the schema object (`{"terms": [...]}`) or as the bare list, so the narrate
    parser is free to store whichever it validated.

    Returns only the keys that have substance; a repo whose new units were
    never answered gets an empty dict and a content.json identical to @2's.
    """
    narration = (result or {}).get("narration") or {}
    gloss: list = []
    nodes: dict = {}
    tour: list = []
    cols: list = []

    def unwrap(answer, key):
        if isinstance(answer, dict):
            answer = answer.get(key)
        return list(answer) if isinstance(answer, list) else []

    for unit_id in sorted(narration, key=str):
        answer = narration[unit_id]
        head, _, tail = str(unit_id).partition(":")
        if head == "gloss" and not tail:
            gloss.extend(unwrap(answer, "terms"))
        elif head == "node" and tail and isinstance(answer, dict):
            nodes[tail] = answer
        elif head == "tour" and not tail:
            tour = unwrap(answer, "steps")
        elif head == "cols" and not tail:
            cols = unwrap(answer, "labels")

    out: dict = {}
    if gloss:
        out["glossary"] = gloss
    if nodes:
        out["map_answers"] = nodes
    if tour:
        out["tour"] = tour
    if cols:
        out["cols"] = cols
    # A narrate stage that already attached an answer set at the result's top
    # level is authoritative over this lift.
    for key in ("glossary", "map_answers", "tour", "cols"):
        if (result or {}).get(key):
            out[key] = result[key]
    return out


def _windows(content) -> dict | None:
    """The window map as `assemble` wants it, or None to mean "do not scope".

    None and `{}` are different answers and the difference is a whole run:
    `{}` scopes every file to nothing and drops every claim as *resolved
    outside the excerpt shown to the model*, which is a total loss dressed up
    as a verification result.
    """
    raw = (content or {}).get("windows") or {}
    windows = {f: [tuple(s) for s in spans] for f, spans in raw.items() if spans}
    return windows or None


def _hops_for(sv: dict) -> tuple[list, str]:
    """The hand-specified trace hops for THIS repo, and where they came from.

    `chain.py` — a generic call-chain walker — was cut at hour 0 (decision #25),
    so the hops are input, not output: a repo carries its chain in
    `fixtures/trace.<repo-name>.json` or it has no chain at all. `restored` has
    one because its eight `file:line` hops were read off disk by hand and
    checked in; nothing else on this machine does.

    **The trace stop is therefore presented as hand-verified, never as
    generated.** That is the decision the audit asked for, made here and said
    out loud by the second return value, which the build prints under the claim
    counts on every run. The distinction matters because those eight anchors are
    the bulk of `report.verified`: the pipeline re-reads and hash-matches every
    one of them against the working tree — that part is real, deterministic and
    exactly as strict as it is for a model claim — but it did not *discover*
    them, and a headline of "8 verified" read as a genericity result would be
    over-claiming by a whole stage.

    Looking the fixture up by name rather than hard-coding one path is what
    keeps this a documented input and not a special case: any repo may ship
    hops, none has to, and the `repo` field inside the file is still checked so
    that a fixture copied under the wrong name cannot put eight anchors from
    someone else's codebase into the stop. A repo with no fixture gets §9 row
    1's labelled callout and zero anchored hops — a labelled gap, by design.

    **The key is `repo.dir`, the checkout directory, not `repo.name`.** Survey
    resolves `name` to the project's own declared name — `restored/` calls
    itself `volforecast` in its `pyproject.toml` — and a fixture is a property
    of *this checkout on this disk*, not of whatever the project calls itself
    upstream. Keying on `name` built `fixtures/trace.volforecast.json`, missed,
    and silently deleted all eight hand-verified anchors plus checkpoint `cp-c`
    from the one real repo we demo on: the failure of this lookup is invisible
    by construction, because "no fixture" and "wrong filename" degrade
    identically. `repo.dir` is the key `survey.py` added for exactly this, and
    `name` survives only as the fallback for a `survey.json` written before it
    existed.
    """
    repo = sv.get("repo") or {}
    name = str(repo.get("dir") or repo.get("name") or "")
    fixtures = Path(compose_mod.HOPS_FIXTURE).parent
    # `name` reaches a filename, so it must stay one path segment: a repo
    # directory called `..` is not a lookup key, it is a way out of `fixtures/`.
    safe = name and name not in (".", "..") and name == Path(name).name
    path = fixtures / f"trace.{name}.json"
    rel = f"fixtures/{path.name}"

    if not safe or not path.is_file():
        return [], (f"trace   no {rel} - the trace stop degrades to a labelled "
                    f"callout (0 anchored hops)")
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    if str(doc.get("repo") or "") != name:
        return [], (f"trace   {rel} is for repo '{doc.get('repo')}', not "
                    f"'{name}' - ignored, 0 anchored hops")
    hops = list(doc.get("hops") or [])
    return hops, (f"trace   {len(hops)} hop(s) hand-specified in {rel} "
                  f"(decision #25) - anchors re-verified from disk, not discovered")


def _regen_line(args) -> str:
    """The regeneration command the ledger footer prints as `report.regen`.

    Built from THIS run's own arguments, never from a constant: the footer is
    provenance, and before this existed the renderer's fallback sentence
    claimed the hand-built template artifact's pedigree ("re-verified by
    template/verify.mjs") for every generated page — a provenance lie on the
    one panel whose whole job is honesty. The paths are echoed as the user
    typed them, forward-slashed so the line pastes into the documented
    `cd hackathon` invocation on any shell, and the string is kept dash-free
    (plain hyphens only) like every other authored string in the payload.
    """
    repo = str(args.repo or ".").replace("\\", "/")
    line = (f"Regenerate: PYTHONPATH=src python -m trailhead build {repo} "
            f"-o {Path(args.out).as_posix()} "
            f"--run-commands {args.run_commands}")
    return line.replace("\u2014", "-").replace("\u2013", "-")


def _root_of(root: Path | None, sv: dict | None) -> Path | None:
    """The repo root: the argument if given, else what survey recorded.

    `--from-stage verify` on a survey taken an hour ago must re-read the same
    files the quotes were copied from, and `survey.repo.root` is the only
    record of where they were.
    """
    if root is not None:
        return root
    recorded = (sv or {}).get("repo", {}).get("root")
    return Path(recorded) if recorded else None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _talker(verbose: bool):
    """Progress to stderr, so stdout stays the one path that was written."""
    def say(line: str) -> None:
        if verbose:
            sys.stderr.write(f"{line}\n")
    return say


def _summarise(payload: dict, provenance: list[str] = ()) -> None:
    """The three numbers the pitch turns on, printed whether or not -v is set.

    The dropped count is on the never-cut list. A build that printed only
    "wrote out/x.html" would hide the number the entire project exists to
    produce, on the command the audience watches you run.

    `provenance` prints directly under them because a number without its source
    is how a run gets over-claimed on stage. `verified 8` is true and is not the
    same statement as "the model wrote eight sentences and eight survived": it
    is worth exactly as much as the lines that say where those claims came from,
    so those lines are printed on the same screen, by the same command, always.
    """
    r = payload.get("report") or {}
    print(f"  claims {r.get('claims', 0)}  verified {r.get('verified', 0)}  "
          f"inferred {r.get('inferred', 0)}  DROPPED {r.get('dropped', 0)}")
    print(f"  commands {r.get('commands', 0)} ({r.get('failed', 0)} failing)  "
          f"stops {sum(len(t.get('stops') or []) for t in payload.get('tracks') or [])}"
          f"  {r.get('duration_s', 0)}s")
    for line in provenance or ():
        print(f"  {line}")


def _provenance(hops_note: str | None, content: dict | None) -> list[str]:
    """Where the claims came from — the two lines that keep the counts honest.

    One for the trace hops (input, hand-specified, see `_hops_for`) and one for
    the model, which reports how many units actually came back with claims. A
    cold narration store answers none of them, and then every sentence on the
    page is a deterministic template and the machine caught the model inventing
    nothing because the model was never asked. That is a fine artifact and a
    dishonest pitch, and the difference between the two is this line.

    Both are derived from artifacts on disk, so `--from-stage verify` prints the
    same two lines as a full run; `--from-stage render` has neither survey nor
    `content.json` and prints nothing rather than guessing.
    """
    lines = [hops_note] if hops_note else []
    units = (content or {}).get("units") or []
    if units:
        model = (content or {}).get("model") or {}
        got = sum(1 for u in units if int(u.get("claims") or 0) > 0)
        claims = sum(int(u.get("claims") or 0) for u in units)
        tail = ("" if got else
                " - every sentence on the page is a deterministic template")
        lines.append(f"model   {claims} claim(s) from {got}/{len(units)} unit(s) "
                     f"via {model.get('provider', '?')}{tail}")
    return lines


def run_gates(out: Path) -> int:
    """`check-bundle.js` and `verify-contract.js` against the written bundle.

    A missing `node` **warns and returns 0**. The bundle is already written and
    a missing gate runner is an environment problem, not a bad artifact — so it
    prints the two commands to run by hand instead of failing a build that may
    be perfectly good.
    """
    node = shutil.which("node")
    if node is None:
        sys.stderr.write(
            "trailhead: node not found — the bundle is written but ungated. Run:\n"
            + "".join(f"  node {TOOLS / g} {out}\n" for g in GATES))
        return EXIT_OK

    failures = 0
    for gate in GATES:
        proc = subprocess.run([node, str(TOOLS / gate), str(out)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace")
        tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
        verdict = "ok" if proc.returncode == 0 else "FAILED"
        print(f"  gate {gate}: {verdict}")
        if proc.returncode != 0:
            failures += 1
            sys.stderr.write("\n".join(tail[-40:]) + "\n")
        elif tail:
            print(f"       {tail[-1]}")
    return EXIT_GATE if failures else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
