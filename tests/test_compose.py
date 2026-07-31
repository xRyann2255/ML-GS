"""Stage 3 NARRATE — the deterministic half (compose).

compose decides which stops exist, what blocks they hold, and what a stop does
when the repo will not cooperate. None of that involves a model, so all of it is
testable, and three of its failure modes are invisible in a browser:

  * a tenth block type renders NOTHING and both gates still pass;
  * a stop with no blocks, or a callout with no title, renders `undefined` on
    exactly the stops that carry the honest-degradation story;
  * a checkpoint stop with no checkpoint auto-ticks itself complete.

So these tests are mostly about what compose refuses to emit. The `restored`
trace fixture is checked against the files on disk, because it is the hour-4
pivot-rule safety net and a stale line range there is a gate failure on the one
stop the pitch turns on.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_compose -v
"""
import copy
import json
import re
import unittest
from pathlib import Path
from unittest import mock

from trailhead import compose
from trailhead.textio import read_source

HACKATHON = Path(__file__).resolve().parents[1]
RESTORED = HACKATHON / "restored"


def _cp(prompt, options, answer=1):
    return {"kind": "single", "prompt": prompt, "options": options,
            "answer": answer, "provenance": "survey.json → edges",
            "explanation": "Because the import graph says so."}


#: One synthetic repo, shaped like `restored` after stage 2: no git history, a
#: broken declared entry point, and a test candidate that was denied rather than
#: run. Every degradation test starts from a copy of this.
SURVEY = {
    "contract": "trailhead/survey@1",
    "repo": {"name": "restored", "commit": "nogit-4b17c2e9",
             "surveyed_at": "2026-07-30T18:40:11Z"},
    "stats": {"files": 1125, "py_files": 455, "loc": 96000, "modules": 364},
    "roots": {"import_roots": ["src"], "test_roots": ["src/tests"],
              "declared_packages": ["volforecast"]},
    "files": [
        {"path": "src/volforecast/data/__init__.py", "module": "volforecast.data",
         "loc": 8,
         "doc": "Data ingestion and cache layout. Raw parquet lands here."},
        {"path": "src/volforecast/cli/__init__.py", "module": "volforecast.cli",
         "loc": 4},
        {"path": "src/tests/test_ohlcv.py", "module": None, "loc": 380},
        {"path": "src/tests/unit/test_paths.py", "module": None, "loc": 120},
        {"path": "src/tests_extra/not_under_a_test_root.py", "module": None,
         "loc": 10},
    ],
    "modules": {
        "volforecast.data": {"path": "src/volforecast/data", "files": 21,
                             "loc": 9195, "commits": None,
                             "top": [{"path": "src/volforecast/data/ohlcv.py",
                                      "fan_in": 12}]},
        "volforecast.cli": {"path": "src/volforecast/cli", "files": 28,
                            "loc": 7342, "commits": None,
                            "top": [{"path": "src/volforecast/cli/ingest.py",
                                     "fan_in": 5}]},
        "volforecast.utils": {"path": "src/volforecast/utils", "files": 7,
                              "loc": 1552, "commits": None,
                              "top": [{"path": "src/volforecast/utils/paths.py",
                                       "fan_in": 34}]},
    },
    "edges": [{"a": "volforecast.cli", "b": "volforecast.data", "n": 31}],
    "entry_points": [{"kind": "console_script", "name": "volforecast",
                      "file": "src/pyproject.toml", "line": 53,
                      "target": "volforecast.__main__:main"}],
    "command_candidates": [
        {"cmd": 'python -c "import volforecast"', "kind": "run", "cwd": "src",
         "source": "src/pyproject.toml:50", "confidence": "high"},
        {"cmd": "python -m volforecast --help", "kind": "run", "cwd": "src",
         "source": "src/pyproject.toml:53", "confidence": "high"},
        {"cmd": "python -m pytest --collect-only -q tests", "kind": "test",
         "cwd": "src", "source": "src/pyproject.toml:79", "allowed": False,
         "deny_reason": "pytest not importable under the resolved interpreter"},
    ],
    "checkpoints": {
        "cp-a1": _cp("Which module is imported by the most others?",
                     ["registry", "paths", "ohlcv", "_base"]),
        "cp-a2": _cp("Which file does the console script start in?",
                     ["__main__.py", "ingest.py", "paths.py", "ohlcv.py"]),
        "cp-c1": {"kind": "order", "prompt": "Order these four packages.",
                  "options": ["cli", "features", "data", "utils"],
                  "answer": [1, 2, 3, 4],
                  "provenance": "map.json → node column index",
                  "explanation": "Column order is the import DAG."},
        "cp-c2": _cp("Which file does ingest-ohlcv write through?",
                     ["ohlcv.py", "vol", "__main__.py", "ingest_ohlcv.py"], 0),
    },
    "churn": {"state": "GIT_UNTRACKED", "available": False,
              "reason": "This path has no tracked history in the enclosing "
                        "repository.",
              "substitute": "fan_in", "by_file": {}, "committers": {}},
    "dangling": [{"target": "volforecast.constants", "n": 120,
                  "sites": [{"file": "src/volforecast/__main__.py", "line": 3},
                            {"file": "src/volforecast/cli/__init__.py",
                             "line": 2}]}],
    "walk": {"scanned": 1125, "excluded_dirs": 15, "skipped": []},
    "parse_failures": [],
    "text_files": ["src/pyproject.toml", "vol"],
}

MAP = {
    "contract": "trailhead/map@1",
    "nodes": [
        {"id": "n-cli", "label": "cli", "loc": 7342, "files": 28, "x": 8,
         "y": 10, "w": 142, "why": "…", "top": ["ingest.py — fan-in 5"]},
        {"id": "n-data", "label": "data", "loc": 9195, "files": 21, "x": 260,
         "y": 10, "w": 142, "why": "…", "top": ["ohlcv.py — fan-in 12"]},
        {"id": "n-utils", "label": "utils", "loc": 1552, "files": 7, "x": 512,
         "y": 10, "w": 142, "why": "…", "top": ["paths.py — fan-in 34"]},
    ],
    "edges": [{"a": "n-cli", "b": "n-data", "n": 31},
              {"a": "n-data", "b": "n-utils", "n": 9}],
    "diagnostics": {"modules_in": 364, "groups": 3, "edges_dropped_backward": 9},
}

COMMANDS = {
    "contract": "trailhead/commands@1",
    "env": "captured 2026-07-30, Windows 11, python 3.11.1",
    "runs": [
        {"cmd": 'python -c "import volforecast"', "cwd": "src", "exit": 0,
         "kind": "run", "source": "src/pyproject.toml:50",
         "dur_ms": 61, "dur": "0.1 s", "out": "(no output)", "timed_out": False},
        {"cmd": "python -m volforecast --help", "cwd": "src", "exit": 1,
         "kind": "run", "source": "src/pyproject.toml:53",
         "dur_ms": 166, "dur": "0.2 s", "timed_out": False,
         "out": "ModuleNotFoundError: No module named 'volforecast.cli.ingest_iv'",
         "broken": "ModuleNotFoundError: No module named "
                   "'volforecast.cli.ingest_iv'",
         "hypothesis": "__main__.py imports a cli module that is not on disk."},
    ],
    "skipped": [{"cmd": "python -m pytest --collect-only -q tests",
                 "cwd": "src", "kind": "test",
                 "source": "src/pyproject.toml:79",
                 "reason": "pytest not importable under the resolved "
                           "interpreter"}],
}


