"""Checkpoint answer keys — derivation, and the direction that grades.

Non-negotiable #6 says the keys come from `survey.json` and never from a model,
so the derivation is ordinary deterministic code and is therefore testable in
full. It is also the one piece of the payload no gate can check:
`verify-contract.js:169-176` range-checks a `single` answer and permutation-
checks an `order` answer, and both of those pass a key that is simply wrong.
Decision #15 is the proof — the shipped `cp-c1` key was the inverse permutation
for a day, passed both gates, and would have marked the correct answer wrong on
stage. §15 risk 13 names this test module as the only recompute that exists.

So these tests do two things a build cannot do for itself. They re-derive the
frozen fixture's key from the execution order of the trace it describes, rather
than reading it back off the answer. And they answer the question the way a
reader answers it, then run that answer through the renderer's own comparison
and assert it grades CORRECT.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_checkpoints -v
"""
import json
import unittest
from pathlib import Path

from trailhead import checkpoints

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class OrderKey(unittest.TestCase):
    def test_the_order_answer_is_the_inverse_permutation(self):
        # answer[i] is the RANK of options[i], not "the option at rank i".
        # Options B, C, A of a true order A, B, C rank 2, 3, 1 — the naive
        # reading gives 3, 1, 2, which is a valid permutation and wrong.
        self.assertEqual(
            checkpoints.order_key(["B", "C", "A"], ["A", "B", "C"]),
            [2, 3, 1],
        )

    def test_an_already_ordered_option_list_keys_to_the_identity(self):
        self.assertEqual(
            checkpoints.order_key(["A", "B", "C"], ["A", "B", "C"]),
            [1, 2, 3],
        )


class TheFrozenFixtureKey(unittest.TestCase):
    """`cp-c1` in `fixtures/*.sample.json` — decision #15, recomputed.

    `TRUE_ORDER` is derived from the fixture's own trace semantics and NOT from
    its answer array: a priced request validates its inputs, builds the
    instrument from the registry, rolls the date forward to a business day,
    discounts and branches in the engine, and serialises last. That is the
    order the fixture's `explanation` describes in words ("validation runs
    before the handler body"), so recomputing the key from it is an independent
    check rather than a restatement.
    """

    TRUE_ORDER = [
        "PriceRequest",
        "build_instrument",
        "roll_forward",
        "ENGINE.price",
        "serialize_price",
    ]
    CORRECTED = [4, 3, 1, 5, 2]
    SHIPPED_WRONG = [3, 5, 2, 1, 4]

    def setUp(self):
        survey = json.loads(
            (FIXTURES / "survey.sample.json").read_text(encoding="utf-8")
        )
        self.block = survey["checkpoints"]["cp-c1"]
        self.symbols = [self._symbol(o) for o in self.block["options"]]

    def _symbol(self, option):
        """The one TRUE_ORDER symbol this option names.

        Matched by substring because the option strings carry markup and an
        em-dash, and the point of the test is the key, not the prose.
        """
        found = [s for s in self.TRUE_ORDER if s in option]
        self.assertEqual(len(found), 1, f"ambiguous option: {option!r}")
        return found[0]

    def test_the_corrected_fixture_key_round_trips(self):
        self.assertEqual(self.block["answer"], self.CORRECTED)

        self.assertEqual(
            checkpoints.order_key(self.symbols, self.TRUE_ORDER),
            self.CORRECTED,
        )

    def test_the_correct_answer_grades_correct(self):
        # A reader who knows the execution order fills each option's select
        # with that option's position in it. This is the on-stage moment.
        picks = [self.TRUE_ORDER.index(s) + 1 for s in self.symbols]

        self.assertTrue(checkpoints.grade_order(self.block, picks))

    def test_the_key_that_shipped_first_would_have_graded_it_wrong(self):
        picks = [self.TRUE_ORDER.index(s) + 1 for s in self.symbols]
        was_shipped = dict(self.block, answer=self.SHIPPED_WRONG)

        self.assertFalse(checkpoints.grade_order(was_shipped, picks))

    def test_swapping_two_ranks_grades_wrong(self):
        picks = [self.TRUE_ORDER.index(s) + 1 for s in self.symbols]
        picks[0], picks[1] = picks[1], picks[0]

        self.assertFalse(checkpoints.grade_order(self.block, picks))


