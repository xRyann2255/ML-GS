"""Stage 4 VERIFY — quote → line range. Deterministic. No model.

This is where non-negotiable #7 is actually enforced. The model is never asked
for a line number, because models count badly and copy well; it is asked to
quote, and this module derives the range in ordinary code. Measured, that is the
difference between a ~40% claim-drop rate and ~3%.

The design rule for everything below is that a **drop is honest and a wrong
resolution is a lie**. A dropped claim is counted on screen and is part of the
pitch; an anchor that landed in the wrong place renders as `verified`, carries a
matching sha256 and passes both gates while pointing the reader at code that
never supported the sentence. So every fuzzy repair that could change *which*
occurrence matches is rejected outright:

    difflib / SequenceMatcher similarity   ·  lstrip-per-line matching
    first-hit-wins on ambiguity            ·  AST- or token-normalised matching
    dedenting a uniformly indented quote   ·  accepting single-line quotes

Only two normalisations touch the haystack at all — CRLF folding and a trailing
rstrip — and neither can move a match from one occurrence to another.

    resolve        one quote against one file, window-scoped
    arbitrate      the same quote against every file the model was shown
    expand_anchor  match range → the contiguous window that ships
    focus_lines    focus substrings → absolute line numbers inside that window

What lives elsewhere: `verify.py` owns `verify_claim`, the sha256 (via
`textio.sha256_range`), the ledger rows and the `files` bundle. Nothing here
reads the disk, so the whole module is testable from two lists of strings.
"""
import ast
import re
from typing import Mapping, Sequence

#: `prompts.py` renders every shown line as `f"{n:5d}| {line}"`, so a careful
#: model copying from the prompt hands the gutter straight back. `\s?` eats the
#: single space that follows the pipe and NOT the source's own indentation,
#: which is the main disambiguator a quote has.
_GUTTER = re.compile(r"^\s*\d+\s*\|\s?")

#: The subset of the §6.6 vocabulary this module can emit. `verify.py` owns the
#: rest (missing file, out-of-range lines, hash mismatch, unparseable output).
#: Frozen literals: the on-screen detail is appended at the ledger boundary by
#: `Drop.full()`, never baked into the reason itself.
REASONS = frozenset({
    "snippet not found verbatim in file",
    "snippet ambiguous",
    "snippet ambiguous across files shown to the model",
    "snippet belongs to a different file than the one cited",
    "snippet resolved outside the excerpt shown to the model",
    "quote too thin to be unique",
    "quote shorter than two lines",
    "quote longer than the anchor cap",
})

#: `file -> (lines, quotable windows)`. Quotable ⊂ shown: `prompts.py` rule 5
#: excludes lines 1-12 of every file from the quotable set while still showing
#: them, because `from __future__ import annotations` / blank / `import logging`
#: clears every quality floor and heads twenty files in the calibration repo.
Snapshot = Mapping[str, tuple[list[str], Sequence[tuple[int, int]] | None]]

#: What `arbitrate` hands back: the file and the range the QUOTE occupies.
#: `verify.py` widens it with `expand_anchor`, adds `focus` and `sha256`, and
#: only then is it a contract anchor.
Anchor = dict


class Drop(str):
    """A drop reason: a frozen vocabulary literal that also carries its detail.

    §6.6 freezes twelve reason strings and `verified-contract.md` documents
    them, but the ledger row is much more readable when it names the match count
    — "snippet ambiguous — 2 matches" tells the audience the resolver found the
    same code twice, which is the whole point of the row.

    Subclassing `str` is what lets both be true at once. `why == "snippet
    ambiguous"` is True, `json.dumps` writes the bare literal, and a caller that
    never learns about this class still writes a valid vocabulary string into
    the ledger. `full()` is the formatted form for the on-screen reason.

    (No `__slots__`: CPython refuses a non-empty one on a str subclass.)
    """

    def __new__(cls, code: str, detail: str | None = None) -> "Drop":
        self = super().__new__(cls, code)
        self.code = code
        self.detail = detail
        return self

    def full(self) -> str:
        """`code — detail`, the string the ledger shows."""
        return f"{self.code} — {self.detail}" if self.detail else self.code


