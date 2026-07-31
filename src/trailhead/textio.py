"""Foundation — THE file reader, THE path key, the hash, the escapes.

Not a stage. Every stage imports this, and that is the whole point: a line read
at survey time must hash identically at verify time and must be byte-identical
to the line `tools/verify-contract.js` recomputes from the shipped bundle. Three
independent readers would be three sha256 recipes and a 100% claim-drop rate.

What lives here and nowhere else:

    read_source    the only function permitted to read a source file
    rel_key        the only permitted producer of a repo-relative path key
    sha256_range   the anchor hash, exactly as docs/verified-contract.md states
    esc_html/cell  the only way a string reaches a raw-interpolation surface
    armour_json    the four escapes that stop the payload tripping the gates

Windows is the hostile case. `core.autocrlf=true` with no `.gitattributes` means
CRLF is the majority checkout on this machine, and a `\\r` that survives to the
hash makes every verbatim model quote unfindable and every digest wrong. Step 3
of read_source is the fix and it is not optional.
"""
import hashlib
import html
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

#: Bytes scanned for a NUL before we are willing to call a file text. A PNG
#: named `.py` must never reach `ast.parse`, and 8 KB is well past any header.
_BINARY_SNIFF_BYTES = 8192

_UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class Source:
    """One decoded, newline-normalised file.

    `lines` is 0-indexed here and 1-based everywhere in the contract; the
    conversion happens once, in `sha256_range`, so no caller does the arithmetic
    twice. `degraded` records that we fell back to latin-1 and the text may not
    mean what it says — survey reports it rather than hiding it. `note` is
    "not text" when the file was never decoded at all, and stage 1 replaces it
    with "syntax error" (via `dataclasses.replace`) when `ast.parse` refuses.
    """

    lines: list[str]
    encoding: str
    degraded: bool
    note: str | None

    def text(self) -> str:
        """The normalised text — exactly the string that gets parsed and hashed.

        Callers must feed *this* to `ast.parse`, not a fresh read of the file.
        Parsing different bytes than you hashed is how `ast.lineno` drifts from
        the line numbers in the bundle.
        """
        return "\n".join(self.lines)


def read_source(path: Path) -> Source:
    """Read one file the one permitted way.

    The order below is load-bearing and is spelled out in the plan §3.1:
    sniff for binary, decode, normalise newlines, split, drop the phantom
    trailing element. Deviating in any step desynchronises this module's line
    index from `ast.lineno`, from git blame, and from the reader's editor.
    """
    b = path.read_bytes()
    if b"\x00" in b[:_BINARY_SNIFF_BYTES]:
        return Source([], "", False, "not text")

    text, encoding, degraded = _decode(b)

    # In this order, explicitly. Replacing lone \r first would turn every CRLF
    # into a blank line.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # NEVER str.splitlines(). It also breaks on \x0b \x0c \x1c \x1d \x1e \x85
    # \u2028 and \u2029 (spelled escaped on purpose), none of which end a line
    # for ast, for git, or for the person reading the file. Measured:
    # 'a\x0cb\nc\x85d\ne f'.splitlines() is 6 fragments; .split('\n') is 3.
    lines = text.split("\n")

    # A file ending in a newline splits to a final "" that is not a line. Only
    # the last one — "a\n\n" really does have a blank line 2.
    if lines and lines[-1] == "":
        lines.pop()

    return Source(lines, encoding, degraded, None)


def _decode(b: bytes) -> tuple[str, str, bool]:
    """Bytes to text, preferring truth over success, but never failing.

    utf-8-sig first because it strips a BOM and is byte-identical to utf-8
    otherwise. Then a PEP 263 cookie, because a repo old enough to declare
    `# -*- coding: cp1252 -*-` means it. latin-1 last: it cannot raise for any
    byte sequence, so a file is never skipped for being undecodable — it is
    decoded, flagged `degraded`, and the flag is reported rather than swallowed.
    """
    try:
        text = b.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    else:
        return text, ("utf-8-sig" if b.startswith(_UTF8_BOM) else "utf-8"), False

    cookie = _cookie_encoding(b)
    if cookie is not None:
        try:
            return b.decode(cookie), cookie, False
        except (UnicodeDecodeError, LookupError):
            pass

    return b.decode("latin-1"), "latin-1", True


def _cookie_encoding(b: bytes) -> str | None:
    """The PEP 263 encoding declared in the first two lines, if any.

    `tokenize.detect_encoding` returns "utf-8" when there is no cookie, which we
    have already tried and which failed — reporting it would send the caller
    round the same loop, so it is filtered out here.
    """
    try:
        enc, _ = tokenize.detect_encoding(io.BytesIO(b).readline)
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return None
    if enc.lower().replace("_", "-") in ("utf-8", "utf-8-sig"):
        return None
    return enc