class BuildCheckpoints(unittest.TestCase):
    """End-to-end derivation from one small synthetic repo.

    `widgets` is shaped like the proving-ground repo in the ways that matter:
    a src layout, a console script pointing at `__main__.py`, several
    `if __name__` sites, and an 8-line package `__init__.py` carrying the
    highest raw fan-in in the repo — the trap §3.6's filter exists for.
    """

    SURVEY = {
        "contract": "trailhead/survey@1",
        "repo": {"name": "widgets", "commit": "nogit-4b17c2e9"},
        "files": [
            {"path": "src/widgets/__init__.py", "module": "widgets",
             "loc": 8, "fan_in": 30},
            {"path": "src/widgets/registry.py", "module": "widgets.registry",
             "loc": 120, "fan_in": 9},
            {"path": "src/widgets/utils/paths.py",
             "module": "widgets.utils.paths", "loc": 80, "fan_in": 6},
            {"path": "src/widgets/models/base.py",
             "module": "widgets.models.base", "loc": 200, "fan_in": 4},
            {"path": "src/widgets/data/store.py",
             "module": "widgets.data.store", "loc": 150, "fan_in": 3},
            {"path": "src/widgets/__main__.py", "module": "widgets.__main__",
             "loc": 40, "fan_in": 1},
            {"path": "src/widgets/cli/build.py", "module": "widgets.cli.build",
             "loc": 60, "fan_in": 0},
            {"path": "src/widgets/cli/serve.py", "module": "widgets.cli.serve",
             "loc": 55, "fan_in": 0},
        ],
        "entry_points": [
            {"kind": "console_script", "name": "widgets",
             "file": "src/pyproject.toml", "line": 53,
             "target": "widgets.__main__:main"},
            # Same file as the answer. Deduped, or the quiz offers the right
            # answer twice and the gate passes it.
            {"kind": "module_main", "name": "widgets",
             "file": "src/widgets/__main__.py", "line": 1,
             "target": "widgets.__main__"},
            {"kind": "main_guard", "name": "build",
             "file": "src/widgets/cli/build.py", "line": 42, "target": None},
            {"kind": "main_guard", "name": "serve",
             "file": "src/widgets/cli/serve.py", "line": 31, "target": None},
            {"kind": "main_guard", "name": "store",
             "file": "src/widgets/data/store.py", "line": 90, "target": None},
        ],
    }

    # Four columns. Column 0 holds two nodes of different widths, both centred
    # on x = 78 — which is what `_columns` has to recover without a `col` key.
    MAP = {
        "contract": "trailhead/map@1",
        "nodes": [
            {"id": "n-cli", "label": "cli", "loc": 115, "files": 2,
             "x": 8, "y": 10, "w": 140},
            {"id": "n-graphs", "label": "graphs", "loc": 40, "files": 1,
             "x": 28, "y": 120, "w": 100},
            {"id": "n-data", "label": "data", "loc": 150, "files": 1,
             "x": 180, "y": 10, "w": 140},
            {"id": "n-models", "label": "models", "loc": 200, "files": 1,
             "x": 350, "y": 10, "w": 140},
            {"id": "n-utils", "label": "utils", "loc": 80, "files": 1,
             "x": 520, "y": 10, "w": 140},
        ],
        "edges": [{"a": "n-cli", "b": "n-data", "n": 4}],
    }

    HOPS = [
        {"anchor": {"file": "bin/widgets", "start": 10, "end": 14}},
        {"anchor": {"file": "src/widgets/__main__.py", "start": 20, "end": 26}},
        {"anchor": {"file": "src/widgets/cli/build.py", "start": 40, "end": 48}},
        {"anchor": {"file": "src/widgets/data/store.py", "start": 60, "end": 70}},
        {"anchor": {"file": "src/widgets/utils/paths.py", "start": 80, "end": 88}},
    ]

    def build(self, survey=None, mp=None, hops=None):
        return checkpoints.build_checkpoints(
            survey if survey is not None else self.SURVEY,
            self.MAP if mp is None else mp,
            hops=self.HOPS if hops is None else hops,
        )

    def picked(self, block):
        """The option text the answer index points at."""
        return block["options"][block["answer"]]

    def test_the_most_imported_module_is_the_answer_not_the_init_shelf(self):
        block = self.build()["cp-a1"]

        self.assertEqual(self.picked(block), "<code>widgets.registry</code>")
        self.assertNotIn("<code>widgets</code>", block["options"])

    def test_the_console_script_answer_is_the_file_its_target_resolves_to(self):
        block = self.build()["cp-a2"]

        # Not src/pyproject.toml, which is where it is DECLARED.
        self.assertEqual(
            self.picked(block), "<code>src/widgets/__main__.py</code>"
        )

    def test_option_pool_is_deduped_by_file_before_sampling_distractors(self):
        block = self.build()["cp-a2"]

        self.assertEqual(
            block["options"].count("<code>src/widgets/__main__.py</code>"), 1
        )
        self.assertEqual(len(set(block["options"])), len(block["options"]))

    COLUMN_ORDER = ["cli", "data", "models", "utils"]

    # Eight seeds, not one. Half of all 4-element permutations are their own
    # inverse, so a single seed has even odds of hiding exactly the decision
    # #15 bug this file exists to catch: with an involution, an inverted key
    # is identical to the correct one and every assertion below still passes.
    SEEDS = [f"nogit-seed{n}" for n in range(8)]

    def order_block(self, commit):
        survey = dict(self.SURVEY, repo={"name": "widgets", "commit": commit})
        block = self.build(survey=survey)["cp-c1"]
        return block, [o.split("</code>")[0][6:] for o in block["options"]]

    def test_the_order_key_is_the_map_column_order_left_to_right(self):
        for commit in self.SEEDS:
            with self.subTest(commit=commit):
                block, labels = self.order_block(commit)

                # Read each option's rank back out of the key and rebuild the
                # sequence it describes.
                got = [None] * len(self.COLUMN_ORDER)
                for label, rank in zip(labels, block["answer"]):
                    got[rank - 1] = label
                self.assertEqual(got, self.COLUMN_ORDER)

    def test_a_reader_who_knows_the_column_order_grades_correct(self):
        for commit in self.SEEDS:
            with self.subTest(commit=commit):
                block, labels = self.order_block(commit)

                picks = [self.COLUMN_ORDER.index(x) + 1 for x in labels]

                self.assertTrue(checkpoints.grade_order(block, picks))

    def test_the_seeds_really_do_exercise_a_non_involution(self):
        # Guards the guard: if every seed above happened to shuffle into a
        # self-inverse permutation, the two tests would be blind to an
        # inverted key and would say so nowhere.
        inverted = []
        for commit in self.SEEDS:
            block, _ = self.order_block(commit)
            answer = block["answer"]
            inverse = [answer.index(i + 1) + 1 for i in range(len(answer))]
            inverted.append(inverse != answer)

        self.assertTrue(any(inverted))

    def test_the_traced_chain_ends_in_the_last_hops_file(self):
        block = self.build()["cp-c2"]

        self.assertEqual(
            self.picked(block), "<code>src/widgets/utils/paths.py</code>"
        )
        # Every distractor is a real hop in the same trace, never invented.
        traced = {h["anchor"]["file"] for h in self.HOPS}
        for option in block["options"]:
            self.assertIn(option[6:-7], traced)

    def test_the_map_derived_key_appears_only_once_the_map_exists(self):
        # Stage 1 has no map; stage 2 re-runs with one and merges. The survey-
        # only keys must come back byte-identical or the merge moves an answer
        # index that narrate and the renderer have already seen.
        stage1 = checkpoints.build_checkpoints(self.SURVEY)
        stage2 = self.build()

        self.assertEqual(sorted(stage1), ["cp-a1", "cp-a2"])
        self.assertEqual(sorted(stage2), ["cp-a1", "cp-a2", "cp-c1", "cp-c2"])
        self.assertEqual(stage1["cp-a1"], stage2["cp-a1"])
        self.assertEqual(stage1["cp-a2"], stage2["cp-a2"])

    def test_the_same_repo_twice_gives_identical_keys(self):
        # The one seed is repo.commit (§3.6): same tree, same option order,
        # same answer indices, and localStorage progress survives a rerun.
        self.assertEqual(self.build(), self.build())

    def test_a_different_commit_reshuffles_the_options(self):
        other = dict(self.SURVEY, repo={"name": "widgets", "commit": "deadbee1"})

        self.assertNotEqual(
            self.build()["cp-a1"]["options"],
            self.build(survey=other)["cp-a1"]["options"],
        )

    def test_every_emitted_key_satisfies_the_gate(self):
        # verify-contract.js:167-176, reproduced. provenance and explanation
        # are required because the page states on screen where the key is from.
        for cp_id, block in self.build().items():
            with self.subTest(cp=cp_id):
                self.assertTrue(block["provenance"].strip())
                self.assertTrue(block["explanation"].strip())
                self.assertGreaterEqual(len(block["options"]), 4)
                if block["kind"] == "single":
                    self.assertIn(block["answer"], range(len(block["options"])))
                else:
                    self.assertEqual(
                        sorted(block["answer"]),
                        list(range(1, len(block["options"]) + 1)),
                    )

    READER_SUFFIX = (
        "options shuffled deterministically by the commit seed, so a "
        "regenerated page asks the same question the same way."
    )

    def test_provenance_speaks_to_the_reader_not_about_the_generator(self):
        # "options ordered by seed repo.commit" is a generator internal on a
        # reader-facing surface. The reworded suffix says what the seed MEANS
        # for the reader; the leading survey-source clause stays, because the
        # page stating where its key came from is non-negotiable #6.
        for cp_id, block in self.build().items():
            with self.subTest(cp=cp_id):
                self.assertNotIn("seed repo.commit", block["provenance"])
                self.assertTrue(
                    block["provenance"].endswith(self.READER_SUFFIX),
                    block["provenance"],
                )

    def test_provenance_still_opens_with_its_survey_source_clause(self):
        built = self.build()

        self.assertTrue(built["cp-a1"]["provenance"].startswith("survey.json → "))
        self.assertTrue(built["cp-a2"]["provenance"].startswith("survey.json → "))
        self.assertTrue(built["cp-c1"]["provenance"].startswith("map.json → "))
        self.assertTrue(built["cp-c2"]["provenance"].startswith("trace hops → "))

    def test_options_are_escaped_and_carry_only_whitelisted_markup(self):
        # checkpoint.options[] is interpolated raw by the renderer (#20b), so a
        # `<` in a path must arrive escaped.
        hostile = json.loads(json.dumps(self.SURVEY))
        winner = next(f for f in hostile["files"] if f["fan_in"] == 9)
        winner["path"], winner["module"] = "src/<script>.py", None

        options = checkpoints.build_checkpoints(hostile)["cp-a1"]["options"]

        self.assertIn("<code>src/&lt;script&gt;.py</code>", options)


