"""Stage 4 VERIFY — the quote → line resolver. The project's risk lives here.

Non-negotiable #7 says the model is never asked for a line number, only for a
verbatim quote, and that ordinary code derives the range. `resolve.py` IS that
code, so every rule it applies is asserted here rather than trusted.

The tests are written against one principle: a drop is honest and is counted on
screen, a wrong resolution is a lie with a `file:line` attached. So most of what
follows asserts that the resolver *refuses* — near misses, repeated snippets,
dedented quotes and quotes that landed outside what the model was shown all have
to come back as a reason, never as a guess.

Run:  PYTHONPATH=src py -3.11 -m unittest discover -s tests -v
"""
import json
import unittest

from trailhead import resolve


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


if __name__ == "__main__":
    unittest.main()
