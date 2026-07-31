"""Stage 4 VERIFY — the quote → line resolver. The project's risk lives here.

Non-negotiable #7 says the model is never asked for a line number, only for a
verbatim quote, and that ordinary code derives the range. `resolve.py` IS that
code, so every rule it applies is asserted here rather than trusted.

The tests are written against one principle: a drop is honest and is counted on
screen, a wrong resolution is a lie with a `file:line` attached. So most of what
follows asserts that the resolver *refuses* — near misses, repeated snippets,
dedented quotes and quotes that landed outside what the model was shown all have
to come back as a reason, never as a guess.

The classes from `DashClippedWindows` down cover the `trailhead/verified@3`
surfaces (template-parity spec 1.6 and section 5): the dash-avoiding excerpt
windows, and the glossary / node / tour / cols answers that `verify.assemble`
resolves with the same machinery as the prose claims. Dash characters appear
only as escapes, because the house style bars the characters themselves from
this package's source.

Run:  PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from trailhead import resolve, verify


#: One synthetic module. Lines 7-10 and 15-18 are byte-identical on purpose —
#: 12.4% of distinct lines in the calibration repo repeat inside their own file,
#: so a haystack without a duplicate would not be testing the real case.
FILE = [
    '"""Pricing helpers."""',                                              # 1
    "import math",                                                         # 2
    "",                                                                    # 3
    "",                                                                    # 4
    "def price(instrument, curve):",                                       # 5
    '    """Price one instrument off a curve."""',                         # 6
    "    if instrument is None:",                                          # 7
    '        raise ValueError("no instrument")',                           # 8
    "    rate = curve.rate(instrument.tenor)",                             # 9
    "    return instrument.notional * math.exp(-rate * instrument.tenor)",  # 10
    "",                                                                    # 11
    "",                                                                    # 12
    "def price_again(instrument, curve):",                                 # 13
    '    """The duplicate that makes ambiguity real."""',                  # 14
    "    if instrument is None:",                                          # 15
    '        raise ValueError("no instrument")',                           # 16
    "    rate = curve.rate(instrument.tenor)",                             # 17
    "    return instrument.notional * math.exp(-rate * instrument.tenor)",  # 18
]

#: The unique head of the first function: two lines, 61 non-space characters,
#: clears every quality floor and appears exactly once.
UNIQUE = "\n".join(FILE[4:6])

#: Lines 7-8, which appear again at 15-16. Every ambiguity test uses this.
DUPLICATE = "\n".join(FILE[6:8])


class Resolve(unittest.TestCase):
    """`resolve()` against a single file, with no window scoping."""

    def test_two_line_exact_quote_resolves_to_its_line_range(self):
        span, why = resolve.resolve(UNIQUE, FILE)

        self.assertEqual(span, (5, 6))
        self.assertIsNone(why)

    def test_a_quote_that_does_not_appear_is_dropped_not_approximated(self):
        # One character off. difflib would happily land this on line 5; the
        # resolver has no fuzzy path at all, by design.
        span, why = resolve.resolve("def price(instrument, curves):\n" + FILE[5], FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "snippet not found verbatim in file")

    def test_crlf_in_the_quote_matches_an_lf_normalised_file(self):
        # The model is fed text that came through textio (LF only) but a quote
        # can still arrive CRLF-wrapped from a Windows-hosted transport.
        span, why = resolve.resolve(UNIQUE.replace("\n", "\r\n"), FILE)

        self.assertEqual(span, (5, 6))
        self.assertIsNone(why)

    def test_a_lone_carriage_return_is_treated_as_a_line_break(self):
        span, why = resolve.resolve(UNIQUE.replace("\n", "\r"), FILE)

        self.assertEqual(span, (5, 6))

    def test_leading_indentation_must_match_exactly(self):
        # Dedenting a uniformly indented quote is explicitly rejected: the same
        # body text appears at two indentation levels in real code, and the
        # indentation is the main disambiguator we have.
        dedented = "\n".join(line.lstrip() for line in FILE[6:8])

        span, why = resolve.resolve(dedented, FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "snippet not found verbatim in file")

    def test_trailing_whitespace_is_ignored_identically_on_both_sides(self):
        # rstrip is applied to both sides, so it cannot change which occurrence
        # matches — the one whitespace rule that is safe.
        haystack = ["def scale(value, factor):   ", "    return value * factor  \t", "print(1)"]

        span, why = resolve.resolve("def scale(value, factor):\n    return value * factor   ", haystack)

        self.assertEqual(span, (1, 2))
        self.assertIsNone(why)

    def test_blank_lines_around_the_quote_are_trimmed_but_interior_ones_are_kept(self):
        # Lines 10-13 span two interior blanks. If interior blanks were dropped
        # the quote would be two lines and would match nowhere.
        quote = "\n\n" + "\n".join(FILE[9:13]) + "\n  \n"

        span, why = resolve.resolve(quote, FILE)

        self.assertEqual(span, (10, 13))
        self.assertIsNone(why)


class Gutter(unittest.TestCase):
    """The `f"{n:5d}| "` prefix `prompts.py` puts in front of every shown line."""

    def test_line_number_gutter_is_stripped_when_every_line_carries_one(self):
        quote = "    5| def price(instrument, curve):\n    6|     \"\"\"Price one instrument off a curve.\"\"\""

        span, why = resolve.resolve(quote, FILE)

        self.assertEqual(span, (5, 6))
        self.assertIsNone(why)

    def test_a_partially_gutter_prefixed_quote_is_left_alone_and_drops(self):
        # Half-copied output means the model was not copying carefully. Repairing
        # it silently is exactly the guess this resolver refuses to make.
        quote = "    5| def price(instrument, curve):\n" + FILE[5]

        span, why = resolve.resolve(quote, FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "snippet not found verbatim in file")

    def test_stripping_the_gutter_removes_exactly_one_following_space(self):
        # `{n:5d}| ` has one space after the pipe; the rest of the line is the
        # source's own indentation and must survive byte-for-byte.
        quote = "    7|     if instrument is None:\n    8|         raise ValueError(\"no instrument\")"

        span, why = resolve.resolve(quote, FILE, windows=[(5, 10)])

        self.assertEqual(span, (7, 8))


class Guards(unittest.TestCase):
    """The quality floors, checked before any scanning happens."""

    def test_a_single_line_quote_is_refused_rather_than_guessed(self):
        # Measured on the calibration repo: 23.63% of one-line quotes are
        # ambiguous inside their own file. There is no safe single-line path.
        span, why = resolve.resolve(FILE[9], FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "quote shorter than two lines")

    def test_a_quote_that_is_only_blank_lines_is_refused_as_too_short(self):
        span, why = resolve.resolve("\n\n\n", FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "quote shorter than two lines")

    def test_a_quote_longer_than_the_anchor_cap_is_refused(self):
        # An anchor is one contiguous window of at most 24 lines, so a 25-line
        # quote could never become one even if it resolved.
        quote = "\n".join(f"x_{n} = {n}" for n in range(25))

        span, why = resolve.resolve(quote, FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "quote longer than the anchor cap")

    def test_a_quote_of_exactly_the_cap_passes_the_length_guard(self):
        quote = "\n".join(f"x_{n} = {n}" for n in range(24))

        span, why = resolve.resolve(quote, FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "snippet not found verbatim in file")

    def test_a_quote_of_only_punctuation_is_refused_as_too_thin(self):
        span, why = resolve.resolve("    )\n)\n", FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "quote too thin to be unique")

    def test_the_payload_floor_counts_non_space_characters_only(self):
        # 39 non-space characters is thin, 40 is not. Whitespace pads a quote
        # without making it any more unique, so it does not count.
        thin = "\n".join(["a" * 19, "b" * 20])
        fat = "\n".join(["a" * 20, "b" * 20])

        self.assertEqual(resolve.resolve(thin, FILE)[1], "quote too thin to be unique")
        self.assertEqual(resolve.resolve(fat, FILE)[1], "snippet not found verbatim in file")

    def test_a_non_string_quote_is_refused_rather_than_raising(self):
        # resolve() promises never to raise; model output is not trustworthy.
        span, why = resolve.resolve(None, FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "quote shorter than two lines")


class Ambiguity(unittest.TestCase):
    """Repeated snippets, with and without a window to arbitrate against."""

    def test_a_snippet_appearing_twice_is_dropped_not_resolved_to_the_first_hit(self):
        span, why = resolve.resolve(DUPLICATE, FILE)

        self.assertIsNone(span)
        self.assertEqual(why, "snippet ambiguous")

    def test_the_ambiguous_reason_carries_the_match_count_as_its_detail(self):
        # The frozen vocabulary stays a set of literals; the on-screen ledger
        # row gets the count appended at the ledger boundary.
        _, why = resolve.resolve(DUPLICATE, FILE)

        self.assertEqual(why.detail, "2 matches")

    def test_a_snippet_appearing_twice_resolves_when_only_one_copy_was_shown(self):
        # Window scoping narrows; it never relocates. Only the first copy was
        # inside the excerpt the model saw, so only the first copy is in play.
        span, why = resolve.resolve(DUPLICATE, FILE, windows=[(5, 10)])

        self.assertEqual(span, (7, 8))
        self.assertIsNone(why)

    def test_two_copies_inside_the_shown_windows_stay_ambiguous(self):
        span, why = resolve.resolve(DUPLICATE, FILE, windows=[(5, 10), (13, 18)])

        self.assertIsNone(span)
        self.assertEqual(why, "snippet ambiguous")

    def test_a_quote_resolving_outside_every_shown_window_is_dropped(self):
        # Both copies exist, neither was shown. A quote we did not show and the
        # model produced anyway was not copied, whatever else it was.
        span, why = resolve.resolve(DUPLICATE, FILE, windows=[(1, 6)])

        self.assertIsNone(span)
        self.assertEqual(why, "snippet resolved outside the excerpt shown to the model")

    def test_a_match_straddling_a_window_edge_is_not_inside_it(self):
        # Half-shown is not shown: lines 7-8 with only line 7 in the window.
        span, why = resolve.resolve(DUPLICATE, FILE, windows=[(1, 7)])

        self.assertIsNone(span)
        self.assertEqual(why, "snippet resolved outside the excerpt shown to the model")

    def test_an_empty_window_list_shows_nothing_and_resolves_nothing(self):
        span, why = resolve.resolve(UNIQUE, FILE, windows=[])

        self.assertIsNone(span)
        self.assertEqual(why, "snippet resolved outside the excerpt shown to the model")

    def test_windows_do_not_rescue_a_quote_that_is_absent_entirely(self):
        absent = "nothing like this appears\nanywhere in the file at all, not once"

        span, why = resolve.resolve(absent, FILE, windows=[(1, 18)])

        self.assertIsNone(span)
        self.assertEqual(why, "snippet not found verbatim in file")


class Arbitrate(unittest.TestCase):
    """The cross-file wrapper, whose precedence is asserted, not just its strings."""

    APP = ["def handler(request):", "    return price(request.body)", "", "ROUTES = {}"]
    CURVE = ["def price(instrument, curve):"] + FILE[5:10]
    #: Present byte-identically in two files — the same head appears in twenty
    #: files of the calibration repo, which is why rule 1 exists.
    SHARED = ["import math", "", "def scale(value, factor):", "    return value * factor * math.pi"]
    #: 45 non-space characters, so it clears the payload floor and drops for the
    #: reason under test rather than for being thin.
    ABSENT = "def nothing(value, factor):\n    return value + factor + 1"

    def snap(self, **files):
        """file -> (lines, quotable windows), everything shown by default."""
        return {name: (lines, ((1, len(lines)),)) for name, lines in files.items()}

    def test_a_quote_resolving_in_the_cited_file_returns_that_anchor(self):
        snap = self.snap(**{"src/api/app.py": self.APP, "src/pricing/curve.py": self.CURVE})
        cite = {"file": "src/pricing/curve.py", "quote": "\n".join(self.CURVE[0:2])}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(why)
        self.assertEqual(anchor, {"file": "src/pricing/curve.py", "start": 1, "end": 2})

    def test_a_quote_matching_a_different_shown_file_reports_the_wrong_file_reason(self):
        # Without this check a wrong-file anchor renders as verified with a
        # matching sha256 and passes both gates. It is the best-reading row in
        # the ledger and the one most worth getting right.
        snap = self.snap(**{"src/api/app.py": self.APP, "src/pricing/curve.py": self.CURVE})
        cite = {"file": "src/api/app.py", "quote": "\n".join(self.CURVE[0:2])}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "snippet belongs to a different file than the one cited")

    def test_a_quote_in_two_shown_files_reports_ambiguity_across_files(self):
        snap = self.snap(**{"a.py": list(self.SHARED), "b.py": list(self.SHARED)})
        cite = {"file": "zzz/elsewhere.py", "quote": "\n".join(self.SHARED[2:4])}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "snippet ambiguous across files shown to the model")

    def test_cross_file_ambiguity_outranks_the_wrong_file_reason(self):
        # Precedence, not just strings: the quote resolves in both files AND the
        # cited file is one of them. Row 1 must win over row 3, or a genuinely
        # ambiguous snippet would silently anchor to the cited copy.
        snap = self.snap(**{"a.py": list(self.SHARED), "b.py": list(self.SHARED)})
        cite = {"file": "a.py", "quote": "\n".join(self.SHARED[2:4])}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "snippet ambiguous across files shown to the model")

    def test_a_guard_failure_is_reported_before_any_file_is_scanned(self):
        # A one-line quote is a property of the quote, not of a file, so the
        # ledger row must say so even when the cited file was never shown.
        snap = self.snap(**{"a.py": self.APP})
        cite = {"file": "never/shown.py", "quote": "import math"}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "quote shorter than two lines")

    def test_a_cited_file_that_was_never_shown_drops_without_guessing(self):
        snap = self.snap(**{"a.py": self.APP})
        cite = {"file": "never/shown.py", "quote": self.ABSENT}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "snippet not found verbatim in file")

    def test_the_cited_files_own_reason_survives_when_nothing_resolves(self):
        # The informative reason (ambiguous within the file) must not be
        # flattened into a generic not-found by the cross-file wrapper.
        snap = {"src/pricing/curve.py": (FILE, ((1, 18),))}
        cite = {"file": "src/pricing/curve.py", "quote": DUPLICATE}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "snippet ambiguous")

    def test_an_unquotable_window_set_blocks_resolution_in_that_file(self):
        # prompts.py excludes lines 1-12 of every file from the quotable set:
        # `from __future__ import annotations` heads 20 files in the real repo.
        snap = {"a.py": (self.CURVE, ((3, 6),))}
        cite = {"file": "a.py", "quote": "\n".join(self.CURVE[0:2])}

        anchor, why = resolve.arbitrate(cite, snap)

        self.assertIsNone(anchor)
        self.assertEqual(why, "snippet resolved outside the excerpt shown to the model")

    def test_an_empty_snapshot_drops_rather_than_raising(self):
        cite = {"file": "a.py", "quote": self.ABSENT}

        anchor, why = resolve.arbitrate(cite, {})

        self.assertIsNone(anchor)
        self.assertIsNotNone(why)

    def test_a_cite_with_no_quote_is_refused(self):
        anchor, why = resolve.arbitrate({"file": "a.py"}, self.snap(**{"a.py": self.APP}))

        self.assertIsNone(anchor)
        self.assertEqual(why, "quote shorter than two lines")


class ExpandAnchor(unittest.TestCase):
    """Match range → the contiguous window that ships as the anchor."""

    SRC = [
        "import math",                      # 1
        "",                                 # 2
        "",                                 # 3
        "@register",                        # 4
        "def small(x):",                    # 5
        '    """A function well inside the cap."""',  # 6
        "    return x * 2",                 # 7
        "",                                 # 8
        "",                                 # 9
        "def big(x):",                      # 10
    ] + [f"    x += {n}" for n in range(40)] + ["    return x"]

    def test_the_returned_range_always_contains_the_match(self):
        # verify-contract.js:69 fails any focus line outside the anchor, and it
        # fails it after every model call is already spent.
        for ms, me in [(5, 7), (10, 40), (1, 1), (12, 41), (51, 51)]:
            start, end = resolve.expand_anchor(self.SRC, ms, me)

            self.assertLessEqual(start, ms, f"{ms}-{me}")
            self.assertLessEqual(me, end, f"{ms}-{me}")

    def test_a_match_longer_than_the_cap_never_yields_a_negative_pad(self):
        # The reproduced bug: (cap - span) // 2 is -3 for a 30-line match, which
        # produced an anchor strictly inside its own focus.
        start, end = resolve.expand_anchor(self.SRC, 12, 41)

        self.assertEqual((start, end), (12, 41))

    def test_a_short_enclosing_function_becomes_the_anchor(self):
        start, end = resolve.expand_anchor(self.SRC, 6, 7)

        self.assertEqual((start, end), (4, 7))

    def test_the_decorator_is_part_of_the_functions_span(self):
        # ast puts `lineno` on the `def`, so a decorated function read from
        # node.lineno alone would ship an anchor whose first line is orphaned.
        start, _ = resolve.expand_anchor(self.SRC, 5, 5, cap=24)

        self.assertEqual(start, 4)

    def test_a_function_longer_than_the_cap_falls_back_to_a_padded_window(self):
        # 42.1% of the functions in the calibration repo exceed cap 24, so this
        # is the common path and not the fallback.
        start, end = resolve.expand_anchor(self.SRC, 20, 21)

        self.assertEqual(end - start + 1, 24)
        self.assertLessEqual(start, 20)
        self.assertLessEqual(21, end)

    def test_padding_is_clamped_to_the_files_own_bounds(self):
        start, end = resolve.expand_anchor(self.SRC, 1, 2, python=False)

        self.assertEqual(start, 1)
        self.assertLessEqual(end, len(self.SRC))

    def test_a_file_that_does_not_parse_falls_back_to_padding_without_raising(self):
        broken = ["def f(:", "    ???", "    return"] * 5

        start, end = resolve.expand_anchor(broken, 4, 5)

        self.assertLessEqual(start, 4)
        self.assertLessEqual(5, end)

    def test_a_non_python_file_is_never_handed_to_ast(self):
        # ast.parse on TOML falls through silently and would pick a def out of
        # a string; python=False is how the caller says "do not try".
        toml = ["[project]", 'name = "trailhead"', "", "[tool.x]", "y = 1"]

        start, end = resolve.expand_anchor(toml, 2, 3, python=False)

        self.assertLessEqual(start, 2)
        self.assertLessEqual(3, end)


class FocusLines(unittest.TestCase):
    """Focus substrings → absolute line numbers inside the resolved range."""

    QUOTE = "\n".join([
        "def build(parser):",                     # +0
        '    parser.add_argument("--in")',        # +1
        '    parser.add_argument("--out")',       # +2
        "    return parser",                      # +3
    ])

    def test_a_focus_string_resolves_to_the_line_of_its_first_character(self):
        self.assertEqual(resolve.focus_lines(self.QUOTE, ["return parser"], 58), [61])

    def test_a_repeated_token_takes_its_first_occurrence(self):
        # backfill_rk.py alone repeats `parser.add_argument(` 96 times; last-hit
        # or all-hits would highlight the wrong line about half the time.
        self.assertEqual(resolve.focus_lines(self.QUOTE, ["parser.add_argument("], 58), [59])

    def test_a_focus_string_spanning_a_newline_emits_every_line_it_touches(self):
        spanning = '--in")\n    parser.add_argument("--out'

        self.assertEqual(resolve.focus_lines(self.QUOTE, [spanning], 58), [59, 60])

    def test_a_focus_string_that_is_not_in_the_quote_drops_the_focus_only(self):
        self.assertEqual(resolve.focus_lines(self.QUOTE, ["nowhere at all"], 58), [])

    def test_several_focus_strings_are_merged_deduped_and_sorted(self):
        focus = ["return parser", "def build", "return parser"]

        self.assertEqual(resolve.focus_lines(self.QUOTE, focus, 58), [58, 61])

    def test_a_focus_wider_than_four_lines_is_capped(self):
        # A 20-line focus inside a 24-line anchor highlights nothing.
        quote = "\n".join(f"line {n}" for n in range(10))

        self.assertEqual(resolve.focus_lines(quote, [quote], 1), [1, 2, 3, 4])

    def test_focus_lines_are_read_through_the_same_gutter_strip_as_the_quote(self):
        # The narrate parser checks `focus in quote` on the RAW text, so a
        # gutter-prefixed quote yields gutter-prefixed focus strings.
        quote = "    5| def build(parser):\n    6|     return parser"

        self.assertEqual(resolve.focus_lines(quote, ["    6|     return parser"], 5), [6])

    def test_no_focus_at_all_is_not_an_error(self):
        self.assertEqual(resolve.focus_lines(self.QUOTE, [], 58), [])
        self.assertEqual(resolve.focus_lines(self.QUOTE, None, 58), [])


class DropReason(unittest.TestCase):
    """The reason object: a frozen vocabulary literal that carries its detail."""

    def test_a_reason_compares_equal_to_the_frozen_literal(self):
        why = resolve.Drop("snippet ambiguous", "2 matches")

        self.assertEqual(why, "snippet ambiguous")
        self.assertIn(why, resolve.REASONS)

    def test_a_reason_serialises_as_the_bare_literal(self):
        # A ledger row written straight out must not leak the detail into the
        # frozen vocabulary field.
        why = resolve.Drop("snippet ambiguous", "2 matches")

        self.assertEqual(json.dumps({"reason": why}), '{"reason": "snippet ambiguous"}')

    def test_the_ledger_string_appends_the_detail_after_an_em_dash(self):
        why = resolve.Drop("snippet ambiguous", "2 matches")

        self.assertEqual(why.full(), "snippet ambiguous — 2 matches")

    def test_a_reason_without_a_detail_formats_as_itself(self):
        why = resolve.Drop("snippet not found verbatim in file")

        self.assertEqual(why.full(), "snippet not found verbatim in file")

    def test_every_reason_this_module_emits_is_in_the_frozen_vocabulary(self):
        # §6.6 froze the vocabulary at twelve; inventing a thirteenth here would
        # put a string on screen that the contract does not document.
        emitted = [
            resolve.resolve("x", FILE)[1],
            resolve.resolve("\n".join(f"y = {n}" for n in range(30)), FILE)[1],
            resolve.resolve(")\n)", FILE)[1],
            resolve.resolve(DUPLICATE, FILE)[1],
            resolve.resolve(DUPLICATE, FILE, windows=[(1, 6)])[1],
            resolve.resolve("no such\nthing anywhere in this file at all", FILE)[1],
        ]

        for why in emitted:
            self.assertIn(why, resolve.REASONS)


class DashClippedWindows(unittest.TestCase):
    """Spec 1.6: the padded excerpt window prefers not to show dash-bearing
    CONTEXT lines. Match lines are the quote and are never touched."""

    #: Ten lines; line 2 carries an em dash, line 8 an en dash. `python=False`
    #: forces the padded branch, which is the one that clips.
    PAD = [
        "a = 1",
        "b = 'x \u2014 y'",
        "c = 3",
        "d = 4",
        "e = 5",
        "f = 6",
        "g = 7",
        "h = 'x \u2013 y'",
        "i = 9",
        "j = 10",
    ]

    def test_padding_stops_short_of_dash_bearing_context_lines(self):
        start, end = resolve.expand_anchor(self.PAD, 5, 6, python=False)

        self.assertEqual((start, end), (3, 7))

    def test_a_dash_free_file_pads_exactly_as_before(self):
        clean = [f"x{n} = {n}" for n in range(1, 11)]

        start, end = resolve.expand_anchor(clean, 5, 6, python=False)

        self.assertEqual((start, end), (1, 10))

    def test_a_dash_on_a_match_line_never_shrinks_the_match(self):
        # Line 2 is INSIDE the match. The quote ships verbatim (hash integrity
        # wins), so only the context below is clipped.
        start, end = resolve.expand_anchor(self.PAD, 2, 3, python=False)

        self.assertLessEqual(start, 2)
        self.assertGreaterEqual(end, 3)
        self.assertEqual((start, end), (1, 7))

    def test_the_enclosing_def_branch_is_not_clipped(self):
        # A definition is a semantic unit; a dash inside it stays.
        src = [
            "import math",
            "",
            "def f(x):",
            "    # note \u2014 tricky",
            "    return x",
        ]

        start, end = resolve.expand_anchor(src, 3, 5, python=True)

        self.assertEqual((start, end), (3, 5))


#: Two synthetic source files for the assemble-level tests. The quotes below
#: are unique across both files and clear every quality floor.
PRICING = [
    '"""Pricing helpers."""',
    "import math",
    "",
    "def price(instrument, curve):",
    "    rate = curve.rate(instrument.tenor)",
    "    return instrument.notional * math.exp(-rate * instrument.tenor)",
]
LOSS = [
    '"""Loss functions."""',
    "import math",
    "",
    "def qlike(forecast, realised):",
    "    ratio = realised / forecast",
    "    return ratio - math.log(ratio) - 1.0",
]
PRICING_QUOTE = "\n".join(PRICING[3:5])
GLOSS_QUOTE = "\n".join(LOSS[3:5])
NODE_QUOTE = "\n".join(LOSS[4:6])
#: Clears the payload floor (63 non-space characters) but appears nowhere.
ABSENT_QUOTE = ("def missing_function_name(alpha, beta):\n"
                "    return alpha * beta + alpha - beta")

SURVEY = {"repo": {"name": "demo", "commit": "abc1234"}}


def _content(extra=None, claim_text="It prices instruments off a curve."):
    """A minimal content.json: one verified claim plus the mandatory ledger."""
    content = {
        "tracks": [{"title": "ORIENT", "minutes": 5, "stops": [
            {"id": "cover", "title": "Cover", "minutes": 5, "lede": "A lede.",
             "blocks": [
                 {"type": "prose", "claims": [
                     {"id": "c-001", "text": claim_text, "status": "verified",
                      "cite": {"file": "src/pricing.py",
                               "quote": PRICING_QUOTE}}]},
                 {"type": "ledger"},
             ]}]}],
    }
    content.update(extra or {})
    return content


def _map(columns=True):
    """Four boards nodes; @3 columns and viewBox only when asked for."""
    nodes = [{"id": nid, "label": nid[2:], "loc": 100, "files": 2,
              "x": 10, "y": 10, "w": 150,
              "why": "2 files, 100 loc.", "top": ["a.py (3)"]}
             for nid in ("n-core", "n-data", "n-cli", "n-eval")]
    out = {"nodes": nodes, "edges": []}
    if columns:
        out["columns"] = [{"label": "LAYER 1", "x": 100, "line": False},
                          {"label": "LAYER 2", "x": 300, "line": True}]
        out["w"] = 1000
        out["h"] = 300
    return out


def _assemble(extra=None, columns=True, claim_text="It prices instruments off a curve.",
              **kw):
    """Run the real `verify.assemble` against a throwaway on-disk repo, so the
    cited_files -> build_snapshot -> iter_anchors chain is exercised end to
    end rather than stubbed. Extra keywords go straight to `assemble`."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "pricing.py").write_text(
            "\n".join(PRICING) + "\n", encoding="utf-8")
        (root / "src" / "loss.py").write_text(
            "\n".join(LOSS) + "\n", encoding="utf-8")
        return verify.assemble(_content(extra, claim_text), SURVEY,
                               _map(columns), None, root, **kw)