class Preconditions(unittest.TestCase):
    """§9 row 8: too few real options DROPS the checkpoint. Never a placeholder.

    Padding an option list with invented distractors would put a fabrication
    inside the one artifact whose entire pitch is that it contains none.
    """

    BASE = BuildCheckpoints.SURVEY

    def test_fewer_than_four_real_options_emits_nothing(self):
        thin = dict(self.BASE, files=self.BASE["files"][:3], entry_points=[])

        self.assertEqual(checkpoints.build_checkpoints(thin), {})

    def test_a_tie_for_the_most_imported_module_emits_nothing(self):
        # Two modules imported 9 times each means two correct answers, and the
        # page would mark one of them wrong — decision #15 with another cause.
        tied = json.loads(json.dumps(self.BASE))
        tied["files"][2]["fan_in"] = 9

        self.assertNotIn("cp-a1", checkpoints.build_checkpoints(tied))

    def test_a_map_with_three_columns_emits_no_order_checkpoint(self):
        mp = {
            "nodes": [
                n for n in BuildCheckpoints.MAP["nodes"] if n["id"] != "n-utils"
            ]
        }

        self.assertNotIn(
            "cp-c1", checkpoints.build_checkpoints(self.BASE, mp)
        )

    def test_a_trace_crossing_three_files_emits_no_final_file_checkpoint(self):
        hops = BuildCheckpoints.HOPS[:3]

        self.assertNotIn(
            "cp-c2", checkpoints.build_checkpoints(self.BASE, hops=hops)
        )

    def test_no_entry_point_drops_cp_a2_and_keeps_the_rest(self):
        blind = dict(self.BASE, entry_points=[])

        built = checkpoints.build_checkpoints(blind, BuildCheckpoints.MAP)

        self.assertNotIn("cp-a2", built)
        self.assertIn("cp-a1", built)
        self.assertIn("cp-c1", built)


