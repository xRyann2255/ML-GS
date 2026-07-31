"""Genericity harness (plan §11) — the four fixture repos, machine-checked.

§11.3's acceptance criterion is *"both artifact gates exit 0, zero unhandled
exceptions, and `verification-report.json.degradations` matches `expect.json`
where one exists."* Until this file existed the first two clauses were checked
by a shell loop nobody runs and the third was checked by nothing at all: the
four `expect.json` files were inert prose that no test, tool or CLI path read,
so a regression in degradation behaviour on these repos would have been silent
— which is the one failure mode they were authored to prevent.

Each repo is built exactly as its own `expect.json` declares in `invocation`
(`--provider stub --run-commands none`) and then interrogated. The build runs
in-process rather than through `subprocess`, so an unhandled exception arrives
as a stack trace naming the line rather than as `FAIL flat_script`.

**`expect.json` is the oracle and it is measured, not guessed.** Its
`degradations` sets were reconciled against a real run, so the comparison here
is exact set equality on the code strings — no fuzzy matching, no subset. Four
things follow from that and are checked rather than assumed:

  `no_churn` is conditional on the checkout, not on the repo, so it lives in
  `degradations_if_no_churn` and is merged in from the build's own
  `churn.available` (README caveat 2);

  `no_commands` and `narration_budget` belong to the *invocation* — nothing is
  run and no narration store is checked in — which is why `invocation` is
  itself asserted against the flags this harness passes;

  rows 9 and 10 append no degradation row at all, so `hazards` carries them in
  `ledger_rows` and they are proved off `survey.json` instead;

  row 1 fires on all four whatever their entry points are, because hops are
  hand-specified per decision 25 and only `restored/` ships a fixture. That is
  asserted directly, so the day someone writes `fixtures/trace.hazards.json`
  the expectation fails loudly instead of drifting.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_genericity -v
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from trailhead import cli, compose

HACKATHON = Path(__file__).resolve().parents[1]
REPOS = HACKATHON / "tests" / "repos"
FIXTURES = Path(compose.HOPS_FIXTURE).parent

#: The four fixture repos of §11.1. Named rather than globbed so that a fifth
#: repo added without an `expect.json` cannot silently opt out of everything
#: below — which is how this file came to be needed in the first place.
FIXTURE_REPOS = ("flat_script", "hazards", "nested_root", "no_entry")

#: §11.3's invocation, and the string every `expect.json` must agree with. Its
#: `degradations` sets are exact, so they are only true under these flags.
INVOCATION = ("--provider", "stub", "--run-commands", "none")

#: §9's row number for every degradation code the pipeline emits. Used only to
#: cross-check each `expect.json` against its own `degradation_rows`; the
#: repo-behaviour assertions compare code strings directly.
#:
#: Rows 9 and 10 are absent on purpose. `compose.DEGRADATIONS` records that
#: they "emit no callout of their own", and the implementation records no code
#: for them either — they are counted into the audit stop, which is the reading
#: their empty Mode column supports. `hazards/expect.json` carries them in
#: `ledger_rows` and they are proved off `survey.json`.
ROW_OF_CODE = {
    "no_trace": 1,
    "no_test_command": 2,
    "setup_all_failed": 3,
    "few_modules": 4,
    "low_confidence": 5,
    "no_churn": 6,
    "narration_budget": 7,
    "narrate_budget": 7,
    "stop_dropped": 8,
}

#: Codes that are deliberate and are not one of §9's eleven rows. `no_commands`
#: is the allowlist admitting nothing, which `--run-commands none` guarantees.
NOT_A_ROW = {"no_commands"}

#: Row 1's repo-determined half — "no entry point at all", as opposed to the
#: fewer-than-two-hops half that fires on all four regardless. `expect.json`
#: has no field for it; the claim lives in each repo's `notes`, quoted here.
ENTRY_POINTS_EXPECTED = {
    # "main.py carries an if __name__ guard, so entry_points is NOT empty".
    "flat_script": True,
    # "Row 1 fires here on its NO-ENTRY-POINT half (entry_points is empty,
    # correctly)".
    "hazards": False,
    # "entry_points rank 1 fires from [project.scripts] … and rank 3 from
    # widget/__main__.py. VERIFIED: three entries".
    "nested_root": True,
    # "entry_points must come back EMPTY. … If any rank of 3.7 fires here, 3.7
    # is over-matching."
    "no_entry": False,
}

#: §11.3's loop also runs the one real repo that ships in this tree. It carries
#: no `expect.json`, so only the "gates exit 0, zero unhandled exceptions" half
#: of the criterion applies — but it is the only repo here with a hops fixture,
#: which is what makes the row-1 expectation above a fact about fixtures rather
#: than an excuse.
REAL_REPO = HACKATHON / "restored"


@dataclass(frozen=True)
class Built:
    """One repo taken through all five stages, with every artifact read back."""

    name: str
    exit_code: int
    html: Path
    survey: dict
    map: dict
    payload: dict
    report: dict


_WORK: tempfile.TemporaryDirectory | None = None
_CACHE: dict[str, object] = {}


def setUpModule() -> None:
    global _WORK
    # One temp tree for the whole module: five builds at well under a second
    # each is cheap, five builds per test class is not.
    _WORK = tempfile.TemporaryDirectory(prefix="trailhead-genericity-",
                                        ignore_cleanup_errors=True)


def tearDownModule() -> None:
    if _WORK is not None:
        _WORK.cleanup()


def _build(name: str, repo: Path) -> Built:
    """Run §11.3's command on one repo and read every artifact it left.

    `--work` follows `--out` into the temp tree, so nothing is written inside
    the fixture repos — a `.trailhead/` appearing under `tests/repos/hazards/`
    would change the very walk the next build surveys, and `hazards` is the one
    repo whose whole value is what the walk finds in it.
    """
    out = Path(_WORK.name) / name / "out.html"
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = cli.main(["build", str(repo), "-o", str(out), *INVOCATION])
    work = out.parent / ".trailhead"

    def read(filename: str) -> dict:
        path = work / filename
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    return Built(name=name, exit_code=code, html=out,
                 survey=read("survey.json"), map=read("map.json"),
                 payload=read("verified.json"),
                 report=read("verification-report.json"))


def built(name: str, repo: Path | None = None) -> Built:
    """The memoised build for one repo, re-raising whatever it raised.

    A build that blew up is cached as its exception rather than retried: §11.3
    counts unhandled exceptions, and a failure that only surfaced in the first
    test to reach it would hide which repo caused it.
    """
    if name not in _CACHE:
        try:
            _CACHE[name] = _build(name, repo or (REPOS / name))
        except Exception as exc:  # re-raised below, once per test that needs it
            _CACHE[name] = exc
    got = _CACHE[name]
    if isinstance(got, Exception):
        raise AssertionError(
            f"{name}: build raised {type(got).__name__}: {got}") from got
    return got


def expectations() -> list[tuple[str, dict]]:
    """Every `tests/repos/*/expect.json`, in a stable order."""
    return [(p.parent.name, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(REPOS.glob("*/expect.json"))]


def codes_fired(b: Built) -> set[str]:
    """The degradation codes this build recorded.

    `verification-report.json.degradations` is the merge point: survey's rows,
    compose's rows and verify's rows all arrive there, which is why it is the
    field §11.3 names and the one asserted here.
    """
    return {d.get("code") for d in b.report.get("degradations") or []}


def codes_expected(b: Built, expect: dict) -> set[str]:
    """`expect.json`'s exact set, with `no_churn` decided by the build.

    README caveat 2: these repos live inside the ML-GS working tree, so whether
    row 6 fires depends on whether they have been committed yet and not on what
    is in them. `degradations` is written for the committed case and
    `degradations_if_no_churn` carries the other, so the build's own
    `churn.available` is the only honest arbiter.
    """
    codes = set(expect.get("degradations") or ())
    conditional = set(expect.get("degradations_if_no_churn") or ())
    available = ((b.survey.get("churn") or {}).get("available")) is True
    return (codes - conditional) if available else (codes | conditional)


def stops_dropped(b: Built) -> dict[str, str]:
    """`{stop id: reason}` for every stop §9 row 8 removed from the tracks."""
    return {d.get("stop"): d.get("reason")
            for d in b.report.get("degradations") or []
            if d.get("code") == "stop_dropped"}


class EveryFixtureRepoBuilds(unittest.TestCase):
    """§11.3 clause 2: zero unhandled exceptions, on all four."""

    def test_all_four_fixture_repos_carry_an_expect_json(self):
        named = {name for name, _ in expectations()}

        self.assertEqual(named, set(FIXTURE_REPOS))

    def test_every_expect_json_declares_the_invocation_this_harness_runs(self):
        # The exact degradation sets below are only true under these flags —
        # `--run-commands safe` alone would subtract `no_commands`. Pinning the
        # string keeps the oracle and the harness from drifting apart in
        # silence.
        for name, expect in expectations():
            with self.subTest(repo=name):
                self.assertEqual(expect.get("invocation"), " ".join(INVOCATION))

    def test_every_fixture_repo_builds_end_to_end_and_exits_zero(self):
        for name, _ in expectations():
            with self.subTest(repo=name):
                self.assertEqual(built(name).exit_code, cli.EXIT_OK)

    def test_every_fixture_repo_leaves_a_bundle_and_every_stage_artifact(self):
        for name, _ in expectations():
            with self.subTest(repo=name):
                b = built(name)

                self.assertTrue(b.html.is_file(), f"{name}: no HTML written")
                self.assertTrue(b.survey and b.map and b.payload and b.report,
                                f"{name}: a stage artifact is missing or empty")


class DegradationsMatchExpectJson(unittest.TestCase):
    """§11.3 clause 3 — the clause that was asserted in prose and nowhere else."""

    def test_the_degradation_code_set_matches_expect_json_exactly(self):
        for name, expect in expectations():
            with self.subTest(repo=name):
                b = built(name)

                self.assertEqual(codes_fired(b), codes_expected(b, expect))

    def test_no_churn_fires_exactly_when_the_repo_has_no_usable_git_history(self):
        # The one code whose truth is a property of the checkout rather than of
        # the repo, so both sides are read from churn.available.
        for name, _ in expectations():
            with self.subTest(repo=name):
                b = built(name)
                available = ((b.survey.get("churn") or {}).get("available")) is True

                self.assertEqual("no_churn" in codes_fired(b), not available)

    def test_every_emitted_code_is_a_section_9_row_or_a_documented_exception(self):
        # The regression guard on the vocabulary. Without it, renaming a code
        # in compose.py would leave the set comparison above failing with no
        # indication that the *name* rather than the *behaviour* moved.
        for name, _ in expectations():
            with self.subTest(repo=name):
                unknown = codes_fired(built(name)) - set(ROW_OF_CODE) - NOT_A_ROW

                self.assertEqual(unknown, set())

    def test_each_expect_json_agrees_with_its_own_row_numbers(self):
        # `degradations` and `degradation_rows` are two spellings of one claim.
        # Both are hand-maintained, and a fixture that contradicts itself is a
        # worse oracle than no fixture at all.
        for name, expect in expectations():
            with self.subTest(repo=name):
                rows = {ROW_OF_CODE[c] for c in expect["degradations"]
                        if c not in NOT_A_ROW}

                self.assertEqual(rows, set(expect["degradation_rows"]))

    def test_the_dropped_stops_match_expect_json_with_their_reasons(self):
        # Row 8's rows carry the reason a checkpoint could not be built, and
        # the reason is the interesting part: `no_entry` and `flat_script` both
        # drop cp-a, for two different refusals inside checkpoints.py.
        for name, expect in expectations():
            with self.subTest(repo=name):
                self.assertEqual(stops_dropped(built(name)),
                                 expect.get("stop_drops") or {})

    def test_a_dropped_stop_never_inflates_the_dropped_claim_count(self):
        # §9: "A DROPped stop goes in the audit callout, never in dropped[]."
        # It is the number the pitch turns on, and these four repos are the
        # only ones that drop a stop at all.
        for name, _ in expectations():
            with self.subTest(repo=name):
                b = built(name)

                self.assertTrue(stops_dropped(b), f"{name}: no stop dropped")
                self.assertEqual(b.payload["report"]["dropped"], 0)


class MapNodesMatchExpectJson(unittest.TestCase):
    """`len(map.nodes)` — §4.1's fallback reports 0 on every repo without it."""

    def test_map_nodes_matches_expect_json_wherever_it_is_pinned(self):
        for name, expect in expectations():
            if "map_nodes" not in expect:
                continue
            with self.subTest(repo=name):
                b = built(name)

                self.assertEqual(len(b.map.get("nodes") or []), expect["map_nodes"])

    def test_hazards_pins_no_node_count_on_purpose(self):
        # Its own expect.json: "pinning a node count here would make an
        # unrelated collapse tweak look like an encoding regression." If an
        # edit ever adds one, HazardsDegradesHonestly is what it displaces.
        _, expect = next(p for p in expectations() if p[0] == "hazards")

        self.assertNotIn("map_nodes", expect)

    def test_few_modules_fires_exactly_when_the_map_has_fewer_than_three_nodes(self):
        for name, _ in expectations():
            with self.subTest(repo=name):
                b = built(name)
                thin = len(b.map.get("nodes") or []) < 3

                self.assertEqual("few_modules" in codes_fired(b), thin)


