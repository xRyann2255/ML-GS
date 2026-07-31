"""Stage 3 NARRATE — the parser's rejection rules, and the replay key.

Stage 3 is the only stage that touches a model, so it is also the only stage
where "it worked when I ran it" means nothing. What is tested here is the code
that decides which model output is allowed to become data:

  * the parser rejects rather than repairs (non-negotiable #7 and #1)
  * a conventions unit is quarantined in CODE, not in the prompt
  * lines 1-12 of every file are shown but never quotable (§5.4 rule 5)
  * the key a prompt pack tells an agent to write is the key the replay reads

Nothing here calls a model. Every "response" is a dict written by hand in the
test, and the provider is `StubProvider` over a temporary directory.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_narrate -v
"""
import json
import tempfile
import unittest
from pathlib import Path

from trailhead import narrate, prompts, provider

FIVE = prompts.Unit(id="five", kind="five", title="Five sentences", max_claims=5)
CONV = prompts.Unit(id="conv", kind="conventions", title="Conventions", max_claims=4)


def claim(text="payments-core prices instruments behind one HTTP endpoint.",
          status="verified", cite=None):
    """One model claim, in the shape the schema allows and nothing more."""
    out = {"text": text, "status": status}
    if cite is not None:
        out["cite"] = cite
    return out


CITE = {"file": "src/api/app.py",
        "quote": "def price(req):\n    return ENGINE.price(req)",
        "focus": ["    return ENGINE.price(req)"]}


class ParseRejectsWholeResponses(unittest.TestCase):
    """Rejections that take the response down, because repair is not an option."""

    def test_a_cite_carrying_a_start_or_end_key_is_rejected_not_repaired(self):
        # The single rule the project turns on. A parser that dropped the key
        # and kept the claim would be a model verifying itself with extra steps.
        raw = {"claims": [claim(cite=dict(CITE, start=12, end=14))]}

        with self.assertRaises(narrate.Rejected) as caught:
            narrate.parse(raw, FIVE)

        self.assertIn("start", str(caught.exception))
        self.assertIn("end", str(caught.exception))

    def test_a_cite_key_outside_the_schema_rejects_even_when_the_claim_is_good(self):
        raw = {"claims": [claim(cite=dict(CITE, line=41))]}

        with self.assertRaises(narrate.Rejected):
            narrate.parse(raw, FIVE)

    def test_a_response_with_no_claims_array_is_rejected(self):
        with self.assertRaises(narrate.Rejected):
            narrate.parse({"result": "ok"}, FIVE)

        with self.assertRaises(narrate.Rejected):
            narrate.parse({"claims": "one claim"}, FIVE)

    def test_a_truncated_or_refused_response_is_rejected_with_its_stop_reason(self):
        # §9 row 11: max_tokens and refusal both arrive HTTP 200. They are parse
        # failures with their own ledger detail, never exceptions from the SDK.
        with self.assertRaises(narrate.Rejected) as caught:
            narrate.parse({"_stop_reason": "max_tokens"}, FIVE)

        self.assertIn("max_tokens", str(caught.exception))