class FanInRanking(unittest.TestCase):
    """Where "imported the most" comes from, and what it refuses to count."""

    def test_fan_in_falls_back_to_the_module_rollup_when_files_lack_it(self):
        # The frozen schema puts per-file fan-in in modules[].top[]; only an
        # additive survey extension puts it on files[] directly.
        survey = {
            "repo": {"commit": "abc"},
            "files": [
                {"path": f"src/{n}.py", "module": n, "loc": 30}
                for n in "abcd"
            ],
            "modules": {
                "src": {"top": [{"path": "src/a.py", "fan_in": 7},
                                {"path": "src/b.py", "fan_in": 2},
                                {"path": "src/c.py", "fan_in": 1},
                                {"path": "src/d.py", "fan_in": 0}]},
            },
        }

        ranked, source, _ = checkpoints._fan_in_ranking(survey)

        self.assertEqual([r["display"] for r in ranked[:2]], ["a", "b"])
        self.assertEqual(ranked[0]["fan_in"], 7)
        self.assertIn("per-file", source)

    def test_a_package_init_is_ranked_once_it_carries_real_code(self):
        survey = {
            "repo": {"commit": "abc"},
            "files": [
                {"path": "pkg/__init__.py", "module": "pkg",
                 "loc": 200, "fan_in": 40},
                {"path": "pkg/thin/__init__.py", "module": "pkg.thin",
                 "loc": 8, "fan_in": 90},
            ],
        }

        ranked = checkpoints._file_fan_in_ranking(survey)

        self.assertEqual([r["display"] for r in ranked], ["pkg"])

    def test_a_repo_with_git_history_ranks_from_edges_not_from_top(self):
        # Decision #18 runs the substitution the other way: when churn IS
        # available, modules[].top[] carries `commits`, so there is no per-file
        # fan-in anywhere and a file-level ranking would silently be empty —
        # taking cp-a1 with it on every healthy repo. edges[] is frozen,
        # always present, and is the literal reading of the question.
        survey = {
            "repo": {"commit": "abc"},
            "roots": {"declared_packages": ["pkg"]},
            "modules": {m: {"loc": 100} for m in
                        ["pkg", "pkg.a", "pkg.b", "pkg.c", "pkg.d"]},
            "edges": [
                {"a": "pkg.a", "b": "pkg.b", "n": 3},
                {"a": "pkg.c", "b": "pkg.b", "n": 1},
                {"a": "pkg.d", "b": "pkg.c", "n": 9},
                {"a": "pkg.a", "b": "pkg.d", "n": 1},
                {"a": "pkg.b", "b": "pkg", "n": 40},
            ],
            "files": [{"path": "pkg/a.py", "module": "pkg.a", "loc": 30}],
        }

        ranked, source, _ = checkpoints._fan_in_ranking(survey)

        self.assertEqual(ranked[0]["display"], "pkg.b")
        self.assertEqual(ranked[0]["fan_in"], 2)
        self.assertIn("edges[]", source)
        # The declared package root wins on raw count and says nothing.
        self.assertNotIn("pkg", [r["display"] for r in ranked])


