"""Edit and create Slang scripts via secexpr.

Supports single replacements, batch multi-edits (JSON), prepend/append,
insert-before/after, delete, delete-between-markers, and full rewrite
-- all in one tool.

Usage:
    # Single replace
    python edit.py --db DB --script NAME --old TEXT --new TEXT
    # Batch multi-edit (JSON file with array of operations)
    python edit.py --db DB --script NAME --edit-file OPS.json
    # Full rewrite of existing script
    python edit.py --db DB --script NAME --rewrite --content-file FILE
    # Prepend / append text
    python edit.py --db DB --script NAME --prepend-file HEADER.txt
    python edit.py --db DB --script NAME --append-file FOOTER.txt
    # Read / inspect
    python edit.py --db DB --script NAME --read
    python edit.py --db DB --script NAME --check-ascii
    # Create new script
    python edit.py --db DB --script NAME --create [--content-file FILE]
    # Delete a script
    python edit.py --db DB --script NAME --delete
"""

import argparse
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
from typing import Optional, Tuple


ENV_CMD = r"H:\all-languages-env.cmd"
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_SKILL_DIR, "..", "..", ".."))

# ---------------------------------------------------------------------------
# Subprocess helper — run with timeout and kill process tree on timeout/error
# ---------------------------------------------------------------------------