class ParseDropsSingleClaims(unittest.TestCase):
    """Per-claim drops: one ledger row each, and never also a kept claim."""

    def test_a_quote_containing_digits_is_not_mistaken_for_a_line_number(self):
        # The rejection is scoped to cite KEY NAMES. A digit scan over the quote
        # text would reject most true responses, since `timeout=60` and
        # `argv[1]` are ordinary code.
        cite = {"file": "src/runner.py",
                "quote": "def run(cmd):\n    return subprocess.run(cmd, timeout=60)",
                "focus": ["    return subprocess.run(cmd, timeout=60)"]}
        kept, dropped = narrate.parse({"claims": [claim(cite=cite)]}, FIVE)

        self.assertEqual(len(kept), 1)
        self.assertEqual(dropped, [])
        self.assertEqual(kept[0]["cite"]["quote"], cite["quote"])

    def test_an_inferred_claim_is_stripped_of_any_cite_the_model_returned(self):
        raw = {"claims": [claim(text="The team prefers explicit errors.",
                                status="inferred", cite=CITE)]}
        kept, dropped = narrate.parse(raw, FIVE)

        self.assertEqual(dropped, [])
        self.assertNotIn("cite", kept[0])
        self.assertEqual(kept[0]["status"], "inferred")

    def test_a_verified_claim_with_no_cite_is_dropped_entirely(self):
        # Dropped, not downgraded: a sentence that claimed to be anchored and
        # was not is exactly what the audit ledger exists to show.
        kept, dropped = narrate.parse({"claims": [claim()]}, FIVE)

        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 1)
        self.assertTrue(dropped[0]["reason"].startswith(narrate.REASON_UNPARSEABLE))

    def test_a_verified_claim_with_an_empty_quote_is_dropped(self):
        kept, dropped = narrate.parse(
            {"claims": [claim(cite={"file": "a.py", "quote": "   "})]}, FIVE)

        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 1)

    def test_a_quote_longer_than_the_anchor_cap_is_dropped_with_that_reason(self):
        # The cap is the anchor cap: a longer quote cannot be expanded into a
        # range whose focus lines still fall inside it.
        long_quote = "\n".join(f"    line_{n} = {n}" for n in range(30))
        kept, dropped = narrate.parse(
            {"claims": [claim(cite={"file": "a.py", "quote": long_quote})]}, FIVE)

        self.assertEqual(kept, [])
        self.assertTrue(dropped[0]["reason"].startswith(narrate.REASON_QUOTE_CAP))

    def test_claim_text_carrying_markup_or_a_newline_is_dropped(self):
        for text in ("a `backticked` sentence.", "two\nlines.", "an <b>tag.",
                     "a [link](http://x) sentence.", "   ", "x" * 281):
            kept, dropped = narrate.parse({"claims": [claim(text=text, cite=CITE)]}, FIVE)

            self.assertEqual(kept, [], text[:20])
            self.assertEqual(len(dropped), 1, text[:20])

    def test_a_focus_string_that_is_not_in_the_quote_drops_the_focus_not_the_claim(self):
        cite = dict(CITE, focus=["    return ENGINE.price(req)", "not in the quote"])
        kept, dropped = narrate.parse({"claims": [claim(cite=cite)]}, FIVE)

        self.assertEqual(dropped, [])
        self.assertEqual(kept[0]["cite"]["focus"], ["    return ENGINE.price(req)"])

    def test_more_claims_than_the_unit_asked_for_are_truncated_never_an_error(self):
        raw = {"claims": [claim(text=f"sentence {n}.", cite=CITE) for n in range(9)]}
        kept, dropped = narrate.parse(raw, FIVE)

        self.assertEqual(len(kept), FIVE.max_claims)
        self.assertEqual(dropped, [])

    def test_no_claim_is_both_kept_and_dropped(self):
        # verify-contract.js:131 calls this the failure that would discredit the
        # entire pitch, so it is asserted at the stage that could cause it.
        raw = {"claims": [claim(text="anchored.", cite=CITE),
                          claim(text="unanchored."),
                          claim(text="a reading.", status="inferred")]}
        kept, dropped = narrate.parse(raw, FIVE)

        self.assertEqual([c["text"] for c in kept], ["anchored.", "a reading."])
        self.assertEqual([d["text"] for d in dropped], ["unanchored."])


class ConventionsQuarantine(unittest.TestCase):
    def test_a_conventions_unit_forces_every_claim_to_inferred(self):
        # Spec §3 stop 13. Enforced in code, not in the prompt, so the
        # quarantine holds even if the prompt drifts.
        raw = {"claims": [claim(text="Errors are raised, never swallowed.", cite=CITE),
                          claim(text="Modules stay small.", status="verified", cite=CITE)]}
        kept, dropped = narrate.parse(raw, CONV)

        self.assertEqual(dropped, [])
        self.assertEqual([c["status"] for c in kept], ["inferred", "inferred"])
        self.assertTrue(all("cite" not in c for c in kept))