class TheShippedSurveyFixture(unittest.TestCase):
    """`fixtures/survey.sample.json` — the one real survey shape on disk.

    A synthetic dict proves the arithmetic; this proves the field names. The
    fixture is a git-tracked repo, so its rollup carries `commits` and it
    exercises the `edges[]` path end to end.
    """

    def setUp(self):
        self.survey = json.loads(
            (FIXTURES / "survey.sample.json").read_text(encoding="utf-8")
        )

    def test_both_survey_only_keys_are_derivable_from_it(self):
        built = checkpoints.build_checkpoints(self.survey)

        self.assertEqual(sorted(built), ["cp-a1", "cp-a2"])

    def test_the_entry_point_answer_is_the_file_not_the_pyproject(self):
        block = checkpoints.build_checkpoints(self.survey)["cp-a2"]

        # pyproject.toml:34 DECLARES payments-core; src/cli.py runs it.
        self.assertEqual(
            block["options"][block["answer"]], "<code>src/cli.py</code>"
        )
        self.assertNotIn("<code>pyproject.toml</code>", block["options"])


class TheShippedTraceFixture(unittest.TestCase):
    """`fixtures/trace.restored.json` — the hop list `cp-c2` is keyed from.

    The fixture specifies hops flat (`file`/`start`/`end`), because it is
    written before stage 4 exists to anchor them; the same hops reach this
    module as `anchor.file` once verify has run. Reading only the anchored
    shape dropped `cp-c2` here in silence, which is the failure mode §9 is
    supposed to make loud, so the real file is the test input.
    """

    def setUp(self):
        self.hops = json.loads(
            (FIXTURES / "trace.restored.json").read_text(encoding="utf-8")
        )
        self.survey = {"repo": {"name": "restored", "commit": "nogit-4b17c2e9"}}

    def test_the_wrapper_the_fixture_ships_is_unwrapped(self):
        block = checkpoints.build_checkpoints(
            self.survey, hops=self.hops
        )["cp-c2"]

        self.assertEqual(len(block["options"]), 4)

    def test_the_flat_and_anchored_hop_shapes_key_identically(self):
        flat = self.hops["hops"]
        anchored = [
            {"anchor": {"file": h["file"], "start": h["start"],
                        "end": h["end"]}}
            for h in flat
        ]

        self.assertEqual(
            checkpoints.build_checkpoints(self.survey, hops=flat)["cp-c2"],
            checkpoints.build_checkpoints(self.survey, hops=anchored)["cp-c2"],
        )

    def test_the_answer_is_the_file_the_last_hop_lands_in(self):
        block = checkpoints.build_checkpoints(
            self.survey, hops=self.hops
        )["cp-c2"]
        last = self.hops["hops"][-1]["file"]

        self.assertEqual(
            block["options"][block["answer"]], f"<code>{last}</code>"
        )