def _kill_tree(pid: int) -> None:
    """Kill an entire process tree (cross-platform)."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def _run_cmd(cmd, timeout=600, capture_output=True):
    """Run *cmd* with a timeout.  On timeout, kill the entire process tree
    so the terminal doesn't hang.  Returns a CompletedProcess.
    """
    popen_kwargs = {
        "stdout": subprocess.PIPE if capture_output else None,
        "stderr": subprocess.PIPE if capture_output else None,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["preexec_fn"] = os.setsid

    proc = subprocess.Popen(cmd, **popen_kwargs)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc.pid)
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()
            stdout, stderr = proc.communicate()
        print(f"ERROR: command timed out after {timeout}s — process tree killed",
              file=sys.stderr)
        return subprocess.CompletedProcess(
            cmd, returncode=1,
            stdout=stdout or b"", stderr=stderr or b"",
        )
    return subprocess.CompletedProcess(
        cmd, returncode=proc.returncode,
        stdout=stdout or b"", stderr=stderr or b"",
    )


# ---------------------------------------------------------------------------
# Batch templates for secexpr invocation
#
# After calling the env script, we resolve secexpr to its full path and then
# trim PATH to a minimal set before invoking it.  secexpr.cmd internally
# builds a ~6K PATH; if the pre-existing PATH from all-languages-env.cmd
# (~2K) is appended, the total exceeds cmd.exe's 8191-char line limit and
# causes "The input line is too long" (exit code 255).
# ---------------------------------------------------------------------------
_BATCH_PREAMBLE = (
    "@echo off\n"
    "setlocal DisableDelayedExpansion\n"
    "call {env} >nul 2>&1\n"
    "setlocal DisableDelayedExpansion\n"
    'for /f "delims=" %%i in (\'where secexpr\') do set "SECEXPR_CMD=%%i"\n'
    'set "PATH=%SystemRoot%\\system32;%SystemRoot%"\n'
)
BATCH_TEMPLATE = (
    _BATCH_PREAMBLE +
    '"%SECEXPR_CMD%" "{db}" --source "{source}" {mode} -t -e "{expr}"\n'
)
BATCH_TEMPLATE_STDIN = (
    _BATCH_PREAMBLE +
    '"%SECEXPR_CMD%" "{db}" --source "{source}" {mode} -t < "{expr_path}"\n'
)

# ---------------------------------------------------------------------------
# ASCII validation
# ---------------------------------------------------------------------------

def validate_ascii(text: str, label: str) -> None:
    """Raise ValueError if text contains non-ASCII characters."""
    for i, ch in enumerate(text):
        if ord(ch) > 127:
            ctx_start = max(0, i - 20)
            ctx_end = min(len(text), i + 20)
            context = text[ctx_start:ctx_end]
            raise ValueError(
                f"Non-ASCII character U+{ord(ch):04X} in {label} at offset {i}.\n"
                f"  Context: {context!r}\n"
                f"  Slang scripts must be pure ASCII. Replace with ASCII equivalent."
            )


# ---------------------------------------------------------------------------
# Slang string encoding
# ---------------------------------------------------------------------------

def slang_escape(text: str) -> str:
    """Escape a Python string for embedding inside a Slang string literal.

    In Slang, a literal double-quote inside a string is written as "".
    """
    return text.replace('"', '""')


def batch_escape(text: str) -> str:
    """Escape a string for embedding inside a cmd.exe double-quoted argument."""
    # cmd.exe expands %VAR% even inside double-quotes; double % to preserve
    # literal percent signs (e.g., Printf("%s", ...)).
    return text.replace('%', '%%').replace('"', '""')


def to_slang_str_safe(s: str) -> str:
    """Convert a Python string to a Slang expression using Chr() for special chars.

    Handles: newline (Chr(10)), tab (Chr(9)), double-quote (Chr(34)),
    backslash (Chr(92)), carriage-return (stripped).

    WARNING: For large strings (>50 special chars), the generated expression
    has deep nesting (one + per special char) which can exceed Slang's
    expression depth limit. Use build_content_stmts() for large content.
    """
    parts = []
    current = []

    def flush():
        if current:
            text = "".join(current)
            parts.append('"' + text + '"')
            current.clear()

    for ch in s:
        if ch == "\n":
            flush()
            parts.append("Chr(10)")
        elif ch == "\t":
            flush()
            parts.append("Chr(9)")
        elif ch == "\r":
            pass  # strip CR
        elif ch == '"':
            flush()
            parts.append("Chr(34)")
        elif ch == "\\":
            flush()
            parts.append("Chr(92)")
        else:
            current.append(ch)

    flush()
    return " + ".join(parts) if parts else '""'


def _slang_str_line(line: str) -> str:
    """Convert a single line (no newline) to a safe Slang string expression.

    Uses Chr() only for special chars within a single line — keeps expression
    depth shallow since each line is a separate statement.
    """
    parts = []
    current = []

    def flush():
        if current:
            parts.append('"' + "".join(current) + '"')
            current.clear()

    for ch in line:
        if ch == "\r":
            pass
        elif ch == "\t":
            flush()
            parts.append("Chr(9)")
        elif ch == '"':
            flush()
            parts.append("Chr(34)")
        elif ch == "\\":
            flush()
            parts.append("Chr(92)")
        else:
            current.append(ch)

    flush()
    return " + ".join(parts) if parts else '""'


def build_content_stmts(var_name: str, content: str) -> list:
    """Build a list of Slang statements that incrementally construct a string.

    Instead of one massive expression with 100s of + operators (which exceeds
    Slang's expression depth limit), this generates:
        T = "line1" + Chr(10);
        T = T + "line2" + Chr(10);
        T = T + "line3" + Chr(10);
        ...

    This keeps each statement shallow and works for any content size.
    """
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    stmts = []
    # Remove trailing empty line from final \n (content usually ends with \n)
    if lines and lines[-1] == "":
        lines = lines[:-1]

    for i, line in enumerate(lines):
        line_expr = _slang_str_line(line)
        if i == 0:
            stmts.append(f"{var_name} = {line_expr} + Chr(10);")
        else:
            stmts.append(f"{var_name} = {var_name} + {line_expr} + Chr(10);")

    return stmts


def _needs_chr_encoding(s: str) -> bool:
    """Return True if the string contains chars that need Chr() encoding."""
    return any(ch in s for ch in '\n\t\r\\"')


# ---------------------------------------------------------------------------
# Slang expression builders — single operations
# ---------------------------------------------------------------------------

READ_START_MARKER = "===SLANG_READ_START==="
READ_END_MARKER = "===SLANG_READ_END==="
READ_PAYLOAD_PREFIX = "===SLANG_READ_PAYLOAD_PREFIX==="


def build_read_expr(script_name: str) -> str:
    name = slang_escape(script_name)
    return (
        f'Sec = GetSecurity( "{name}" ); '
        f'Txt = GetValue( "Expression", Sec ); '
        f'Print( "{READ_START_MARKER}" ); '
        f'Print( "{READ_PAYLOAD_PREFIX}" + Txt ); '
        f'Print( "{READ_END_MARKER}" );'
    )


def build_edit_expr(script_name: str, old: str, new: str) -> str:
    name = slang_escape(script_name)
    if _needs_chr_encoding(old) or _needs_chr_encoding(new):
        old_slang = to_slang_str_safe(old)
        new_slang = to_slang_str_safe(new)
        return (
            f'Sec = GetSecurity( "{name}" );\n'
            f'Txt = GetValue( "Expression", Sec );\n'
            f'Old = {old_slang};\n'
            f'New = {new_slang};\n'
            f'New Txt = StrReplace( Txt, Old, New, REPL_GLOBAL );\n'
            f'Changed = Txt != New Txt;\n'
            f'Print( "changed=", Changed );\n'
            f'If( Changed ) {{\n'
            f'  SetValue( "Expression", Sec, New Txt );\n'
            f'  Check( UpdateSecurity( Sec ) );\n'
            f'  Print( "saved=1" );\n'
            f'}} : Print( "no match found" );\n'
        )
    old_slang = slang_escape(old)
    new_slang = slang_escape(new)
    return (
        f'Sec = GetSecurity( "{name}" ); '
        f'Txt = GetValue( "Expression", Sec ); '
        f'New Txt = StrReplace( Txt, "{old_slang}", "{new_slang}", REPL_GLOBAL ); '
        f'Changed = Txt != New Txt; '
        f'Print( "changed=", Changed ); '
        f'If( Changed ) {{ '
        f'  SetValue( "Expression", Sec, New Txt ); '
        f'  Check( UpdateSecurity( Sec ) ); '
        f'  Print( "saved=1" ); '
        f'}} : Print( "no match found" ); '
    )


def build_create_expr(script_name: str, content: str = None) -> str:
    """Build a Slang expression to create a new script.

    Uses line-by-line string construction (build_content_stmts) to avoid
    Slang's expression depth limit for large scripts.  Wraps SetValue and
    UpdateSecurity in Check() so errors are caught and 'saved=1' only
    prints on actual success.
    """
    lines = []

    if ":" in script_name:
        parts = script_name.split(":")
        sprint_args = '", Chr(58), "'.join(slang_escape(p) for p in parts)
        lines.append(f'Name = Sprint("{sprint_args}");')
    else:
        name = slang_escape(script_name)
        lines.append(f'Name = "{name}";')

    lines.append('NewSec = SecDbNew("Slang Expression");')
    lines.append("Check( RenameSecurity(NewSec, Name) );")

    if content:
        lines.extend(build_content_stmts("T", content))
        lines.append('Check( SetValue("Expression", NewSec, T) );')

    lines.append("Check( UpdateSecurity(NewSec) );")
    lines.append('Print("saved=1");')

    return "\n".join(lines)


def build_delete_expr(script_name: str) -> str:
    """Build a Slang expression to delete (remove) a script from the database.

    DeleteSecurity takes a String (the security name), not a Security handle.
    The expression is wrapped in a block so Print only runs on success.
    """
    name = slang_escape(script_name)
    return f'{{ Check( DeleteSecurity( "{name}" ) ); Print( "deleted=1" ) }};'


def build_rewrite_expr(script_name: str, content: str) -> str:
    """Build a Slang expression to replace an existing script's entire content.

    Uses line-by-line string construction (build_content_stmts) to avoid
    Slang's expression depth limit for large scripts.  Wraps SetValue and
    UpdateSecurity in Check() so errors are caught and 'saved=1' only
    prints on actual success.
    """
    name = slang_escape(script_name)
    lines = [f'Sec = GetSecurity( "{name}" );']
    lines.extend(build_content_stmts("T", content))
    lines.append('Check( SetValue( "Expression", Sec, T ) );')
    lines.append("Check( UpdateSecurity( Sec ) );")
    lines.append('Print( "changed=1" );')
    lines.append('Print( "saved=1" );')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Batch multi-edit expression builder
# ---------------------------------------------------------------------------

def _slang_var(prefix: str, idx: int) -> str:
    """Generate a unique Slang variable name for an edit step."""
    return f"{prefix}{idx}"


def build_batch_edit_expr(script_name: str, operations: list) -> str:
    """Build a single Slang expression that applies multiple edit operations.

    Each operation is a dict with an "action" key:
      - {"action": "replace", "old": "...", "new": "..."}
      - {"action": "delete", "old": "..."}
      - {"action": "delete-between", "start_marker": "...", "end_marker": "..."}
      - {"action": "prepend", "text": "..."}
      - {"action": "append", "text": "..."}
      - {"action": "insert-before", "marker": "...", "text": "..."}
      - {"action": "insert-after", "marker": "...", "text": "..."}

    All operations are applied sequentially to the script text in a single
    secexpr invocation, then saved once at the end.
    """
    name = slang_escape(script_name)
    lines = [
        f'Sec = GetSecurity( "{name}" );',
        'Orig Txt = GetValue( "Expression", Sec );',
        'Txt = Orig Txt;',
        '',
    ]

    for i, op in enumerate(operations):
        action = op["action"]
        step_label = f"step {i + 1}/{len(operations)} ({action})"
        lines.append(f'// --- {step_label} ---')

        if action == "replace":
            old_s = to_slang_str_safe(op["old"])
            new_s = to_slang_str_safe(op["new"])
            lines.append(f'Txt = StrReplace( Txt, {old_s}, {new_s}, REPL_GLOBAL );')

        elif action == "delete":
            old_s = to_slang_str_safe(op["old"])
            lines.append(f'Txt = StrReplace( Txt, {old_s}, "", REPL_GLOBAL );')

        elif action == "delete-between":
            start_s = to_slang_str_safe(op["start_marker"])
            end_s = to_slang_str_safe(op["end_marker"])
            vsp = _slang_var("SP", i)
            vep = _slang_var("EP", i)
            vendlen = _slang_var("EL", i)
            vend = _slang_var("EE", i)
            lines.append(f'{vsp} = StrPos( Txt, {start_s} );')
            lines.append(f'{vep} = StrPos( Txt, {end_s} );')
            lines.append(f'{vendlen} = Size( {end_s} );')
            lines.append(f'If( {vsp} >= 0 && {vep} >= {vsp} )')
            lines.append('{')
            lines.append(f'    {vend} = {vep} + {vendlen} - 1;')
            lines.append(f'    If( {vsp} > 0 )')
            lines.append(f'        Head = SubStr( Txt, 0, {vsp} - 1 )')
            lines.append('    : Head = "";')
            lines.append(f'    Tail = SubStr( Txt, {vend} + 1 );')
            lines.append('    Txt = Head + Tail;')
            lines.append('}')
            lines.append(f': Print( "WARNING: markers not found for {step_label}" );')

        elif action == "prepend":
            text_s = to_slang_str_safe(op["text"])
            lines.append(f'Txt = {text_s} + Txt;')

        elif action == "append":
            text_s = to_slang_str_safe(op["text"])
            lines.append(f'Txt = Txt + {text_s};')

        elif action == "insert-before":
            marker_s = to_slang_str_safe(op["marker"])
            text_s = to_slang_str_safe(op["text"])
            vp = _slang_var("IP", i)
            vmlen = _slang_var("ML", i)
            vmatch = _slang_var("IM", i)
            lines.append(f'{vmlen} = Size( {marker_s} );')
            lines.append(f'{vp} = StrPos( Txt, {marker_s} );')
            lines.append(f'{vmatch} = {vp} >= 0 && SubStr( Txt, {vp}, {vp} + {vmlen} - 1 ) == {marker_s};')
            lines.append(f'If( {vmatch} )')
            lines.append('{')
            lines.append(f'    If( {vp} > 0 )')
            lines.append(f'        Head = SubStr( Txt, 0, {vp} - 1 )')
            lines.append('    : Head = "";')
            lines.append(f'    Tail = SubStr( Txt, {vp} );')
            lines.append(f'    Txt = Head + {text_s} + Tail;')
            lines.append('}')
            lines.append(f': Print( "WARNING: marker not found for {step_label}" );')

        elif action == "insert-after":
            marker_s = to_slang_str_safe(op["marker"])
            text_s = to_slang_str_safe(op["text"])
            vp = _slang_var("AP", i)
            vmlen = _slang_var("ML", i)
            vmatch = _slang_var("AM", i)
            lines.append(f'{vmlen} = Size( {marker_s} );')
            lines.append(f'{vp} = StrPos( Txt, {marker_s} );')
            lines.append(f'{vmatch} = {vp} >= 0 && SubStr( Txt, {vp}, {vp} + {vmlen} - 1 ) == {marker_s};')
            lines.append(f'If( {vmatch} )')
            lines.append('{')
            lines.append(f'    AEnd = {vp} + {vmlen};')
            lines.append(f'    Head = SubStr( Txt, 0, AEnd - 1 );')
            lines.append(f'    Tail = SubStr( Txt, AEnd );')
            lines.append(f'    Txt = Head + {text_s} + Tail;')
            lines.append('}')
            lines.append(f': Print( "WARNING: marker not found for {step_label}" );')

        else:
            raise ValueError(f"Unknown action: {action!r} in operation {i + 1}")

        lines.append('')

    # Save if anything changed
    lines.append('Changed = Orig Txt != Txt;')
    lines.append('Print( "changed=", Changed );')
    lines.append('If( Changed )')
    lines.append('{')
    lines.append('    SetValue( "Expression", Sec, Txt );')
    lines.append('    Check( UpdateSecurity( Sec ) );')
    lines.append('    Print( "saved=1" );')
    lines.append('}')
    lines.append(': Print( "no changes detected" );')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# secexpr runners
# ---------------------------------------------------------------------------

def run_secexpr(db: str, expr: str, dry_run: bool = False, safe: bool = True,
                source: str = None) -> int:
    mode = "--safe" if safe else "--full"
    src = source or db
    batch_expr = batch_escape(expr)
    batch_content = BATCH_TEMPLATE.format(
        env=ENV_CMD, db=db, expr=batch_expr, mode=mode, source=src
    )

    if dry_run:
        print("=== Slang expression ===")
        print(expr)
        print("\n=== Batch file ===")
        print(batch_content)
        return 0

    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="slang_edit_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(batch_content)

        result = _run_cmd(["cmd", "/c", batch_path], timeout=600)

        stdout_text = _normalize_newlines_for_stdout(
            result.stdout.decode("utf-8", errors="replace")
        )
        if stdout_text.strip():
            print(stdout_text)

        if result.stderr:
            stderr_text = result.stderr.decode("utf-8", errors="replace")
            edit_ok = "changed=1" in stdout_text and "saved=1" in stdout_text
            important = [
                line
                for line in stderr_text.splitlines()
                if "Error" in line
                and "3001" not in line
                and "RemoteException" not in line
                and "IsError" not in line
                and not (edit_ok and "Slang Error encountered" in line)
            ]
            if important:
                print("--- errors ---", file=sys.stderr)
                for line in important[:15]:
                    print(line, file=sys.stderr)

            # Detect fatal Slang errors (e.g. GetSecurity failed)
            # If stdout confirms changed=1 + saved=1, the edit succeeded
            # despite stderr noise — downgrade to warning.
            if "ERROR: Slang Error encountered" in stderr_text:
                if edit_ok:
                    print("WARNING: secexpr stderr noise (edit succeeded: changed=1, saved=1)", file=sys.stderr)
                else:
                    print("ERROR: Slang Error encountered during edit", file=sys.stderr)
                    return 1

        # Detect changed=0 (silent failure: old text didn't match)
        if "changed=0" in stdout_text or "changed= 0" in stdout_text:
            print("WARNING: edit had no effect (changed=0) — old text not found in script", file=sys.stderr)
            return 2

        return result.returncode
    finally:
        os.unlink(batch_path)


def run_secexpr_raw(db: str, expr: str, safe: bool = True,
                    source: str = None) -> bytes:
    """Run secexpr and return raw stdout bytes."""
    mode = "--safe" if safe else "--full"
    src = source or db
    batch_expr = batch_escape(expr)
    batch_content = BATCH_TEMPLATE.format(
        env=ENV_CMD, db=db, expr=batch_expr, mode=mode, source=src
    )

    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="slang_edit_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(batch_content)

        result = _run_cmd(["cmd", "/c", batch_path], timeout=120)
        return result.stdout
    finally:
        os.unlink(batch_path)


def run_secexpr_stdin(db: str, expr: str, dry_run: bool = False, safe: bool = True,
                     source: str = None) -> int:
    """Run a large Slang expression via stdin piping."""
    mode = "--safe" if safe else "--full"
    src = source or db

    if dry_run:
        print("=== Slang expression ===")
        print(expr)
        return 0

    fd, expr_path = tempfile.mkstemp(suffix=".slang", prefix="slang_edit_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(expr)

        batch_content = BATCH_TEMPLATE_STDIN.format(
            env=ENV_CMD, db=db, mode=mode, expr_path=expr_path, source=src
        )

        fd2, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="slang_edit_")
        try:
            with os.fdopen(fd2, "w") as f:
                f.write(batch_content)

            result = _run_cmd(["cmd", "/c", batch_path], timeout=600)

            stdout_text = _normalize_newlines_for_stdout(
                result.stdout.decode("utf-8", errors="replace")
            )
            if stdout_text.strip():
                print(stdout_text)

            if result.stderr:
                stderr_text = result.stderr.decode("utf-8", errors="replace")
                # Success if saved=1 is in stdout (covers create, rewrite, edit)
                save_ok = "saved=1" in stdout_text
                important = [
                    line
                    for line in stderr_text.splitlines()
                    if "Error" in line
                    and "3001" not in line
                    and "RemoteException" not in line
                    and "IsError" not in line
                    and not (save_ok and "Slang Error encountered" in line)
                ]
                if important and not save_ok:
                    print("--- errors ---", file=sys.stderr)
                    for line in important[:15]:
                        print(line, file=sys.stderr)

                # Detect fatal Slang errors (e.g. GetSecurity failed)
                # If stdout confirms saved=1, the operation succeeded
                # despite stderr noise — suppress entirely.
                if "ERROR: Slang Error encountered" in stderr_text:
                    if not save_ok:
                        print("ERROR: Slang Error encountered during edit", file=sys.stderr)
                        return 1

            # Detect changed=0 (silent failure: old text didn't match)
            if "changed=0" in stdout_text or "changed= 0" in stdout_text:
                print("WARNING: edit had no effect (changed=0) — old text not found in script", file=sys.stderr)
                return 2

            return result.returncode
        finally:
            os.unlink(batch_path)
    finally:
        os.unlink(expr_path)


# ---------------------------------------------------------------------------
# File reading helpers
# ---------------------------------------------------------------------------

def _read_text_file(path: str) -> str:
    """Read a text file, stripping BOM and normalizing to LF line endings."""
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_newlines_for_stdout(text: str) -> str:
    """Normalize CRLF/CR to LF before printing.

    On Windows, stdout typically translates LF -> CRLF. If the string already
    contains CRLF, printing can become CRCRLF and many tools render that as a
    blank line between every line.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _extract_read_payload(raw: bytes) -> Optional[Tuple[str, bytes]]:
    """Extract the script text printed between READ_START/END markers.

    Returns a tuple of:
      - payload_text: decoded text (UTF-8 with replacement)
      - payload_raw: raw bytes for the same payload

    The returned payload excludes the single newline separator emitted by
    Print(READ_START_MARKER) (i.e., the newline after the marker line), but
    preserves any *real* leading whitespace/newlines that are part of the
    stored Expression itself.
    """
    start = READ_START_MARKER.encode("ascii")
    end = READ_END_MARKER.encode("ascii")

    i = raw.find(start)
    j = raw.find(end)
    if i < 0 or j < 0 or j <= i:
        return None

    between = raw[i + len(start) : j]

    # Strip exactly one newline separator inserted by Print(marker)
    if between.startswith(b"\r\n"):
        payload_raw = between[2:]
    elif between.startswith(b"\n"):
        payload_raw = between[1:]
    elif between.startswith(b"\r"):
        payload_raw = between[1:]
    else:
        payload_raw = between

    payload_text = payload_raw.decode("utf-8", errors="replace")

    # Remove the injected prefix used to preserve leading newlines.
    prefix = READ_PAYLOAD_PREFIX.encode("ascii")
    if payload_raw.startswith(prefix):
        payload_raw = payload_raw[len(prefix) :]
        payload_text = payload_raw.decode("utf-8", errors="replace")
    return payload_text, payload_raw


def _trim_leading_blank_lines(text: str) -> str:
    """Remove leading blank/whitespace-only lines.

    A "blank line" is a line that is empty or contains only spaces/tabs.
    Line ending handling:
      - Normalizes CRLF/CR to LF for trimming logic.
      - The returned string uses LF line endings.
    """
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    while True:
        nl = t.find("\n")
        if nl == -1:
            return "" if t.strip(" \t") == "" else t
        first_line = t[:nl]
        if first_line.strip(" \t") != "":
            return t
        t = t[nl + 1 :]




# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Edit, create, and inspect Slang scripts via secexpr."
    )
    parser.add_argument(
        "--db", required=False, default="",
        help="Slang database path (e.g. !NYC UserDBs!home!{kerberos}!clean)",
    )
    parser.add_argument(
        "--script", required=False, default="",
        help="Script name (e.g. 'Test: Eq1D Brazil Ref Asset')",
    )

    # --- Single replace ---
    parser.add_argument("--old", help="Text to find (single replace mode)")
    parser.add_argument("--new", help="Replacement text (single replace mode)")
    parser.add_argument("--old-file", dest="old_file",
                        help="File containing text to find (alternative to --old)")
    parser.add_argument("--new-file", dest="new_file",
                        help="File containing replacement text (alternative to --new)")

    # --- Batch multi-edit ---
    parser.add_argument("--edit-file", dest="edit_file",
                        help="JSON file with array of edit operations (batch mode)")

    # --- Prepend / append ---
    parser.add_argument("--prepend", help="Text to prepend to the script")
    parser.add_argument("--prepend-file", dest="prepend_file",
                        help="File whose content to prepend to the script")
    parser.add_argument("--append", help="Text to append to the script")
    parser.add_argument("--append-file", dest="append_file",
                        help="File whose content to append to the script")

    # --- Read / inspect ---
    parser.add_argument("--read", action="store_true",
                        help="Print current script text and exit")
    parser.add_argument("--trim-leading-blank-lines", action="store_true",
                        help="Remove leading blank/whitespace-only lines from the stored Expression")
    parser.add_argument("--check-ascii", action="store_true",
                        help="Check script for non-ASCII bytes")

    # --- Create / rewrite / delete ---
    parser.add_argument("--create", action="store_true",
                        help="Create a new script")
    parser.add_argument("--delete", action="store_true",
                        help="Delete (remove) a script from the database")
    parser.add_argument("--rewrite", action="store_true",
                        help="Replace entire content of an existing script (requires --content-file)")
    parser.add_argument("--content-file", dest="content_file",
                        help="File with script content (used with --create or --rewrite)")

    # --- Flags ---
    parser.add_argument("--from-prod", action="store_true", dest="from_prod",
                        help="Include ProdSource (;PS) in the source list "
                             "(automatic for write operations)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the Slang expression without executing")

    # --- Task-based execution (zero Allow) ---
    parser.add_argument("--args-file", default=None, metavar="PATH",
                        help="JSON file with edit arguments (keys mirror CLI flags)")
    parser.add_argument("--output-json", default=None, metavar="PATH",
                        help="Write machine-readable JSON results to PATH (with sentinel)")

    args = parser.parse_args()

    # ---------- Load from args-file if provided ----------
    # JSON values are authoritative — they override any CLI flags for
    # consistent behaviour across CLI and task-based execution paths.
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as af:
            af_data = json.load(af)

        # --- "action" shorthand: maps to the equivalent boolean flag ---
        _ACTION_MAP = {
            "read": "read",
            "delete": "delete",
            "create": "create",
            "rewrite": "rewrite",
            "check_ascii": "check_ascii",
            "check-ascii": "check_ascii",
            "trim_leading_blank_lines": "trim_leading_blank_lines",
            "trim-leading-blank-lines": "trim_leading_blank_lines",
        }
        action = af_data.get("action", "")
        if action and action in _ACTION_MAP:
            setattr(args, _ACTION_MAP[action], True)
        elif action and action not in ("edit", "replace", "prepend", "append", ""):
            print(f"WARNING: unknown action '{action}' in args-file. "
                  f"Valid: {', '.join(sorted(set(_ACTION_MAP.keys()) | {'edit','replace','prepend','append'}))}",
                  file=sys.stderr)

        # String args: JSON overrides CLI when present
        if af_data.get("db"):
            args.db = af_data["db"]
        if af_data.get("script"):
            args.script = af_data["script"]
        if af_data.get("old"):
            args.old = af_data["old"]
        if af_data.get("new"):
            args.new = af_data["new"]
        if af_data.get("old_file"):
            args.old_file = af_data["old_file"]
        if af_data.get("new_file"):
            args.new_file = af_data["new_file"]
        if af_data.get("edit_file"):
            args.edit_file = af_data["edit_file"]
        if af_data.get("prepend"):
            args.prepend = af_data["prepend"]
        if af_data.get("prepend_file"):
            args.prepend_file = af_data["prepend_file"]
        if af_data.get("append"):
            args.append = af_data["append"]
        if af_data.get("append_file"):
            args.append_file = af_data["append_file"]
        if af_data.get("content_file"):
            args.content_file = af_data["content_file"]
        if af_data.get("output_json"):
            args.output_json = af_data["output_json"]
        # Map "out_file" → output_json (agent compat)
        if af_data.get("out_file") and not af_data.get("output_json"):
            args.output_json = af_data["out_file"]
        # Boolean args: JSON can only enable (never disable via args-file)
        if af_data.get("read"):
            args.read = True
        if af_data.get("delete"):
            args.delete = True
        if af_data.get("create"):
            args.create = True
        if af_data.get("rewrite"):
            args.rewrite = True
        if af_data.get("check_ascii"):
            args.check_ascii = True
        if af_data.get("trim_leading_blank_lines"):
            args.trim_leading_blank_lines = True
        if af_data.get("from_prod"):
            args.from_prod = True
        if af_data.get("dry_run"):
            args.dry_run = True
        if af_data.get("run_id"):
            args.run_id = af_data["run_id"]

    run_id = getattr(args, "run_id", None) or ""

    # ---------- Write sentinel (signals "running") ----------
    json_path = args.output_json
    if not json_path:
        json_path = os.path.join(_REPO_ROOT, "workspace", "tmp",
                                 "slang_edit_results.json")
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"status": "running", "run_id": run_id,
                   "script": args.script}, jf, indent=2)

    # ---------- Capture stdout for JSON output ----------
    captured_buf = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = _TeeWriter(original_stdout, captured_buf)

    try:
        rc = _run_operation(args, parser)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        print(f"EXCEPTION: {e}", file=sys.stderr)
        rc = 1
    finally:
        sys.stdout = original_stdout

    # ---------- Write final sentinel (signals "done") ----------
    result_obj = {
        "status": "done",
        "run_id": run_id,
        "script": args.script,
        "exit_code": rc or 0,
        "output": captured_buf.getvalue(),
    }
    # For --read operations, extract content from output for easy parsing
    captured_text = captured_buf.getvalue()
    if args.read and rc == 0 and captured_text.strip():
        result_obj["content"] = captured_text.rstrip("\n")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(result_obj, jf, indent=2)

    return rc or 0


