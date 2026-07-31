"""The command runner — real execution, real capture. Deterministic. No model.

Not one of the five stages: it sits between MAP and NARRATE (decision #12) so
that narrate can see which commands really failed. It emits `commands.json`
(`trailhead/commands@1`), which VERIFY merges into command blocks by `(cmd, cwd)`.

**Non-negotiable #4 lives in this file.** Output is real or the whole project is
a fraud. Nothing here invents stdout, an exit code or a timing, and the type
system is what enforces it rather than discipline: a candidate that was not
executed becomes a `SkippedCommand`, which has no `exit`, no `out` and no `dur`
to be wrong about. There is no constructor path producing those three fields
without a real child process.

The one synthesised string in a command block is the literal `(no output)`
(§8.3). It describes an absence rather than inventing content, `exit` and `dur`
stay real, and the alternative is not "show nothing" — `verify-contract.js:121`
fails an empty `out` — but "fail the gate".

Two traps this file exists to not fall into, both confirmed by running them:

  * `capture_output=True` cannot be combined with `stderr=subprocess.STDOUT`.
    It raises `ValueError` *before* a single child spawns, so a runner written
    that way degrades every command block to "Not executed" on every run and
    non-negotiable #4 is never exercised.
  * `argv[0]` must be an absolute resolved path or a `shutil.which()` result.
    `['vol.cmd', 'help']` with `shell=False` raises `FileNotFoundError` while
    the absolute path exits 0 — and a naive handler turns that into
    `exit 127, "vol.cmd not found on PATH"`, a false sentence about a file that
    is sitting in the repo root. Resolution failure emits a `SkippedCommand`,
    never a fabricated 127.

Safety posture is deny-by-default (decision #22): commands execute because they
match one of four admitted argv shapes, never because survey discovered them.
That makes a denylist and an import-reachability walk dead code.
"""
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

from .textio import rel_key

#: The contract tag written into `commands.json`. Frozen in pipeline-contracts.md.
CONTRACT = "trailhead/commands@1"

#: Decision #21. Every measured candidate on the proving-ground repo finishes
#: under 3 s; the brief's 300 s default is a dead demo waiting to happen.
PER_COMMAND_TIMEOUT_S = 60.0
TOTAL_BUDGET_S = 120.0

#: `commands@1` caps `out` at 400 lines. The byte cap is this file's addition:
#: `uvx ruff check .` emits 219 KB and `lint_all.py` 25.8 KB, and 400 surviving
#: lines of either still blow any sane payload budget.
MAX_LINES = 400
HEAD_LINES = 240
TAIL_LINES = 160
MAX_BYTES = 8192

#: The one blessed placeholder. See the module docstring.
NO_OUTPUT = "(no output)"

#: Overlaid on `os.environ` for every child. The first two are not cosmetic: an
#: em-dash in real lint output arrived as a replacement character without them,
#: in a bundle whose whole point is that its output is real. The rest stop a
#: child deciding it is talking to a human — colour codes, progress bars and a
#: credential prompt are all worse than useless inside a captured string.
_CHILD_ENV_OVERLAY = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "NO_COLOR": "1",
    "TERM": "dumb",
    "CI": "1",
    "COLUMNS": "100",
    "GIT_TERMINAL_PROMPT": "0",
}

#: §8.5's rule table. The last line matching this is the `broken` banner.
_BROKEN_RE = re.compile(r"(Error|Exception|error:|FAILED|assert)")

#: The only pattern that earns a `hypothesis`. Everything else the rule table
#: could say restates the exit code the page already prints.
_MODULE_MISSING_RE = re.compile(r"ModuleNotFoundError: No module named '([^']+)'")

_DOTTED = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
_IMPORT_SMOKE_RE = re.compile(r"import " + _DOTTED + r"$")
_DOTTED_RE = re.compile(_DOTTED + r"$")


