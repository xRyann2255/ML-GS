"""Stage 4 VERIFY — the merge, the ledger, the report cross-checks.

VERIFY is the machine that checks the model, so it is the one module where a
bug is indistinguishable from success: a resolver that anchors to the wrong
place, a `report.failed` counted off the run log instead of the page, or an
inferred claim that kept its anchor all produce a page that looks *more*
trustworthy than the truth. Both Node gates pass several of those, and neither
executes the renderer, so these tests stand in for the browser as well.

The four that matter most, and why:

  * an anchor whose file changed after narration must DROP, with the reason
    that says so — that is the only path in the pipeline that catches evidence
    going stale between stage 3 and stage 4;
  * `report.dropped` must equal the ledger length and `report.failed` must
    count RENDERED command blocks, because those are the two cross-checks
    `verify-contract.js` fails a payload for;
  * an inferred claim must carry no `anchor` KEY — not a null one, not an empty
    one; `if (c.anchor)` is true for `{}`;
  * the `files` map must bundle trace-step anchors, or every hop on the stop
    that carries the pitch fails with `file not bundled`.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_verify -v
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from trailhead import TOOL_VERSION, verify
from trailhead.textio import read_source, sha256_range

HACKATHON = Path(__file__).resolve().parents[1]
FIXTURES = HACKATHON / "fixtures"
TOOLS = HACKATHON / "tools"

#: A two-file repo small enough to reason about and real enough to parse. Both
#: quotes clear the resolver's floors (>= 2 lines, >= 40 non-space characters)
#: and appear exactly once, so anything that drops here dropped for a reason the
#: test put there.
APP_PY = '''"""App."""
import os


def handler(req):
    value = compute(req)
    return {"value": value, "ok": True}


def compute(req):
    total = req["a"] + req["b"]
    return total * 2
'''

STORE_PY = '''"""Store."""

DATA_BY_NAME = {"alpha": 1}


def load(key, default=None):
    if key not in DATA_BY_NAME:
        raise KeyError(f"no such key: {key}")
    return DATA_BY_NAME[key]
'''

APP_QUOTE = '    value = compute(req)\n    return {"value": value, "ok": True}'
STORE_QUOTE = ('    if key not in DATA_BY_NAME:\n'
               '        raise KeyError(f"no such key: {key}")')


class Repo(unittest.TestCase):
    """Base for tests that need real files — VERIFY re-reads from disk."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.addCleanup(self._dir.cleanup)
        self.write("pkg/app.py", APP_PY)
        self.write("pkg/store.py", STORE_PY)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return path

    def sources(self):
        return {rel: read_source(self.root / rel)
                for rel in ("pkg/app.py", "pkg/store.py")}

    def snap(self, sources=None):
        sources = sources or self.sources()
        return {rel: (src.lines, None) for rel, src in sources.items()}


def claim(cid, file, quote, focus=(), status="verified"):
    """One `content@1` claim: a verbatim quote, never a line number."""
    body = {"id": cid, "text": f"claim {cid}", "status": status}
    if status == "verified":
        body["cite"] = {"file": file, "quote": quote, "focus": list(focus)}
    return body


def content(blocks, *, stop_id="five", kind=None):
    """A minimal `content@1` payload wrapping one stop's blocks."""
    stop = {"id": stop_id, "title": "A stop", "minutes": 4,
            "lede": "One deterministic sentence.", "blocks": list(blocks)}
    if kind:
        stop["kind"] = kind
    return {
        "contract": "trailhead/content@1",
        "repo": {"name": "tiny", "commit": "deadbee"},
        "tracks": [{"title": "ORIENT", "minutes": 4, "stops": [stop]}],
    }


def ledger_stop():
    """The audit stop. Self-police refuses a payload with no ledger block."""
    return {"id": "audit", "title": "Audit", "minutes": 3,
            "lede": "What was deleted, and why.",
            "blocks": [{"type": "ledger"}]}


