"""Stage 5 RENDER — armour, splice, self-police.

Render is not test-driven the way survey and resolve are: the layout and the
aesthetics are iterated against a browser and the two gates. What *is* tested is
everything that can silently turn the artifact into a lie or into a blank page —
the three cases neither `check-bundle.js` nor `verify-contract.js` can see:

  1. a payload byte sequence that breaks the gates' own scraping (`/*`, `<`, `@`,
     `//`, an em dash) — the gate reports "crashed", not "generator broken"
  2. a dropped claim resurfacing in a block type the gate does not walk
  3. a payload that passes both gates and then throws inside `shell()`, leaving
     a blank page nobody's checks caught

The node-backed cases are skipped when `node` is absent; they are the only proof
that `shell()` actually runs, because both gates parse the page and neither
executes it.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_render -v
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from trailhead import render
from trailhead.render import RenderError

HACKATHON = Path(__file__).resolve().parents[1]
SAMPLE = HACKATHON / "fixtures" / "verified.sample.json"

NODE = shutil.which("node")


def minimal() -> dict:
    """The smallest payload `check_payload` accepts. A fresh dict every call.

    Tests mutate this into the shape they are about to reject, so it must never
    be shared state.
    """
    return {
        "contract": "trailhead/verified@2",
        "repo": {"name": "demo-repo", "commit": "abc1234",
                 "generated_at": "2026-07-30T14:02:11Z"},
        "report": {"claims": 10, "verified": 9, "dropped": 1, "inferred": 0,
                   "commands": 0, "failed": 0, "tool_version": "0.4.0",
                   "duration_s": 12},
        "map": {"nodes": [], "edges": []},
        "files": {"a.py": {"1": "x = 1"}},
        "tracks": [{"title": "ORIENT", "minutes": 4, "stops": [
            {"id": "one", "title": "One", "kind": "stop", "minutes": 4,
             "lede": "Where the repo starts.", "blocks": [
                 {"type": "prose", "claims": [
                     {"id": "c-001", "text": "It starts here.", "status": "verified",
                      "anchor": {"file": "a.py", "start": 1, "end": 1,
                                 "focus": [1], "sha256": "0" * 64}}]},
                 {"type": "ledger"}]}]}],
        "dropped": [{"id": "c-002", "text": "It caches in Redis.",
                     "file": "a.py", "reason": "file does not exist at this commit"}],
    }


def data_region(html: str) -> str:
    """The JSON text the gate will scrape, exactly as it will scrape it."""
    a = html.index(render.DATA_START) + len(render.DATA_START)
    b = html.index(render.DATA_END)
    body = html[a:b].strip()
    assert body.startswith("const BUNDLES = ") and body.endswith(";"), body[:60]
    return body[len("const BUNDLES = "):-1]


class Splice(unittest.TestCase):
    TEMPLATE = None

    @classmethod
    def setUpClass(cls):
        cls.TEMPLATE = render.load_template()

    def test_both_scrape_markers_survive_in_order(self):
        # verify-contract.js slices between the two DATA markers, then looks for
        # `const BUNDLES =` inside the slice. Out of order or duplicated, it
        # exits 2 — which reads as a broken gate, not a broken generator.
        html = render.splice(self.TEMPLATE, minimal())

        for marker in (render.DATA_START, render.DATA_END, render.BUNDLE_MARKER):
            self.assertEqual(html.count(marker), 1, marker)
        self.assertLess(html.index(render.DATA_START), html.index(render.BUNDLE_MARKER))
        self.assertLess(html.index(render.BUNDLE_MARKER), html.index(render.DATA_END))
        self.assertLess(html.index(render.DATA_END), html.index(render.SCRAPE_MARKER))

    def test_the_dangerous_sequences_are_escaped(self):
        # Every one of these is a real line shape from a real repo, and every one
        # of them defeats a different check: `/*` truncates a comment-aware
        # scrape, `</script>` ends the script element in the browser regardless
        # of JS string context, `@font-face` and `://` trip check-bundle's
        # whole-file greps, and an em dash moves a marker index into the payload.
        payload = minimal()
        payload["files"]["evil.py"] = {
            "1": "# features/*.py re-export these for backward compatibility.",
            "2": "URL = 'https://example.com/a/b.js'  // not a comment",
            "3": "HTML = '<script src=\"//cdn.example.com/x.js\"></script>'",
            "4": "CSS = '@font-face { src: url(x) }'  # @import too",
            "5": "BANNER = 'RENDER — knows only the nine block types'",
        }

        region = data_region(render.splice(self.TEMPLATE, payload))

        for seq in ("/*", "//", "</script>", "@font-face", "@import", "://",
                    "<", "@", "/", "—"):
            self.assertNotIn(seq, region, f"{seq!r} survived the armour")

    def test_json_round_trips_through_the_armour(self):
        # All four escapes are legal JSON string escapes, so `JSON.parse`, `eval`
        # and the browser must all see the original characters back. If they do
        # not, every bundled excerpt is corrupted and every sha256 the gate
        # recomputes from `files` mismatches.
        payload = minimal()
        payload["files"]["evil.py"] = {
            "1": "a = '/* @ // — </script> https://x/y'",
            "2": "b = 'café ✓ ·'",
        }

        got = json.loads(data_region(render.splice(self.TEMPLATE, payload)))

        self.assertEqual(got, {"demo-repo": payload})

    def test_the_payload_cannot_forge_the_end_marker(self):
        # The armour removes every `/`, so a bundled line quoting the marker
        # cannot truncate the gate's slice. This is the assertion in splice().
        payload = minimal()
        payload["files"]["a.py"]["2"] = render.DATA_END + " " + render.DATA_START

        html = render.splice(self.TEMPLATE, payload)

        self.assertEqual(html.count(render.DATA_END), 1)

    def test_a_template_whose_placeholder_is_populated_is_refused(self):
        # The splice needs no brace matcher precisely because the placeholder is
        # exactly `{}`. Against a populated template `index("}")` would land on
        # the first nested object and produce syntactically broken JS.
        populated = self.TEMPLATE.replace("const BUNDLES = {};",
                                          'const BUNDLES = {"x":{"y":1}};', 1)

        with self.assertRaises(RenderError):
            render.splice(populated, minimal())

    def test_a_template_missing_a_marker_names_the_marker(self):
        broken = self.TEMPLATE.replace(render.DATA_END, "/* gone */", 1)

        with self.assertRaises(RenderError) as ctx:
            render.splice(broken, minimal())

        self.assertIn("TRAILHEAD-DATA-END", str(ctx.exception))


class CheckPayload(unittest.TestCase):
    def test_the_shipped_fixture_passes(self):
        # The guard against this module over-policing: fixtures/verified.sample.json
        # is frozen and gate-green, so any complaint here is a bug in check_payload,
        # not in the fixture.
        payload = json.loads(SAMPLE.read_text(encoding="utf-8"))

        self.assertEqual(render.check_payload(payload), [])

    def test_an_inferred_claim_with_an_anchor_is_rejected(self):
        # An anchor is the only thing that makes a sentence render as verified.
        # An inferred claim carrying one is a lie by markup (non-negotiable #2).
        payload = minimal()
        claim = payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0]
        claim["status"] = "inferred"

        problems = render.check_payload(payload)

        self.assertTrue(any("inferred but carries an anchor" in p for p in problems), problems)

    def test_a_verified_claim_without_an_anchor_is_rejected(self):
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0].pop("anchor")

        self.assertTrue(any("no anchor" in p for p in render.check_payload(payload)))

    def test_a_payload_with_no_ledger_block_is_rejected(self):
        # Non-negotiable #3: hiding the dropped-claim count defeats the point of
        # the project, and no gate asks for the ledger block.
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"] = \
            payload["tracks"][0]["stops"][0]["blocks"][:1]

        self.assertTrue(any("no ledger block" in p for p in render.check_payload(payload)))

    def test_a_dropped_claim_hiding_in_a_table_cell_is_caught(self):
        # verify-contract.js builds its "rendered" set from prose claims only,
        # so a dropped sentence carried by a table cell or a trace hop passes it.
        # This is the one failure that would discredit the entire pitch.
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"].insert(1, {
            "type": "table", "caption": "Modules", "sortable": False,
            "columns": ["Module", "Why"],
            "rows": [["a.py", 'It caches<button class="mark" data-claim="c-002">002</button>']],
        })

        self.assertTrue(any("c-002 appears somewhere in tracks" in p
                            for p in render.check_payload(payload)))

    def test_a_missing_generated_at_is_rejected(self):
        # The documented worst case: shell() throws before the first stop is
        # drawn and BOTH gates still pass, because neither executes the page.
        payload = minimal()
        payload["repo"]["generated_at"] = ""

        self.assertTrue(any("generated_at" in p for p in render.check_payload(payload)))

    def test_a_command_exit_that_is_not_a_real_int_is_rejected(self):
        # The page tests truthiness: null renders a green PASSING pill and the
        # string "0" renders a red one. Both fabricate a result (non-negotiable #4).
        for code in ("0", None, True, 0.0):
            with self.subTest(exit=code):
                payload = minimal()
                payload["tracks"][0]["stops"][0]["blocks"].insert(1, {
                    "type": "command", "cmd": "pytest -q", "cwd": ".", "exit": code,
                    "out": "1 passed", "dur": "1.2 s", "env": "captured 2026-07-30"})

                self.assertTrue(any("must be a real int" in p
                                    for p in render.check_payload(payload)))

    def test_a_failing_command_without_a_broken_banner_is_rejected(self):
        payload = minimal()
        payload["report"]["failed"] = 1
        payload["tracks"][0]["stops"][0]["blocks"].insert(1, {
            "type": "command", "cmd": "pytest -q", "cwd": ".", "exit": 1,
            "out": "E   ModuleNotFoundError", "dur": "1.2 s", "env": "captured 2026-07-30"})

        self.assertTrue(any("no BROKEN banner" in p for p in render.check_payload(payload)))

    def test_a_backslash_in_an_anchor_path_is_named_as_the_cause(self):
        # verify-contract.js does an exact-string dict lookup into `files`, so
        # one backslash reports "file not bundled" for every anchor in the file
        # and says nothing about why.
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0]["anchor"]["file"] = "src\\a.py"

        self.assertTrue(any("backslash" in p for p in render.check_payload(payload)))

    def test_an_unknown_block_type_is_rejected(self):
        # B[block.type] is undefined, which takes down this stop and every stop
        # after it — a blank page that both gates pass.
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"].insert(1, {"type": "diagram"})

        self.assertTrue(any("unknown block type" in p for p in render.check_payload(payload)))

    def test_an_all_digit_checkpoint_id_is_rejected(self):
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"].insert(1, {
            "type": "checkpoint", "id": "12", "kind": "single",
            "prompt": "Which module owns the HTTP surface?",
            "options": ["a.py", "b.py"], "answer": 0,
            "provenance": "survey.json entry_points", "explanation": "It is the only one."})

        self.assertTrue(any("all digits" in p for p in render.check_payload(payload)))

    def test_a_report_count_that_disagrees_with_the_ledger_is_rejected(self):
        payload = minimal()
        payload["report"]["dropped"] = 7

        self.assertTrue(any("the ledger lists 1" in p for p in render.check_payload(payload)))


class Render(unittest.TestCase):
    def test_it_writes_inside_the_repo_rather_than_refusing(self):
        # The ledger prints `trailhead build . --out trailhead.html` on screen as
        # the regeneration command. Refusing writes inside the repo would make
        # the one command shown to the audience the one command the tool rejects
        # (plan 7.1). The output is kept out of its own walkthrough by excluding
        # the RESOLVED PATH THIS RETURNS from the survey walk instead.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "src").mkdir(parents=True)
            (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")

            written = render.render(minimal(), repo / "trailhead.html")

            self.assertTrue(written.is_file())
            self.assertEqual(written, (repo / "trailhead.html").resolve())

    def test_it_leaves_no_temp_file_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            render.render(minimal(), Path(tmp) / "out.html")

            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["out.html"])

    def test_it_refuses_rather_than_writing_a_lie(self):
        # No file at all beats a bundle whose claims and ledger disagree: the
        # bad file is the one that ends up on the projector.
        payload = minimal()
        payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0]["status"] = "inferred"

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            with self.assertRaises(RenderError):
                render.render(payload, out)

            self.assertFalse(out.exists())

    def test_the_written_file_is_utf8_with_lf_endings(self):
        # CRLF in the bundle would change nothing the gates read, but it would
        # change every sha256 anyone recomputed from a copy-pasted excerpt.
        with tempfile.TemporaryDirectory() as tmp:
            out = render.render(minimal(), Path(tmp) / "out.html")

            self.assertNotIn(b"\r\n", out.read_bytes())


@unittest.skipUnless(NODE, "node is not on PATH")
class Shell(unittest.TestCase):
    """`shell()` is the one line of the page both gates are blind to.

    They parse the bundle; neither executes it. A payload that throws inside
    `shell()` renders a blank page and passes both. So the function is pulled
    out of the template and run against a stub DOM.
    """

    HARNESS = r"""