@dataclass(frozen=True)
class CommandResult:
    """One command that actually ran, with everything the run really produced.

    `cmd` is the canonical display string from `survey.command_candidates` —
    `verify.py` merges command blocks on `(cmd, cwd)`, so this string is
    load-bearing and is never rebuilt from `argv` (whose `argv[0]` is an
    absolute interpreter path the reader should not have to look at).

    `dur` is the display string the renderer prints; `dur_ms` is the number.
    `check-fixtures.js:127` asserts every run carries both.

    `kind`, `source` and `truncated` are additive over `commands@1` and exist
    for `compose.py`: §9 rows 2 and 3 need to know which runs were tests and
    which were setup, and the "Not executed" callouts quote the candidate's
    provenance.
    """

    cmd: str
    argv: tuple[str, ...]
    cwd: str
    exit: int
    out: str
    dur_ms: int
    dur: str
    started: str
    timed_out: bool
    env: str
    broken: str | None = None
    hypothesis: str | None = None
    kind: str = ""
    source: str = ""
    truncated: bool = False

    def to_dict(self) -> dict:
        """The `commands@1` run record.

        `broken` and `hypothesis` are omitted when absent rather than emitted as
        `null`: the renderer tests them for truthiness and a serialized `null`
        that survives a careless merge into a command block would render an
        empty BROKEN banner on a command that passed.
        """
        d = {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "exit": self.exit,
            "dur_ms": self.dur_ms,
            "dur": self.dur,
            "started": self.started,
            "timed_out": self.timed_out,
            "env": self.env,
            "out": self.out,
            "argv": list(self.argv),
            "kind": self.kind,
            "source": self.source,
            "truncated": self.truncated,
        }
        if self.broken:
            d["broken"] = self.broken
        if self.hypothesis:
            d["hypothesis"] = self.hypothesis
        return d


@dataclass(frozen=True)
class SkippedCommand:
    """A candidate that was NOT executed, and therefore has no results at all.

    The type split is the point. A skipped candidate cannot accidentally acquire
    an exit code, because this class has nowhere to put one. Its only renderer
    is `callout level="info"` titled "Not executed", naming the candidate, its
    source and the reason (§8.4).
    """

    cmd: str
    reason: str
    cwd: str = "."
    kind: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "kind": self.kind,
            "source": self.source,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------
# The environment note
# --------------------------------------------------------------------------

_VERSION_CACHE: dict[str, str | None] = {}


def env_note(interpreter: str | Path | None = None) -> str:
    """The capture note: a measured string, never a label.

    `verify-contract.js:120` fails **every** command block that lacks one, so
    omitting this is a hard gate failure on the first real run rather than a
    cosmetic omission.

    When the resolved interpreter is not the one generating the bundle, the note
    carries that interpreter's own `--version` output — a real capture, because
    claiming the generating interpreter's version for a child that ran under a
    different one is exactly the kind of small lie this project exists to catch.
    If `--version` cannot be captured we say so instead of substituting a
    version we did not measure.
    """
    stamp = (f"captured {date.today().isoformat()}, "
             f"{platform.system()} {platform.release()}, ")
    if interpreter is None or _is_generating_interpreter(interpreter):
        return stamp + f"python {sys.version.split()[0]}"
    reported = _interpreter_version(str(interpreter))
    if reported:
        return stamp + reported
    return stamp + f"interpreter {Path(str(interpreter)).name} (version not reported)"


def _is_generating_interpreter(interpreter: str | Path) -> bool:
    try:
        return Path(str(interpreter)).resolve() == Path(sys.executable).resolve()
    except OSError:
        return False


def _interpreter_version(interpreter: str) -> str | None:
    """`<interp> --version`, captured for real, or None if it could not run."""
    if interpreter in _VERSION_CACHE:
        return _VERSION_CACHE[interpreter]
    reported = None
    try:
        p = subprocess.run([interpreter, "--version"], shell=False,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=10, env=child_env())
        text = p.stdout.decode("utf-8", errors="replace").strip()
        if p.returncode == 0 and text:
            reported = text.splitlines()[0].strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        reported = None
    _VERSION_CACHE[interpreter] = reported
    return reported


def child_env() -> dict:
    """`os.environ` plus the overlay. A copy — never mutate the parent's env."""
    env = dict(os.environ)
    env.update(_CHILD_ENV_OVERLAY)
    return env


# --------------------------------------------------------------------------
# Truncation
# --------------------------------------------------------------------------