def _cite(file, quote):
    return {"file": file, "quote": quote, "focus": []}


NARRATION = {
    "five": {"claims": [
        {"text": f"Sentence {i}.", "status": "verified",
         "cite": _cite("src/volforecast/registry.py", "def get(name):\n    ...")}
        for i in range(1, 5)
    ] + [{"text": "It is not a trading system.", "status": "inferred"}]},
    "conv": {"claims": [{"text": "Errors are raised, never returned.",
                         "status": "inferred"}]},
    "green": {"claims": [
        {"text": "The package imports from the resolved source root.",
         "status": "verified",
         "cite": _cite("src/pyproject.toml", "[project]\nname = \"volforecast\"")}]},
}


def ctx(survey=None, mp=None, commands=None, narration=None, hops=None):
    """A Ctx over the synthetic repo. Every argument is deep-copied.

    Builders append to `ctx.degradations`, so a shared Ctx between two tests
    would make the §9 assertions order-dependent.
    """
    return compose.Ctx(
        copy.deepcopy(SURVEY if survey is None else survey),
        copy.deepcopy(MAP if mp is None else mp),
        copy.deepcopy(COMMANDS if commands is None else commands),
        copy.deepcopy(NARRATION if narration is None else narration),
        copy.deepcopy(compose.load_hops() if hops is None else hops),
    )


def blocks_of(tracks):
    return [b for t in tracks for s in t["stops"] for b in s["blocks"]]


def stops_of(tracks):
    return [s for t in tracks for s in t["stops"]]


class StopTable(unittest.TestCase):
    def test_every_stop_belongs_to_a_declared_track(self):
        keys = {k for k, _, _ in compose.TRACKS}

        self.assertTrue(all(s.track in keys for s in compose.STOP_TABLE))

    def test_stop_ids_are_unique_and_the_audit_stop_exists(self):
        ids = [s.id for s in compose.STOP_TABLE]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(compose.AUDIT_STOP, ids)

    def test_only_checkpoint_stops_are_allowed_to_drop(self):
        # A DROPped stop leaves a labelled gap in the audit callout. Every other
        # stop degrades in place, because §9's rule is that a stop is never
        # silently omitted.
        droppers = [s.id for s in compose.STOP_TABLE if s.on_fail == compose.DROP]

        self.assertEqual(droppers, ["cp-a", "cp-c"])

    def test_a_lede_is_specified_for_every_prose_stop(self):
        for spec in compose.STOP_TABLE:
            if spec.kind == "stop":
                self.assertIsNotNone(spec.lede, spec.id)


class BlockVocabulary(unittest.TestCase):
    """The renderer's dispatch has no default arm. An unknown type renders
    nothing, so the vocabulary here is closed and pinned. `@3` added `stats`.
    """

    def test_the_vocabulary_is_exactly_the_ten_renderable_types(self):
        self.assertEqual(
            compose.BLOCK_TYPES,
            frozenset(["prose", "excerpt", "command", "graph", "table",
                       "trace", "checkpoint", "callout", "ledger", "stats"]))

    def test_a_full_generation_emits_only_known_block_types(self):
        types = {b["type"] for b in blocks_of(compose.build_course(ctx()))}

        self.assertTrue(types <= compose.BLOCK_TYPES, types - compose.BLOCK_TYPES)

    def test_an_empty_generation_emits_only_known_block_types(self):
        bare = compose.Ctx({}, {}, {}, {}, [])

        types = {b["type"] for b in blocks_of(compose.build_course(bare))}

        self.assertTrue(types <= compose.BLOCK_TYPES, types - compose.BLOCK_TYPES)

    def test_build_course_refuses_a_block_type_the_renderer_cannot_draw(self):
        rogue = compose.StopSpec("rogue", "Rogue", "ORIENT", 1, "stop",
                                 compose._always,
                                 lambda c: [{"type": "timeline"}],
                                 compose.PLACEHOLDER, lambda c: "…")

        with mock.patch.object(compose, "STOP_TABLE", (rogue,)):
            with self.assertRaises(ValueError):
                compose.build_course(ctx())

    def test_a_callout_without_a_title_is_refused(self):
        # The renderer emits <b>${esc(b.title)}</b> unconditionally, so an empty
        # title prints the literal word `undefined`.
        with self.assertRaises(ValueError):
            compose.callout("info", "", "text")

    def test_a_callout_level_outside_the_three_is_refused(self):
        with self.assertRaises(ValueError):
            compose.callout("warning", "TITLE", "text")

    def test_a_short_table_row_is_refused(self):
        with self.assertRaises(ValueError):
            compose.table(["A", "B"], [["only one"]])