class Prompting(unittest.TestCase):
    """Context packing: the gutter, the head exclusion, the recorded windows."""

    SOURCE = (
        "\n".join(f"# header line {n}" for n in range(1, 13))
        + "\n\n"
        + "def price(req):\n"
        + '    """Price one instrument."""\n'
        + "    if req is None:\n"
        + "        raise ValueError('no request')\n"
        + "    return ENGINE.price(req)\n"
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "app.py").write_text(self.SOURCE, encoding="utf-8", newline="\n")
        self.addCleanup(self.tmp.cleanup)

    def test_the_gutter_is_five_columns_and_preserves_indentation(self):
        lines = ["def price(req):", "    return ENGINE.price(req)"]

        self.assertEqual(
            prompts.number(lines, 1, 2),
            "    1| def price(req):\n    2|     return ENGINE.price(req)",
        )

    def test_the_head_of_a_file_is_shown_but_never_quotable(self):
        # §5.4 rule 5. `from __future__ import annotations` clears every quality
        # floor the resolver has and appears verbatim at the top of 20 files.
        unit = prompts.Unit(id="five", kind="five", title="t", max_claims=5,
                            files=("app.py",))

        system, user, windows = prompts.pack(unit, {}, self.root)

        self.assertIn("    1| # header line 1", user)
        self.assertTrue(windows)
        self.assertTrue(all(w.start > prompts.HEAD_LINES for w in windows))

    def test_a_caller_specified_region_is_always_shown_with_context(self):
        # The trace hops. A hop shown without its anchor is a hop whose claim
        # cannot survive verification.
        unit = prompts.Unit(id="trace", kind="trace", title="t", max_claims=2,
                            regions=(("app.py", 16, 17),))

        _, user, windows = prompts.pack(unit, {}, self.root)

        self.assertIn("   16| ", user)
        self.assertTrue(any(w.start <= 16 and w.end >= 17 for w in windows))

    def test_a_file_that_is_not_on_disk_contributes_nothing_and_does_not_raise(self):
        unit = prompts.Unit(id="five", kind="five", title="t", max_claims=5,
                            files=("app.py", "gone.py"))

        _, user, windows = prompts.pack(unit, {}, self.root)

        self.assertNotIn("gone.py", user)
        self.assertTrue(all(w.file == "app.py" for w in windows))

    def test_the_facts_block_survives_a_survey_with_every_optional_key_missing(self):
        # survey.json grows additively and a degraded repo empties half of it.
        text = prompts.facts({})

        self.assertIn("FACTS", text)

    def test_the_prompt_never_asks_for_a_line_number(self):
        unit = prompts.Unit(id="five", kind="five", title="t", max_claims=5,
                            files=("app.py",))

        system, user, _ = prompts.pack(unit, {}, self.root)

        self.assertIn("NEVER return a line number", system)
        self.assertNotIn('"start"', system + user)
        self.assertNotIn('"end"', system + user)