class V3Glossary(unittest.TestCase):
    """Spec 1.1 and section 5: glossary answers become the payload's top-level
    glossary, anchored and hashed like claims, degrading softly."""

    ENTRY = {"term": "QLIKE", "def": "A loss for variance forecasts.",
             "cite": {"file": "src/loss.py", "quote": GLOSS_QUOTE}}

    def test_a_resolving_cite_ships_an_anchor_and_bundles_the_file(self):
        payload, _ = _assemble({"glossary": [dict(self.ENTRY)]})

        entry = payload["glossary"][0]
        self.assertEqual(entry["id"], "qlike")
        self.assertEqual(entry["anchor"]["file"], "src/loss.py")
        self.assertTrue(entry["anchor"]["sha256"])
        bundled = payload["files"]["src/loss.py"]
        for n in range(entry["anchor"]["start"], entry["anchor"]["end"] + 1):
            self.assertIn(str(n), bundled)

    def test_a_failed_cite_keeps_the_definition_and_ledgers_g_slug(self):
        entry = {"term": "VRP", "def": "Implied minus expected variance.",
                 "cite": {"file": "src/loss.py", "quote": ABSENT_QUOTE}}

        payload, _ = _assemble({"glossary": [entry]})

        kept = payload["glossary"][0]
        self.assertEqual(kept["def"], "Implied minus expected variance.")
        self.assertNotIn("anchor", kept)
        rows = {row["id"]: row for row in payload["dropped"]}
        self.assertIn("g-vrp", rows)
        self.assertEqual(rows["g-vrp"]["reason"],
                         "snippet not found verbatim in file")

    def test_terms_are_slugged_and_deduped_first_wins(self):
        entries = [{"term": "QLIKE", "def": "First spelling."},
                   {"term": "qlike!", "def": "Second spelling."}]

        payload, _ = _assemble({"glossary": entries})

        self.assertEqual([e["id"] for e in payload["glossary"]], ["qlike"])
        self.assertEqual(payload["glossary"][0]["def"], "First spelling.")