class BuildCourse(unittest.TestCase):
    def test_no_stop_is_ever_emitted_with_an_empty_blocks_array(self):
        for tracks in (compose.build_course(ctx()),
                       compose.build_course(compose.Ctx({}, {}, {}, {}, []))):
            for s in stops_of(tracks):
                self.assertTrue(s["blocks"], s["id"])

    def test_the_audit_stop_and_its_ledger_survive_an_empty_generation(self):
        tracks = compose.build_course(compose.Ctx({}, {}, {}, {}, []))

        ids = [s["id"] for s in stops_of(tracks)]
        self.assertIn(compose.AUDIT_STOP, ids)
        self.assertIn("ledger", [b["type"] for b in blocks_of(tracks)])

    def test_the_audit_stop_is_last(self):
        tracks = compose.build_course(ctx())

        self.assertEqual(stops_of(tracks)[-1]["id"], compose.AUDIT_STOP)

    def test_a_lede_is_present_on_stops_and_absent_on_checkpoints(self):
        # The frozen fixture does exactly this and the renderer treats `lede` as
        # optional; a rule demanding one everywhere rejects the reference
        # payload.
        for s in stops_of(compose.build_course(ctx())):
            if s["kind"] == "cp":
                self.assertNotIn("lede", s)
            else:
                self.assertTrue(s["lede"], s["id"])

    def test_every_stop_carries_a_kind_and_minutes(self):
        for s in stops_of(compose.build_course(ctx())):
            self.assertIn(s["kind"], ("stop", "cp"))
            self.assertIsInstance(s["minutes"], int)

    def test_a_checkpoint_stop_is_marked_cp_exactly_when_it_holds_one(self):
        # A stop not marked `cp` is auto-marked complete the instant it is drawn.
        for s in stops_of(compose.build_course(ctx())):
            holds = any(b["type"] == "checkpoint" for b in s["blocks"])

            self.assertEqual(holds, s["kind"] == "cp", s["id"])

    def test_track_minutes_are_track_constants_not_stop_sums(self):
        tracks = compose.build_course(ctx())
        orient = next(t for t in tracks if t["title"] == "ORIENT")

        self.assertEqual(orient["minutes"], 15)
        self.assertNotEqual(orient["minutes"],
                            sum(s["minutes"] for s in orient["stops"]))

    def test_claim_ids_are_unique_and_shaped_for_the_renderers_marker(self):
        # The marker label is `c.id.slice(-3)`, so ids shorter than that render
        # their whole selves; VERIFY renumbers, but never onto a collision.
        ids = [c["id"] for b in blocks_of(compose.build_course(ctx()))
               if b["type"] == "prose" for c in b["claims"]]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(re.fullmatch(r"c-\d{3,}", i) for i in ids), ids)

    def test_an_inferred_claim_carries_no_cite_at_all(self):
        for b in blocks_of(compose.build_course(ctx())):
            if b["type"] != "prose":
                continue
            for c in b["claims"]:
                if c["status"] == "inferred":
                    self.assertNotIn("cite", c)

    def test_the_conventions_stop_forces_every_claim_to_inferred(self):
        loud = copy.deepcopy(NARRATION)
        loud["conv"] = {"claims": [
            {"text": "The house style raises rather than returns None.",
             "status": "verified",
             "cite": _cite("src/volforecast/registry.py", "raise KeyError(name)")}]}

        tracks = compose.build_course(ctx(narration=loud))

        conv = next(s for s in stops_of(tracks) if s["id"] == "conv")
        claims = [c for b in conv["blocks"] if b["type"] == "prose"
                  for c in b["claims"]]
        self.assertTrue(claims)
        self.assertTrue(all(c["status"] == "inferred" for c in claims))
        self.assertTrue(all("cite" not in c for c in claims))

    def test_the_emitted_course_carries_no_line_numbers(self):
        # Non-negotiable #7, asserted the way check-fixtures.js:80 asserts it.
        text = json.dumps(compose.build_course(ctx()))

        self.assertIsNone(re.search(r'"(start|end)"\s*:\s*\d', text))

    def test_every_focus_string_is_a_substring_of_its_own_quote(self):
        # check-fixtures.js:96 on content, and the rule VERIFY resolves focus
        # lines with. A focus string that is not in its quote resolves to
        # nothing and silently highlights the wrong line.
        cited = []
        for b in blocks_of(compose.build_course(ctx())):
            if b["type"] == "prose":
                cited += [c["cite"] for c in b["claims"] if c.get("cite")]
            elif b["type"] == "trace":
                cited += [s["cite"] for s in b["steps"]]

        self.assertTrue(cited)
        for cite in cited:
            for f in cite.get("focus") or []:
                self.assertIn(f, cite["quote"])

    def test_the_green_command_is_not_repeated_on_the_setup_stop(self):
        tracks = compose.build_course(ctx())
        by_stop = {s["id"]: s for s in stops_of(tracks)}

        green = [b["cmd"] for b in by_stop["green"]["blocks"]
                 if b["type"] == "command"]
        setup = [b["cmd"] for b in by_stop["setup"]["blocks"]
                 if b["type"] == "command"]
        self.assertEqual(green, ['python -c "import volforecast"'])
        self.assertNotIn(green[0], setup)

    def test_a_command_block_carries_no_exit_code_or_output(self):
        # Non-negotiable #4 made structural: there is no field here in which a
        # fabricated result could travel. VERIFY merges the real capture.
        for b in blocks_of(compose.build_course(ctx())):
            if b["type"] == "command":
                self.assertEqual(set(b) - {"predict", "hypothesis"},
                                 {"type", "cmd", "cwd"})

    def test_a_command_prediction_never_ships_an_answer(self):
        for b in blocks_of(compose.build_course(ctx())):
            if b["type"] == "command" and "predict" in b:
                self.assertNotIn("answer", b)
                self.assertTrue(b["predict"].strip())