class HazardsDegradesHonestly(unittest.TestCase):
    """The assertions `hazards/expect.json` names in place of a node count.

    This repo is the only thing on this machine that exercises `read_source`'s
    error surface before demo day, and "it did not crash" is not the claim —
    the claim is that it declined the right file for the right reason. Its
    `ledger_rows` (§9 rows 9 and 10) append no degradation code, so this is
    also where those two rows are proved at all.
    """

    def setUp(self):
        self.built = built("hazards")
        self.expect = next(e for n, e in expectations() if n == "hazards")

    def test_exactly_one_file_failed_to_parse_and_it_is_broken_py(self):
        self.assertEqual(
            self.built.survey.get("parse_failures"),
            [{"path": "broken.py", "line": 3, "offset": 12, "msg": "invalid syntax"}])

    def test_the_png_named_dot_py_is_skipped_as_not_text_and_never_parsed(self):
        # A NUL through ast.parse is a ValueError, not a SyntaxError. Were this
        # to land in parse_failures instead, §3.5's second except clause is the
        # only thing that kept the build alive at all.
        skipped = (self.built.survey.get("walk") or {}).get("skipped") or []

        self.assertEqual(skipped, [{"path": "image.py", "reason": "not text"}])

    def test_both_ledger_rows_are_backed_by_something_in_the_survey(self):
        # Rows 9 and 10 emit no code, so `ledger_rows` is the only claim they
        # make and survey.json is the only place to check it.
        rows = set(self.expect.get("ledger_rows") or ())
        counted = {9: (self.built.survey.get("counts") or {}).get("parse_failures"),
                   10: len((self.built.survey.get("walk") or {}).get("skipped") or [])}

        self.assertEqual(rows, {9, 10})
        self.assertEqual({r: counted[r] for r in rows}, {9: 1, 10: 1})

    def test_the_repo_module_shadowing_a_stdlib_name_is_reported(self):
        self.assertEqual(self.built.survey.get("stdlib_shadowed"), ["secrets"])

    def test_the_import_with_no_file_on_disk_stays_dangling(self):
        # A dangling target must never become a node or an edge (§3.4), so it
        # is checked both ways round.
        dangling = self.built.survey.get("dangling") or []

        self.assertEqual(dangling, [{"target": "pkg.missing", "n": 1,
                                     "sites": [{"file": "evil.py", "line": 23}]}])
        self.assertNotIn("pkg.missing",
                         {n.get("label") for n in self.built.map.get("nodes") or []})

    def test_evil_pys_splice_marker_does_not_cut_the_bundle_in_half(self):
        # evil.py contains the literal marker text, so a splice that searches
        # the payload rather than the template truncates the file here. The
        # gates are the real check; this one fails first and names the repo.
        html = self.built.html.read_text(encoding="utf-8")

        self.assertIn("TRAILHEAD-DATA-START", html)
        self.assertIn("TRAILHEAD-DATA-END", html)