class V3SlugStripping(unittest.TestCase):
    """The glossary id is what a bare `[[marker]]` in prose slugs to, so a
    trailing parenthetical on the term must never reach the slug: an id of
    `realized-variance-rv` leaves every bare `[[realized variance]]` marker
    dead on screen."""

    def test_a_trailing_parenthetical_is_stripped_from_the_id(self):
        entry = {"term": "realized variance (RV)",
                 "def": "The sum of squared returns."}

        payload, _ = _assemble({"glossary": [entry]})

        self.assertEqual(payload["glossary"][0]["id"], "realized-variance")
        # The TERM keeps its parenthetical; only the id is stripped.
        self.assertEqual(payload["glossary"][0]["term"], "realized variance (RV)")

    def test_an_all_parenthetical_term_falls_back_to_its_full_slug(self):
        entry = {"term": "(RV)", "def": "An abbreviation, nothing else."}

        payload, _ = _assemble({"glossary": [entry]})

        self.assertEqual(payload["glossary"][0]["id"], "rv")

    def test_a_collision_after_stripping_keeps_the_first_and_ledgers_nothing(self):
        entries = [{"term": "realized variance (RV)", "def": "First spelling."},
                   {"term": "realized variance", "def": "Second spelling."}]

        payload, _ = _assemble({"glossary": entries})

        self.assertEqual([e["id"] for e in payload["glossary"]],
                         ["realized-variance"])
        self.assertEqual(payload["glossary"][0]["def"], "First spelling.")
        self.assertFalse([r for r in payload["dropped"]
                          if str(r.get("id") or "").startswith("g-")])

    def test_a_marker_written_as_the_stripped_slug_survives_sanitise(self):
        # The whole point of the strip: the marker the prose actually writes
        # now names a real glossary id and is NOT rewritten to its bare label.
        payload, audit = _assemble(
            {"glossary": [{"term": "realized variance (RV)",
                           "def": "The sum of squared returns."}]},
            claim_text="Computed as [[realized-variance|realized variance]] daily.")

        claim = payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0]
        self.assertIn("[[realized-variance|realized variance]]", claim["text"])
        self.assertEqual(audit["glossary_markers_rewritten"], [])

    def test_a_mid_term_parenthetical_is_not_stripped(self):
        # Only a TRAILING parenthetical is noise; one inside the term is part
        # of its spelling.
        entry = {"term": "P(0) hedge ratio", "def": "The ratio at zero."}

        payload, _ = _assemble({"glossary": [entry]})

        self.assertEqual(payload["glossary"][0]["id"], "p-0-hedge-ratio")