class DegradedGeneration(unittest.TestCase):
    """§9, row by row. Every row emits a LABELLED placeholder, never silence."""

    def test_row_1_no_entry_point_labels_the_trace_and_drops_checkpoint_c(self):
        sv = copy.deepcopy(SURVEY)
        sv["entry_points"] = []
        c = ctx(survey=sv)

        tracks = compose.build_course(c)

        by_stop = {s["id"]: s for s in stops_of(tracks)}
        self.assertNotIn("cp-c", by_stop)
        note = by_stop["trace"]["blocks"][0]
        self.assertEqual(note["type"], "callout")
        self.assertEqual(note["level"], "broken")
        self.assertIn("NO TRACEABLE ENTRY POINT", note["title"])
        self.assertNotIn("trace", [b["type"] for b in by_stop["trace"]["blocks"]])

    def test_row_1_also_fires_when_there_are_fewer_than_two_hops(self):
        c = ctx(hops=[])

        blocks = compose.build_trace(c)

        self.assertEqual([b["type"] for b in blocks], ["callout"])
        self.assertTrue(compose._fired(c, "no_trace"))

    def test_row_2_names_every_denied_test_candidate(self):
        c = ctx()

        blocks = compose.build_green(c)

        note = blocks[0]
        self.assertEqual(note["title"], "NO TEST COMMAND DETECTED")
        self.assertIn("pytest not importable", note["text"])
        # Rule 2: a passing non-test command is still shown, under a caption
        # that says plainly it is not a test suite.
        self.assertEqual(blocks[1]["type"], "command")
        self.assertIn("NOT A TEST SUITE", blocks[-1]["title"])

    def test_row_2_tells_the_truth_about_an_executed_failing_candidate(self):
        # The contradiction fix: when the runner actually RAN a test candidate
        # and it failed, the callout must describe the real result. Calling it
        # "not executed" while the setup stop shows the same command with a
        # real exit code is the page contradicting its own evidence.
        cmds = copy.deepcopy(COMMANDS)
        cmds["skipped"] = []
        cmds["runs"].append({"cmd": "python -m pytest --collect-only -q tests",
                             "cwd": "src", "exit": 2, "kind": "test",
                             "dur_ms": 912, "dur": "0.9 s", "timed_out": False,
                             "out": "ERROR: file or directory not found: tests"})

        blocks = compose.build_green(ctx(commands=cmds))

        note = blocks[0]
        self.assertEqual(note["title"], "NO TEST COMMAND DETECTED")
        self.assertIn("python -m pytest --collect-only -q tests was executed "
                      "and failed with exit 2, so there is no green test "
                      "command to hand you", note["text"])
        self.assertNotIn("not executed", note["text"])

    def test_a_timed_out_candidate_is_reported_as_executed_and_timed_out(self):
        # The runner records exit 124 and timed_out on a kill; "not executed"
        # would be false and "failed with exit 124" would bury the reason.
        cmds = copy.deepcopy(COMMANDS)
        cmds["skipped"] = []
        cmds["runs"].append({"cmd": "python -m pytest --collect-only -q tests",
                             "cwd": "src", "exit": 124, "kind": "test",
                             "dur_ms": 10000, "dur": "10.0 s",
                             "timed_out": True, "out": "(killed)"})

        note = compose.build_green(ctx(commands=cmds))[0]

        self.assertIn("was executed and timed out", note["text"])
        self.assertNotIn("not executed", note["text"])

    def test_an_unexecuted_candidate_keeps_the_not_executed_wording(self):
        # Only candidates with NO run record may be described as not executed.
        sv = copy.deepcopy(SURVEY)
        sv["command_candidates"].append(
            {"cmd": "tox -q", "kind": "test", "cwd": "src",
             "source": "src/tox.ini:1", "confidence": "low"})

        note = compose.build_green(ctx(survey=sv))[0]

        self.assertIn("tox -q: not executed", note["text"])

    def test_a_passing_test_command_takes_the_green_stop_without_a_caveat(self):
        # Rule 1, the happy path: an admitted kind=test run that passed.
        cmds = copy.deepcopy(COMMANDS)
        cmds["runs"].append({"cmd": "python -m pytest -q", "cwd": "src",
                             "exit": 0, "kind": "test", "dur": "2.5 s",
                             "dur_ms": 2500, "out": "69 passed",
                             "timed_out": False})

        blocks = compose.build_green(ctx(commands=cmds))

        self.assertEqual([b["type"] for b in blocks],
                         ["command", "prose", "callout"])
        self.assertEqual(blocks[0]["cmd"], "python -m pytest -q")

    def test_row_2_alone_when_nothing_passed(self):
        cmds = copy.deepcopy(COMMANDS)
        for r in cmds["runs"]:
            r["exit"] = 1

        blocks = compose.build_green(ctx(commands=cmds))

        self.assertEqual([b["type"] for b in blocks], ["callout"])

    def test_row_3_fires_when_every_setup_command_failed(self):
        cmds = copy.deepcopy(COMMANDS)
        for r in cmds["runs"]:
            r["exit"] = 1
            r["kind"] = "setup"

        blocks = compose.build_setup(ctx(commands=cmds))

        self.assertEqual(blocks[0]["level"], "broken")
        self.assertIn("DID NOT BUILD", blocks[0]["title"])
        # Every failure is still shown in full, as a real command block.
        self.assertEqual(sum(1 for b in blocks if b["type"] == "command"), 2)

    def test_the_map_prose_names_nodes_by_label_not_by_slug(self):
        # `n-cli` is an id the reader has never seen; the map draws the label.
        blocks = compose.build_map(ctx())

        text = " ".join(c["text"] for c in blocks[1]["claims"])
        self.assertIn("cli to data", text)
        self.assertNotIn("n-cli", text)

    def test_row_4_replaces_the_graph_with_a_table(self):
        thin = copy.deepcopy(MAP)
        thin["nodes"] = thin["nodes"][:2]
        thin["edges"] = []

        blocks = compose.build_map(ctx(mp=thin))

        self.assertNotIn("graph", [b["type"] for b in blocks])
        self.assertEqual(blocks[0]["title"], "TOO FEW MODULES TO DRAW A GRAPH")
        self.assertEqual(blocks[1]["type"], "table")

    def test_row_6_relabels_the_rank_column_and_says_why(self):
        c = ctx()

        blocks = compose.build_where(c)

        note, tbl = blocks[0], blocks[1]
        self.assertEqual(note["title"], "NO GIT HISTORY FOR THIS PATH")
        self.assertIn("fan-in", note["text"])
        # Never label fan-in as churn: the substitution has to be visible.
        self.assertIn("FAN-IN (NO GIT HISTORY)", tbl["columns"])
        self.assertNotIn("CHURN", tbl["columns"])
        self.assertNotIn("RECENT COMMITTERS", tbl["columns"])
        # The column prints the metric itself, never the row's 1..n rank.
        idx = tbl["columns"].index("FAN-IN (NO GIT HISTORY)")
        self.assertEqual([r[idx] for r in tbl["rows"]], ["34", "12", "5"])

    def test_a_repo_with_git_history_shows_real_commit_counts(self):
        sv = copy.deepcopy(SURVEY)
        sv["churn"] = {"state": "GIT_OK", "available": True, "reason": "",
                       "by_file": {},
                       "committers": {"src/volforecast/data": ["r.vincent"]}}
        for commits, m in zip((40, 30, 20), sv["modules"].values()):
            m["commits"] = commits

        blocks = compose.build_where(ctx(survey=sv))

        self.assertEqual(len(blocks), 1)
        tbl = blocks[0]
        self.assertIn("COMMITS", tbl["columns"])
        self.assertIn("RECENT COMMITTERS", tbl["columns"])
        # Actual counts, descending because they RANK the rows — not 1, 2, 3.
        idx = tbl["columns"].index("COMMITS")
        self.assertEqual([r[idx] for r in tbl["rows"]], ["40", "30", "20"])
        lede = compose._lede_where(ctx(survey=sv))
        self.assertIn("Ranked by commits", lede)

    def test_a_one_commit_snapshot_does_not_fake_a_churn_ranking(self):
        # Git churn available but degenerate: every module at the same count,
        # which is what a snapshot committed in one commit looks like, and no
        # committers anywhere. The old table printed rank numbers under a
        # COMMITS header and "n/a" down the committers column — history the
        # repo does not have, fabricated by the one page that promises none.
        sv = copy.deepcopy(SURVEY)
        sv["churn"] = {"state": "GIT_OK", "available": True, "reason": "",
                       "by_file": {}, "committers": {}}
        for m in sv["modules"].values():
            m["commits"] = 1

        blocks = compose.build_where(ctx(survey=sv))

        self.assertEqual(len(blocks), 1)
        tbl = blocks[0]
        self.assertIn("COMMITS", tbl["columns"])
        self.assertNotIn("RECENT COMMITTERS", tbl["columns"])
        idx = tbl["columns"].index("COMMITS")
        self.assertEqual([r[idx] for r in tbl["rows"]], ["1", "1", "1"])
        # Identical counts fall back to path order, and the lede says so
        # instead of promising a ranking the numbers cannot carry.
        self.assertEqual([r[0] for r in tbl["rows"]],
                         ["<code>src/volforecast/cli/</code>",
                          "<code>src/volforecast/data/</code>",
                          "<code>src/volforecast/utils/</code>"])
        lede = compose._lede_where(ctx(survey=sv))
        self.assertNotIn("Ranked by commits", lede)
        self.assertIn("identical for every module", lede)

    def test_a_committerless_history_drops_the_committers_column(self):
        # Distinct counts (a real ranking) but no committer data for any row:
        # the ranking stays, the column of eleven "n/a" cells goes.
        sv = copy.deepcopy(SURVEY)
        sv["churn"] = {"state": "GIT_OK", "available": True, "reason": "",
                       "by_file": {}, "committers": {}}
        for commits, m in zip((40, 30, 20), sv["modules"].values()):
            m["commits"] = commits

        tbl = compose.build_where(ctx(survey=sv))[0]

        self.assertIn("COMMITS", tbl["columns"])
        self.assertNotIn("RECENT COMMITTERS", tbl["columns"])

    def test_row_7_labels_a_stop_whose_unit_never_narrated(self):
        blocks = compose.build_five(ctx(narration={}))

        self.assertEqual([b["type"] for b in blocks], ["callout"])
        self.assertEqual(blocks[0]["title"], "NARRATION BUDGET REACHED")

    def test_row_8_records_a_dropped_stop_for_the_audit_callout(self):
        sv = copy.deepcopy(SURVEY)
        del sv["checkpoints"]["cp-a2"]
        c = ctx(survey=sv)

        tracks = compose.build_course(c)

        self.assertNotIn("cp-a", [s["id"] for s in stops_of(tracks)])
        rows = [d for d in c.degradations if d["code"] == "stop_dropped"]
        self.assertEqual([r["stop"] for r in rows], ["cp-a"])
        audit = next(s for s in stops_of(tracks) if s["id"] == "audit")
        titles = [b.get("title") for b in audit["blocks"]]
        self.assertIn("STOPS NOT GENERATED", titles)

    def test_a_thin_option_pool_drops_the_checkpoint_rather_than_padding_it(self):
        # Never render a placeholder quiz, and never invent a distractor: this
        # artifact's whole claim is that it contains no fabrication.
        sv = copy.deepcopy(SURVEY)
        sv["checkpoints"]["cp-a1"]["options"] = ["registry", "paths"]

        tracks = compose.build_course(ctx(survey=sv))

        self.assertNotIn("cp-a", [s["id"] for s in stops_of(tracks)])

    def test_the_audit_stop_states_what_the_tool_did_not_read(self):
        tracks = compose.build_course(ctx())

        audit = next(s for s in stops_of(tracks) if s["id"] == "audit")
        scope = next(b for b in audit["blocks"]
                     if b.get("title") == "WHAT THIS PAGE DID NOT READ")
        self.assertIn("ast", scope["text"])
        self.assertIn("120 import statements", scope["text"])


