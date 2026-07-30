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

    def test_a_repo_with_no_commands_and_no_hops_gets_five_and_conv_only(self):
        units, degradations = narrate.build_units(Replay.SURVEY)

        self.assertEqual([u.id for u in units], ["five", "conv"])
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
        self.assertEqual([u.id for u in narrate.build_units(Replay.SURVEY, None, hops[:1])[0]],
                         ["five", "conv"])

    def test_the_budget_drops_units_in_reverse_priority_and_says_so(self):
        hops = [{"file": "app.py", "start": 14, "end": 15},
                {"file": "app.py", "start": 18, "end": 19}]
        commands = {"runs": [{"cmd": "python -c \"import app\"", "cwd": ".", "exit": 0,
                              "dur": "0.06 s", "out": ""}]}

        units, degradations = narrate.build_units(Replay.SURVEY, commands, hops, max_units=2)

        self.assertEqual([u.id for u in units], ["five", "trace"])
        self.assertEqual(degradations[0]["code"], "narrate_budget")
        self.assertIn("2 of 4", degradations[0]["reason"])


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