class Replay(unittest.TestCase):
    """The agent route: emit a pack, answer it at its own `out`, replay it."""

    SURVEY = {
        "repo": {"name": "tiny", "commit": "abc1234"},
        "stats": {"files": 2, "py_files": 1, "loc": 18, "modules": 1},
        "modules": {"app": {"path": ".", "files": 1, "loc": 18,
                            "top": [{"path": "app.py", "fan_in": 3}]}},
        "entry_points": [{"kind": "module_main", "name": "app", "file": "app.py",
                          "target": "app:main"}],
    }

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / ".trailhead"
        (self.root / "app.py").write_text(
            "\n".join(f"# header {n}" for n in range(1, 13))
            + "\n\ndef main():\n    return price(1)\n\n\ndef price(x):\n    return x * 2\n",
            encoding="utf-8", newline="\n")
        self.addCleanup(self.tmp.cleanup)

    def test_a_pack_carries_the_out_path_the_stub_will_later_read(self):
        # If these two keys were computed in two places they would drift, and
        # every replay would miss silently.
        packs = narrate.emit_prompts(self.SURVEY, self.root, self.work)
        pack = next(p for p in packs if p["unit"] == "five")

        written = json.loads((self.work / "prompts" / f"{pack['key']}.json")
                             .read_text(encoding="utf-8"))

        self.assertEqual(written["out"], pack["out"])
        self.assertEqual(Path(pack["out"]).name, f"{pack['key']}.json")
        self.assertEqual(Path(pack["out"]).parent.name, narrate.CACHE_DIRNAME)
        self.assertEqual(pack["key"], provider.cache_key(pack["system"], pack["user"]))

    def test_an_answer_written_to_the_pack_out_path_is_replayed_by_the_stub(self):
        packs = narrate.emit_prompts(self.SURVEY, self.root, self.work)
        pack = next(p for p in packs if p["unit"] == "five")
        Path(pack["out"]).write_text(json.dumps({"claims": [
            claim(text="tiny doubles its input.",
                  cite={"file": "app.py",
                        "quote": "def price(x):\n    return x * 2",
                        "focus": ["    return x * 2"]}),
        ]}), encoding="utf-8")

        result = narrate.run(self.SURVEY, self.root,
                             provider.StubProvider(self.work / narrate.CACHE_DIRNAME),
                             work=self.work)

        self.assertEqual([c["text"] for c in result["narration"]["five"]],
                         ["tiny doubles its input."])
        five = next(u for u in result["units"] if u["id"] == "five")

        # Replayed from the store without reaching the provider at all. The
        # `conv` unit of the same run was not answered, so it misses and falls
        # through to the stub — which is what makes cache_hits the number to
        # assert on, not calls.
        self.assertEqual(five["source"], "cache")
        self.assertEqual(result["model"]["cache_hits"], 1)
        self.assertEqual(result["narration"]["conv"], [])

    def test_a_stub_miss_narrates_nothing_and_does_not_poison_the_store(self):
        result = narrate.run(self.SURVEY, self.root,
                             provider.StubProvider(self.work / narrate.CACHE_DIRNAME),
                             work=self.work)

        self.assertEqual(result["narration"]["five"], [])
        self.assertFalse(list((self.work / narrate.CACHE_DIRNAME).glob("*.json")))

    def test_offline_turns_a_miss_into_a_hard_error(self):
        with self.assertRaises(provider.MissingNarration):
            narrate.run(self.SURVEY, self.root,
                        provider.StubProvider(self.work / narrate.CACHE_DIRNAME,
                                              offline=True),
                        work=self.work, offline=True)

    def test_claim_ids_are_unique_across_kept_and_dropped_claims(self):
        packs = narrate.emit_prompts(self.SURVEY, self.root, self.work)
        for pack in packs:
            Path(pack["out"]).write_text(json.dumps({"claims": [
                claim(text="an anchored sentence.",
                      cite={"file": "app.py", "quote": "def price(x):\n    return x * 2"}),
                claim(text="an unanchorable sentence."),
            ]}), encoding="utf-8")

        result = narrate.run(self.SURVEY, self.root,
                             provider.StubProvider(self.work / narrate.CACHE_DIRNAME),
                             work=self.work)

        ids = [c["id"] for claims in result["narration"].values() for c in claims]
        ids += [row["id"] for row in result["ledger"]]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(i) >= 5 and i.startswith("c-") for i in ids))

    def test_a_rejected_response_costs_the_unit_its_claims_and_earns_one_row(self):
        packs = narrate.emit_prompts(self.SURVEY, self.root, self.work)
        pack = next(p for p in packs if p["unit"] == "five")
        Path(pack["out"]).write_text(
            json.dumps({"claims": [claim(cite=dict(CITE, start=1, end=2))]}),
            encoding="utf-8")

        result = narrate.run(self.SURVEY, self.root,
                             provider.StubProvider(self.work / narrate.CACHE_DIRNAME),
                             work=self.work)

        self.assertEqual(result["narration"]["five"], [])
        rows = [r for r in result["ledger"] if r["reason"].startswith(narrate.REASON_UNPARSEABLE)]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["text"] and rows[0]["id"])