class Ledes(unittest.TestCase):
    """A lede is a factual sentence on a surface with no claim marker."""

    def test_a_degraded_trace_stop_does_not_promise_hops_it_has_not_got(self):
        sv = copy.deepcopy(SURVEY)
        sv["entry_points"] = []

        tracks = compose.build_course(ctx(survey=sv, hops=[]))

        trace = next(s for s in stops_of(tracks) if s["id"] == "trace")
        self.assertIn("no traceable entry point", trace["lede"])
        self.assertNotIn("hops, each one a real line range", trace["lede"])

    def test_a_degraded_map_stop_does_not_invite_a_click_on_a_missing_graph(self):
        thin = copy.deepcopy(MAP)
        thin["nodes"] = thin["nodes"][:1]

        tracks = compose.build_course(ctx(mp=thin))

        mp = next(s for s in stops_of(tracks) if s["id"] == "map")
        self.assertNotIn("Click any module", mp["lede"])

    def test_a_repo_with_nothing_runnable_says_so_rather_than_promising_green(self):
        tracks = compose.build_course(ctx(commands={}))

        green = next(s for s in stops_of(tracks) if s["id"] == "green")
        self.assertIn("no green command", green["lede"])

    def test_counts_of_one_are_not_pluralised(self):
        # Every degraded path is the path where n == 1, and "1 modules" on the
        # audit stop undermines the one page whose subject is rigour.
        self.assertEqual(compose._plural(1, "command"), "1 command")
        self.assertEqual(compose._plural(2, "command"), "2 commands")
        self.assertEqual(compose._plural(1, "directory", "directories"),
                         "1 directory")


class BuildTrace(unittest.TestCase):
    HOPS = [
        {"file": "vol", "symbol": "ingest-ohlcv", "claim": "The wrapper dispatches.",
         "quote": "  ingest-ohlcv)\n    python -m volforecast ingest-ohlcv \"$@\"",
         "focus": ["  ingest-ohlcv)"]},
        {"file": "src/a.py", "symbol": "main", "claim": "main builds the parser.",
         "quote": "def main(argv):\n    parser = build()", "focus": ["def main(argv):"]},
        {"file": "src/a.py", "symbol": "build", "claim": "build registers each one.",
         "quote": "def build():\n    return p", "focus": ["def build():"]},
        {"file": "src/b.py", "symbol": "run", "claim": "run does the work.",
         "quote": "def run():\n    return 0", "focus": ["def run():"]},
    ]

    def test_every_hop_carries_a_sentence_and_a_verbatim_quote(self):
        # One claim per hop or a hop renders esc(undefined) inside a claim span.
        steps = compose.build_trace(ctx(hops=self.HOPS))[0]["steps"]

        self.assertEqual(len(steps), len(self.HOPS))
        for s in steps:
            self.assertTrue(s["claim"].strip())
            self.assertTrue(s["cite"]["quote"].strip())

    def test_next_is_emitted_on_every_hop_but_the_last(self):
        steps = compose.build_trace(ctx(hops=self.HOPS))[0]["steps"]

        self.assertEqual([s["next"] for s in steps],
                         ["main in src/a.py", "build in src/a.py",
                          "run in src/b.py", None])

    def test_predict_only_where_the_next_hop_is_a_new_file(self):
        # verify-contract.js:110 rejects a predict on the last hop and one whose
        # next hop is the same file; the renderer collides two predicts in one
        # file onto one localStorage slot.
        steps = compose.build_trace(ctx(hops=self.HOPS))[0]["steps"]

        self.assertEqual([i for i, s in enumerate(steps) if "predict" in s],
                         [0, 2])

    def test_a_model_sentence_about_another_file_falls_back_to_the_template(self):
        narr = {"trace": {"claims": [
            {"text": "This is about a different file entirely.",
             "status": "verified", "cite": _cite("src/zzz.py", "x = 1")}]}}

        steps = compose.build_trace(ctx(narration=narr, hops=self.HOPS))[0]["steps"]

        self.assertEqual(steps[0]["claim"], "The wrapper dispatches.")

    def test_a_model_sentence_about_this_hops_file_is_used(self):
        narr = {"trace": {"claims": [
            {"text": "The wrapper matches the subcommand name.",
             "status": "verified", "cite": _cite("vol", "ingest-ohlcv)")}]}}

        steps = compose.build_trace(ctx(narration=narr, hops=self.HOPS))[0]["steps"]

        self.assertEqual(steps[0]["claim"],
                         "The wrapper matches the subcommand name.")

    def test_the_trace_stop_closes_with_what_it_does_not_prove(self):
        blocks = compose.build_trace(ctx(hops=self.HOPS))

        self.assertEqual(blocks[-1]["level"], "inferred")
        self.assertIn("nothing was executed", blocks[-1]["text"])