class V3NodeAnswers(unittest.TestCase):
    """Section 5: `node:<gid>` answers enrich the map node, or the node keeps
    its deterministic why/top fallback and the failure is ledgered."""

    ANSWER = {"role": ["Para one.", "Para two."],
              "reads": "YAML configs.", "feeds": "Everything downstream.",
              "key_files": [{"file": "loss.py", "purpose": "the loss"}],
              "concepts": ["registry pattern"],
              "cite": {"file": "src/loss.py", "quote": NODE_QUOTE},
              "caption": "Where the loss lives."}

    def node(self, payload, nid="n-core"):
        return next(n for n in payload["map"]["nodes"] if n["id"] == nid)

    def test_an_answer_with_a_resolving_cite_merges_onto_the_node(self):
        payload, _ = _assemble({"map_answers": {"core": dict(self.ANSWER)}})

        node = self.node(payload)
        self.assertEqual(node["role"], ["Para one.", "Para two."])
        self.assertEqual(node["reads"], "YAML configs.")
        self.assertEqual(node["feeds"], "Everything downstream.")
        self.assertEqual(node["key_files"],
                         [{"file": "loss.py", "purpose": "the loss"}])
        self.assertEqual(node["concepts"], ["registry pattern"])
        self.assertEqual(node["anchor"]["file"], "src/loss.py")
        self.assertEqual(node["anchor_caption"], "Where the loss lives.")
        self.assertIn("src/loss.py", payload["files"])

    def test_a_failed_cite_keeps_the_why_fallback_and_ledgers_n_gid(self):
        answer = dict(self.ANSWER)
        answer["cite"] = {"file": "src/loss.py", "quote": ABSENT_QUOTE}

        payload, _ = _assemble({"map_answers": {"core": answer}})

        node = self.node(payload)
        self.assertNotIn("role", node)
        self.assertNotIn("anchor", node)
        self.assertEqual(node["why"], "2 files, 100 loc.")
        self.assertIn("n-core", {row["id"] for row in payload["dropped"]})

    def test_an_answer_for_a_group_off_the_board_is_ignored(self):
        payload, _ = _assemble({"map_answers": {"ghost": dict(self.ANSWER)}})

        self.assertNotIn("n-ghost",
                         {row["id"] for row in payload["dropped"]})