class Units(unittest.TestCase):
    """Which units a repo can support — a data question, not a control-flow one."""

    def test_a_repo_with_no_commands_and_no_hops_gets_five_conv_and_gloss(self):
        # Updated for @3: `gloss` is repo-level (windows come from the survey,
        # not the map), so it joins the two units every repo supports. The
        # node/dive/tour/cols units still need map_data.
        units, degradations = narrate.build_units(Replay.SURVEY)

        self.assertEqual([u.id for u in units], ["five", "conv", "gloss"])
        self.assertEqual(degradations, [])

    def test_a_passing_command_earns_the_green_unit_a_failing_one_does_not(self):
        failing = {"runs": [{"cmd": "pytest", "cwd": ".", "exit": 1, "out": "boom"}]}
        passing = {"runs": [{"cmd": "python -c \"import app\"", "cwd": ".", "exit": 0,
                             "dur": "0.06 s", "out": ""}]}

        self.assertNotIn("green", [u.id for u in narrate.build_units(Replay.SURVEY, failing)[0]])
        self.assertIn("green", [u.id for u in narrate.build_units(Replay.SURVEY, passing)[0]])

    def test_a_string_exit_code_is_not_a_passing_command(self):
        # "0" renders PASSING in the page while being a failure. Never trust it.
        commands = {"runs": [{"cmd": "make", "cwd": ".", "exit": "0", "out": ""}]}

        self.assertNotIn("green", [u.id for u in narrate.build_units(Replay.SURVEY, commands)[0]])

    def test_the_trace_unit_needs_at_least_two_hops_and_asks_one_claim_per_hop(self):
        hops = [{"file": "app.py", "start": 14, "end": 15, "what": "main"},
                {"anchor": {"file": "app.py", "start": 18, "end": 19}, "what": "price"}]

        units, _ = narrate.build_units(Replay.SURVEY, None, hops)
        trace = next(u for u in units if u.id == "trace")

        self.assertEqual(trace.max_claims, len(hops))
        self.assertEqual(len(trace.regions), len(hops))
        # Updated for @3: gloss joins the no-map baseline.
        self.assertEqual([u.id for u in narrate.build_units(Replay.SURVEY, None, hops[:1])[0]],
                         ["five", "conv", "gloss"])

    def test_the_budget_drops_units_in_reverse_priority_and_says_so(self):
        hops = [{"file": "app.py", "start": 14, "end": 15},
                {"file": "app.py", "start": 18, "end": 19}]
        commands = {"runs": [{"cmd": "python -c \"import app\"", "cwd": ".", "exit": 0,
                              "dur": "0.06 s", "out": ""}]}

        units, degradations = narrate.build_units(Replay.SURVEY, commands, hops, max_units=2)

        # Updated for @3: the same repo now also builds `gloss`, so the total
        # is 5. The reverse priority still ends conv < green < five < trace.
        self.assertEqual([u.id for u in units], ["five", "trace"])
        self.assertEqual(degradations[0]["code"], "narrate_budget")
        self.assertIn("2 of 5", degradations[0]["reason"])


NODE = prompts.Unit(id="node:data", kind="node", title="Drawer: data",
                    max_claims=1,
                    files=("data/measures.py", "data/__init__.py"),
                    choices=("measures.py", "__init__.py"))

GLOSS = prompts.Unit(id="gloss", kind="gloss", title="Glossary",
                     max_claims=narrate.GLOSS_TERMS_MAX)

TOUR = prompts.Unit(id="tour", kind="tour", title="Guided tour", max_claims=3,
                    choices=("n-a", "n-b", "n-c"))

COLS = prompts.Unit(id="cols", kind="cols", title="Column labels", max_claims=2)


def node_answer(**over):
    """A valid node drawer answer; keyword overrides poke holes in it."""
    out = {
        "role": ["Turns raw ticks into the daily measures every model consumes.",
                 "Owns the parquet caches and writes them atomically."],
        "reads": "Raw ticks and daily series from the market data services.",
        "feeds": "Feature construction and the model training loop.",
        "key_files": [{"file": "measures.py", "purpose": "the canonical estimators"}],
        "concepts": ["realized variance", "atomic caches", "estimators"],
    }
    out.update(over)
    return out