class ExpandAnchor(unittest.TestCase):
    LINES = APP_PY.split("\n")

    def test_focus_lines_always_fall_inside_the_returned_range(self):
        # A 30-line quote yields a negative pad under the naive formula, and an
        # anchor strictly inside its own focus, and the gate then reports
        # `focus line 1 outside 8-23` after every model call is spent.
        lines = [f"line {n}" for n in range(1, 41)]

        start, end = verify.expand_anchor(lines, 1, 30, python=False)

        self.assertLessEqual(start, 1)
        self.assertGreaterEqual(end, 30)

    def test_a_function_longer_than_the_cap_falls_back_to_a_padded_window(self):
        # 42% of the functions in the proving-ground repo exceed cap 24, so the
        # padded window is the common path, not the fallback.
        body = ["def big():"] + [f"    step_{n}()" for n in range(1, 40)]

        start, end = verify.expand_anchor(body, 20, 21, cap=24)

        self.assertEqual((start, end), (9, 32))
        self.assertEqual(end - start + 1, 24)

    def test_the_smallest_enclosing_definition_wins_when_it_fits_the_cap(self):
        start, end = verify.expand_anchor(self.LINES, 6, 7)

        self.assertEqual((start, end), (5, 7))

    def test_a_file_that_does_not_parse_falls_back_to_padding_without_raising(self):
        # `restored/` has genuinely broken modules. A claim anchored into one
        # still deserves a window instead of taking the run down.
        broken = ["def oops(:", "    return 1", "    return 2", "x = ("]

        start, end = verify.expand_anchor(broken, 2, 3)

        self.assertLessEqual(start, 2)
        self.assertGreaterEqual(end, 3)


class TheVocabulary(unittest.TestCase):
    def test_every_reason_this_module_names_is_in_the_shared_vocabulary(self):
        # DROP_REASONS is composed from resolve.REASONS plus the four that need
        # the disk or the parser, so a rename on either side of the seam shows
        # up here rather than as an unexplained ledger row on stage.
        named = {getattr(verify, name) for name in dir(verify)
                 if name.startswith("REASON_")}

        self.assertEqual(named - verify.DROP_REASONS, set())

    def test_a_reason_may_carry_a_detail_and_still_be_vocabulary(self):
        self.assertTrue(verify.is_known_reason("snippet ambiguous — 3 matches"))
        self.assertTrue(verify.is_known_reason(
            verify.reason_out_of_range(44, 51, 38)))
        self.assertFalse(verify.is_known_reason("verification failed"))
        self.assertFalse(verify.is_known_reason(""))


class TheHash(Repo):
    def test_the_hash_matches_the_frozen_recipe_on_a_shipped_fixture_anchor(self):
        # Recomputed from the bundle exactly as the gate's excerptOf does it,
        # against the digest the frozen payload recorded at generation time.
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        anchor = next(verify.iter_anchors(payload))
        bundled = payload["files"][anchor["file"]]
        lines = [bundled[str(n)] for n in range(anchor["start"], anchor["end"] + 1)]

        self.assertEqual(sha256_range(lines, 1, len(lines)), anchor["sha256"])

    def test_a_surviving_carriage_return_changes_the_hash(self):
        # The single most likely way to drop 100% of anchors on Windows: a CRLF
        # checkout reaching the hash with the \r intact hashes something the
        # gate's recomputation over the bundled (stripped) text can never match.
        clean = ["import os", "import sys"]
        dirty = ["import os\r", "import sys\r"]

        self.assertNotEqual(sha256_range(clean, 1, 2), sha256_range(dirty, 1, 2))