def truncate(out: str) -> tuple[str, bool]:
    """400-line cap (contract), THEN an 8192-byte cap. Both markers explicit.

    A line cap alone is not enough: 400 lines of `uvx ruff check .` is still
    tens of kilobytes, and the payload is spliced into a single HTML file.

    Both passes drop from the middle and keep the head and the tail, because
    that is where the useful content of a failing command lives — the invocation
    at the top and the traceback plus summary line at the bottom.

    The plan describes the byte pass as adding a *second* marker. One marker
    carrying the true total is the same information: both passes elide one
    contiguous middle region, and two adjacent markers describing one gap reads
    as a bug rather than as honesty.

    Returns `(text, truncated)`. `truncated` is what tells the caller that the
    `… N lines elided` marker in `text` is not something the command printed.
    """
    text = out.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    # A trailing newline splits to a final "" that is not a line. Same rule as
    # textio.read_source, for the same reason.
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return "", False

    total = len(lines)
    head, tail = lines, []
    if total > MAX_LINES:
        head, tail = lines[:HEAD_LINES], lines[total - TAIL_LINES:]

    cut = False
    if _byte_len(head, tail, total) > MAX_BYTES:
        head, tail, cut = _fit_bytes(head, tail, total)

    # A line the byte pass had to cut mid-way counts as elided: the fragment is
    # shown because it is the most useful thing left, and most of that line is
    # gone, so saying so is the honest arithmetic.
    elided = total - len(head) - len(tail) + (1 if cut else 0)
    if elided <= 0:
        return "\n".join(lines), False
    return "\n".join(head + [_marker(elided)] + tail), True


def _marker(n: int) -> str:
    """The contract's elision marker, verbatim: `… N lines elided`."""
    return f"… {n} lines elided"


def _byte_len(head: list[str], tail: list[str], total: int) -> int:
    kept = head + ([_marker(total - len(head) - len(tail))] if total > len(head) + len(tail) else []) + tail
    return len("\n".join(kept).encode("utf-8"))


def _fit_bytes(head: list[str], tail: list[str], total: int) -> tuple[list[str], list[str], bool]:
    """Trim head and tail further until the joined text fits `MAX_BYTES`.

    60/40 head/tail, because the invocation and the first error matter more than
    the summary. A single line longer than the whole budget is cut mid-line —
    the alternative is emitting nothing but a marker, and a visibly cut line is
    more useful than an empty command block.

    `tail` is empty when the line cap did not fire, which is the common case for
    a command that printed 300 very long lines. The tail then has to be drawn
    from the same list as the head, with an index guard so no line is shown
    twice — losing the last lines of a failing command would throw away the
    traceback, which is the part worth keeping.
    """
    room = max(0, MAX_BYTES - len(_marker(total).encode("utf-8")) - 2)
    head_room = int(room * 0.6)
    tail_room = room - head_room
    contiguous = not tail
    tail_src = head if contiguous else tail

    kept_head: list[str] = []
    used = 0
    for line in head:
        size = len(line.encode("utf-8")) + 1
        if used + size > head_room:
            break
        kept_head.append(line)
        used += size

    floor = len(kept_head) if contiguous else 0
    kept_tail: list[str] = []
    used = 0
    for idx in range(len(tail_src) - 1, floor - 1, -1):
        size = len(tail_src[idx].encode("utf-8")) + 1
        if used + size > tail_room:
            break
        kept_tail.insert(0, tail_src[idx])
        used += size

    if not kept_head and not kept_tail:
        first = head[0] if head else tail[0]
        kept_head = [first.encode("utf-8")[:room].decode("utf-8", errors="ignore")]
        return kept_head, kept_tail, True
    return kept_head, kept_tail, False


# --------------------------------------------------------------------------
# Failure classification — a rule table, never a model call
# --------------------------------------------------------------------------

def classify_failure(argv: Sequence[str], exit_code: int, out: str) -> tuple[str, str | None]:
    """-> (broken, hypothesis|None). A RULE TABLE, never a model call.

    This is the **only** producer of `command.hypothesis` (decision #26). A
    `hyp:<cmd-id>` narrate unit would not break non-negotiable #1 — it runs
    inside stage 3 — but it costs one model call, one cache entry and one
    parse-failure path per failing command, to restate a traceback the page
    already prints verbatim. `verify.py` tags whatever arrives as `inferred`
    regardless of which of us produced it.

    `broken` is the last output line matching `Error|Exception|error:|FAILED|
    assert`, else the last non-empty line, **verbatim**. It is never empty:
    `verify-contract.js:103` fails any command with `exit != 0` and no banner,
    and a command that failed silently still has an exit code to report.

    `argv` is part of the signature and is deliberately unused by the current
    rules — the table keys off output text, which is what makes it work for a
    command shape nobody anticipated.
    """
    lines = [ln for ln in out.replace("\r\n", "\n").split("\n") if ln.strip()]
    broken = ""
    for line in reversed(lines):
        if _BROKEN_RE.search(line):
            broken = line.strip()
            break
    if not broken and lines:
        broken = lines[-1].strip()
    if not broken:
        broken = f"exited {exit_code} with no output"

    hypothesis = None
    m = _MODULE_MISSING_RE.search(out)
    if m:
        hypothesis = (
            f"An import of `{m.group(1)}` could not be resolved: either the module "
            f"is missing from this environment or it does not exist in this repo."
        )
    return broken, hypothesis