class StructuredParsers(unittest.TestCase):
    """Per-kind schema validation: reject whole answers, drop bad slots."""

    def test_a_valid_node_answer_round_trips(self):
        answer, rows = narrate.parse_structured(node_answer(), NODE)

        self.assertEqual(rows, [])
        self.assertEqual(len(answer["role"]), 2)
        self.assertEqual(answer["key_files"][0]["file"], "measures.py")
        self.assertEqual(answer["concepts"][0], "realized variance")

    def test_an_unknown_key_rejects_the_whole_node_answer(self):
        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(node_answer(extra="x"), NODE)

        bad_item = node_answer(
            key_files=[{"file": "measures.py", "purpose": "ok", "line": 3}])
        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(bad_item, NODE)

    def test_a_key_files_entry_must_name_a_listed_file(self):
        # One good entry survives a bad sibling; all-bad rejects the answer.
        mixed = node_answer(key_files=[
            {"file": "invented.py", "purpose": "does not exist"},
            {"file": "measures.py", "purpose": "the canonical estimators"},
        ])
        answer, _ = narrate.parse_structured(mixed, NODE)
        self.assertEqual([k["file"] for k in answer["key_files"]], ["measures.py"])

        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(
                node_answer(key_files=[{"file": "invented.py", "purpose": "x"}]),
                NODE)

    def test_a_node_cite_with_a_start_key_rejects_like_a_claims_cite(self):
        raw = node_answer(cite={"file": "data/measures.py", "quote": "def rv():",
                                "start": 40})
        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(raw, NODE)

    def test_node_role_cardinality_is_strict_but_backticks_are_legal(self):
        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(node_answer(role=["only one paragraph."]), NODE)
        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(node_answer(role=["a <b>tag.", "second."]), NODE)

        ticked = node_answer(role=["`measures.py` computes RV.", "Second paragraph."])
        answer, _ = narrate.parse_structured(ticked, NODE)
        self.assertIn("`measures.py`", answer["role"][0])

    def test_the_stub_miss_sentinel_is_absence_for_every_structured_kind(self):
        for unit in (NODE, GLOSS, TOUR, COLS):
            answer, rows = narrate.parse_structured({"claims": []}, unit)

            self.assertEqual(answer, {}, unit.kind)
            self.assertEqual(rows, [], unit.kind)

    def test_gloss_drops_bad_terms_and_keeps_good_ones(self):
        raw = {"terms": [
            {"term": "RV", "def": "Realized variance, the daily forecast target."},
            {"term": "x" * 41, "def": "over the term cap, dropped."},
            {"term": "BPV", "def": "Jump-robust variance.",
             "cite": {"file": "data/measures.py", "quote": "   "}},
        ]}
        answer, _ = narrate.parse_structured(raw, GLOSS)

        self.assertEqual([t["term"] for t in answer["terms"]], ["RV", "BPV"])
        self.assertNotIn("cite", answer["terms"][1])  # unusable cite dropped

    def test_an_unknown_key_inside_one_gloss_term_rejects_the_whole_answer(self):
        raw = {"terms": [{"term": "RV", "def": "fine.", "anchor": {}}]}

        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(raw, GLOSS)

    def test_tour_steps_are_filtered_to_the_fixed_ids_and_reordered(self):
        raw = {"steps": [{"id": "n-b", "text": "B first in the reply."},
                         {"id": "n-x", "text": "not on the board."},
                         {"id": "n-a", "text": "A second in the reply."}]}
        answer, _ = narrate.parse_structured(raw, TOUR)

        self.assertEqual([s["id"] for s in answer["steps"]], ["n-a", "n-b"])

        with self.assertRaises(narrate.Rejected):
            narrate.parse_structured(
                {"steps": [{"id": "n-a", "text": "ok", "order": 1}]}, TOUR)

    def test_cols_labels_are_positional_uppercase_and_capped(self):
        answer, _ = narrate.parse_structured({"labels": ["DATA", "MODELS"]}, COLS)
        self.assertEqual(answer["labels"], ["DATA", "MODELS"])

        for bad in ([["DATA"]],                       # wrong count
                    [["DATA", "models"]],             # not uppercase
                    [["DATA", "X" * 15]]):            # over the label cap
            with self.assertRaises(narrate.Rejected):
                narrate.parse_structured({"labels": bad[0]}, COLS)

    def test_dive_claims_allow_backticks_where_five_still_bans_them(self):
        dive = prompts.Unit(id="dive:core", kind="dive", title="Inside core",
                            max_claims=narrate.DIVE_MAX_CLAIMS)
        text = "The `registry` maps names to classes."

        kept, dropped = narrate.parse({"claims": [claim(text=text, cite=CITE)]}, dive)
        self.assertEqual([c["text"] for c in kept], [text])
        self.assertEqual(dropped, [])

        kept, dropped = narrate.parse({"claims": [claim(text=text, cite=CITE)]}, FIVE)
        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 1)


