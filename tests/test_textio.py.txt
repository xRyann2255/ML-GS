"""Foundation — the reader, the path key, the hash, the escapes.

textio is the module every stage imports, so it is the module where a bug is
silent and total: a `\\r` that survives normalisation drops 100% of anchors, a
backslash in a path key reports `file not bundled` for every claim in that file,
and one byte of divergence in the sha256 recipe makes `verify-contract.js`
disagree with stage 4 about everything.

These tests are therefore mostly about *sameness*: the same logical lines from a
CRLF file and an LF file must hash to the same value, and the digest must match
a value computed outside this codebase.

Run:  PYTHONPATH=src py -3.11 -m unittest tests.test_textio -v
"""
import json
import tempfile
import unittest
from pathlib import Path

from trailhead import textio


class Tmp(unittest.TestCase):
    """Base for tests that need real files — read_source takes a Path."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.addCleanup(self._dir.cleanup)

    def write(self, name, data: bytes) -> Path:
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p


class ReadSourceNewlines(Tmp):
    def test_crlf_and_lf_produce_identical_lines(self):
        # The whole project rests on this. On this machine CRLF is the majority
        # checkout, and `restored/` — the demo repo — is LF-only, so nothing in
        # the happy path would ever surface a regression here.
        crlf = self.write("crlf.py", b"import os\r\nimport sys\r\n")
        lf = self.write("lf.py", b"import os\nimport sys\n")

        self.assertEqual(
            textio.read_source(crlf).lines,
            textio.read_source(lf).lines,
        )
        self.assertEqual(textio.read_source(crlf).lines, ["import os", "import sys"])

    def test_crlf_and_lf_hash_to_the_same_value(self):
        crlf = textio.read_source(self.write("crlf.py", b"import os\r\nimport sys\r\n"))
        lf = textio.read_source(self.write("lf.py", b"import os\nimport sys\n"))

        self.assertEqual(
            textio.sha256_range(crlf.lines, 1, 2),
            textio.sha256_range(lf.lines, 1, 2),
        )

    def test_lone_carriage_return_is_also_a_line_break(self):
        # Classic-Mac line endings still turn up in vendored files. A lone \r
        # left in place would make the "line" hundreds of characters long and
        # unquotable.
        src = textio.read_source(self.write("cr.py", b"one\rtwo\rthree"))

        self.assertEqual(src.lines, ["one", "two", "three"])

    def test_mixed_endings_normalise_without_inventing_blank_lines(self):
        # Replacing lone \r first would turn every \r\n into two breaks. This is
        # why read_source does \r\n before \r, explicitly.
        src = textio.read_source(self.write("mix.py", b"a\r\nb\rc\nd"))

        self.assertEqual(src.lines, ["a", "b", "c", "d"])

    def test_only_the_phantom_trailing_element_is_dropped(self):
        # "a\nb\n" has two lines; "a\nb\n\n" really does have a blank line 3.
        self.assertEqual(
            textio.read_source(self.write("t1.py", b"a\nb\n")).lines, ["a", "b"]
        )
        self.assertEqual(
            textio.read_source(self.write("t2.py", b"a\nb")).lines, ["a", "b"]
        )
        self.assertEqual(
            textio.read_source(self.write("t3.py", b"a\nb\n\n")).lines, ["a", "b", ""]
        )

    def test_exotic_unicode_breaks_are_not_line_breaks(self):
        # str.splitlines() would report 6 fragments here and desynchronise every
        # index from ast.lineno. The measured example from the plan, verbatim.
        src = textio.read_source(
            self.write("odd.py", "a\x0cb\nc\x85d\ne f".encode("utf-8"))
        )

        self.assertEqual(len(src.lines), 3)
        self.assertEqual(src.lines[0], "a\x0cb")

    def test_empty_file_is_zero_lines_not_one_blank(self):
        self.assertEqual(textio.read_source(self.write("empty.py", b"")).lines, [])


class ReadSourceDecoding(Tmp):
    def test_bom_is_stripped_and_recorded(self):
        # A surviving BOM makes line 1 unquotable: the model quotes `import os`
        # and the file says `﻿import os`.
        src = textio.read_source(self.write("bom.py", b"\xef\xbb\xbfimport os\n"))

        self.assertEqual(src.lines, ["import os"])
        self.assertEqual(src.encoding, "utf-8-sig")
        self.assertFalse(src.degraded)

    def test_bom_file_hashes_the_same_as_the_plain_file(self):
        bom = textio.read_source(self.write("bom.py", b"\xef\xbb\xbfimport os\n"))
        plain = textio.read_source(self.write("plain.py", b"import os\n"))

        self.assertEqual(
            textio.sha256_range(bom.lines, 1, 1),
            textio.sha256_range(plain.lines, 1, 1),
        )

    def test_plain_utf8_is_not_reported_as_utf8_sig(self):
        src = textio.read_source(self.write("u.py", "x = 'é'\n".encode("utf-8")))

        self.assertEqual(src.encoding, "utf-8")
        self.assertFalse(src.degraded)

    def test_pep263_cookie_is_honoured_before_the_fallback(self):
        # cp1252 0x93/0x94 are smart quotes and are not valid utf-8, so this
        # file only decodes correctly if the cookie is read.
        raw = b"# -*- coding: cp1252 -*-\ns = \x93hi\x94\n"
        src = textio.read_source(self.write("cookie.py", raw))

        self.assertFalse(src.degraded)
        self.assertEqual(src.lines[1], "s = “hi”")

    def test_undecodable_bytes_fall_back_and_say_so(self):
        # latin-1 cannot fail, so the file is never skipped — but `degraded`
        # records that the text may not mean what it says.
        src = textio.read_source(self.write("bad.py", b"x = '\xff\xfe'\n"))

        self.assertTrue(src.degraded)
        self.assertEqual(src.encoding, "latin-1")
        self.assertEqual(len(src.lines), 1)

    def test_binary_file_never_reaches_the_parser(self):
        # A PNG named .py. Returning no lines is what keeps ast.parse away from
        # it without a try/except around every call site.
        png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00"
        src = textio.read_source(self.write("fake.py", png))

        self.assertEqual(src.lines, [])
        self.assertEqual(src.note, "not text")
        self.assertFalse(src.degraded)

    def test_text_is_the_string_that_gets_parsed(self):
        src = textio.read_source(self.write("t.py", b"def f():\r\n    return 1\r\n"))

        self.assertEqual(src.text(), "def f():\n    return 1")


class RelKey(Tmp):
    def test_nested_path_becomes_a_forward_slash_key(self):
        p = self.write("src/pkg/mod.py", b"")

        self.assertEqual(textio.rel_key(p, self.root), "src/pkg/mod.py")

    def test_windows_separators_never_survive(self):
        # verify-contract.js:102 does an exact-string dict lookup. One backslash
        # reports `file not bundled` for every anchor in the file.
        p = Path(str(self.root) + "\\src\\pkg\\mod.py")
        self.write("src/pkg/mod.py", b"")

        key = textio.rel_key(p, self.root)

        self.assertEqual(key, "src/pkg/mod.py")
        self.assertNotIn("\\", key)

    def test_a_path_outside_the_root_has_no_key(self):
        outside = self.root.parent / "elsewhere" / "mod.py"

        self.assertIsNone(textio.rel_key(outside, self.root))

    def test_a_trailing_dot_segment_in_the_root_does_not_change_the_key(self):
        p = self.write("src/mod.py", b"")

        self.assertEqual(textio.rel_key(p, self.root / "."), "src/mod.py")


class Sha256Range(unittest.TestCase):
    # Computed outside this codebase and cross-checked in Node:
    #   node -e "console.log(require('crypto').createHash('sha256')
    #            .update('import os\nimport sys','utf8').digest('hex'))"
    # If this literal ever needs changing, every anchor in the project is about
    # to drop — check the gate before changing the test.
    LINES = ["import os", "import sys", "", "def f():", "    return 1"]
    HASH_1_2 = "76b25f263d1e6b8c90944967fdac9875cd01dd346fff02ac6fc656a2fb3f6ca4"

    def test_matches_the_hand_computed_digest(self):
        self.assertEqual(textio.sha256_range(self.LINES, 1, 2), self.HASH_1_2)

    def test_is_one_based_and_inclusive(self):
        # sha256("def f():\n    return 1") — the last two lines, not the last
        # one and not lines 3-4.
        self.assertEqual(
            textio.sha256_range(self.LINES, 4, 5),
            textio.sha256_range(["def f():", "    return 1"], 1, 2),
        )

    def test_single_line_carries_no_trailing_newline(self):
        # "no trailing newline" is the half of the recipe that is easiest to get
        # wrong and impossible to notice without a fixed digest.
        self.assertEqual(
            textio.sha256_range(["def price(x):"], 1, 1),
            "97e36d41375cf9e97094e3567cddab6801c0ecfee2ef20a5a40cad4bbe530962",
        )

    def test_blank_lines_inside_a_range_are_hashed_as_themselves(self):
        self.assertEqual(
            textio.sha256_range(["a", "b", "c"], 1, 3),
            "ea7fb08b7a2dc4619ffb7c7bb38d95a2047935fa165d71b12efd3852a2e6d0cc",
        )

    def test_out_of_range_raises_rather_than_hashing_a_short_slice(self):
        # A truncated slice produces a digest that can never match the gate's
        # recomputation, and the failure would surface three stages later.
        with self.assertRaises(ValueError):
            textio.sha256_range(self.LINES, 0, 2)
        with self.assertRaises(ValueError):
            textio.sha256_range(self.LINES, 4, 99)
        with self.assertRaises(ValueError):
            textio.sha256_range(self.LINES, 3, 2)


class EscapeAndCell(unittest.TestCase):
    def test_esc_html_covers_all_five(self):
        self.assertEqual(
            textio.esc_html("""<a href="x">&'"""),
            "&lt;a href=&quot;x&quot;&gt;&amp;&#x27;",
        )

    def test_esc_html_escapes_the_ampersand_first(self):
        # &lt; must not become &amp;lt;.
        self.assertEqual(textio.esc_html("&lt;"), "&amp;lt;")

    def test_esc_html_coerces_a_non_string(self):
        self.assertEqual(textio.esc_html(1240), "1240")

    def test_cell_escapes_the_value(self):
        self.assertEqual(
            textio.cell("<script>alert(1)</script>"),
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )

    def test_cell_adds_whitelisted_markup_around_the_escaped_value(self):
        # The shipped fixture's `<code>src/pricing/</code>` must render as
        # markup; blanket-escaping the finished cell would show the tags.
        self.assertEqual(textio.cell("src/pricing/", code=True), "<code>src/pricing/</code>")

    def test_cell_still_escapes_inside_the_wrapper(self):
        self.assertEqual(
            textio.cell("a < b & c", code=True),
            "<code>a &lt; b &amp; c</code>",
        )

    def test_cell_whitelist_composes(self):
        self.assertEqual(textio.cell("x", code=True, bold=True), "<b><code>x</code></b>")

    def test_cell_never_lets_markup_arrive_in_the_data(self):
        # A model-authored or repo-derived `<b>` must not become live markup on
        # a surface with no claim marker on it.
        self.assertNotIn("<b>", textio.cell("<b>owned</b>"))