# --------------------------------------------------------------------------
# The allowlist — deny by default
# --------------------------------------------------------------------------

def _is_python(argv0: str) -> bool:
    stem = Path(argv0).stem.lower()
    return stem == "py" or stem.startswith("python") or stem.startswith("pypy")


def _safe_rel(p: str) -> bool:
    """A repo-relative path that cannot escape the repo or name a device."""
    if not p or p.startswith(("/", "\\", "-")):
        return False
    if ":" in p or "\\" in p:
        return False
    return ".." not in Path(p).parts


def _shape(argv: list[str], repo_root: Path, cwd_key: str) -> str | None:
    """The name of the admitted argv shape, or None if this is not one of them.

    Exactly §3.8's four candidates and nothing else. Every shape requires
    `argv[0]` to be a Python interpreter, which is what keeps a `.pre-commit`
    `entry:` of `uvx ruff check .` — 11.4 MiB of first-run download and 219 KB
    of output — off the list without needing a denylist to name it.
    """
    if not argv or not _is_python(argv[0]):
        return None
    rest = argv[1:]

    if len(rest) == 2 and rest[0] == "-c" and _IMPORT_SMOKE_RE.fullmatch(rest[1]):
        return "import-smoke"

    if len(rest) == 3 and rest[0] == "-m" and rest[2] == "--help" and _DOTTED_RE.fullmatch(rest[1]):
        return "module-help"

    if rest[:4] == ["-m", "pytest", "--collect-only", "-q"] and all(_safe_rel(p) for p in rest[4:]):
        return "pytest-collect"

    if len(rest) == 1 and rest[0].endswith(".py") and _safe_rel(rest[0]):
        if (repo_root / cwd_key / rest[0]).is_file():
            return "repo-script"
        return None

    return None


def admit(candidate: dict, repo_root: Path) -> tuple[list[str] | None, str | None]:
    """-> (argv, None) if this candidate may run, else (None, reason).

    Deny-by-default. **Execute from an allowlist, never because a command was
    discovered.** Survey's job is to find candidates with provenance; deciding
    that one of them is safe to spawn is a separate decision made here, once.

    A candidate survey already marked `allowed=false` (the pytest import probe)
    keeps its own `deny_reason`, so §9 row 2 can list what was considered and
    why it was not run.
    """
    cmd = candidate.get("cmd") or " ".join(candidate.get("argv") or [])
    if not cmd:
        return None, "candidate carries no cmd string"

    if candidate.get("allowed") is False:
        return None, candidate.get("deny_reason") or "marked not-allowed by survey"

    cwd_key, reason = _cwd_key(candidate, repo_root)
    if reason:
        return None, reason

    argv = list(candidate.get("argv") or [])
    if not argv:
        try:
            argv = shlex.split(cmd, posix=True)
        except ValueError as e:
            return None, f"cmd string could not be parsed into an argv: {e}"
    if not argv:
        return None, "no argv could be derived from the candidate"

    argv0, reason = _resolve_argv0(argv[0])
    if reason:
        return None, reason
    argv = [argv0] + [str(a) for a in argv[1:]]

    if not (repo_root / cwd_key).is_dir():
        return None, f"working directory does not exist: {cwd_key}"

    if _shape(argv, repo_root, cwd_key) is None:
        # A script shape that failed only on existence gets the specific reason:
        # "Not executed" callouts that say why are the point of §8.4, and
        # "not on the allowlist" would be a misleading thing to say about a
        # command whose only problem is a path that moved.
        if (len(argv) == 2 and _is_python(argv[0])
                and argv[1].endswith(".py") and _safe_rel(argv[1])):
            return None, f"script not found in the repo: {argv[1]}"
        return None, ("not on the execution allowlist: the four admitted shapes are "
                      "`python -c \"import <pkg>\"`, `python -m <pkg> --help`, "
                      "`python -m pytest --collect-only -q <paths>` and "
                      "`python <script.py>` inside the repo")
    return argv, None