class RowOneFiresForWantOfAHopsFixture(unittest.TestCase):
    """Why every fixture repo degrades its trace stop, entry points or not.

    All four `expect.json` files assert `no_trace`, and three of them explain
    it by decision 25: hops are hand-specified in `fixtures/trace.<repo>.json`
    and only `restored/` ships one. An explanation nobody checks decays into an
    explanation nobody can justify, so it is checked — and the day a hops
    fixture is written for one of these repos, this fails and forces the
    expectation to be re-derived rather than silently drift.
    """

    def test_no_fixture_repo_ships_a_hops_fixture(self):
        for name, _ in expectations():
            with self.subTest(repo=name):
                self.assertEqual(compose.load_hops(FIXTURES / f"trace.{name}.json"), [])

    def test_no_trace_therefore_fires_on_every_fixture_repo(self):
        for name, _ in expectations():
            with self.subTest(repo=name):
                self.assertIn("no_trace", codes_fired(built(name)))

    def test_the_entry_points_half_of_the_trigger_is_still_what_each_repo_intends(self):
        # This is the part of row 1 the repo really does decide, and it is the
        # whole reason no_entry/ exists. If any rank of §3.7 fires there, §3.7
        # is over-matching and no test but this one would say so.
        for name, wanted in sorted(ENTRY_POINTS_EXPECTED.items()):
            with self.subTest(repo=name):
                found = built(name).survey.get("entry_points") or []

                self.assertEqual(bool(found), wanted, f"entry_points={found}")


