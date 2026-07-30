"""Shared SSP execution helpers for skills that support --ssp mode.

Transforms Print()-based Slang code into an accumulator pattern suitable
for the VS Code extension's SSP/REPL endpoint, where Print() output goes
to the extension's output channel (not the JSON response value).

Pattern:
  1. Prepend  _Out = "";
  2. Replace  Print( X )  with  _Out = _Out + X;
  3. Append   _Out  as the final expression (returned in JSON value)
"""

import os
import re
import sys
import time

# Bootstrap: import from SLANG_EVAL skill
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_EVAL_SRC = os.path.join(_SKILL_DIR, "..", "SLANG_EVAL", "src")
sys.path.insert(0, _EVAL_SRC)
from eval import discover_ssp_port, ssp_evaluate  # noqa: E402


def _rewrite_prints(slang: str) -> str:
    """Rewrite Print(...) calls to accumulate into _Out variable.

    Handles:
      Print( expr )         -> _Out = _Out + Sprint( expr );
      Print( Sprint(...) )  -> _Out = _Out + Sprint(...);
    """
    # Replace Print( ... ) with _Out = _Out + Sprint( ... );
    # We need careful matching since Print args can contain nested parens.
    result = []
    i = 0
    while i < len(slang):
        # Look for Print( at word boundary
        m = re.match(r'Print\s*\(', slang[i:])
        if m:
            # Check it's not part of a larger identifier (e.g. "Sprint(")
            if i > 0 and (slang[i - 1].isalnum() or slang[i - 1] == '_'):
                result.append(slang[i])
                i += 1
                continue

            # Find the matching closing paren
            start = i + m.end()  # position after "Print("
            depth = 1
            j = start
            in_string = False
            while j < len(slang) and depth > 0:
                ch = slang[j]
                if ch == '"' and not in_string:
                    in_string = True
                elif ch == '"' and in_string:
                    # Check for escaped quote ""
                    if j + 1 < len(slang) and slang[j + 1] == '"':
                        j += 1  # skip escaped quote
                    else:
                        in_string = False
                elif not in_string:
                    if ch == '(':
                        depth += 1
                    elif ch == ')':
                        depth -= 1
                j += 1

            if depth == 0:
                inner = slang[start:j - 1].strip()  # content between Print( and )
                # If inner is already Sprint(...), use it directly
                if inner.startswith("Sprint(") or inner.startswith("Sprintf("):
                    result.append(f"_Out = _Out + {inner}")
                else:
                    result.append(f"_Out = _Out + Sprint( {inner} )")
                i = j
            else:
                # Couldn't match parens, leave as is
                result.append(slang[i])
                i += 1
        else:
            result.append(slang[i])
            i += 1

    return "".join(result)


def slang_to_ssp_expr(slang_code: str) -> str:
    """Transform a multi-line Print()-based Slang script into a single SSP expression.

    1. Prepend _Out = "";
    2. Rewrite Print() -> _Out accumulator
    3. Join all lines with space
    4. Append _Out as the return value
    """
    # Rewrite Print calls
    rewritten = _rewrite_prints(slang_code)

    # Join lines into single expression, filtering empties
    lines = [ln.strip() for ln in rewritten.splitlines() if ln.strip()]

    # Prepend accumulator init
    lines.insert(0, '_Out = "";')

    # Ensure each line ends with ;
    normalized = []
    for ln in lines:
        if not ln.endswith(";") and not ln.endswith("}") and not ln.endswith("{"):
            ln = ln + ";"
        normalized.append(ln)

    # Append return expression
    normalized.append("_Out")

    return " ".join(normalized)


def run_slang_via_ssp(
    slang_code: str,
    port: int = 0,
    timeout: int = 120,
    quiet: bool = False,
) -> tuple[int, str, str]:
    """Execute Slang code via SSP/REPL instead of secexpr.

    Returns (rc, stdout_equivalent, stderr_equivalent) to match run_slang() signature.
    stderr is always empty in SSP mode (no stderr channel).
    """
    # Discover port if not provided
    if port == 0:
        if not quiet:
            print("[ssp] Auto-detecting SSP port...", file=sys.stderr)
        port = discover_ssp_port()
        if port == 0:
            return 1, "", "ERROR: Could not find VS Code extension SSP endpoint."

    if not quiet:
        print(f"[ssp] Using port {port}", file=sys.stderr)

    # Transform to SSP expression
    expr = slang_to_ssp_expr(slang_code)

    if not quiet:
        print(f"[ssp] Expression: {len(expr)} chars", file=sys.stderr)

    t0 = time.time()
    result = ssp_evaluate(port, expr, timeout)
    elapsed = time.time() - t0

    if not quiet:
        print(f"[ssp] Elapsed: {elapsed:.1f}s", file=sys.stderr)

    if result["ok"]:
        return 0, result["value"], ""
    else:
        return 1, "", result["error"]