class ArmourJson(unittest.TestCase):
    # Every hazard the two gates grep for, in one string.
    HAZARD = (
        "# /* not a comment */ // nor this "
        '<script src="https://a/b.js"></script> '
        "</style> @font-face @import "
        "RENDER — knows only src/pricing/engine.py"
    )

    def payload(self):
        return {"files": {"src/x.py": {"1": self.HAZARD}}, "n": 12, "ok": True}

    def test_round_trips_through_json_loads(self):
        # All four are legal JSON string escapes, so JSON.parse, eval and the
        # browser see the original characters back unchanged.
        raw = json.dumps(self.payload())

        self.assertEqual(json.loads(textio.armour_json(raw)), self.payload())

    def test_removes_the_characters_the_gates_grep_for(self):
        armoured = textio.armour_json(json.dumps(self.payload()))

        self.assertNotIn("<", armoured)
        self.assertNotIn("@", armoured)
        self.assertNotIn("/", armoured)
        self.assertNotIn("—", armoured)

    def test_the_slash_escape_actually_removes_the_slash(self):
        # The obvious `\/*` rule is a no-op: `\/*` still CONTAINS `/*`, which is
        # exactly what a comment-aware scraper greps for. Only / works.
        armoured = textio.armour_json('"a /* b // c"')

        self.assertNotIn("/*", armoured)
        self.assertNotIn("//", armoured)
        self.assertIn("\\u002f", armoured)

    def test_closing_script_tag_cannot_survive(self):
        # This one is a real browser bug, not just a grep artefact: a bundled
        # `</script>` ends the script element regardless of JS string context.
        armoured = textio.armour_json('"x </script> y"')

        self.assertNotIn("</script>", armoured)

    def test_structural_json_is_untouched(self):
        # The proof that a blanket replace is safe: in JSON these four can only
        # occur inside string literals.
        raw = json.dumps({"a": [1, 2], "b": None})

        self.assertEqual(textio.armour_json(raw), raw)

    def test_leaves_ascii_source_text_alone_apart_from_the_four(self):
        armoured = textio.armour_json('"def f(x): return x + 1"')

        self.assertEqual(armoured, '"def f(x): return x + 1"')


if __name__ == "__main__":
    unittest.main()