def resolve(quote: str, lines: list[str], *,
            windows: Sequence[tuple[int, int]] | None = None,
            min_lines: int = 2, max_lines: int = 24,
            min_payload: int = 40) -> tuple[tuple[int, int] | None, str | None]:
    """-> ((start, end), None) 1-based inclusive, or (None, reason).

    Never raises. Never guesses.

    `windows` are the 1-based inclusive ranges of this file that were quotable
    in the prompt. They **narrow, never relocate**: a match must be wholly
    inside one of them to count, and a quote that resolves only outside them was
    not copied from what we showed, whatever else it was. `None` means "do not
    scope"; an empty sequence means "nothing from this file was quotable", which
    is a real state and not the same thing.

    The three floors (`min_lines`, `max_lines`, `min_payload`) are calibrated,
    not arbitrary — see the module docstring of `test_resolve.py` and §6.1. With
    the 40-character payload floor and window scoping, two-line quotes drop from
    12.80% ambiguous to 3.26%.
    """
    q, reason = _prepare(quote, min_lines=min_lines, max_lines=max_lines,
                         min_payload=min_payload)
    if reason is not None:
        return None, reason

    # rstrip is applied to both sides. It is the only haystack normalisation
    # there is, and it cannot change which occurrence matches.
    hay = [line.rstrip() for line in lines]

    # The one and only matching operation in this module.
    k = len(q)
    hits = [i for i in range(len(hay) - k + 1) if hay[i:i + k] == q]
    spans = [(i + 1, i + k) for i in hits]

    if windows is None:
        if not spans:
            return None, Drop("snippet not found verbatim in file")
        if len(spans) > 1:
            return None, Drop("snippet ambiguous", f"{len(spans)} matches")
        return spans[0], None

    shown = [s for s in spans if _inside(s, windows)]
    if len(shown) == 1:
        return shown[0], None
    if len(shown) > 1:
        return None, Drop("snippet ambiguous", f"{len(shown)} matches")
    if spans:
        return None, Drop("snippet resolved outside the excerpt shown to the model",
                          f"{len(spans)} matches, none inside the excerpt")
    return None, Drop("snippet not found verbatim in file")


def arbitrate(cite: dict, snap: Snapshot) -> tuple[Anchor | None, str | None]:
    """The same quote against every file shown to the model, in precedence order.

    `resolve()` sees one file and therefore cannot produce the single most
    damning ledger row there is — the one that says the model quoted real code
    from the wrong file. This wrapper can, and the precedence below is fixed
    because two orderings give two different strings for the same failure and
    the ledger is the pitch:

      1. resolves in more than one shown file  → ambiguous across files
      2. resolves in exactly one file, not the cited one → wrong file
      3. otherwise → the cited file's own window arbitration

    Without rule 2 a wrong-file anchor ships as `verified` with a sha256 that
    matches, and both gates pass.
    """
    quote = cite.get("quote") or ""
    cited = cite.get("file")

    # A floor failure is a property of the quote, not of any file, so it is
    # reported before a single file is scanned. Otherwise a one-line quote whose
    # cited file was never shown would report "not found" and hide the real
    # reason from the ledger.
    _, reason = _prepare(quote)
    if reason is not None:
        return None, reason

    found: dict[str, tuple[int, int]] = {}
    reasons: dict[str, str] = {}
    for path in sorted(snap):                       # sorted: the row must not
        lines, windows = snap[path]                 # depend on dict order
        span, why = resolve(quote, lines, windows=windows)
        if span is not None:
            found[path] = span
        else:
            reasons[path] = why

    if len(found) > 1:
        return None, Drop("snippet ambiguous across files shown to the model",
                          "matches " + ", ".join(sorted(found)))
    if len(found) == 1:
        path, (start, end) = next(iter(found.items()))
        if path != cited:
            return None, Drop("snippet belongs to a different file than the one cited",
                              f"cited {cited}, found in {path}")
        return {"file": path, "start": start, "end": end}, None

    if cited in reasons:
        return None, reasons[cited]
    return None, Drop("snippet not found verbatim in file",
                      f"{cited} was not among the files shown to the model")