class VerifyClaimContract(Repo):
    def test_a_resolvable_quote_becomes_an_anchor_with_a_matching_digest(self):
        sources = self.sources()

        kept, row = verify.verify_claim(
            claim("c-001", "pkg/app.py", APP_QUOTE, ["    value = compute(req)"]),
            self.snap(sources), sources)

        self.assertIsNone(row)
        self.assertEqual(kept["anchor"]["file"], "pkg/app.py")
        self.assertEqual(kept["anchor"]["focus"], [6])
        self.assertEqual(kept["anchor"]["sha256"],
                         sha256_range(sources["pkg/app.py"].lines,
                                      kept["anchor"]["start"], kept["anchor"]["end"]))

    def test_an_inferred_claim_carries_no_anchor_key_at_all(self):
        sources = self.sources()

        kept, row = verify.verify_claim(
            claim("c-002", None, None, status="inferred"), self.snap(sources), sources)

        self.assertIsNone(row)
        self.assertNotIn("anchor", kept)
        self.assertNotIn("cite", kept)

    def test_an_inferred_claim_that_wrongly_carries_an_anchor_has_it_deleted(self):
        # Not blanked, not set to null, not kept with a null sha256:
        # The gate's `if (c.anchor)` is true for {}, so it would render verified.
        sources = self.sources()
        liar = claim("c-003", "pkg/app.py", APP_QUOTE, status="inferred")
        liar["cite"] = {"file": "pkg/app.py", "quote": APP_QUOTE, "focus": []}
        liar["anchor"] = {"file": "pkg/app.py", "start": 5, "end": 7, "sha256": "x"}

        kept, row = verify.verify_claim(liar, self.snap(sources), sources)

        self.assertIsNone(row)
        self.assertEqual(kept["status"], "inferred")
        self.assertNotIn("anchor", kept)

    def test_a_missing_file_drops_with_the_frozen_reason(self):
        sources = self.sources()

        kept, row = verify.verify_claim(
            claim("c-004", "pkg/gone.py", APP_QUOTE), self.snap(sources), sources)

        self.assertIsNone(kept)
        self.assertEqual(row["reason"], verify.REASON_NO_FILE)
        self.assertEqual(row["file"], "pkg/gone.py")

    def test_a_quote_matching_a_different_shown_file_reports_the_wrong_file(self):
        # Without this check a wrong-file anchor ships as `verified`, with a
        # matching sha256, and passes both gates.
        sources = self.sources()

        kept, row = verify.verify_claim(
            claim("c-005", "pkg/store.py", APP_QUOTE), self.snap(sources), sources)

        self.assertIsNone(kept)
        self.assertTrue(row["reason"].startswith(verify.REASON_WRONG_FILE), row["reason"])
        self.assertIn("pkg/app.py", row["reason"])

    def test_an_anchor_whose_file_changed_after_narration_is_dropped(self):
        # The model was shown one thing; disk now holds another. Resolving
        # against the snapshot and re-hashing against disk is the only way this
        # is ever caught, and a stale anchor renders as verified.
        shown = self.sources()
        self.write("pkg/store.py", STORE_PY.replace("no such key", "unknown key"))
        now = self.sources()

        kept, row = verify.verify_claim(
            claim("c-006", "pkg/store.py", STORE_QUOTE), self.snap(shown), now)

        self.assertIsNone(kept)
        self.assertEqual(row["reason"], verify.REASON_HASH)
        self.assertTrue(verify.is_known_reason(row["reason"]))

    def test_a_truncated_file_drops_with_the_out_of_range_reason(self):
        shown = self.sources()
        self.write("pkg/store.py", '"""Store."""\n')
        now = self.sources()

        kept, row = verify.verify_claim(
            claim("c-007", "pkg/store.py", STORE_QUOTE), self.snap(shown), now)

        self.assertIsNone(kept)
        self.assertIn("out of range", row["reason"])
        self.assertTrue(verify.is_known_reason(row["reason"]))

    def test_a_verified_claim_with_no_quote_is_dropped_never_kept_bare(self):
        sources = self.sources()
        naked = {"id": "c-008", "text": "no evidence", "status": "verified"}

        kept, row = verify.verify_claim(naked, self.snap(sources), sources)

        self.assertIsNone(kept)
        self.assertTrue(verify.is_known_reason(row["reason"]))