class BuildWhere(unittest.TestCase):
    def test_purpose_comes_from_the_package_init_docstring(self):
        # Decision #20: a table cell has no claim marker and the gate never
        # walks one, so a model sentence here is an unverified factual claim on
        # the stop a joiner reads second.
        table = compose.build_where(ctx())[1]

        row = next(r for r in table["rows"] if "data" in r[0])
        self.assertEqual(row[1], "Data ingestion and cache layout")

    def test_purpose_is_an_honest_gap_when_the_package_has_no_docstring(self):
        # `@3`'s dash policy bans the em dash on every authored surface and
        # `purpose` is on the scanned list, so the gap is spelled out now.
        table = compose.build_where(ctx())[1]

        row = next(r for r in table["rows"] if "cli" in r[0])
        self.assertEqual(row[1], "no docstring")

    def test_a_cell_is_escaped_before_it_reaches_the_raw_surface(self):
        # The renderer interpolates table cells without esc().
        sv = copy.deepcopy(SURVEY)
        sv["files"].append({"path": "src/volforecast/utils/__init__.py",
                            "doc": "Helpers for <script>alert(1)</script> paths."})

        table = compose.build_where(ctx(survey=sv))[1]

        row = next(r for r in table["rows"] if "utils" in r[0])
        self.assertIn("&lt;script&gt;", row[1])
        self.assertNotIn("<script>", row[1])

    def test_every_row_is_as_long_as_the_column_list(self):
        table = compose.build_where(ctx())[1]

        self.assertTrue(all(len(r) == len(table["columns"])
                            for r in table["rows"]))


class TraceFixture(unittest.TestCase):
    """`fixtures/trace.restored.json` against the files on disk.

    Decision #25 cut generic chain extraction, so this file *is* the trace on
    the demo repo and the hour-4 pivot-rule safety net. A window that has moved
    means a dropped anchor on the stop that carries beat 4 of the pitch, and the
    only way to find out early is to check it here.
    """

    @classmethod
    def setUpClass(cls):
        cls.hops = compose.load_hops()

    def test_the_fixture_loads_eight_hops(self):
        self.assertEqual(len(self.hops), 8)

    def test_every_hop_quote_is_the_file_on_disk_at_those_lines(self):
        if not RESTORED.exists():
            self.skipTest("hackathon/restored is not present")
        for i, h in enumerate(self.hops, 1):
            src = read_source(RESTORED / h["file"])

            got = "\n".join(src.lines[h["start"] - 1:h["end"]])
            self.assertEqual(got, h["quote"], f"hop {i} {h['file']}")

    def test_every_window_is_contiguous_and_within_the_anchor_cap(self):
        # An anchor is a single start..end range: a hop specified as scattered
        # linenos is not expressible and fails verify-contract.js:74.
        for i, h in enumerate(self.hops, 1):
            span = h["end"] - h["start"] + 1

            self.assertEqual(len(h["quote"].split("\n")), span, f"hop {i}")
            self.assertLessEqual(span, 24, f"hop {i}")

    def test_every_focus_line_falls_inside_its_own_window(self):
        for i, h in enumerate(self.hops, 1):
            for line in h["focus_lines"]:
                self.assertTrue(h["start"] <= line <= h["end"], f"hop {i}")

    def test_every_focus_string_appears_exactly_once_in_its_quote(self):
        # The resolver takes the FIRST occurrence, so a focus string that
        # repeats highlights the wrong line without failing anything.
        for i, h in enumerate(self.hops, 1):
            for f in h["focus"]:
                self.assertEqual(h["quote"].count(f), 1, f"hop {i}: {f!r}")

    def test_no_window_starts_or_ends_on_a_blank_line(self):
        # The resolver pops leading and trailing blank lines, so a window that
        # has them would resolve to a narrower range than the one recorded here.
        for i, h in enumerate(self.hops, 1):
            lines = h["quote"].split("\n")

            self.assertTrue(lines[0].strip(), f"hop {i} start")
            self.assertTrue(lines[-1].strip(), f"hop {i} end")

    def test_every_quote_is_unique_within_its_own_file(self):
        if not RESTORED.exists():
            self.skipTest("hackathon/restored is not present")
        for i, h in enumerate(self.hops, 1):
            src = read_source(RESTORED / h["file"])
            q = [ln.rstrip() for ln in h["quote"].split("\n")]
            hay = [ln.rstrip() for ln in src.lines]

            hits = sum(1 for j in range(len(hay) - len(q) + 1)
                       if hay[j:j + len(q)] == q)
            self.assertEqual(hits, 1, f"hop {i} {h['file']}: {hits} hits")

    def test_the_hops_span_five_files_so_checkpoint_c2_has_distractors(self):
        # cp-c2's distractors are the other distinct anchor.file values in the
        # hop list — which is why there are eight hops across five files.
        self.assertEqual(len({h["file"] for h in self.hops}), 5)

    def test_the_predict_rule_admits_hops_one_three_six_and_seven(self):
        flags = compose._trace_predicts(self.hops)

        self.assertEqual([i + 1 for i, f in enumerate(flags) if f], [1, 3, 6, 7])


#: Narration with two answered dive units and one that came back empty.
DIVES = {
    **NARRATION,
    "dive:n-data": {"claims": [
        {"text": "Ticks become parquet caches here.", "status": "verified",
         "cite": _cite("src/volforecast/data/ohlcv.py",
                       "def load(symbol):\n    ...")},
        {"text": "It is the heaviest group on the board.",
         "status": "inferred"},
    ]},
    "dive:n-cli": {"claims": [
        {"text": "One module per subcommand.", "status": "verified",
         "cite": _cite("src/volforecast/cli/__init__.py", "import ingest")},
    ]},
    "dive:n-utils": {"claims": []},
}

GLOSSARY = [
    {"id": "qlike", "term": "QLIKE", "def": "A loss function for vol forecasts."},
    {"id": "rv", "term": "RV", "def": "Realized volatility."},
]