def _cwd_key(candidate: dict, repo_root: Path) -> tuple[str, str | None]:
    """The repo-relative cwd this run records, or a reason it cannot have one.

    `commands@1` records `cwd` repo-relative and `verify.py` merges command
    blocks on `(cmd, cwd)`, so this string has to match what compose put in the
    block. An absolute cwd is folded back through `textio.rel_key` — the one
    permitted producer of a repo-relative key — and one that escapes the repo is
    refused rather than silently producing a `..` key.
    """
    raw = str(candidate.get("cwd") or ".").strip() or "."
    p = Path(raw)
    if p.is_absolute():
        key = rel_key(p, repo_root)
        if key is None:
            return ".", f"working directory is outside the repo: {raw}"
        return key or ".", None
    if ".." in p.parts:
        return ".", f"working directory escapes the repo: {raw}"
    return p.as_posix(), None


def _resolve_argv0(argv0: str) -> tuple[str, str | None]:
    """An absolute executable path, or a reason we will not guess one.

    A bare `python` resolves to `sys.executable`, never to a PATH lookup: on
    this box `python` is the Microsoft Store shim and running it fails outright.
    Survey resolves the interpreter once per repo and stores the absolute path
    on the candidate; this is the fallback for a candidate that arrived without
    one, and it ends where §3.8's resolution order ends.
    """
    if not argv0:
        return "", "candidate has an empty argv[0]"
    p = Path(argv0)
    if p.is_absolute():
        if p.is_file():
            return str(p), None
        return argv0, f"{argv0} does not exist"
    if _is_python(argv0) and not p.suffix:
        return sys.executable, None
    found = shutil.which(argv0)
    if found:
        return found, None
    return argv0, f"could not resolve {argv0} to an executable"


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

def run_one(argv: Sequence[str], cwd: Path, *, cmd: str | None = None,
            cwd_key: str = ".", timeout: float = PER_COMMAND_TIMEOUT_S,
            env: str | None = None, kind: str = "", source: str = "") -> CommandResult:
    """Run one command and capture what it really did.

    `stderr=STDOUT` rather than two pipes, because capturing two streams and
    concatenating them **fabricates the interleaving** — real output has them
    interwoven, and a traceback split from the progress line above it is a
    different artifact than the one the command produced.

    Never `text=True`: it applies the locale codec, which is cp1252 on this box,
    and every em-dash and box-drawing character in real tool output becomes a
    replacement character. Decode utf-8 with `errors="replace"` instead, so a
    genuinely non-UTF-8 byte is visible as one damaged character rather than
    taking the generation down.

    Every failure path below records a real exit code. Never `exit: None` — the
    renderer tests truthiness, so it renders **green** while
    `verify-contract.js:103` demands a BROKEN banner, a self-contradictory page
    that still passes one gate. Never `exit: "0"` — that renders as failing.
    """
    argv = [str(a) for a in argv]
    display = cmd if cmd is not None else " ".join(argv)
    note = env or env_note(argv[0] if argv else None)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    forced: str | None = None
    timed_out = False
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            argv, shell=False, cwd=str(Path(cwd).resolve()),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, env=child_env(),
        )
        code, raw = p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        # Partial output is kept: what a hung command managed to print before it
        # was killed is usually the most informative thing about it.
        code, raw, timed_out = 124, e.output, True
        forced = f"timed out after {timeout:g} s and was killed"
    except FileNotFoundError:
        code, raw = 127, b""
        forced = f"{Path(argv[0]).name if argv else 'command'} not found on PATH"
    except PermissionError as e:
        code, raw = 126, b""
        forced = f"{Path(argv[0]).name if argv else 'command'} could not be executed: {e.strerror or e}"
    dur_ms = int(round((time.monotonic() - t0) * 1000))

    text = raw.decode("utf-8", errors="replace") if raw else ""
    out, truncated = truncate(text)
    if not out.strip():
        out = NO_OUTPUT

    broken = hypothesis = None
    if code != 0:
        broken, hypothesis = classify_failure(argv, code, out)
        if forced:
            broken = forced

    return CommandResult(
        cmd=display, argv=tuple(argv), cwd=cwd_key, exit=code, out=out,
        dur_ms=dur_ms, dur=display_duration(dur_ms), started=started,
        timed_out=timed_out, env=note, broken=broken, hypothesis=hypothesis,
        kind=kind, source=source, truncated=truncated,
    )


