"""The command runner — real execution, real capture.

Non-negotiable #4 is the reason this file spawns real child processes instead of
mocking `subprocess`. A mocked runner proves the code arranges its own fields
correctly and proves nothing about the thing that matters: that the exit code,
the duration and the bytes in `out` came from a process that actually ran. Every
test below that asserts a capture runs `sys.executable` for real.

The tests are slow by unit-test standards — a few seconds, mostly interpreter
start-up and one deliberate 0.75 s timeout. That is the price of testing the
non-negotiable rather than testing a mock of it.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_runner -v
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

from trailhead import runner

#: The interpreter running the tests. Absolute, real, and the same shape survey
#: puts on a candidate — never a bare "python", which on this box is the
#: Microsoft Store shim.
PY = sys.executable


def tiny_repo(tmp: str) -> Path:
    """A three-file repo that produces one passing and one failing command.

    `pkg` imports cleanly, so `python -c "import pkg"` exits 0. It has no
    `__main__.py`, so `python -m pkg --help` fails for a real reason — the same
    shape as the proving-ground repo's broken console script, in miniature.
    """
    root = Path(tmp)
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tools").mkdir()
    (root / "tools" / "hello.py").write_text(
        "print('hello from a repo script')\n", encoding="utf-8")
    return root


def candidate(cmd, argv, cwd=".", kind="run", source="test"):
    return {"cmd": cmd, "argv": argv, "cwd": cwd, "kind": kind,
            "source": source, "confidence": "high"}


class RealCapture(unittest.TestCase):
    """Everything in a command block came from a process that really ran.

    `run_one` is the execution primitive and does not consult the allowlist —
    that gate lives in `admit` and is applied by `run_commands`. These tests
    call the primitive directly so they can exercise capture paths (a hang, a
    missing binary, non-ASCII output) that no admitted shape produces.
    """

    def test_exit_code_and_duration_are_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = runner.run_one([PY, "-c", "print('hello from a real child')"], Path(tmp))

        self.assertEqual(r.exit, 0)
        self.assertIs(type(r.exit), int)          # never "0", never None
        self.assertIn("hello from a real child", r.out)
        self.assertFalse(r.timed_out)
        self.assertGreater(r.dur_ms, 0)           # a process start is not free
        self.assertTrue(r.dur.endswith(("ms", " s")), r.dur)
        self.assertTrue(r.started.endswith("Z"), r.started)
        self.assertIn("captured ", r.env)
        self.assertIsNone(r.broken)

    def test_the_duration_is_measured_not_invented(self):
        # A command that sleeps a known time must report at least that time.
        # This is what makes dur_ms a measurement rather than a decoration.
        with tempfile.TemporaryDirectory() as tmp:
            wall = time.monotonic()
            r = runner.run_one([PY, "-c", "import time; time.sleep(0.4)"], Path(tmp))
            elapsed_ms = (time.monotonic() - wall) * 1000

        self.assertGreaterEqual(r.dur_ms, 400)
        self.assertLessEqual(r.dur_ms, elapsed_ms + 50)
        self.assertEqual(r.dur, runner.display_duration(r.dur_ms))

    def test_a_sub_second_run_does_not_display_as_zero(self):
        # The fixture's one-decimal format renders the real 32 ms import smoke
        # on the proving-ground repo as "0.0 s", which reads as a placeholder.
        self.assertEqual(runner.display_duration(32), "32 ms")
        self.assertEqual(runner.display_duration(999), "999 ms")
        self.assertEqual(runner.display_duration(2118), "2.1 s")
        self.assertEqual(runner.display_duration(11400), "11.4 s")

    def test_failing_command_always_carries_broken(self):
        # verify-contract.js:103 fails any command with exit != 0 and no banner.
        with tempfile.TemporaryDirectory() as tmp:
            r = runner.run_one(
                [PY, "-c", "import totally_missing_module_xyz"], Path(tmp))

        self.assertEqual(r.exit, 1)
        self.assertIn("ModuleNotFoundError", r.out)     # the real traceback
        self.assertTrue(r.broken)
        self.assertIn("ModuleNotFoundError", r.broken)
        self.assertIn("totally_missing_module_xyz", r.hypothesis)
        self.assertIn("broken", r.to_dict())

    def test_a_failing_command_is_reported_not_swallowed(self):
        # The failure has to survive the whole run_commands path, not just
        # run_one: a red command block is the most convincing thing in the
        # artifact and the pipeline must not quietly drop it.
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            doc = runner.run_commands(
                {"command_candidates": [
                    candidate('python -m pkg --help', [PY, "-m", "pkg", "--help"])]},
                root)

        self.assertEqual(len(doc["runs"]), 1)
        run = doc["runs"][0]
        self.assertNotEqual(run["exit"], 0)
        self.assertTrue(run["broken"])
        self.assertNotEqual(run["out"], runner.NO_OUTPUT)
        self.assertIn("pkg", run["out"])

    def test_silent_command_gets_the_no_output_placeholder_but_keeps_its_real_exit(self):
        # The only synthesised string in a command block. `exit` stays real, so
        # a silent failure still renders red with its true code.
        with tempfile.TemporaryDirectory() as tmp:
            quiet = runner.run_one([PY, "-c", "pass"], Path(tmp))
            loud = runner.run_one([PY, "-c", "raise SystemExit(3)"], Path(tmp))

        self.assertEqual(quiet.exit, 0)
        self.assertEqual(quiet.out, "(no output)")
        self.assertEqual(loud.exit, 3)
        self.assertEqual(loud.out, "(no output)")
        self.assertTrue(loud.broken)                   # never an empty banner

    def test_non_ascii_output_survives_on_windows(self):
        # The child prints from ASCII source, so this tests the capture path and
        # not argv encoding. Without PYTHONIOENCODING/PYTHONUTF8 in the child
        # env the console codec here is cp1252 and the tick becomes a "?".
        with tempfile.TemporaryDirectory() as tmp:
            r = runner.run_one(
                [PY, "-c", "print('caf\\u00e9 \\u2014 \\u2713 \\u6c49\\u5b57')"],
                Path(tmp))

        self.assertEqual(r.exit, 0)
        self.assertIn("café — ✓ 汉字", r.out)

    def test_timeout_reports_124_and_never_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = runner.run_one(
                [PY, "-c", "print('before the hang', flush=True); "
                           "import time; time.sleep(30)"],
                Path(tmp), timeout=0.75)

        self.assertEqual(r.exit, 124)
        self.assertIs(type(r.exit), int)
        self.assertTrue(r.timed_out)
        self.assertIn("timed out", r.broken)
        self.assertGreaterEqual(r.dur_ms, 700)
        self.assertLess(r.dur_ms, 20000)               # it really was killed
        self.assertIn("before the hang", r.out)        # partial output kept

    def test_missing_executable_reports_127(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = runner.run_one(
                [str(Path(tmp) / "no-such-binary.exe"), "--help"], Path(tmp))

        self.assertEqual(r.exit, 127)
        self.assertIn("not found on PATH", r.broken)
        self.assertEqual(r.out, "(no output)")
        self.assertTrue(r.env)                         # still a real env note


class Truncation(unittest.TestCase):
    """400 lines first, then 8192 bytes, both with an explicit marker."""

    def test_short_output_is_left_alone(self):
        self.assertEqual(runner.truncate("alpha\nbeta\n"), ("alpha\nbeta", False))

    def test_empty_output_stays_empty_here(self):
        # The `(no output)` placeholder is applied by run_one, not by truncate:
        # a pure function that invents content for its own empty input is a
        # surprise waiting to happen in the byte accounting.
        self.assertEqual(runner.truncate(""), ("", False))

    def test_long_output_is_capped_by_lines_then_by_bytes(self):
        text = "\n".join(f"line {i}" for i in range(2000))

        out, truncated = runner.truncate(text)
        lines = out.split("\n")

        self.assertTrue(truncated)
        self.assertLessEqual(len(lines), runner.MAX_LINES + 1)
        self.assertLessEqual(len(out.encode("utf-8")), runner.MAX_BYTES)
        self.assertEqual(lines[0], "line 0")           # head kept
        self.assertEqual(lines[-1], "line 1999")       # tail kept
        marker = [ln for ln in lines if "lines elided" in ln]
        self.assertEqual(len(marker), 1, marker)
        elided = int(marker[0].split()[1])
        self.assertEqual(elided, 2000 - (len(lines) - 1))

    def test_output_inside_the_line_cap_is_still_capped_by_bytes(self):
        # 300 lines of 200 chars never trips the 400-line cap and is still 60 KB.
        text = "\n".join(f"{i:03d} " + "x" * 196 for i in range(300))

        out, truncated = runner.truncate(text)

        self.assertTrue(truncated)
        self.assertLessEqual(len(out.encode("utf-8")), runner.MAX_BYTES)
        self.assertTrue(out.startswith("000 "))
        self.assertTrue(out.endswith("x"))
        self.assertIn("lines elided", out)
        # The tail is drawn from the same list as the head when the line cap did
        # not fire — losing it would throw away the traceback.
        self.assertIn("299 ", out)

    def test_a_single_enormous_line_still_fits_the_byte_cap(self):
        out, truncated = runner.truncate("z" * 40000)

        self.assertTrue(truncated)
        self.assertLessEqual(len(out.encode("utf-8")), runner.MAX_BYTES)
        self.assertIn("lines elided", out)

    def test_a_real_command_emitting_two_thousand_lines_is_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = runner.run_one(
                [PY, "-c", "\n".join(["for i in range(2000):",
                                      "    print('output line %d' % i)"])],
                Path(tmp))

        self.assertEqual(r.exit, 0)
        self.assertTrue(r.truncated)
        self.assertLessEqual(len(r.out.encode("utf-8")), runner.MAX_BYTES)
        self.assertIn("output line 0", r.out)
        self.assertIn("output line 1999", r.out)
        self.assertIn("lines elided", r.out)


class ClassifyFailure(unittest.TestCase):
    """A rule table. No model, and the only producer of `hypothesis`."""

    def test_broken_is_the_last_matching_line_verbatim(self):
        out = ("running checks\n"
               "ValueError: bad thing\n"
               "  File \"x.py\", line 3\n"
               "AssertionError: worse thing\n"
               "done\n")

        broken, hypothesis = runner.classify_failure(["x"], 1, out)

        self.assertEqual(broken, "AssertionError: worse thing")
        self.assertIsNone(hypothesis)

    def test_broken_falls_back_to_the_last_non_empty_line(self):
        broken, _ = runner.classify_failure(["x"], 2, "collected 69 items\n\n\n")

        self.assertEqual(broken, "collected 69 items")

    def test_broken_is_never_empty_even_with_no_output(self):
        # verify-contract.js:103 fails a failing command with no banner, so an
        # empty string here would be a gate failure on a silent crash.
        broken, _ = runner.classify_failure(["x"], 9, "")

        self.assertTrue(broken)
        self.assertIn("9", broken)

    def test_hypothesis_is_emitted_only_for_a_missing_module(self):
        trace = ("Traceback (most recent call last):\n"
                 "  File \"<string>\", line 1, in <module>\n"
                 "ModuleNotFoundError: No module named 'volforecast.constants'\n")

        _, hypothesis = runner.classify_failure(["py"], 1, trace)
        _, none = runner.classify_failure(["py"], 1, "make: *** [lint] Error 1\n")

        self.assertIn("volforecast.constants", hypothesis)
        self.assertIsNone(none)


class Allowlist(unittest.TestCase):
    """Deny by default. Execution follows the allowlist, never discovery."""

    def test_the_four_admitted_shapes_are_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            (root / "tests").mkdir()
            shapes = [
                candidate('python -c "import pkg"', [PY, "-c", "import pkg"]),
                candidate("python -m pkg --help", [PY, "-m", "pkg", "--help"]),
                candidate("python -m pytest --collect-only -q tests",
                          [PY, "-m", "pytest", "--collect-only", "-q", "tests"],
                          kind="test"),
                candidate("python tools/hello.py", [PY, "tools/hello.py"], kind="lint"),
            ]

            for cand in shapes:
                argv, reason = runner.admit(cand, root)
                with self.subTest(cmd=cand["cmd"]):
                    self.assertIsNone(reason)
                    self.assertEqual(argv[0], PY)

    def test_a_command_not_on_the_allowlist_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            denied = [
                candidate("uvx ruff check .", ["uvx", "ruff", "check", "."], kind="lint"),
                candidate("uv sync", ["uv", "sync"], kind="setup"),
                candidate("rm -rf /", ["rm", "-rf", "/"]),
                # Close to shape 1 but not it — arbitrary code after the import.
                candidate('python -c "import os; os.remove(1)"',
                          [PY, "-c", "import os; os.remove(1)"]),
                # Close to shape 2 but not it — an argument that is not --help.
                candidate("python -m pkg --write-everything",
                          [PY, "-m", "pkg", "--write-everything"]),
            ]

            for cand in denied:
                argv, reason = runner.admit(cand, root)
                with self.subTest(cmd=cand["cmd"]):
                    self.assertIsNone(argv)
                    self.assertIn("allowlist", reason)

    def test_a_script_that_is_not_there_is_skipped_not_fabricated_as_127(self):
        # A 127 here would be a false sentence about a file the repo never had.
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)

            argv, reason = runner.admit(
                candidate("python tools/absent.py", [PY, "tools/absent.py"], kind="lint"),
                root)

            self.assertIsNone(argv)
            self.assertIn("script not found", reason)

    def test_a_denied_candidate_is_never_executed(self):
        # The strongest form of this test: the denied command would leave a file
        # behind. Deny-by-default means the file must not exist afterwards.
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            sentinel = root / "sentinel.txt"
            src = f"import pathlib; pathlib.Path(r'{sentinel}').write_text('ran')"

            doc = runner.run_commands(
                {"command_candidates": [
                    candidate('python -c "import pathlib; ..."', [PY, "-c", src])]},
                root)

            self.assertFalse(sentinel.exists())
            self.assertEqual(doc["runs"], [])
            self.assertEqual(len(doc["skipped"]), 1)
            self.assertIn("allowlist", doc["skipped"][0]["reason"])

    def test_a_candidate_survey_already_denied_keeps_its_own_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            cand = candidate("python -m pytest --collect-only -q tests",
                             [PY, "-m", "pytest", "--collect-only", "-q", "tests"],
                             kind="test")
            cand["allowed"] = False
            cand["deny_reason"] = "pytest not importable under the resolved interpreter"

            argv, reason = runner.admit(cand, root)

            self.assertIsNone(argv)
            self.assertEqual(reason, "pytest not importable under the resolved interpreter")

    def test_a_cwd_outside_the_repo_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            cand = candidate('python -c "import pkg"', [PY, "-c", "import pkg"],
                             cwd="../elsewhere")

            argv, reason = runner.admit(cand, root)

            self.assertIsNone(argv)
            self.assertIn("escapes the repo", reason)


class CommandsJson(unittest.TestCase):
    """`trailhead/commands@1` — the fields the gates read, on a real run."""

    def test_every_emitted_run_carries_the_fields_the_gate_demands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            doc = runner.run_commands(
                {"command_candidates": [
                    candidate('python -c "import pkg"', [PY, "-c", "import pkg"]),
                    candidate("python -m pkg --help", [PY, "-m", "pkg", "--help"]),
                    candidate("python tools/hello.py", [PY, "tools/hello.py"], kind="lint"),
                    candidate("uvx ruff check .", ["uvx", "ruff", "check", "."], kind="lint"),
                ]},
                root, out_path=root / ".trailhead" / "commands.json")

            written = json.loads((root / ".trailhead" / "commands.json")
                                 .read_text(encoding="utf-8"))

        self.assertEqual(doc["contract"], "trailhead/commands@1")
        self.assertEqual(written, doc)                       # round-trips
        self.assertTrue(doc["env"].startswith("captured "))
        self.assertEqual(len(doc["runs"]), 3)
        self.assertEqual(len(doc["skipped"]), 1)

        exits = [r["exit"] for r in doc["runs"]]
        self.assertEqual(exits[0], 0)                        # import smoke passes
        self.assertNotEqual(exits[1], 0)                     # no __main__ to run

        for r in doc["runs"]:
            with self.subTest(cmd=r["cmd"]):
                # check-fixtures.js:125-128 and verify-contract.js:120-121.
                self.assertIs(type(r["exit"]), int)
                self.assertIsInstance(r["dur_ms"], int)
                self.assertIsInstance(r["dur"], str)
                self.assertTrue(r["out"].strip())
                self.assertTrue(r["env"])
                self.assertTrue(r["started"])
                self.assertIn(r["cwd"], (".", "src"))
                self.assertNotIn("\\", r["cwd"])
                if r["exit"] != 0:
                    self.assertTrue(r["broken"])
                else:
                    self.assertNotIn("broken", r)            # never a null banner

    def test_policy_none_executes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            doc = runner.run_commands(
                {"command_candidates": [
                    candidate('python -c "import pkg"', [PY, "-c", "import pkg"])]},
                root, policy="none")

        self.assertEqual(doc["runs"], [])
        self.assertIn("disabled", doc["skipped"][0]["reason"])

    def test_the_total_budget_stops_the_remaining_candidates(self):
        # Budget is checked between commands, so the first candidate starts and
        # everything after it is skipped with a real reason rather than being
        # dropped silently.
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            doc = runner.run_commands(
                {"command_candidates": [
                    candidate('python -c "import pkg"', [PY, "-c", "import pkg"]),
                    candidate('python -c "import os"', [PY, "-c", "import os"]),
                    candidate('python -c "import sys"', [PY, "-c", "import sys"]),
                ]},
                root, budget=0.001)

        exhausted = [s for s in doc["skipped"]
                     if s["reason"] == "generation command budget exhausted"]
        self.assertLessEqual(len(doc["runs"]), 1)
        self.assertGreaterEqual(len(exhausted), 2)
        self.assertEqual(len(doc["runs"]) + len(doc["skipped"]), 3)

    def test_a_duplicate_candidate_is_skipped_not_run_twice(self):
        # verify.py merges command blocks on (cmd, cwd); two runs under one key
        # would make that merge a coin flip.
        with tempfile.TemporaryDirectory() as tmp:
            root = tiny_repo(tmp)
            cand = candidate('python -c "import pkg"', [PY, "-c", "import pkg"])
            doc = runner.run_commands({"command_candidates": [cand, dict(cand)]}, root)

        self.assertEqual(len(doc["runs"]), 1)
        self.assertIn("duplicate", doc["skipped"][0]["reason"])

    def test_a_skipped_candidate_carries_no_results_to_be_wrong_about(self):
        skipped = runner.SkippedCommand("uv sync", "not on the execution allowlist")

        self.assertNotIn("exit", skipped.to_dict())
        self.assertNotIn("out", skipped.to_dict())
        self.assertNotIn("dur", skipped.to_dict())


if __name__ == "__main__":
    unittest.main()