#: A dive stop as compose emits it on a cold @3 run: prose only, because the
#: map node has no anchor until the `node:<gid>` answer resolves one stage
#: later. The excerpt tests below assert verify closes that gap.
DIVE_STOP = {
    "id": "dive-core", "title": "Inside core", "kind": "stop", "minutes": 4,
    "lede": "A closer read of core.",
    "blocks": [{"type": "prose", "claims": [
        {"id": "c-201", "text": "Core owns the loss function.",
         "status": "verified",
         "cite": {"file": "src/pricing.py", "quote": PRICING_QUOTE}}]}],
}


class V3DiveExcerpt(unittest.TestCase):
    """After a `node:<gid>` anchor resolves, the matching dive stop
    (`dive-<slug(gid)>`) gains the evidence as an excerpt block. Compose could
    not emit it: at compose time the node had no anchor yet."""

    ANSWER = {"role": ["Core routes everything."],
              "cite": {"file": "src/loss.py", "quote": NODE_QUOTE},
              "caption": "Where the loss lives."}

    def build(self, dive_stop=None, answer=None, gid="core"):
        stop = copy.deepcopy(DIVE_STOP if dive_stop is None else dive_stop)
        tracks = _content()["tracks"]
        tracks.append({"title": "DIVE", "minutes": 4, "stops": [stop]})
        return _assemble({"tracks": tracks,
                          "map_answers": {gid: copy.deepcopy(
                              self.ANSWER if answer is None else answer)}})

    def stop(self, payload):
        return payload["tracks"][1]["stops"][0]

    def test_the_dive_stop_gains_an_excerpt_after_its_prose_block(self):
        payload, _ = self.build()

        blocks = self.stop(payload)["blocks"]
        self.assertEqual([b["type"] for b in blocks], ["prose", "excerpt"])
        node = next(n for n in payload["map"]["nodes"] if n["id"] == "n-core")
        self.assertEqual(blocks[1]["anchor"], node["anchor"])
        self.assertEqual(blocks[1]["caption"], "Where the loss lives.")

    def test_the_injected_anchor_lines_are_bundled(self):
        # `iter_anchors` walks excerpt blocks, so the injected anchor's lines
        # must be in `files` or the gate fails every one with `file not bundled`.
        payload, _ = self.build()

        anchor = self.stop(payload)["blocks"][1]["anchor"]
        bundled = payload["files"][anchor["file"]]
        for n in range(anchor["start"], anchor["end"] + 1):
            self.assertIn(str(n), bundled)

    def test_a_captionless_answer_injects_a_blank_caption_not_a_missing_one(self):
        answer = dict(self.ANSWER)
        answer.pop("caption")

        payload, _ = self.build(answer=answer)

        self.assertEqual(self.stop(payload)["blocks"][1]["caption"], "")

    def test_a_stop_that_already_carries_an_excerpt_is_left_alone(self):
        stop = copy.deepcopy(DIVE_STOP)
        stop["blocks"].append({"type": "excerpt", "caption": "Already here.",
                               "cite": {"file": "src/pricing.py",
                                        "quote": PRICING_QUOTE}})

        payload, _ = self.build(dive_stop=stop)

        blocks = self.stop(payload)["blocks"]
        self.assertEqual([b["type"] for b in blocks].count("excerpt"), 1)
        self.assertEqual(blocks[-1]["caption"], "Already here.")

    def test_a_failed_node_cite_injects_nothing(self):
        answer = dict(self.ANSWER)
        answer["cite"] = {"file": "src/loss.py", "quote": ABSENT_QUOTE}

        payload, _ = self.build(answer=answer)

        self.assertEqual([b["type"] for b in self.stop(payload)["blocks"]],
                         ["prose"])

    def test_an_answer_with_no_cite_injects_nothing(self):
        payload, _ = self.build(answer={"role": ["Prose only, no evidence."]})

        self.assertEqual([b["type"] for b in self.stop(payload)["blocks"]],
                         ["prose"])

    def test_a_missing_dive_stop_is_not_an_error(self):
        # The node still gets its anchor; there is simply no stop to enrich.
        payload, _ = _assemble({"map_answers": {"core": dict(self.ANSWER)}})

        node = next(n for n in payload["map"]["nodes"] if n["id"] == "n-core")
        self.assertIn("anchor", node)