class TheMerge(Repo):
    SURVEY = {
        "repo": {"name": "tiny", "commit": "deadbee"},
        "checkpoints": {
            "cp-a1": {"kind": "single", "prompt": "Which package owns loading?",
                      "options": ["<code>pkg/app.py</code>", "<code>pkg/store.py</code>"],
                      "answer": 1,
                      "provenance": "survey.json → imports → store is imported by app",
                      "explanation": "load() lives in store.py and app.py calls it."},
        },
    }
    COMMANDS = {
        "contract": "trailhead/commands@1",
        "env": "captured 2026-07-30, Windows 11, python 3.11.1",
        "runs": [
            {"cmd": "py -3.11 -m pytest -q", "cwd": ".", "exit": 0, "dur_ms": 1200,
             "dur": "1.2 s", "out": "2 passed in 1.18s", "timed_out": False},
            {"cmd": "py -3.11 -m ruff check .", "cwd": ".", "exit": 1, "dur_ms": 800,
             "dur": "0.8 s", "timed_out": False,
             "env": "captured 2026-07-30, Windows 11, ruff 0.3.4",
             "out": "pkg/app.py:2:1: F401 `os` imported but unused\nFound 1 error."},
            {"cmd": "py -3.11 -m mypy .", "cwd": ".", "exit": 1, "dur_ms": 400,
             "dur": "0.4 s", "out": "error: cannot find module\nFound 1 error",
             "timed_out": False},
        ],
    }

    def assemble(self, blocks, **kwargs):
        doc = content(blocks)
        doc["tracks"][0]["stops"].append(ledger_stop())
        return verify.assemble(doc, self.SURVEY, None, self.COMMANDS, self.root, **kwargs)

    def test_a_checkpoint_reference_is_replaced_by_the_survey_answer_key(self):
        # Acceptance test 6. Non-negotiable #6: the key comes from survey.json,
        # never from the model, and the substitution is total.
        payload, _ = self.assemble([{"type": "checkpoint", "id": "cp-a1"}])
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "checkpoint")

        self.assertEqual({k: v for k, v in block.items() if k not in ("type", "id")},
                         self.SURVEY["checkpoints"]["cp-a1"])

    def test_an_unknown_checkpoint_reference_drops_its_block_and_is_logged(self):
        payload, audit = self.assemble([
            {"type": "checkpoint", "id": "cp-a1"},
            {"type": "checkpoint", "id": "cp-a9-does-not-exist"},
        ])
        blocks = [b for b in verify.iter_blocks(payload["tracks"])
                  if b["type"] == "checkpoint"]

        self.assertEqual([b["id"] for b in blocks], ["cp-a1"])
        self.assertEqual(audit["blocks_dropped"][0]["id"], "cp-a9-does-not-exist")

    def test_a_command_block_takes_its_exit_output_and_env_from_the_real_run(self):
        payload, _ = self.assemble([
            {"type": "command", "cmd": "py -3.11 -m pytest -q", "cwd": "."}])
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "command")

        self.assertEqual(block["exit"], 0)
        self.assertEqual(block["out"], "2 passed in 1.18s")
        self.assertEqual(block["env"], self.COMMANDS["env"])

    def test_a_per_run_environment_note_beats_the_file_level_one(self):
        payload, _ = self.assemble([
            {"type": "command", "cmd": "py -3.11 -m ruff check .", "cwd": "."}])
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "command")

        self.assertIn("ruff 0.3.4", block["env"])

    def test_a_failing_command_always_carries_a_banner_quoted_from_its_output(self):
        payload, _ = self.assemble([
            {"type": "command", "cmd": "py -3.11 -m ruff check .", "cwd": "."}])
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "command")

        self.assertEqual(block["broken"], "Found 1 error.")
        self.assertIn(block["broken"], block["out"])

    def test_a_command_with_no_captured_run_drops_its_block(self):
        # Non-negotiable #4: there is no path here that invents an exit code.
        payload, audit = self.assemble([
            {"type": "command", "cmd": "py -3.11 -m pytest -q", "cwd": "."},
            {"type": "command", "cmd": "make coverage", "cwd": "."},
        ])
        blocks = [b for b in verify.iter_blocks(payload["tracks"])
                  if b["type"] == "command"]

        self.assertEqual([b["cmd"] for b in blocks], ["py -3.11 -m pytest -q"])
        self.assertEqual(audit["blocks_dropped"][0]["id"], "make coverage")

    def test_a_hypothesis_from_the_content_block_survives_the_merge(self):
        payload, _ = self.assemble([{
            "type": "command", "cmd": "py -3.11 -m mypy .", "cwd": ".",
            "hypothesis": "mypy is not configured for this layout.",
        }])
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "command")

        self.assertEqual(block["hypothesis"], "mypy is not configured for this layout.")

    def test_report_failed_counts_rendered_blocks_not_the_run_log(self):
        # Two of the three runs failed; only one failing block is rendered.
        # Emitting 2 here is the single easiest way to fail the gate.
        payload, _ = self.assemble([
            {"type": "command", "cmd": "py -3.11 -m pytest -q", "cwd": "."},
            {"type": "command", "cmd": "py -3.11 -m ruff check .", "cwd": "."},
        ])

        self.assertEqual(payload["report"]["failed"], 1)
        self.assertEqual(payload["report"]["commands"], 3)

    def test_report_dropped_equals_the_ledger_length(self):
        payload, _ = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE),
            claim("c-002", "pkg/gone.py", APP_QUOTE),
            claim("c-003", "pkg/store.py", APP_QUOTE),
        ]}])

        self.assertEqual(payload["report"]["dropped"], len(payload["dropped"]))
        self.assertEqual(payload["report"]["dropped"], 2)

    def test_the_report_counts_add_up_to_the_claims_made(self):
        payload, _ = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE),
            claim("c-002", None, None, status="inferred"),
            claim("c-003", "pkg/gone.py", APP_QUOTE),
        ]}])
        report = payload["report"]

        self.assertEqual(report["claims"],
                         report["verified"] + report["inferred"] + report["dropped"])

    def test_generated_at_tool_version_and_duration_are_present(self):
        # shell() reads all three and throws before the first stop renders
        # without them — a blank page that both gates still pass.
        payload, _ = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE)]}], t0=0.0)

        self.assertTrue(payload["repo"]["generated_at"].endswith("Z"))
        self.assertEqual(payload["report"]["tool_version"], TOOL_VERSION)
        self.assertIsInstance(payload["report"]["duration_s"], int)
        self.assertGreaterEqual(payload["report"]["duration_s"], 0)

    def test_claim_ids_are_unique_across_kept_and_dropped_claims(self):
        payload, _ = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE),
            claim("c-002", "pkg/gone.py", APP_QUOTE),
            {"text": "an id-less claim from a sloppy parser", "status": "inferred"},
        ]}])
        kept = [c["id"] for b in verify.iter_blocks(payload["tracks"])
                if b["type"] == "prose" for c in b["claims"]]
        every = kept + [d["id"] for d in payload["dropped"]]

        self.assertEqual(len(set(every)), len(every))
        self.assertTrue(all(i and i.startswith("c-") for i in every))

    def test_a_dropped_claim_id_appears_nowhere_in_tracks(self):
        payload, _ = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE),
            claim("c-002", "pkg/gone.py", APP_QUOTE),
        ]}])
        rendered = {c["id"] for b in verify.iter_blocks(payload["tracks"])
                    if b["type"] == "prose" for c in b["claims"]}

        self.assertEqual({d["id"] for d in payload["dropped"]} & rendered, set())

    def test_the_files_map_bundles_trace_step_anchors_too(self):
        # The gate runs its full anchor check on every trace step.
        # A files map built from claim anchors alone fails every hop with
        # `file not bundled` — on the stop that carries the pitch.
        payload, _ = self.assemble([{"type": "trace", "steps": [
            {"claim": "The handler delegates.",
             "cite": {"file": "pkg/app.py", "quote": APP_QUOTE, "focus": []},
             "next": "load in pkg/store.py"},
            {"claim": "The store raises rather than guessing.",
             "cite": {"file": "pkg/store.py", "quote": STORE_QUOTE, "focus": []},
             "next": None},
        ]}])

        self.assertEqual(sorted(payload["files"]), ["pkg/app.py", "pkg/store.py"])
        for anchor in verify.iter_anchors(payload):
            bundled = payload["files"][anchor["file"]]
            for n in range(anchor["start"], anchor["end"] + 1):
                self.assertIn(str(n), bundled)

    def test_a_trace_prediction_never_survives_on_the_last_hop(self):
        # The gate fails `predict on the last hop has no next anchor to key
        # against`, and dropping a hop is what moves the last hop.
        payload, _ = self.assemble([{"type": "trace", "steps": [
            {"claim": "The handler delegates.",
             "cite": {"file": "pkg/app.py", "quote": APP_QUOTE, "focus": []},
             "predict": "Which file runs next?", "next": "load in pkg/store.py"},
            {"claim": "This hop cannot resolve.",
             "cite": {"file": "pkg/gone.py", "quote": STORE_QUOTE, "focus": []},
             "predict": "And after that?", "next": None},
        ]}])
        steps = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "trace")["steps"]

        self.assertEqual(len(steps), 1)
        self.assertNotIn("predict", steps[0])
        self.assertIsNone(steps[0]["next"])

    def test_a_stop_whose_every_block_failed_is_removed_rather_than_blanked(self):
        # The renderer and the gate both TypeError on an empty blocks array; a
        # labelled gap reads as a tool that knows what it does not know.
        payload, audit = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/gone.py", APP_QUOTE)]}])

        self.assertEqual([s["id"] for t in payload["tracks"] for s in t["stops"]],
                         ["audit"])
        self.assertEqual(audit["stops_dropped"][0]["stop"], "five")

    def test_a_low_drop_rate_does_not_flag_the_page(self):
        payload, audit = self.assemble([{"type": "prose", "claims": [
            claim(f"c-0{n:02d}", "pkg/app.py", APP_QUOTE) for n in range(10, 20)]}])

        self.assertFalse(audit["low_confidence"])
        self.assertFalse(any(b.get("level") == "broken"
                             for b in verify.iter_blocks(payload["tracks"])))

    def test_a_high_drop_rate_prepends_a_broken_callout_to_the_audit_stop(self):
        payload, audit = self.assemble([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE),
            claim("c-002", "pkg/gone.py", APP_QUOTE),
            claim("c-003", "pkg/gone.py", APP_QUOTE),
        ]}])
        audit_stop = next(s for t in payload["tracks"] for s in t["stops"]
                          if s["id"] == "audit")

        self.assertTrue(audit["low_confidence"])
        self.assertEqual(audit_stop["blocks"][0]["level"], "broken")
        self.assertIn("67%", audit_stop["blocks"][0]["title"])