class BothArtifactGatesPass(unittest.TestCase):
    """§11.3 clause 1. `--gate` runs two gates, not three (plan §10)."""

    @unittest.skipUnless(shutil.which("node"), "node is not on PATH")
    def test_both_gates_exit_zero_on_every_generated_bundle(self):
        for name, _ in expectations():
            with self.subTest(repo=name):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = cli.run_gates(built(name).html)

                self.assertEqual(code, cli.EXIT_OK)

    def test_the_gate_list_is_the_two_that_read_an_artifact(self):
        # check-fixtures.js hard-codes ../fixtures and takes no argv; running
        # it here would gate the generator on a repo invariant it cannot affect.
        self.assertEqual(list(cli.GATES), ["check-bundle.js", "verify-contract.js"])


@unittest.skipUnless(REAL_REPO.is_dir(), "hackathon/restored is not present")
class TheHarnessOnTheOneRealRepo(unittest.TestCase):
    """§11.3's `restored` arm: no `expect.json`, so only clauses 1 and 2 apply."""

    def setUp(self):
        self.built = built("restored", REAL_REPO)

    def test_it_builds_end_to_end_and_exits_zero(self):
        self.assertEqual(self.built.exit_code, cli.EXIT_OK)

    def test_it_draws_a_real_graph_rather_than_falling_back_to_a_table(self):
        # §4.1's fallback is what stops a repo with no declared packages
        # reporting zero modules — every repo on this machine reports 0 without
        # it, and the map is then never drawn on anything real.
        self.assertGreaterEqual(len(self.built.map.get("nodes") or []), 3)
        self.assertNotIn("few_modules", codes_fired(self.built))

    def test_no_trace_does_not_fire_on_the_one_repo_that_ships_hops(self):
        # The contrast that makes RowOneFiresForWantOfAHopsFixture a statement
        # about fixtures rather than about build_trace being broken.
        self.assertNotEqual(compose.load_hops(FIXTURES / "trace.restored.json"), [])
        self.assertNotIn("no_trace", codes_fired(self.built))

    @unittest.skipUnless(shutil.which("node"), "node is not on PATH")
    def test_both_gates_exit_zero_on_its_bundle(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.run_gates(self.built.html)

        self.assertEqual(code, cli.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