class V3Tour(unittest.TestCase):
    """Section 5: tour steps must name nodes on the board; a tour that cannot
    guide (under three steps) is dropped whole, in the report not the ledger."""

    def steps(self, *ids):
        return [{"id": i, "text": f"Step about {i}."} for i in ids]

    def test_an_off_board_step_is_ledgered_and_the_rest_ship(self):
        payload, _ = _assemble(
            {"tour": self.steps("n-core", "n-data", "n-cli", "n-ghost")})

        self.assertEqual([s["id"] for s in payload["map"]["tour"]],
                         ["n-core", "n-data", "n-cli"])
        rows = {row["id"]: row for row in payload["dropped"]}
        self.assertEqual(rows["t-n-ghost"]["reason"], verify.REASON_OFF_BOARD)

    def test_the_whole_tour_drops_below_three_surviving_steps(self):
        payload, audit = _assemble({"tour": self.steps("n-core", "n-data")})

        self.assertNotIn("tour", payload["map"])
        self.assertTrue(any("map tour dropped" in d
                            for d in audit["degradations"]))


class V3Columns(unittest.TestCase):
    """Section 5: the `cols` answer renames the mapper's LAYER placeholders in
    order, and a count mismatch keeps the placeholders."""

    def test_labels_apply_in_order_and_keep_the_geometry(self):
        payload, _ = _assemble({"cols": ["INTERFACE", "CORE"]})

        columns = payload["map"]["columns"]
        self.assertEqual([c["label"] for c in columns], ["INTERFACE", "CORE"])
        self.assertEqual([c["x"] for c in columns], [100, 300])

    def test_a_count_mismatch_keeps_the_placeholders_and_is_reported(self):
        payload, audit = _assemble({"cols": ["ONLY"]})

        self.assertEqual([c["label"] for c in payload["map"]["columns"]],
                         ["LAYER 1", "LAYER 2"])
        self.assertTrue(any("column labels" in d
                            for d in audit["degradations"]))