def lineage_block(steps):
    """`@2`'s tenth block type, in the shape `verify-contract.js` asserts."""
    return {"type": "lineage", "entities": [{
        "id": "prices", "name": "Price", "meaning": "What the caller is quoted.",
        "steps": steps,
        "boundary": {"text": "The upstream feed is outside this repo.",
                     "status": "verified"},
    }]}


def lineage_step(stage, cite=None, **extra):
    step = {"stage": stage, "label": stage.title(), "description": f"The {stage} step.",
            "evidence_type": "source", "status": "verified"}
    if cite:
        step["cite"] = cite
    step.update(extra)
    return step


class Lineage(Repo):
    """A lineage step is downgraded, never deleted — the shape is the meaning."""

    SURVEY = {"repo": {"name": "tiny", "commit": "deadbee"}, "checkpoints": {}}

    def assemble(self, steps):
        doc = content([lineage_block(steps)])
        doc["tracks"][0]["stops"].append(ledger_stop())
        return verify.assemble(doc, self.SURVEY, None, None, self.root)

    def test_a_resolvable_step_is_anchored_and_its_lines_are_bundled(self):
        payload, _ = self.assemble([
            lineage_step("SOURCE", {"file": "pkg/app.py", "quote": APP_QUOTE,
                                    "focus": []})])
        step = next(b for b in verify.iter_blocks(payload["tracks"])
                    if b["type"] == "lineage")["entities"][0]["steps"][0]

        self.assertEqual(step["status"], "verified")
        self.assertEqual(step["anchor"]["file"], "pkg/app.py")
        self.assertIn(str(step["anchor"]["start"]), payload["files"]["pkg/app.py"])

    def test_an_unresolvable_step_keeps_its_place_and_loses_its_anchor(self):
        # Deleting the middle of SOURCE -> ... -> OUTCOME would show INGESTION
        # feeding the consumer directly, which is a different and false claim.
        payload, _ = self.assemble([
            lineage_step("SOURCE", {"file": "pkg/app.py", "quote": APP_QUOTE,
                                    "focus": []}),
            lineage_step("TRANSFORM", {"file": "pkg/gone.py", "quote": APP_QUOTE,
                                       "focus": []}),
        ])
        steps = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "lineage")["entities"][0]["steps"]

        self.assertEqual([s["stage"] for s in steps], ["SOURCE", "TRANSFORM"])
        self.assertEqual(steps[1]["status"], "inferred")
        self.assertNotIn("anchor", steps[1])
        self.assertEqual(payload["report"]["dropped"], 1)

    def test_a_preresolved_anchor_is_re_read_rather_than_trusted(self):
        # Survey-derived anchors are still evidence, and stage 4 checks
        # everything it ships — not only the parts a model wrote.
        payload, _ = self.assemble([
            lineage_step("SOURCE", anchor={"file": "pkg/app.py", "start": 5,
                                           "end": 7, "focus": [],
                                           "sha256": "not the real digest"})])
        step = next(b for b in verify.iter_blocks(payload["tracks"])
                    if b["type"] == "lineage")["entities"][0]["steps"][0]

        self.assertEqual(step["status"], "inferred")
        self.assertNotIn("anchor", step)
        # @3 sanitisation ships ledger reasons with the ": " join; the em dash
        # form is internal only. is_known_reason accepts both spellings.
        self.assertEqual(payload["dropped"][0]["reason"],
                         "excerpt hash mismatch: file changed after narration")
        self.assertTrue(verify.is_known_reason(payload["dropped"][0]["reason"]))

    def test_a_boundary_can_never_ship_as_verified(self):
        payload, _ = self.assemble([
            lineage_step("SOURCE", {"file": "pkg/app.py", "quote": APP_QUOTE,
                                    "focus": []})])
        entity = next(b for b in verify.iter_blocks(payload["tracks"])
                      if b["type"] == "lineage")["entities"][0]

        self.assertEqual(entity["boundary"]["status"], "inferred")