class Columns(unittest.TestCase):
    def test_columns_are_recovered_from_geometry_without_a_col_key(self):
        # map@1 is frozen at the nine render fields, so the column index the
        # answer key needs has to come back out of x and w. Nodes are centred
        # in their band, so their midpoints agree; bands are more than COL_GAP
        # apart, so two columns never do.
        mp = {"nodes": [
            {"id": "a", "x": 8, "w": 140},
            {"id": "b", "x": 28, "w": 100},
            {"id": "c", "x": 180, "w": 140},
        ]}

        columns = checkpoints._columns(mp)

        self.assertEqual([[n["id"] for n in c] for c in columns],
                         [["a", "b"], ["c"]])

    def test_an_explicit_col_key_wins_over_geometry(self):
        mp = {"nodes": [
            {"id": "a", "x": 8, "w": 140, "col": 1},
            {"id": "b", "x": 28, "w": 100, "col": 0},
        ]}

        columns = checkpoints._columns(mp)

        self.assertEqual([[n["id"] for n in c] for c in columns],
                         [["b"], ["a"]])


class Grading(unittest.TestCase):
    def test_single_grades_the_answer_index_the_renderer_compares(self):
        block = {"kind": "single", "answer": 2}

        self.assertTrue(checkpoints.grade_single(block, 2))
        self.assertFalse(checkpoints.grade_single(block, 0))

    def test_order_grades_position_by_position(self):
        block = {"kind": "order", "answer": [2, 3, 1]}

        self.assertTrue(checkpoints.grade_order(block, [2, 3, 1]))
        self.assertFalse(checkpoints.grade_order(block, [3, 1, 2]))
        self.assertFalse(checkpoints.grade_order(block, [2, 3]))


if __name__ == "__main__":
    unittest.main()