class _TeeWriter:
    """Write to both the original stdout and a capture buffer."""

    def __init__(self, original, buffer):
        self._original = original
        self._buffer = buffer

    def write(self, s):
        self._original.write(s)
        self._buffer.write(s)

    def flush(self):
        self._original.flush()
        self._buffer.flush()


def _run_operation(args, parser):
    """Execute the requested operation. Returns exit code."""

    if not args.db:
        parser.error("--db is required (either via CLI or --args-file)")
    if not args.script:
        parser.error("--script is required (either via CLI or --args-file)")

    # Build two DB chains:
    #   db     = user DB (writes go here); includes ;PS only with --from-prod
    #   source = always includes ;PS (for Link() resolution AND read-only
    #            GetSecurity fallback to ProdSource)
    db = args.db
    if args.from_prod:
        db = f"{args.db};PS"

    # source = full resolution chain (always includes ;PS)
    if ";PS" in db:
        source = db
    else:
        source = f"{db};PS"

    # ── Delete ────────────────────────────────────────────────────────────
    if args.delete:
        print(f"Deleting script '{args.script}' from db '{db}' ...")
        expr = build_delete_expr(args.script)
        rc = run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)
        if args.dry_run:
            return rc
        if rc != 0:
            print(f"FAIL: secexpr returned exit code {rc}", file=sys.stderr)
            return rc
        # Verify deletion: try to read the script back
        print("Verifying deletion ...")
        verify_expr = build_read_expr(args.script)
        raw = run_secexpr_raw(db, verify_expr, safe=True, source=source)
        text = raw.decode("utf-8", errors="replace")
        if READ_START_MARKER in text and READ_END_MARKER in text:
            content = text[
                text.find(READ_START_MARKER) + len(READ_START_MARKER):
                text.find(READ_END_MARKER)
            ].strip()
            if content:
                print(f"WARNING: script '{args.script}' still exists after delete ({len(content)} chars)!", file=sys.stderr)
                return 1
        print(f"OK: script '{args.script}' deleted successfully.")
        return 0

    # ── Create ────────────────────────────────────────────────────────────
    if args.create:
        content = None
        if args.content_file:
            content = _read_text_file(args.content_file)
            validate_ascii(content, "--content-file")
        expr = build_create_expr(args.script, content)
        return run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)

    # ── Rewrite (full content replacement on existing script) ─────────────
    if args.rewrite:
        if not args.content_file:
            parser.error("--rewrite requires --content-file")
        content = _read_text_file(args.content_file)
        validate_ascii(content, "--content-file")
        expr = build_rewrite_expr(args.script, content)
        return run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)

    # ── Read ──────────────────────────────────────────────────────────────
    # Use 'source' (which always has ;PS) as the DB arg so GetSecurity
    # can resolve scripts that live only in ProdSource.
    if args.read:
        expr = build_read_expr(args.script)
        if args.dry_run:
            return run_secexpr(source, expr, dry_run=True, safe=True, source=source)
        raw = run_secexpr_raw(source, expr, safe=True, source=source)
        extracted = _extract_read_payload(raw)
        if extracted is not None:
            content, _content_raw = extracted
            # Drop the single trailing newline added by Print(Txt)
            content = content.replace("\r\n", "\n").replace("\r", "\n")
            if content.endswith("\n"):
                content = content[:-1]
            sys.stdout.write(content)
            sys.stdout.write("\n")
        else:
            # Fallback: print normalized raw output (markers not found)
            text = _normalize_newlines_for_stdout(raw.decode("utf-8", errors="replace"))
            sys.stdout.write(text)
            if not text.endswith("\n"):
                sys.stdout.write("\n")
        return 0

    # ── Trim leading blank lines ───────────────────────────────────────────
    if args.trim_leading_blank_lines:
        # Read via safe path (no writes) then rewrite only if needed.
        # Use 'source' as DB so GetSecurity resolves ProdSource scripts.
        read_expr = build_read_expr(args.script)
        raw = run_secexpr_raw(source, read_expr, safe=True, source=source)
        extracted = _extract_read_payload(raw)
        if extracted is None:
            print("FAIL: could not extract script content (read markers not found)", file=sys.stderr)
            return 1

        content, _content_raw = extracted
        # Drop trailing newline from Print(Txt) but keep everything else.
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        if content.endswith("\n"):
            content = content[:-1]

        trimmed = _trim_leading_blank_lines(content)
        if trimmed == content:
            print("changed=0")
            print("saved=0")
            return 0

        validate_ascii(trimmed, "trimmed content")
        rewrite_expr = build_rewrite_expr(args.script, trimmed)
        return run_secexpr_stdin(db, rewrite_expr, dry_run=args.dry_run, source=source)

    # ── Check ASCII ───────────────────────────────────────────────────────
    # Use 'source' as DB so GetSecurity resolves ProdSource scripts.
    if args.check_ascii:
        expr = build_read_expr(args.script)
        raw = run_secexpr_raw(source, expr, safe=True, source=source)
        non_ascii = [(i, b) for i, b in enumerate(raw) if b > 127]
        if not non_ascii:
            print("OK: script is pure ASCII")
            return 0
        print(f"FAIL: {len(non_ascii)} non-ASCII byte(s) found:")
        for offset, byte_val in non_ascii[:20]:
            start = max(0, offset - 15)
            end = min(len(raw), offset + 15)
            ctx = raw[start:end]
            print(f"  offset {offset}: 0x{byte_val:02x}  context: {ctx!r}")
        if len(non_ascii) > 20:
            print(f"  ... and {len(non_ascii) - 20} more")
        return 1

    # ── Batch multi-edit (--edit-file) ────────────────────────────────────
    if args.edit_file:
        ops_text = _read_text_file(args.edit_file)
        ops = json.loads(ops_text)
        if not isinstance(ops, list) or not ops:
            parser.error("--edit-file must contain a non-empty JSON array")
        # Validate ASCII on all text fields
        for i, op in enumerate(ops):
            for key in ("old", "new", "text", "marker", "start_marker", "end_marker"):
                if key in op and op[key] is not None:
                    validate_ascii(op[key], f"operation {i + 1} '{key}'")
        expr = build_batch_edit_expr(args.script, ops)
        return run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)

    # ── Prepend ───────────────────────────────────────────────────────────
    if args.prepend or args.prepend_file:
        text = args.prepend or _read_text_file(args.prepend_file)
        validate_ascii(text, "--prepend")
        ops = [{"action": "prepend", "text": text}]
        expr = build_batch_edit_expr(args.script, ops)
        return run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)

    # ── Append ────────────────────────────────────────────────────────────
    if args.append or args.append_file:
        text = args.append or _read_text_file(args.append_file)
        validate_ascii(text, "--append")
        ops = [{"action": "append", "text": text}]
        expr = build_batch_edit_expr(args.script, ops)
        return run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)

    # ── Single replace (--old / --new) ────────────────────────────────────
    old = args.old
    new = args.new

    if args.old_file:
        old = _read_text_file(args.old_file)
    if args.new_file:
        new = _read_text_file(args.new_file)

    if old is None or new is None:
        parser.error(
            "Provide --old/--new, --old-file/--new-file, --edit-file, "
            "--prepend[-file], or --append[-file]"
        )

    validate_ascii(old, "--old")
    validate_ascii(new, "--new")

    expr = build_edit_expr(args.script, old, new)
    if _needs_chr_encoding(old) or _needs_chr_encoding(new):
        return run_secexpr_stdin(db, expr, dry_run=args.dry_run, source=source)
    return run_secexpr(db, expr, dry_run=args.dry_run, source=source)


if __name__ == "__main__":
    sys.exit(main())