def display_duration(dur_ms: int) -> str:
    """`dur_ms` as the string the page prints. `"11.4 s"`, or `"62 ms"`.

    The fixture's format is one decimal and a unit, which reads as `0.0 s` for
    the 32 ms import smoke on the proving-ground repo — a real measurement
    rendered as if nothing was measured. Sub-second runs therefore print
    milliseconds. `dur_ms` remains the number; nothing parses `dur`.
    """
    if dur_ms < 1000:
        return f"{dur_ms} ms"
    return f"{dur_ms / 1000:.1f} s"


def run_commands(survey, repo_root, *, policy: str = "safe",
                 per_timeout: float = PER_COMMAND_TIMEOUT_S,
                 budget: float = TOTAL_BUDGET_S,
                 out_path: Path | None = None) -> dict:
    """Execute the admitted candidates and emit `trailhead/commands@1`.

    `survey` is `survey.json` (or, for a caller that has only the list, the
    `command_candidates` list itself). `policy` is the `--run-commands` flag:
    `none` is the stage panic switch and runs nothing at all. There is no `ask`
    policy — an interactive prompt in a build you may re-run on stage is the
    last thing you want.

    The total budget is checked **between** commands, never by shortening a
    command's own timeout: a run killed early because the budget was nearly
    spent would record `timed_out` for a command that was not actually hung,
    which is a false statement about the run. Worst case is therefore the budget
    plus one command's timeout.

    Every candidate appears in the output exactly once — under `runs` if it
    executed, under `skipped` with a real reason if it did not. Nothing is
    silently dropped, because the "Not executed" callout naming what was
    considered is part of the honesty story, not an omission.
    """
    candidates = survey.get("command_candidates", []) if isinstance(survey, dict) else list(survey)
    root = Path(repo_root)
    note = env_note()

    runs: list[CommandResult] = []
    skipped: list[SkippedCommand] = []
    seen: set[tuple[str, str]] = set()
    t0 = time.monotonic()

    for cand in candidates:
        cmd = cand.get("cmd") or " ".join(cand.get("argv") or [])
        kind = cand.get("kind", "")
        source = cand.get("source", "")
        cwd_key, cwd_reason = _cwd_key(cand, root)

        def skip(reason: str) -> None:
            skipped.append(SkippedCommand(cmd=cmd or "(no cmd)", reason=reason,
                                          cwd=cwd_key, kind=kind, source=source))

        if policy != "safe":
            skip(f"command execution disabled (--run-commands {policy})")
            continue

        if cwd_reason:
            skip(cwd_reason)
            continue

        key = (cmd, cwd_key)
        if key in seen:
            skip("duplicate of an earlier candidate with the same cmd and cwd")
            continue
        seen.add(key)

        argv, reason = admit(cand, root)
        if reason:
            skip(reason)
            continue

        if time.monotonic() - t0 >= budget:
            skip("generation command budget exhausted")
            continue

        runs.append(run_one(argv, root / cwd_key, cmd=cmd, cwd_key=cwd_key,
                            timeout=per_timeout, kind=kind, source=source))

    doc = {
        "contract": CONTRACT,
        "env": note,
        "limits": {"per_command_s": per_timeout, "budget_s": budget, "policy": policy},
        "runs": [r.to_dict() for r in runs],
        "skipped": [s.to_dict() for s in skipped],
    }
    if out_path is not None:
        write_json(Path(out_path), doc)
    return doc


#: The CLI stage driver spells this stage `commands`; the flag is
#: `--run-commands`. `run` is kept as the short alias so a caller that reached
#: for the obvious name gets the right function instead of an AttributeError.
run = run_commands


def write_json(path: Path, doc: dict) -> Path:
    """Write an artifact atomically, UTF-8, LF. Never a half-written JSON file.

    A run interrupted mid-write would otherwise leave a `commands.json` that
    parses as far as it goes and then does not, and the stage that reads it
    fails three stages downstream with nothing pointing back here.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    return path