class SelfPolice(Repo):
    def test_the_frozen_reference_payload_passes(self):
        # A police rule that rejects the shipped, gate-green fixture is a bug in
        # the rule. This is the calibration for every rule above it.
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))

        self.assertEqual(verify.self_police(payload), [])

    def test_a_missing_generated_at_is_rejected(self):
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        del payload["repo"]["generated_at"]

        violations = verify.self_police(payload)

        self.assertTrue(any("generated_at" in v for v in violations), violations)

    def test_an_inferred_claim_with_an_anchor_is_rejected(self):
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        for block in verify.iter_blocks(payload["tracks"]):
            for c in block.get("claims", []):
                if c["status"] == "inferred":
                    c["anchor"] = {"file": "src/api/app.py", "start": 58, "end": 66,
                                   "sha256": "beef"}
                    break

        violations = verify.self_police(payload)

        self.assertTrue(any("inferred claim carries an anchor" in v
                            for v in violations), violations)

    def test_a_dropped_id_hiding_in_a_table_cell_is_rejected(self):
        # The gate builds its `rendered` set from prose claims only
        # — it filters on `type === 'prose'` — so a dropped id in a table cell, a
        # checkpoint option or a trace step passes it.
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        table = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "table")
        table["rows"][0][0] = payload["dropped"][0]["id"]

        violations = verify.self_police(payload)

        self.assertTrue(any("appears inside tracks" in v for v in violations), violations)

    def test_a_reason_outside_the_vocabulary_is_rejected(self):
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        payload["dropped"][0]["reason"] = "verification failed"

        violations = verify.self_police(payload)

        self.assertTrue(any("vocabulary" in v for v in violations), violations)

    def test_unescaped_markup_on_a_raw_interpolation_surface_is_rejected(self):
        # The renderer interpolates checkpoint options without esc(); textio.cell
        # escapes the value and re-adds markup from a two-tag whitelist.
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "checkpoint")
        block["options"][0] = '<img src=x onerror="boom">'

        violations = verify.self_police(payload)

        self.assertTrue(any("unescaped markup" in v for v in violations), violations)

    def test_a_command_whose_exit_is_a_string_is_rejected(self):
        # "0" renders FAILING and null renders PASSING; both pass one gate.
        payload = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        block = next(b for b in verify.iter_blocks(payload["tracks"])
                     if b["type"] == "command")
        block["exit"] = "0"

        violations = verify.self_police(payload)

        self.assertTrue(any("exit is not an int" in v for v in violations), violations)

    def test_assemble_raises_rather_than_writing_a_policed_payload(self):
        survey = {"repo": {"name": "tiny", "commit": "deadbee"}, "checkpoints": {}}
        doc = content([{"type": "prose", "claims": [
            claim("c-001", "pkg/app.py", APP_QUOTE)]}])
        del doc["tracks"][0]["stops"][0]["lede"]

        with self.assertRaises(verify.VerifyError) as caught:
            verify.assemble(doc, survey, None, None, self.root)

        self.assertIn("lede", str(caught.exception))