def rel_key(p: Path, root: Path) -> str | None:
    """The repo-relative key, forward slashes, or None if `p` escapes `root`.

    This is the ONLY permitted value for `files` keys, `anchor.file`,
    `dropped[].file` and `map.nodes[].label`. Never `str(Path)`, never
    `os.path.relpath`, never `os.path.join`: `verify-contract.js:102` does an
    exact-string dict lookup, so one backslash reports `file not bundled` for
    every anchor in that file — after the model calls are already spent.

    `.resolve()` on both sides is what makes a junction or symlink that points
    outside the repo raise ValueError instead of silently producing a `..` key.
    """
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def sha256_range(lines: Sequence[str], start: int, end: int) -> str:
    """Hex SHA-256 of lines `start..end`, 1-based inclusive.

    Joined with "\\n", NO trailing newline, NO line numbers, UTF-8 — exactly
    docs/verified-contract.md, exactly `verify-contract.js:92-96,114`. One byte
    of divergence drops every anchor in the project, so this function is
    deliberately four lines long and has no options.

    `lines` must come from `read_source`, which has already stripped `\\r`.

    Out-of-range input raises rather than hashing a short slice: a silently
    truncated range yields a digest that can never match the gate's
    recomputation, and the failure would surface three stages downstream with
    nothing pointing back here. Callers clamp before calling.
    """
    if start < 1 or end < start or end > len(lines):
        raise ValueError(
            f"line range {start}-{end} outside 1-{len(lines)}"
        )
    return hashlib.sha256("\n".join(lines[start - 1:end]).encode("utf-8")).hexdigest()


def esc_html(s: str) -> str:
    """HTML-escape a value: & < > " ' — all five, always.

    Non-strings are coerced rather than raising. A `loc` count arriving as an
    int in a table row must not take the generator down at hour 9.
    """
    if not isinstance(s, str):
        s = str(s)
    return html.escape(s, quote=True)


def cell(text: str, code: bool = False, bold: bool = False) -> str:
    """A string safe for a surface the renderer interpolates WITHOUT esc().

    Applies to `table.columns[]`, `table.rows[][]`, `checkpoint.options[]`,
    `excerpt.caption`, `callout.title`/`text` — decision #20b.

    The value is escaped and the markup is added here, from a two-tag whitelist,
    by the generator. Blanket-escaping the finished cell would render the
    shipped fixture's `<code>src/pricing/</code>` as visible `&lt;code&gt;`;
    carrying markup in the data would make every one of those surfaces an
    injection point with no claim marker on it. Escaping the value and
    re-wrapping keeps both properties.

    `code` and `bold` compose: `<b><code>x</code></b>`.
    """
    out = esc_html(text)
    if code:
        out = "<code>" + out + "</code>"
    if bold:
        out = "<b>" + out + "</b>"
    return out


def armour_json(t: str) -> str:
    """Escape the four characters that let a payload break its own gates.

    Applied to the *serialized JSON text* just before it is spliced into the
    template. Safe as a blanket replace because in JSON these four can only ever
    occur inside string literals — the structural characters are `{}[]",:` plus
    numbers and bare keywords — and all four are legal JSON string escapes, so
    `JSON.parse`, `eval` and the browser all see the original characters back.

    Compute sha256 over the PRE-armour text. The gate re-hashes the *decoded*
    `files` map, so armouring first would mismatch every anchor.

    Why each one:

      `<`  a bundled `</script>` ends the script element regardless of JS string
           context — a real browser bug, not just a grep artefact — and
           `check-bundle.js:63` slices inline JS on exactly that pattern.
      `@`  `check-bundle.js:37` greps the whole file for `@import|@font-face`.
      `/`  a bundled `/*` or `//` breaks comment-aware scraping, and `src="//`
           trips the external-loader grep at `check-bundle.js:28`.
           Note the escape has to be `\\u002f`: the "obvious" `\\/` and `\\/*`
           still CONTAIN the `/` and the `/*`, so they defeat nothing. Only
           `\\u002f` removes the character.
      `—`  an em-dash inside the payload can move a scraper's marker index into
           the data region and truncate the slice.

    Cost: measured +5.1% on a 24 KB payload built from
    `fixtures/verified.sample.json` plus deliberately slash-heavy hazard lines
    (the plan's +1.5% estimate assumed ordinary source). Against a 5 MB cap and
    an 81.5 KB shell that is not a budget anyone has to think about.
    """
    return (t.replace("<", "\\u003c")
             .replace("@", "\\u0040")
             .replace("/", "\\u002f")
             .replace("—", "\\u2014"))