class V3DashPolicy(unittest.TestCase):
    """Spec 1.6 at assembly time: authored dashes transliterated, ledger
    reasons colon-joined, bundled source lines exempt."""

    def test_authored_dashes_become_comma_and_hyphen(self):
        payload, _ = _assemble(
            claim_text="Fast \u2014 but risky \u2013 sometimes.")

        claim = payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0]
        self.assertEqual(claim["text"], "Fast, but risky - sometimes.")

    def test_a_ledger_reason_detail_is_colon_joined(self):
        entry = {"term": "VRP", "def": "A premium.",
                 "cite": {"file": "src/loss.py", "quote": "one line only"}}

        payload, _ = _assemble({"glossary": [entry]})

        rows = {row["id"]: row for row in payload["dropped"]}
        self.assertEqual(rows["g-vrp"]["reason"],
                         "quote shorter than two lines: 1 lines")
        self.assertTrue(verify.is_known_reason(rows["g-vrp"]["reason"]))

    def test_no_dash_characters_survive_outside_the_files_map(self):
        entry = {"term": "VRP", "def": "Implied \u2014 minus \u2013 expected.",
                 "cite": {"file": "src/loss.py", "quote": ABSENT_QUOTE}}
        payload, _ = _assemble({"glossary": [entry]},
                               claim_text="A claim \u2014 with a dash.")

        outside = {k: v for k, v in payload.items() if k != "files"}
        text = json.dumps(outside, ensure_ascii=False)
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2013", text)

    def test_dead_glossary_markers_are_rewritten_to_their_label(self):
        payload, audit = _assemble(
            {"glossary": [{"term": "QLIKE", "def": "A loss.",
                           "cite": {"file": "src/loss.py",
                                    "quote": GLOSS_QUOTE}}]},
            claim_text="Ranks by [[qlike|QLIKE]] and [[ghost|spooky]] terms.")

        claim = payload["tracks"][0]["stops"][0]["blocks"][0]["claims"][0]
        self.assertEqual(claim["text"],
                         "Ranks by [[qlike|QLIKE]] and spooky terms.")
        self.assertEqual(audit["glossary_markers_rewritten"], ["ghost"])