@unittest.skipUnless(shutil.which("node"), "node is not on PATH")
class TheNodeGate(Repo):
    """`node tools/verify-contract.js` must pass the payload UNMODIFIED."""

    SURVEY = TheMerge.SURVEY
    COMMANDS = TheMerge.COMMANDS

    def gate(self, payload):
        path = self.root / "verified.json"
        verify.write_json(path, payload)
        done = verify.run_contract_gate(path, TOOLS)
        return done.returncode, done.stdout.decode("utf-8", "replace")

    def test_a_generated_payload_passes_the_contract_gate(self):
        doc = content([
            {"type": "prose", "claims": [
                claim("c-001", "pkg/app.py", APP_QUOTE, ["    value = compute(req)"]),
                claim("c-002", "pkg/store.py", STORE_QUOTE),
                claim("c-003", "pkg/gone.py", APP_QUOTE),
                claim("c-004", None, None, status="inferred"),
            ]},
            {"type": "command", "cmd": "py -3.11 -m ruff check .", "cwd": "."},
            {"type": "command", "cmd": "py -3.11 -m pytest -q", "cwd": "."},
            {"type": "trace", "steps": [
                {"claim": "The handler delegates.",
                 "cite": {"file": "pkg/app.py", "quote": APP_QUOTE, "focus": []},
                 "predict": "Which file runs next?", "next": "load in pkg/store.py"},
                {"claim": "The store raises rather than guessing.",
                 "cite": {"file": "pkg/store.py", "quote": STORE_QUOTE, "focus": []},
                 "next": None},
            ]},
            lineage_block([
                lineage_step("SOURCE", {"file": "pkg/store.py", "quote": STORE_QUOTE,
                                        "focus": []}),
                lineage_step("OUTCOME", {"file": "pkg/gone.py", "quote": APP_QUOTE,
                                         "focus": []}),
            ]),
        ])
        doc["tracks"][0]["stops"].append(
            {"id": "cp-a", "title": "Checkpoint", "minutes": 3,
             "blocks": [{"type": "checkpoint", "id": "cp-a1"}]})
        doc["tracks"][0]["stops"].append(ledger_stop())

        payload, _ = verify.assemble(doc, self.SURVEY, None, self.COMMANDS, self.root)
        code, out = self.gate(payload)

        self.assertEqual(code, 0, out)
        self.assertIn("ALL ANCHOR + CONTRACT CHECKS PASS", out)