def expand_anchor(lines: list[str], ms: int, me: int, *, cap: int = 24,
                  python: bool = True) -> tuple[int, int]:
    """Widen a match range into the window that ships as the anchor.

    A reader who is shown only the two lines that were quoted cannot tell what
    they belong to, so the anchor is widened to the enclosing definition where
    that fits inside `cap`, and to a centred padded window where it does not.
    42.1% of the functions in the calibration repo exceed cap 24, so the padded
    branch is the common path and not a fallback.

    Steps 2 and 3 are load-bearing, not defensive. `(cap - span) // 2` on a
    30-line match is -3, which produced an anchor *strictly inside its own
    focus* — `verify-contract.js:69` then fails with "focus line 32 outside
    35-58", after every model call has already been spent. `max(0, …)` plus the
    final `min`/`max` make focus containment true by construction instead of by
    argument.

    Pass `python=False` for anything that is not a `.py` file: `ast.parse` on
    TOML raises and falls through silently, and on the unlucky input it does not
    raise it picks a `def` out of a string literal.
    """
    span = _enclosing_def(lines, ms, me, cap) if python else None
    if span is not None:
        start, end = span
    else:
        pad = max(0, (cap - (me - ms + 1)) // 2)
        start = max(1, ms - pad)
        end = min(max(len(lines), 1), me + pad)
        start, end = _clip_dash_context(lines, start, end, ms, me)

    # Containment by construction. Never remove these two lines.
    return min(start, ms), max(end, me)


#: The two characters the dash policy (template-parity spec 1.6) keeps out of
#: authored text. Source lines are the repo's own bytes and are exempt from
#: transliteration, so the excerpt window instead PREFERS not to show a context
#: line that carries one. Escapes, not literals: the house style bars the
#: characters themselves from this package's source.
_DASH_CHARS = ("\u2014", "\u2013")


def _clip_dash_context(lines: list[str], start: int, end: int,
                       ms: int, me: int) -> tuple[int, int]:
    """Best effort: shrink a padded window off dash-bearing CONTEXT lines.

    Bundled source is shipped verbatim (hash integrity wins over the dash
    policy), so the only lever is which context lines the window includes at
    all. Scanning outward from the match, the window stops just short of the
    first context line above or below it that carries an em or en dash. Match
    lines themselves are never touched: `start` can only move up to `ms` and
    `end` only down to `me`, so containment, and with it focus containment,
    holds exactly as before. The trade is deliberate: less context beats a
    dash-bearing line in the artifact, and the quoted evidence never shrinks.
    """
    for n in range(ms - 1, start - 1, -1):
        if any(d in lines[n - 1] for d in _DASH_CHARS):
            start = n + 1
            break
    for n in range(me + 1, end + 1):
        if any(d in lines[n - 1] for d in _DASH_CHARS):
            end = n - 1
            break
    return start, end


def focus_lines(quote: str, focus: Sequence[str] | None, start: int, *,
                cap: int = 4) -> list[int]:
    """Focus substrings → absolute 1-based line numbers, or [] for each miss.

    `cite.focus` is an array of substrings of `quote`, never line numbers, for
    the same reason the quote is: the model is not asked to count. Each string
    resolves to the line holding its **first character** at its **first
    occurrence** in the quote — `backfill_rk.py` alone repeats
    `parser.add_argument(` 96 times, so last-hit or all-hits would highlight the
    wrong line about half the time.

    A focus that spans a newline emits every line it touches, because a model
    asked to point at a signature naturally returns both lines of a wrapped one.
    The `cap` then keeps a runaway focus from highlighting the whole anchor: a
    20-line focus inside a 24-line anchor highlights nothing.

    A focus string that cannot be placed **drops the focus, not the claim** — it
    is a presentation detail, and the sentence is still anchored.

    Every returned line lies inside the quote's own range by construction, which
    is what makes `verify-contract.js:73-74` pass once `expand_anchor` has been
    applied.
    """
    q = _normalise(quote)
    if not q or not focus:
        return []

    text = "\n".join(q)
    out: set[int] = set()
    for raw in focus:
        if not isinstance(raw, str) or not raw:
            continue

        # The narrate parser checks `focus in quote` against the RAW quote, so a
        # gutter-prefixed quote yields gutter-prefixed focus strings. Try the
        # string as given first, then the same normalisation the quote got.
        needle = raw
        at = text.find(needle)
        if at < 0:
            needle = "\n".join(_normalise(raw))
            at = text.find(needle) if needle else -1
        if at < 0:
            continue

        first = text.count("\n", 0, at)
        last = text.count("\n", 0, at + len(needle) - 1)
        out.update(range(start + first, start + min(last, first + cap - 1) + 1))

    return sorted(out)


def _prepare(quote: str, *, min_lines: int = 2, max_lines: int = 24,
             min_payload: int = 40) -> tuple[list[str] | None, str | None]:
    """Normalise a quote and apply the quality floors, in that order.

    The floors are checked after normalisation because a gutter, a trailing
    blank line and trailing whitespace are all artefacts of how the quote was
    transported, not of what the model actually copied.
    """
    q = _normalise(quote)

    if len(q) < min_lines:
        # 23.63% of one-line quotes are ambiguous inside their own file. There
        # is no safe single-line path, so there is no single-line path.
        return None, Drop("quote shorter than two lines", f"{len(q)} lines")
    if len(q) > max_lines:
        # An anchor is one contiguous window of at most `cap` lines, so a longer
        # quote could not become one even if it resolved.
        return None, Drop("quote longer than the anchor cap", f"{len(q)} lines")

    payload = len(re.sub(r"\s", "", "".join(q)))
    if payload < min_payload:
        return None, Drop("quote too thin to be unique", f"{payload} characters")
    return q, None


def _normalise(quote: str) -> list[str]:
    """The exact normalisation of §6.1, in order. No rule here can move a match.

    A non-string quote returns [] rather than raising: model output is not
    trustworthy and `resolve()` promises never to raise.
    """
    if not isinstance(quote, str):
        return []

    # 1. CRLF first, then lone CR. The other order turns every CRLF into a
    #    blank line.
    q = quote.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # 2. Gutter strip, all-or-nothing. A partially prefixed quote means the
    #    model was not copying carefully; repairing it silently is exactly the
    #    guess this module refuses to make, so it is left alone and it drops.
    body = [line for line in q if line.strip()]
    if body and all(_GUTTER.match(line) for line in body):
        q = [_GUTTER.sub("", line) for line in q]

    # 3. Leading and trailing wholly-blank lines are transport artefacts.
    #    Interior blanks are content and are kept.
    while q and not q[0].strip():
        q.pop(0)
    while q and not q[-1].strip():
        q.pop()

    # 4. rstrip only. Left-side whitespace is never touched on either side.
    return [line.rstrip() for line in q]


def _inside(span: tuple[int, int], windows: Sequence[tuple[int, int]]) -> bool:
    """Is `span` wholly inside one shown window? Half-shown is not shown."""
    start, end = span
    return any(w0 <= start and end <= w1 for w0, w1 in windows)


def _enclosing_def(lines: list[str], ms: int, me: int,
                   cap: int) -> tuple[int, int] | None:
    """The smallest def/class containing the match and fitting inside `cap`.

    The span starts at the first decorator, not at `def`: `ast` puts `lineno` on
    the `def` line, so an anchor read from `node.lineno` alone opens on a line
    whose `@register` above it has been cut away.

    Returns None for anything that does not parse. A file that reaches stage 4
    with a syntax error is a real state — survey records it — and it must fall
    through to padding rather than take the generator down at hour 9.
    """
    try:
        tree = ast.parse("\n".join(lines))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None

    best: tuple[int, int] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        end = getattr(node, "end_lineno", None)
        if end is None:
            continue
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        if start > ms or me > end or end - start + 1 > cap:
            continue
        if best is None or end - start < best[1] - best[0]:
            best = (start, end)
    return best