class StatsBlocks(unittest.TestCase):
    """`@3`: the cover opens with survey-derived tiles, never model numbers."""

    def tiles(self, blocks):
        st = blocks[0]
        self.assertEqual(st["type"], "stats")
        return {t["l"]: t for t in st["items"]}

    def test_the_cover_opens_with_survey_derived_tiles(self):
        tiles = self.tiles(compose.build_cover(ctx()))

        self.assertEqual(tiles["LINES OF CODE"]["v"], "96,000")
        self.assertEqual(tiles["PYTHON FILES"]["v"], "455")
        self.assertEqual(tiles["PYTHON FILES"]["of"], "1,125")
        self.assertEqual(tiles["MODULES"]["v"], "364")
        # Two files under src/tests; src/tests_extra is NOT under a test root.
        self.assertEqual(tiles["TEST FILES"]["v"], "2")
        self.assertEqual(tiles["COMMANDS RUN"]["v"], "2")
        self.assertEqual(tiles["COMMANDS RUN"]["s"], "1 failing")

    def test_the_missing_modules_tile_appears_only_when_something_dangles(self):
        tiles = self.tiles(compose.build_cover(ctx()))
        self.assertEqual(tiles["MISSING MODULES"]["v"], "1")
        self.assertEqual(tiles["MISSING MODULES"]["color"], "inf")
        self.assertIn("120 import statements", tiles["MISSING MODULES"]["s"])

        sv = copy.deepcopy(SURVEY)
        sv["dangling"] = []
        tiles = self.tiles(compose.build_cover(ctx(survey=sv)))
        self.assertNotIn("MISSING MODULES", tiles)

    def test_every_tile_value_is_a_formatted_figure(self):
        # `v` and `of` are raw-interpolated by the renderer, so they must be
        # plain figures, thousands-separated where big.
        for t in compose.build_cover(ctx())[0]["items"]:
            self.assertRegex(t["v"], r"^[\d,]+$")

    def test_the_stats_constructor_refuses_markup_and_unknown_colors(self):
        with self.assertRaises(ValueError):
            compose.stats([{"v": "<b>1</b>", "l": "TILE"}])
        with self.assertRaises(ValueError):
            compose.stats([{"v": "1", "l": "TILE", "color": "warn"}])
        with self.assertRaises(ValueError):
            compose.stats([{"v": "1", "l": ""}])
        with self.assertRaises(ValueError):
            compose.stats([])


class RestoreLedger(unittest.TestCase):
    """`@3`: dangling imports close the setup stop as a table plus a callout."""

    def test_setup_closes_with_the_missing_module_table_and_callout(self):
        blocks = compose.build_setup(ctx())

        tbl, note = blocks[-2], blocks[-1]
        self.assertEqual(tbl["type"], "table")
        self.assertTrue(tbl["sortable"])
        self.assertEqual(tbl["columns"],
                         ["MISSING MODULE", "IMPORTED FROM", "IMPORT SITES"])
        self.assertEqual(
            tbl["rows"][0][0], "<code>volforecast.constants</code>")
        self.assertIn("src/volforecast/__main__.py", tbl["rows"][0][1])
        self.assertEqual(tbl["rows"][0][2], "120")
        self.assertIn("Missing at this commit", tbl["caption"])

        self.assertEqual(note["type"], "callout")
        self.assertEqual(note["level"], "broken")
        self.assertEqual(note["title"], "MISSING AT THIS COMMIT")
        self.assertIn("volforecast.constants", note["text"])
        self.assertIn("ModuleNotFoundError", note["text"])

    def test_the_ledger_appears_even_when_nothing_was_executed(self):
        blocks = compose.build_setup(ctx(commands={}))

        titles = [b.get("title") for b in blocks]
        self.assertIn("MISSING AT THIS COMMIT", titles)

    def test_no_restore_ledger_when_nothing_dangles(self):
        sv = copy.deepcopy(SURVEY)
        sv["dangling"] = []

        blocks = compose.build_setup(ctx(survey=sv))

        self.assertNotIn("MISSING AT THIS COMMIT",
                         [b.get("title") for b in blocks])
        for b in blocks:
            if b["type"] == "table":
                self.assertNotIn("MISSING MODULE", b["columns"])

    def test_rows_are_capped_at_twenty_by_import_count(self):
        sv = copy.deepcopy(SURVEY)
        sv["dangling"] = [{"target": f"pkg.mod{i:02d}", "n": i, "sites": []}
                         for i in range(1, 26)]

        blocks = compose.build_setup(ctx(survey=sv))
        tbl = blocks[-2]

        self.assertEqual(len(tbl["rows"]), 20)
        self.assertIn("mod25", tbl["rows"][0][0])
        self.assertIn("top 20 of 25", tbl["caption"])
        # No site files known: the cell says so instead of going blank.
        self.assertEqual(tbl["rows"][0][1], "unknown")