@unittest.skipUnless(shutil.which("node"), "node is not on PATH")
class TheFixtureChain(unittest.TestCase):
    """survey + content + commands over a planted repo, gated end to end.

    `fixtures/content.sample.json` is built so a correct verifier drops the
    eight claims the frozen ledger lists, plus one checkpoint block and one
    command block. Two further claims drop here that the frozen ledger keeps —
    `c-012` and `c-041` quote a single line each, and §6.1's floor refuses a
    one-line quote rather than guessing between its occurrences. The target is
    the dropped-id SET containing the eight, not a byte-for-byte preimage.
    """

    #: The frozen ledger of fixtures/verified.sample.json.
    DOOMED = {"c-031", "c-052", "c-058", "c-067", "c-081", "c-094", "c-102", "c-133"}

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.addCleanup(self._dir.cleanup)
        self.content = json.loads((FIXTURES / "content.sample.json").read_text("utf-8"))
        self.survey = json.loads((FIXTURES / "survey.sample.json").read_text("utf-8"))
        self.commands = json.loads((FIXTURES / "commands.sample.json").read_text("utf-8"))
        sample = json.loads((FIXTURES / "verified.sample.json").read_text("utf-8"))
        self.map = {"contract": "trailhead/map@1", **sample["map"]}
        self._plant()
        # `lede` is a deterministic template from compose's STOP_TABLE, which
        # did not exist when this fixture was hand-written. Supplying it here
        # is simulating stage 3, not patching stage 4.
        for track in self.content["tracks"]:
            for stop in track["stops"]:
                stop.setdefault("lede", "One deterministic sentence about this stop.")

    def _plant(self):
        """Write the synthetic repo the fixture's surviving quotes describe.

        Every quote that is expected to verify is planted verbatim, exactly
        once. The eight doomed claims are planted nowhere — which is the whole
        point of them.
        """
        wanted: dict[str, list[str]] = {}
        for block in verify.iter_blocks(self.content["tracks"]):
            cites = []
            if block.get("type") == "prose":
                cites = [c.get("cite") for c in block["claims"]
                         if c.get("id") not in self.DOOMED]
            elif block.get("type") == "trace":
                cites = [s.get("cite") for s in block["steps"]]
            for cite in cites:
                if cite:
                    wanted.setdefault(cite["file"], []).append(cite["quote"])

        for path, quotes in wanted.items():
            lines = ['"""Planted by tests/test_verify.py."""', "", ""]
            for quote in dict.fromkeys(quotes):
                lines.extend(quote.split("\n"))
                lines.extend(["", ""])
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("\n".join(lines) + "\n")

    def test_the_eight_frozen_claims_drop_and_none_of_them_is_rendered(self):
        payload, _ = verify.assemble(self.content, self.survey, self.map,
                                     self.commands, self.root)
        ledger = {row["id"] for row in payload["dropped"]}
        rendered = {c["id"] for b in verify.iter_blocks(payload["tracks"])
                    if b["type"] == "prose" for c in b["claims"]}

        self.assertEqual(self.DOOMED - ledger, set())
        self.assertEqual(ledger & rendered, set())
        self.assertTrue(all(verify.is_known_reason(r["reason"])
                            for r in payload["dropped"]))

    def test_the_unresolvable_checkpoint_and_uncaptured_command_are_dropped(self):
        payload, audit = verify.assemble(self.content, self.survey, self.map,
                                         self.commands, self.root)
        dropped = {row["id"] for row in audit["blocks_dropped"]}

        self.assertIn("cp-a9-does-not-exist", dropped)
        self.assertIn("make coverage", dropped)
        self.assertEqual(payload["report"]["failed"], 2)

    def test_the_assembled_payload_passes_the_contract_gate(self):
        payload, _ = verify.assemble(self.content, self.survey, self.map,
                                     self.commands, self.root)
        path = self.root / "verified.json"
        verify.write_json(path, payload)

        done = verify.run_contract_gate(path, TOOLS)
        out = done.stdout.decode("utf-8", "replace")

        self.assertEqual(done.returncode, 0, out)
        self.assertIn("ALL ANCHOR + CONTRACT CHECKS PASS", out)


if __name__ == "__main__":
    unittest.main()