class MapUnits(unittest.TestCase):
    """The @3 units a map makes possible, and the exact-or-prefix budget."""

    SURVEY = {
        "repo": {"name": "three", "commit": "abc1234"},
        "stats": {"files": 5, "py_files": 4, "loc": 600, "modules": 3},
        "modules": {
            "core": {"path": ".", "files": 1, "loc": 300,
                     "top": [{"path": "core.py", "fan_in": 9}]},
            "data": {"path": "data", "files": 2, "loc": 200,
                     "top": [{"path": "data/measures.py", "fan_in": 4}]},
            "web": {"path": "web", "files": 1, "loc": 100,
                    "top": [{"path": "web/views.py", "fan_in": 1}]},
        },
        "files": [{"path": "README.md"}, {"path": "core.py"},
                  {"path": "data/measures.py"}, {"path": "web/views.py"}],
    }
    MAP = {
        "nodes": [
            {"id": "n-core", "label": "core", "path": "", "loc": 300,
             "files": 1, "x": 40, "y": 40, "w": 150},
            {"id": "n-data", "label": "data", "path": "data", "loc": 200,
             "files": 2, "x": 240, "y": 40, "w": 150},
            {"id": "n-web", "label": "web", "path": "web", "loc": 100,
             "files": 1, "x": 440, "y": 40, "w": 150},
            # Off the board: is_test wins even over the biggest loc.
            {"id": "n-tests", "label": "tests", "path": "tests", "loc": 9999,
             "is_test": True},
        ],
        "columns": [{"label": "LAYER 1", "x": 115}, {"label": "LAYER 2", "x": 315}],
        "tour_order": ["n-core", "n-data", "n-web"],
    }

    def test_a_map_earns_node_dive_tour_and_cols_units(self):
        units, degradations = narrate.build_units(self.SURVEY, map_data=self.MAP)

        self.assertEqual(
            [u.id for u in units],
            ["five", "conv", "node:core", "node:data", "node:web",
             "dive:core", "dive:data", "dive:web", "tour", "cols", "gloss"])
        self.assertEqual(degradations, [])

        node = next(u for u in units if u.id == "node:data")
        self.assertIn("data/measures.py", node.files)
        self.assertIn("measures.py", node.choices)
        self.assertTrue(any("copy the name exactly" in n for n in node.notes))

        tour = next(u for u in units if u.id == "tour")
        self.assertEqual(tour.choices, ("n-core", "n-data", "n-web"))
        self.assertEqual(tour.max_claims, 3)

        cols = next(u for u in units if u.id == "cols")
        self.assertEqual(cols.max_claims, 2)

    def test_a_test_container_node_never_earns_a_unit(self):
        units, _ = narrate.build_units(self.SURVEY, map_data=self.MAP)

        self.assertNotIn("node:tests", [u.id for u in units])
        self.assertNotIn("dive:tests", [u.id for u in units])

    def test_the_budget_drops_prefix_families_smallest_group_first(self):
        units, degradations = narrate.build_units(self.SURVEY, map_data=self.MAP,
                                                  max_units=5)

        # 11 built. cols, conv, gloss, tour go whole; the node family then
        # sheds node:web and node:data (smallest loc first) to reach 5.
        self.assertEqual(
            [u.id for u in units],
            ["five", "node:core", "dive:core", "dive:data", "dive:web"])
        self.assertIn("5 of 11", degradations[0]["reason"])

    def test_without_a_map_the_unit_list_is_the_at2_list_plus_gloss(self):
        units, _ = narrate.build_units(self.SURVEY, map_data=None)

        self.assertEqual([u.id for u in units], ["five", "conv", "gloss"])