const fs = require('fs');
const [tplPath, payloadPath] = process.argv.slice(2);
const tpl = fs.readFileSync(tplPath, 'utf8');
const a = tpl.indexOf('function shell(){');
const b = tpl.indexOf('\n}\n', a);
const src = tpl.slice(a, b + 2);

const el = () => ({ textContent: '', innerHTML: '', hidden: null,
                    classList: { on: new Set(),
                                 toggle(c, v) { v ? this.on.add(c) : this.on.delete(c); } } });
const nodes = { '.brand b': el(), '.meta': el(), '#badge': el(), '#rsel': el() };
const $ = s => nodes[s];
const esc = s => String(s);
const document = { title: '' };
const D = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
const BUNDLES = { [D.repo.name]: D };

eval(src + '\nshell();');

console.log(JSON.stringify({
  title: document.title,
  name: nodes['.brand b'].textContent,
  meta: nodes['.meta'].textContent,
  badge: nodes['#badge'].innerHTML,
  lowconf: nodes['#badge'].classList.on.has('lowconf'),
  selHidden: nodes['#rsel'].hidden,
}));
"""

    def run_shell(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "harness.js"
            harness.write_text(self.HARNESS, encoding="utf-8")
            pj = Path(tmp) / "payload.json"
            pj.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [NODE, str(harness), str(render.template_path()), str(pj)],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_the_shipped_fixture_fills_the_top_bar(self):
        payload = json.loads(SAMPLE.read_text(encoding="utf-8"))

        got = self.run_shell(payload)

        self.assertEqual(got["name"], payload["repo"]["name"])
        self.assertIn(payload["repo"]["commit"], got["meta"])
        self.assertIn("trailhead " + payload["report"]["tool_version"], got["meta"])
        self.assertIn("142", got["badge"])
        self.assertTrue(got["selHidden"], "a one-payload artifact must hide the repo selector")

    def test_the_badge_goes_amber_only_above_forty_percent_dropped(self):
        # The threshold is strictly greater than 0.40 (plan 6.7), so 40/100 is
        # not amber and 41/100 is. This is the badge state a judge looks at
        # hardest, because it only appears when the drop rate is bad.
        for dropped, amber in ((40, False), (41, True)):
            with self.subTest(dropped=dropped):
                payload = minimal()
                payload["report"]["claims"] = 100
                payload["report"]["dropped"] = dropped

                got = self.run_shell(payload)

                self.assertEqual(got["lowconf"], amber)
                self.assertEqual("low confidence" in got["badge"], amber)

    def test_the_amber_percentage_is_recomputed_from_the_two_counts(self):
        payload = minimal()
        payload["report"]["claims"] = 200
        payload["report"]["dropped"] = 101

        got = self.run_shell(payload)

        self.assertIn("51% dropped", got["badge"])

    def test_a_repo_name_containing_markup_is_not_interpolated(self):
        # textContent, not innerHTML — a repo really can be called `<b>`.
        payload = minimal()
        payload["repo"]["name"] = "<script>x</script>"

        got = self.run_shell(payload)

        self.assertEqual(got["name"], "<script>x</script>")
        self.assertNotIn("<script>", got["badge"])

    def test_it_does_not_throw_on_a_payload_missing_its_report(self):
        # Belt-and-braces: render.py refuses this payload, but if one ever
        # reaches the page the top bar must degrade, not blank the walkthrough.
        payload = minimal()
        del payload["report"]

        got = self.run_shell(payload)

        self.assertFalse(got["lowconf"])


@unittest.skipUnless(NODE, "node is not on PATH")
class Ledger(unittest.TestCase):
    """The audit table is the pitch. An empty `<tbody>` is not an acceptable zero.

    Both gates read the payload and neither draws the page, so a ledger that
    renders a heading reading DELETED CLAIM above nothing at all passes every
    check in the project and still looks, on a projector, like a table that
    failed to load. Non-negotiable #3 says the drop count is shown; a count is
    only shown if it is legible as a count.

    The two zeroes are different facts and are asserted separately: nothing
    deleted out of eleven claims is a clean run, nothing deleted out of nothing
    is a degraded one. Printing the same sentence for both would let a run that
    checked nothing wear the result of a run that checked everything.
    """

    HARNESS = r"""