class DiveStops(unittest.TestCase):
    """`@3`: one INSIDE THE SYSTEM stop per dive unit that returned claims."""

    def test_dive_stops_form_their_own_track_before_the_trace_track(self):
        tracks = compose.build_course(ctx(narration=DIVES))

        titles = [t["title"] for t in tracks]
        self.assertIn("INSIDE THE SYSTEM", titles)
        self.assertLess(titles.index("INSIDE THE SYSTEM"),
                        titles.index("FOLLOW ONE PATH"))
        dive = next(t for t in tracks if t["title"] == "INSIDE THE SYSTEM")
        # Map order: n-cli is the leftmost node, so its dive leads.
        self.assertEqual([s["id"] for s in dive["stops"]],
                         ["dive-n-cli", "dive-n-data"])
        self.assertEqual([s["title"] for s in dive["stops"]],
                         ["Inside cli", "Inside data"])
        for s in dive["stops"]:
            self.assertTrue(s["lede"], s["id"])
            self.assertEqual(s["kind"], "stop")

    def test_a_dive_stop_carries_prose_then_group_stats(self):
        tracks = compose.build_course(ctx(narration=DIVES))

        dive = next(t for t in tracks if t["title"] == "INSIDE THE SYSTEM")
        data = next(s for s in dive["stops"] if s["id"] == "dive-n-data")
        self.assertEqual([b["type"] for b in data["blocks"]],
                         ["prose", "stats"])
        tiles = {t["l"]: t for t in data["blocks"][1]["items"]}
        self.assertEqual(tiles["LINES OF CODE"]["v"], "9,195")
        self.assertEqual(tiles["FILES"]["v"], "21")
        self.assertEqual(tiles["FAN-IN"]["v"], "1")   # n-cli -> n-data
        self.assertEqual(tiles["FAN-OUT"]["v"], "1")  # n-data -> n-utils

    def test_dive_claim_ids_do_not_collide_across_stops(self):
        tracks = compose.build_course(ctx(narration=DIVES))

        ids = [c["id"] for b in blocks_of(tracks) if b["type"] == "prose"
               for c in b["claims"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_an_empty_dive_unit_is_omitted_silently(self):
        # Absence-by-default (spec section 4): an unanswered dive unit is
        # indistinguishable from one never planned, so a cold run must produce
        # the exact @2 course, with no ledger row and no audit callout. Claims
        # the parser refused are already in the ledger through that path.
        c = ctx(narration=DIVES)

        tracks = compose.build_course(c)

        self.assertNotIn("dive-n-utils", [s["id"] for s in stops_of(tracks)])
        self.assertEqual(
            [d for d in c.degradations if d["code"] == "dive_empty"], [])
        audit = next(s for s in stops_of(tracks) if s["id"] == "audit")
        self.assertNotIn("SUBSYSTEM DIVES NOT GENERATED",
                         [b.get("title") for b in audit["blocks"]])

    def test_the_dive_excerpt_appears_when_the_node_carries_an_anchor(self):
        mp = copy.deepcopy(MAP)
        mp["nodes"][1]["anchor"] = {
            "file": "src/volforecast/data/__init__.py",
            "quote": "Data ingestion and cache layout."}
        mp["nodes"][1]["anchor_caption"] = "The package docstring."

        tracks = compose.build_course(ctx(mp=mp, narration=DIVES))

        data = next(s for s in stops_of(tracks) if s["id"] == "dive-n-data")
        self.assertEqual([b["type"] for b in data["blocks"]],
                         ["prose", "excerpt", "stats"])
        ex = data["blocks"][1]
        self.assertEqual(ex["cite"]["file"],
                         "src/volforecast/data/__init__.py")
        self.assertEqual(ex["caption"], "The package docstring.")

    def test_a_dive_gid_with_no_node_still_renders_prose_only(self):
        narr = {"dive:mystery": {"claims": [
            {"text": "It exists.", "status": "inferred"}]}}

        tracks = compose.build_course(ctx(narration=narr))

        stop = next(s for s in stops_of(tracks) if s["id"] == "dive-mystery")
        self.assertEqual(stop["title"], "Inside mystery")
        self.assertEqual([b["type"] for b in stop["blocks"]], ["prose"])

    def test_without_dive_narration_the_course_is_unchanged(self):
        tracks = compose.build_course(ctx())

        self.assertNotIn("INSIDE THE SYSTEM", [t["title"] for t in tracks])
        self.assertFalse([s for s in stops_of(tracks)
                          if s["id"].startswith("dive-")])


class DiveLedes(unittest.TestCase):
    """One sentence stamped on every dive stop reads as the template it is.

    The fix is a rotation, not a model: at least four distinct templates,
    dealt by the stop's position on the DIVE track, so adjacent stops never
    open identically and a cold rerun deals the same lede to the same stop.
    """

    def dive_narration(self, gids):
        narr = copy.deepcopy(NARRATION)
        for gid in gids:
            narr[f"dive:{gid}"] = {"claims": [
                {"text": f"A fact about {gid}.", "status": "inferred"}]}
        return narr

    def test_at_least_four_distinct_templates_each_naming_the_group(self):
        self.assertGreaterEqual(len(set(compose.DIVE_LEDES)), 4)
        for t in compose.DIVE_LEDES:
            self.assertIn("{label}", t)

    def test_four_dive_stops_get_four_different_ledes(self):
        narr = self.dive_narration(["n-cli", "n-data", "n-utils", "n-extra"])

        tracks = compose.build_course(ctx(narration=narr))

        dive = next(t for t in tracks if t["title"] == "INSIDE THE SYSTEM")
        ledes = [s["lede"] for s in dive["stops"]]
        self.assertEqual(len(ledes), 4)
        self.assertEqual(len(set(ledes)), 4)
        for s in dive["stops"]:
            label = s["title"].removeprefix("Inside ")
            self.assertIn(label, s["lede"], s["id"])

    def test_adjacent_stops_differ_even_when_an_empty_unit_is_omitted(self):
        # DIVES has n-utils coming back empty between two answered units: the
        # rotation is keyed by emitted position, so the two rendered stops
        # still draw different templates rather than colliding across the gap.
        tracks = compose.build_course(ctx(narration=DIVES))

        dive = next(t for t in tracks if t["title"] == "INSIDE THE SYSTEM")
        ledes = [s["lede"] for s in dive["stops"]]
        self.assertEqual(len(ledes), 2)
        self.assertNotEqual(ledes[0], ledes[1])

    def test_the_rotation_is_deterministic_across_cold_runs(self):
        a = compose.build_course(ctx(narration=DIVES))
        b = compose.build_course(ctx(narration=DIVES))

        self.assertEqual(json.dumps(a), json.dumps(b))


class GlossaryStop(unittest.TestCase):
    """`@3`: the glossary the caller passes becomes a CLOSE stop, else nothing."""

    def test_a_glossary_adds_a_close_stop_before_the_audit(self):
        tracks = compose.build_course(ctx(), glossary=GLOSSARY)

        close = next(t for t in tracks if t["title"] == "CLOSE")
        self.assertEqual([s["id"] for s in close["stops"]], ["gloss", "audit"])
        gloss = close["stops"][0]
        self.assertTrue(gloss["lede"])
        tbl = gloss["blocks"][0]
        self.assertEqual(tbl["type"], "table")
        self.assertTrue(tbl["sortable"])
        self.assertEqual(tbl["columns"], ["TERM", "DEFINITION"])
        self.assertEqual(tbl["rows"][0][0], "<b>QLIKE</b>")

    def test_the_audit_stop_stays_last_with_a_glossary(self):
        tracks = compose.build_course(ctx(), glossary=GLOSSARY)

        self.assertEqual(stops_of(tracks)[-1]["id"], compose.AUDIT_STOP)

    def test_no_glossary_argument_changes_nothing(self):
        ids = [s["id"] for s in stops_of(compose.build_course(ctx()))]

        self.assertNotIn("gloss", ids)

    def test_an_empty_or_malformed_glossary_is_omitted(self):
        self.assertIsNone(compose.build_gloss(None))
        self.assertIsNone(compose.build_gloss([]))
        self.assertIsNone(compose.build_gloss([{"term": "", "def": "x"},
                                               {"term": "y", "def": ""},
                                               "not a dict"]))

    def test_glossary_cells_are_escaped_with_the_term_in_bold(self):
        gloss = compose.build_gloss([{"term": "<QLIKE>", "def": "a & b"}])

        row = gloss["blocks"][0]["rows"][0]
        self.assertEqual(row[0], "<b>&lt;QLIKE&gt;</b>")
        self.assertEqual(row[1], "a &amp; b")


class MapTourLede(unittest.TestCase):
    def test_the_map_lede_mentions_the_tour_only_when_the_map_has_one(self):
        toured = copy.deepcopy(MAP)
        toured["tour"] = [{"id": "n-cli", "text": "Start here."}]

        with_tour = compose._lede_map(ctx(mp=toured))
        without = compose._lede_map(ctx())

        self.assertIn("guided tour", with_tour)
        self.assertNotIn("guided tour", without)


class DashPolicy(unittest.TestCase):
    """`@3` spec §1.6: no em or en dash on any authored surface compose owns.

    Quotes and focus strings are the repo's own bytes and exempt, so the scan
    walks the course skipping them, which is exactly the rule the render gate
    applies to the finished payload.
    """

    def _scan(self, obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("quote", "focus"):
                    continue
                self._scan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                self._scan(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            self.assertNotIn("—", obj, path)
            self.assertNotIn("–", obj, path)

    def test_no_authored_dash_reaches_the_course(self):
        c = ctx(narration=DIVES, hops=BuildTrace.HOPS)

        self._scan(compose.build_course(c, glossary=GLOSSARY))

    def test_no_authored_dash_survives_a_degraded_generation(self):
        sv = copy.deepcopy(SURVEY)
        sv["entry_points"] = []
        cmds = copy.deepcopy(COMMANDS)
        for r in cmds["runs"]:
            r["exit"] = 1

        c = ctx(survey=sv, commands=cmds, narration={}, hops=[])

        self._scan(compose.build_course(c))


if __name__ == "__main__":
    unittest.main()