class MapPacks(unittest.TestCase):
    """Pack emission for the @3 units: per-kind schemas, real windows."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / ".trailhead"
        body = ("\n".join(f"# header {n}" for n in range(1, 13))
                + "\n\ndef work(x):\n    '''Do the work.'''\n"
                + "    if x is None:\n        raise ValueError('no input')\n"
                + "    return x * 2\n")
        (self.root / "core.py").write_text(body, encoding="utf-8", newline="\n")
        (self.root / "data").mkdir()
        (self.root / "data" / "measures.py").write_text(body, encoding="utf-8",
                                                        newline="\n")
        (self.root / "web").mkdir()
        (self.root / "web" / "views.py").write_text(body, encoding="utf-8",
                                                    newline="\n")
        (self.root / "README.md").write_text("# three\n\nA tiny fixture.\n",
                                             encoding="utf-8", newline="\n")
        self.addCleanup(self.tmp.cleanup)

    def emit(self):
        return narrate.emit_prompts(MapUnits.SURVEY, self.root, self.work,
                                    map_data=MapUnits.MAP)

    def test_each_pack_carries_its_own_kind_schema(self):
        packs = {p["unit"]: p for p in self.emit()}

        self.assertIn("terms", packs["gloss"]["schema"]["properties"])
        self.assertIn("steps", packs["tour"]["schema"]["properties"])
        self.assertIn("labels", packs["cols"]["schema"]["properties"])
        self.assertIn("role", packs["node:data"]["schema"]["properties"])
        self.assertEqual(packs["five"]["schema"], provider.SCHEMA)

        # The fixed vocabularies are enums the answering agent can see.
        node_schema = packs["node:data"]["schema"]
        file_enum = (node_schema["properties"]["key_files"]["items"]
                     ["properties"]["file"]["enum"])
        self.assertIn("measures.py", file_enum)
        tour_enum = (packs["tour"]["schema"]["properties"]["steps"]["items"]
                     ["properties"]["id"]["enum"])
        self.assertEqual(tour_enum, ["n-core", "n-data", "n-web"])

    def test_node_and_dive_packs_show_real_quotable_windows(self):
        packs = {p["unit"]: p for p in self.emit()}

        for unit_id in ("node:data", "dive:core", "gloss"):
            windows = packs[unit_id]["windows"]
            self.assertTrue(windows, unit_id)
            self.assertTrue(all(w["start"] > prompts.HEAD_LINES for w in windows),
                            unit_id)
        self.assertIn("data/measures.py",
                      [w["file"] for w in packs["node:data"]["windows"]])

    def test_a_structured_answer_replays_and_a_missing_one_degrades(self):
        packs = {p["unit"]: p for p in self.emit()}
        Path(packs["gloss"]["out"]).write_text(json.dumps({"terms": [
            {"term": "RV", "def": "Realized variance, the forecast target."},
        ]}), encoding="utf-8")
        Path(packs["cols"]["out"]).write_text(json.dumps(
            {"labels": ["CORE", "EDGE"]}), encoding="utf-8")

        result = narrate.run(MapUnits.SURVEY, self.root,
                             provider.StubProvider(self.work / narrate.CACHE_DIRNAME),
                             work=self.work, map_data=MapUnits.MAP)

        self.assertEqual(result["narration"]["gloss"]["terms"][0]["term"], "RV")
        self.assertEqual(result["narration"]["cols"]["labels"], ["CORE", "EDGE"])
        # Unanswered structured units are absent-shaped, never an error ...
        self.assertEqual(result["narration"]["node:core"], {})
        self.assertEqual(result["narration"]["tour"], {})
        # ... and never counted as a silent gap: unit_unnarrated stays scoped
        # to the claim-shaped kinds (here five and conv, which narrated
        # nothing while gloss/cols carried content).
        gaps = [d["unit"] for d in result["degradations"]
                if d.get("code") == narrate.CODE_UNNARRATED]
        self.assertEqual(gaps, ["five", "conv"])

        gloss_record = next(u for u in result["units"] if u["id"] == "gloss")
        self.assertEqual(gloss_record["source"], "cache")
        self.assertEqual(gloss_record["claims"], 1)


class Store(unittest.TestCase):
    def test_the_key_covers_both_halves_of_the_prompt(self):
        # A system-prompt edit must invalidate: it changes what was asked.
        self.assertNotEqual(provider.cache_key("a", "b"), provider.cache_key("ab", ""))
        self.assertEqual(provider.cache_key("a", "b"), provider.cache_key("a", "b"))

    def test_the_schema_has_no_field_a_line_number_could_go_in(self):
        cite = SCHEMA_CITE = provider.SCHEMA["properties"]["claims"]["items"][
            "properties"]["cite"]

        self.assertFalse(cite["additionalProperties"])
        self.assertEqual(set(SCHEMA_CITE["properties"]), set(provider.CITE_KEYS))


if __name__ == "__main__":
    unittest.main()