const fs = require('fs');
const [tplPath, payloadPath] = process.argv.slice(2);
const tpl = fs.readFileSync(tplPath, 'utf8');
const grab = name => {
  const a = tpl.indexOf('function ' + name + '(){');
  if (a < 0) throw new Error('template has no function ' + name);
  return tpl.slice(a, tpl.indexOf('\n}\n', a) + 2);
};
const esc = s => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const yourScore = () => '';
const D = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));

eval(grab('ledgerRows') + '\n' + grab('ledgerTable'));
console.log(JSON.stringify({ rows: ledgerRows(), table: ledgerTable() }));
"""

    def run_ledger(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "harness.js"
            harness.write_text(self.HARNESS, encoding="utf-8")
            pj = Path(tmp) / "payload.json"
            pj.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [NODE, str(harness), str(render.template_path()), str(pj)],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def tbody(self, html: str) -> str:
        return html[html.index("<tbody>") + len("<tbody>"):html.index("</tbody>")]

    def test_a_run_that_dropped_nothing_still_renders_a_row(self):
        # The regression: `dropped: []` produced `<tbody></tbody>` under a
        # four-column heading, on the one stop the whole demo points at.
        payload = minimal()
        payload["report"]["dropped"] = 0
        payload["dropped"] = []

        got = self.run_ledger(payload)

        self.assertNotEqual(self.tbody(got["table"]).strip(), "")
        self.assertIn("<tr", got["rows"])
        self.assertIn('colspan="4"', got["rows"])

    def test_a_clean_zero_and_an_empty_zero_do_not_read_the_same(self):
        # 0 of 10 is a clean run. 0 of 0 is a run in which nothing was checked,
        # and saying so is the whole difference between an audit and a boast.
        clean, empty = minimal(), minimal()
        for p in (clean, empty):
            p["report"]["dropped"] = 0
            p["dropped"] = []
        empty["report"]["claims"] = 0

        a = self.run_ledger(clean)["rows"]
        b = self.run_ledger(empty)["rows"]

        self.assertIn("All 10 claims", a)
        self.assertNotEqual(a, b)
        self.assertIn("nothing was claimed", b)
        self.assertNotIn("clean bill of health", a)

    def test_the_deleted_rows_are_still_rendered_when_there_are_any(self):
        # The guard on the guard: the empty state must not have replaced the
        # thing it stands in for.
        payload = minimal()

        got = self.run_ledger(payload)

        self.assertIn("c-002", got["rows"])
        self.assertIn("It caches in Redis.", got["rows"])
        self.assertIn("file does not exist at this commit", got["rows"])
        self.assertNotIn('colspan="4"', got["rows"])

    def test_a_dropped_claim_carrying_markup_is_escaped(self):
        # Dropped text is model output that failed verification — the least
        # trustworthy string in the payload, and the only one rendered as HTML.
        payload = minimal()
        payload["dropped"][0]["id"] = "<img src=x onerror=1>"
        payload["dropped"][0]["text"] = "<script>x</script>"

        got = self.run_ledger(payload)

        self.assertNotIn("<script>", got["rows"])
        self.assertNotIn("<img", got["rows"])

    def test_the_shipped_fixture_lists_its_four_deletions(self):
        payload = json.loads(SAMPLE.read_text(encoding="utf-8"))

        got = self.run_ledger(payload)

        self.assertEqual(got["rows"].count("<tr>"), len(payload["dropped"]))
        self.assertIn(str(payload["report"]["claims"]), got["table"])


if __name__ == "__main__":
    unittest.main()