class V3Contract(unittest.TestCase):
    """Section 5: the contract names what the payload carries. Barren repos
    stay bit-stable at @2; any @3 surface bumps it and adds report.anchors."""

    def test_a_barren_payload_stays_at_v2_with_no_anchors_field(self):
        payload, _ = _assemble(columns=False)

        self.assertEqual(payload["contract"], verify.CONTRACT)
        self.assertNotIn("anchors", payload["report"])
        self.assertNotIn("glossary", payload)

    def test_map_columns_alone_bump_the_contract_to_v3(self):
        payload, _ = _assemble(columns=True)

        self.assertEqual(payload["contract"], verify.CONTRACT_V3)
        self.assertEqual(payload["report"]["anchors"], 1)

    def test_report_anchors_counts_every_shipped_anchor_surface(self):
        payload, audit = _assemble({
            "glossary": [{"term": "QLIKE", "def": "A loss.",
                          "cite": {"file": "src/loss.py",
                                   "quote": GLOSS_QUOTE}}],
            "map_answers": {"core": {"role": ["Para."],
                                     "cite": {"file": "src/loss.py",
                                              "quote": NODE_QUOTE}}},
        })

        # One claim anchor, one glossary anchor, one node anchor.
        self.assertEqual(payload["report"]["anchors"], 3)
        self.assertEqual(payload["report"]["anchors"], audit["anchors"])
        # Anchors are anchors, not claims: the claim math is exactly @2's.
        self.assertEqual(payload["report"]["claims"], 1)
        self.assertEqual(payload["report"]["verified"], 1)


class RegenProvenance(unittest.TestCase):
    """`report.regen` is the run's own regeneration command. The renderer's
    footer prints it verbatim; without it the footer falls back to a neutral
    sentence, never to a claim of hand-built pedigree."""

    def test_the_regen_kwarg_reaches_the_report_verbatim(self):
        line = ("Regenerate: PYTHONPATH=src python -m trailhead build restored "
                "-o out/restored.html --run-commands safe")

        payload, _ = _assemble(regen=line)

        self.assertEqual(payload["report"]["regen"], line)

    def test_no_regen_argument_leaves_the_key_off_the_report(self):
        # Additive: a direct assemble() call without the kwarg emits the exact
        # report it always did.
        payload, _ = _assemble()

        self.assertNotIn("regen", payload["report"])

    def test_a_dash_in_the_regen_line_is_transliterated_to_a_hyphen(self):
        # A command line reads dashes as flags, so both banned dashes become
        # plain hyphens rather than prose's comma join.
        payload, _ = _assemble(
            regen="Regenerate: build a \u2014 then \u2013 done")

        self.assertEqual(payload["report"]["regen"],
                         "Regenerate: build a - then - done")

    def test_the_cli_builds_the_line_from_its_own_arguments(self):
        # The provenance fix itself: the string names THIS run's repo, output
        # and command policy, not the hand-built template's tooling.
        from trailhead import cli

        args = cli.build_parser().parse_args(
            ["build", "restored", "-o", "out/restored.html",
             "--run-commands", "none"])

        self.assertEqual(
            cli._regen_line(args),
            "Regenerate: PYTHONPATH=src python -m trailhead build restored "
            "-o out/restored.html --run-commands none")

    def test_the_cli_line_uses_forward_slashes_whatever_was_typed(self):
        from trailhead import cli

        args = cli.build_parser().parse_args(
            ["build", "repos\\restored", "-o", "out\\restored.html"])

        line = cli._regen_line(args)
        self.assertIn("build repos/restored", line)
        self.assertIn("-o out/restored.html", line)
        self.assertNotIn("\\", line)


if __name__ == "__main__":
    unittest.main()
