"""Submit or update Slang script code reviews.

Execution is ALWAYS via secexpr stdin — no scratch scripts written to SecDB.

--scripts is ALWAYS required.  It specifies ALL scripts that belong to the
review — both for create and refresh.  This matches the IDE behaviour where
every submission includes the full script list.

Create (new review):
    python review.py --db "~{kerberos}!clean" --scripts "_LIB Foo" "Test: Foo" \\
        --subject "My change" --description "..." --driver-for-change "..." \\
        --testing-description "..."

Refresh existing review (new version with updated diffs):
    python review.py --db "~{kerberos}!clean" --scripts "_LIB Foo" "Test: Foo" \\
        --review "Review 20260331 6010-2204722S*" \\
        --testing-description "Updated testing notes"

Update metadata only (no diff refresh):
    python review.py --db "~{kerberos}!clean" --scripts "_LIB Foo" "Test: Foo" \\
        --review "Review 20260331 6010-2204722S*" \\
        --metadata-only --testing-description "Updated testing notes"

Troubleshooting:
    - If 'Container is a gob / SAFE mode' error on CREATE: the UserDB session blocks
      writes to production CoreData containers. Create the review manually via the
      Slang IDE first, then use --review to refresh it from here.
    - All secexpr logs land in workspace/tmp/slang_review_logs/<debug_id>__*.txt
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import webbrowser
from typing import Optional

# ---------------------------------------------------------------------------
# Bootstrap: import slang_escape from SLANG_EDIT skill
# ---------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SLANG_EDIT_SRC = os.path.join(SKILL_DIR, "..", "..", "SLANG_EDIT", "src")
sys.path.insert(0, SLANG_EDIT_SRC)
from edit import slang_escape  # noqa: E402
sys.path.insert(0, os.path.join(SKILL_DIR, "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

ENV_CMD = r"H:\all-languages-env.cmd"

# ---------------------------------------------------------------------------
# User config: workspace/config/user.yaml (gitignored, per-user preferences)
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
_USER_CONFIG_PATH = os.path.join(_REPO_ROOT, "workspace", "config", "user.json")

_REVIEW_DEFAULTS = {
    "auto_submit": False,
    "auto_commit": True,
    "auto_push": True,
}


def _load_review_config() -> dict:
    """Load review preferences from workspace/config/user.json.

    Falls back to defaults (all True) if the file is missing or malformed.
    """
    cfg = dict(_REVIEW_DEFAULTS)
    if os.path.isfile(_USER_CONFIG_PATH):
        try:
            with open(_USER_CONFIG_PATH, encoding="utf-8-sig") as f:
                data = json.load(f)
            review = data.get("review", {})
            for key in _REVIEW_DEFAULTS:
                if key in review:
                    cfg[key] = bool(review[key])
        except Exception as exc:
            _warn(f"failed to parse {_USER_CONFIG_PATH}: {exc}")
    return cfg


def _build_version_attrs(cfg: dict) -> str:
    """Build Slang Version Attrs expression from review config."""
    parts = []
    if cfg.get("auto_submit"):
        parts.append("SR Version Attr::AutoSubmitPlease, True")
    if cfg.get("auto_commit"):
        parts.append("SR Version Attr::AutoCommitPlease, True")
    if cfg.get("auto_push"):
        parts.append("SR Version Attr::AutoPushPlease, True")
    if parts:
        return f'Version Attrs := Structure( {", ".join(parts)} )'
    return ""


# ---------------------------------------------------------------------------
# Source chain: secexpr --source should be "PS".
# Session DB = CoreData (needed for ScriptReview index access).
# User DB is prepended to source so scripts resolve from there.
# SourceDb = SourceDatabase().Left (matches what the IDE passes).
# ---------------------------------------------------------------------------
DEFAULT_SOURCE = "PS"


def _expand_db(db: str) -> str:
    """Expand ~username!dbname alias to the full !NYC UserDBs!home!username!dbname path.

    secexpr requires the full path for ScriptReview library resolution
    to work correctly. Uses --safe mode (no --full needed).
    """
    m = re.match(r"^~(\w+)(!.*)?$", db)
    if m:
        username = m.group(1)
        suffix = m.group(2) or ""
        return f"!NYC UserDBs!home!{username}{suffix}"
    return db

SCRIPT_REVIEW_BASE_URL = "https://www.epssp.site.gs.com/ssps/ProdSource/ScriptReview?Name="


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _script_review_url(name: str) -> str:
    return SCRIPT_REVIEW_BASE_URL + urllib.parse.quote_plus(name)


def _repo_root() -> str:
    return _REPO_ROOT


def _log_dir() -> str:
    p = os.path.join(_repo_root(), "workspace", "tmp", "slang_review_logs")
    os.makedirs(p, exist_ok=True)
    return p


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _phase(label: str) -> None:
    print(f"\n[{_ts()}] ===== {label} =====")


def _info(msg: str) -> None:
    print(f"[{_ts()}]   {msg}")


def _warn(msg: str) -> None:
    print(f"[{_ts()}] WARN {msg}", file=sys.stderr)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _cmd_preamble() -> str:
    # After calling the env script, resolve secexpr to its full path and
    # trim PATH to a minimal set.  secexpr.cmd internally builds a ~6K
    # PATH; if the pre-existing PATH from all-languages-env.cmd (~2K) is
    # appended, the total exceeds cmd.exe's 8191-char line limit.
    return (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f"call {ENV_CMD} >nul 2>&1\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        'for /f "delims=" %%i in (\'where secexpr\') do set "SECEXPR_CMD=%%i"\r\n'
        'set "PATH=%SystemRoot%\\system32;%SystemRoot%"\r\n'
    )


# ---------------------------------------------------------------------------
# Slang expression helpers
# ---------------------------------------------------------------------------

def _slang_str(name: str) -> str:
    """Slang literal for a name; uses Chr(58) for ':' to avoid secexpr quoting issues."""
    if ":" in name:
        head, tail = name.split(":", 1)
        return f'Sprint( "{slang_escape(head)}", Chr( 58 ), "{slang_escape(tail)}" )'
    return f'"{slang_escape(name)}"'


# ---------------------------------------------------------------------------
# Slang code generators
# ---------------------------------------------------------------------------

def _add_newlines_to_prints(slang: str) -> str:
    """Prefix every Print() call with Chr(10) so markers appear on separate lines."""
    # Print( Sprint( args ) ) -> Print( Sprint( Chr( 10 ), args ) )
    slang = re.sub(r'Print\( Sprint\( ', 'Print( Sprint( Chr( 10 ), ', slang)
    # Print( "literal" ) -> Print( Sprint( Chr( 10 ), "literal" ) )
    # Note: needs an extra ) to close Print after wrapping in Sprint
    slang = re.sub(r'Print\( ("[^"]*") \)', r'Print( Sprint( Chr( 10 ), \1 ) )', slang)
    return slang


# secexpr stdin evaluates each line independently and has a ~4096-byte per-line buffer.
# The -t flag only enables error tracing — the line limit is inherent to stdin mode.
_SECEXPR_LINE_LIMIT = 4096


def _validate_line_lengths(slang: str, label: str) -> None:
    """Raise ValueError if any line in the generated Slang exceeds the secexpr stdin limit."""
    for i, line in enumerate(slang.split("\n")):
        if len(line) > _SECEXPR_LINE_LIMIT:
            raise ValueError(
                f"{label}: line {i} is {len(line)} chars (limit {_SECEXPR_LINE_LIMIT}). "
                f"Shorten --testing-description or reduce script count. "
                f"Preview: {line[:200]}..."
            )


_DEDUP_BLOCK = """\
Script Ptrs = Raw Ptrs;"""

# Build Expressions structure from SourceDatabase() so Generate Diff Datum
# can see user DB overlay content for CVSed scripts (the CoreData session
# otherwise only sees the production expression via Expression(ScriptPtr)).
_EXPRESSIONS_BLOCK = (
    'Exprs = {||}; '
    'ForEach( SP, Script Ptrs ) '
    '{ '
    '    Exprs[ CheckE( Security Name( SP ) ) ] = UseDatabase( SourceDatabase() ) Expression( SP ); '
    '}; '
)

_CLASSIFY_BLOCK = (
    'Existing Scripts = []; '
    'New Script List = []; '
    'ForEach( Script Ptr, Script Ptrs ) '
    '{ '
    '    SN = CheckE( Security Name( Script Ptr ) ); '
    '    Print( Sprint( "STEP=classify script=", SN ) ); '
    '    RevRaw = @CVS::Script Revision( Script Ptr ); '
    '    Rev = If( IsError( RevRaw ) ) "" : String( RevRaw ); '
    '    Print( Sprint( "STEP=classify_rev=", Rev ) ); '
    '    ProdRevRaw = Try() @CVS::Get Prodver Revision( Script Ptr ) : ""; '
    '    ProdRev = If( IsError( ProdRevRaw ) ) "" : String( ProdRevRaw ); '
    '    Print( Sprint( "STEP=classify_prodver=", ProdRev ) ); '
    '    Stat = Try() String( @CVS::Script Status( Script Ptr ) ) : "?"; '
    '    Print( Sprint( "STEP=classify_status=", Stat ) ); '
    '    EffRev = If( Size( Rev ) ) Rev : ProdRev; '
    '    If( !Size( EffRev ) ) '
    '    { '
    '        ProdSec = Try() UseDatabase( SourceDatabase().Left ) GetSecurity( SN ) : Null; '
    '        If( !IsNull( ProdSec ) && !IsError( ProdSec ) ) '
    '        { '
    '            ProdRevRaw2 = Try() @CVS::Script Revision( ProdSec ) : Null; '
    '            ProdRevFB = If( IsError( ProdRevRaw2 ) || IsNull( ProdRevRaw2 ) ) "" : String( ProdRevRaw2 ); '
    '            If( Size( ProdRevFB ) ) { EffRev = ProdRevFB; }; '
    '            Print( Sprint( "STEP=classify_prod_fallback rev=", ProdRevFB ) ) '
    '        } '
    '    }; '
    '    If( Size( EffRev ) ) '
    '    { '
    '        Existing Scripts &= {| Script Name := SN; Revision1 := EffRev; Revision2 := "" |}; '
    '        Print( Sprint( "STEP=classify_result type=cvsed rev=", EffRev ) ) '
    '    } '
    '    : '
    '    { '
    '        Auto Path = @CVS::Get Slang Auto Dir FilePath( SN ); '
    '        Print( Sprint( "STEP=classify_autopath dir=", Auto Path.Directory, " file=", Auto Path.FileName ) ); '
    '        Auto Fp = Auto Path.Directory + "/" + Auto Path.FileName; '
    '        Auto Rev Raw = Try() String( @CVS::Script Revision File( Auto Fp ) ) : ""; '
    '        Auto Rev = If( IsError( Auto Rev Raw ) ) "" : Auto Rev Raw; '
    '        Print( Sprint( "STEP=classify_auto_rev=", Auto Rev ) ); '
    '        If( Size( Auto Rev ) ) '
    '        { '
    '            Existing Scripts &= {| Script Name := SN; Revision1 := Auto Rev; Revision2 := "" |}; '
    '            Print( Sprint( "STEP=classify_result type=auto_cvsed rev=", Auto Rev ) ) '
    '        } '
    '        : '
    '        { '
    '            New Script List &= {| Script Name := SN; Directory := Auto Path.Directory; FileName := Auto Path.FileName |}; '
    '            Print( Sprint( "STEP=classify_result type=new" ) ) '
    '        } '
    '    } '
    '};'
)


def build_review_slang(
    script_names: list[str],
    mail_subject: str = "",
    description: str = "",
    driver_for_change: str = "",
    testing_description: str = "",
    user_db: str = "",
    source: str = "",
) -> str:
    """Slang for creating a NEW code review.

    Structured as sequential top-level statements so each line stays under
    the secexpr stdin ~4096-char per-line buffer.  Top-level variables persist
    across stdin line evaluations.
    """
    array_items = ", ".join(_slang_str(n) for n in script_names)
    # SourceDb = SourceDatabase().Left = ProdSource (matches IDE behavior).
    source_db_arg = 'SourceDatabase().Left'
    # Session is CoreData (for ScriptReview index access), so scripts in the
    # user DB aren't directly resolvable.  UseDatabase(SourceDatabase()) sets
    # the lookup context to the full source chain (userDB;PS) for resolution.
    raw_ptrs_block = "Raw Ptrs = Security List( UseDatabase( SourceDatabase() ) @SecFns::Get Many Securities( All Scripts ) );"

    va_expr = _build_version_attrs(_load_review_config())
    _va_suffix = f", {va_expr}" if va_expr else ""

    edit_params_expr = (
        f'Edit Params = ScriptReview::Edit Params( '
        f'Mail Subject := "{slang_escape(mail_subject)}", '
        f'Description := "{slang_escape(description)}", '
        f'Driver For Change Stored := "{slang_escape(driver_for_change)}", '
        f'Testing Description := "{slang_escape(testing_description)}", '
        f'Change Risk Class := CM ChangeRiskClass::Low, '
        f'Is HRA FI Change := False, Tested := True{_va_suffix} );'
    )

    lines = [
        'Link( "_LIB Script Review Fns" );',
        'Link( "_LIB HTML Helper Fns" );',
        'Link( "_LIB Web Browser Control" );',
        'Link( "_LIB Security Fns" );',
        'Link( "_LIB CVS Script Functions" );',
        'Link( "_LIB CVS Commit Helper Fns" );',
        'Link( "_TYPE Script Review Helpers" );',
        'Link( "_Const Controls CM" );',
        'Link( "_Const Script Review" );',
        'Print( "PHASE=libs_linked" );',
        f'All Scripts = [ {array_items} ];',
        f'{raw_ptrs_block} Print( Sprint( "STEP=raw_ptrs count=", Size( Raw Ptrs ) ) );',
        f'{_DEDUP_BLOCK}',
        f'{_CLASSIFY_BLOCK}',
        f'Print( Sprint( "STEP=classified cvsed=", Size( Existing Scripts ), " new=", Size( New Script List ) ) );',
        f'{_EXPRESSIONS_BLOCK}',
        f'Print( "STEP=gen_diff_datum" );',
        f'Scripts Diff Datum = Try( GDD_Ex ) @ScriptReview::Generate Diff Datum Structure( Security List( Script Ptrs ), Exprs, Existing Scripts, New Scripts := New Script List, SourceDb := {source_db_arg} ) : GDD_Ex;',
        f'Print( Sprint( "STEP=diff_datum is_error=", If( IsError( Scripts Diff Datum ), "YES", "NO" ) ) );',
        f'If( IsError( Scripts Diff Datum ) ) {{ Print( Sprint( "DIFF_DATUM_ERROR=", String( Scripts Diff Datum ) ) ) }};',
        edit_params_expr,
        'Print( "STEP=calling_create_review" );',
        'If( !IsError( Scripts Diff Datum ) ) {{ Diffs = Try( CR_Ex ) @ScriptReview::Create Review( Script Ptrs, Scripts Diff Datum, Display Review Page := False, Edit Params := Edit Params ) : CR_Ex; }} : {{ Diffs = Scripts Diff Datum; }};',
        'Print( Sprint( "STEP=create_review is_error=", If( IsError( Diffs ), "YES", "NO" ) ) );',
        'If( IsError( Diffs ) ) { Print( Sprint( "DIFFS_ERROR=", String( Diffs ) ) ) } : { CN = Try() Diffs.ContainerName : String( Diffs ); Print( Sprint( "REVIEW_URL=", CN ) ) };',
    ]
    slang = "\n".join(lines) + "\n"
    slang = _add_newlines_to_prints(slang)
    _validate_line_lengths(slang, "build_review_slang")
    return slang


def build_refresh_slang(
    review_name: str,
    script_names: list[str],
    mail_subject: str = "",
    description: str = "",
    driver_for_change: str = "",
    testing_description: str = "",
    user_db: str = "",
    source: str = "",
) -> str:
    """Slang for refreshing an EXISTING review (creates a new version with updated diffs).

    script_names is the full list of scripts to include — matches IDE behaviour.

    Structured as sequential top-level statements so each line stays under
    the secexpr stdin ~4096-char per-line buffer.  Top-level variables persist
    across stdin line evaluations.
    """
    review_expr = _slang_str(review_name)
    array_items = ", ".join(_slang_str(n) for n in script_names)
    # SourceDb = SourceDatabase().Left = ProdSource (matches IDE behavior).
    source_db_arg = 'SourceDatabase().Left'
    # Session is CoreData, so use the source chain for script resolution.
    raw_ptrs_block = "Raw Ptrs = Security List( UseDatabase( SourceDatabase() ) @SecFns::Get Many Securities( All Scripts ) );"
    edit_parts = []
    if mail_subject:
        edit_parts.append(f'Mail Subject := "{slang_escape(mail_subject)}"')
    if description:
        edit_parts.append(f'Description := "{slang_escape(description)}"')
    if driver_for_change:
        edit_parts.append(f'Driver For Change Stored := "{slang_escape(driver_for_change)}"')
    if testing_description:
        edit_parts.append(f'Testing Description := "{slang_escape(testing_description)}"')
    edit_parts.append('Tested := True')
    edit_parts.append('Is HRA FI Change := False')
    edit_args_inline = ", ".join(edit_parts)

    lines = [
        'Link( "_LIB Script Review Load Fns" );',
        'Link( "_LIB Script Review Fns" );',
        'Link( "_LIB Security Fns" );',
        'Link( "_LIB CVS Script Functions" );',
        'Link( "_LIB CVS Commit Helper Fns" );',
        'Link( "_TYPE Script Review Helpers" );',
        'Link( "_Const Controls CM" );',
        'Link( "_Const Script Review" );',
        'Print( "PHASE=libs_linked" );',
        f'Review Name = {review_expr};',
        'Print( Sprint( "STEP=loading_review name=", Review Name ) );',
        'Existing = @Script Review::Load Review( Review Name, Use RW Db := True, Refresh := True );',
        'Print( Sprint( "STEP=load_done is_error=", If( IsError( Existing ), "YES", "NO" ) ) );',
        'Old Ver = Try() Existing.Latest Version Number() : 0; Print( Sprint( "REFRESH_OLD_VERSION=", String( Old Ver ) ) );',
        f'All Scripts = [ {array_items} ];',
        f'{raw_ptrs_block} Print( Sprint( "STEP=raw_ptrs count=", Size( Raw Ptrs ) ) );',
        f'{_DEDUP_BLOCK}',
        f'{_CLASSIFY_BLOCK}',
        f'Print( Sprint( "STEP=classified cvsed=", Size( Existing Scripts ), " new=", Size( New Script List ) ) );',
        f'{_EXPRESSIONS_BLOCK}',
        f'Print( "STEP=gen_diff_datum" );',
        f'Scripts Diff Datum = Try( GDD_Ex ) @ScriptReview::Generate Diff Datum Structure( Security List( Script Ptrs ), Exprs, Existing Scripts, New Scripts := New Script List, SourceDb := {source_db_arg} ) : GDD_Ex;',
        f'Print( Sprint( "STEP=diff_datum is_error=", If( IsError( Scripts Diff Datum ), "YES", "NO" ) ) );',
        f'If( IsError( Scripts Diff Datum ) ) {{ Print( Sprint( "DIFF_DATUM_ERROR=", String( Scripts Diff Datum ) ) ) }};',
        f'Edit Params = ScriptReview::Edit Params( {edit_args_inline} );',
        'Print( "STEP=calling_create_review_refresh" );',
        'If( !IsError( Scripts Diff Datum ) ) {{ Diffs = Try( CR_Ex ) @ScriptReview::Create Review( Script Ptrs, Scripts Diff Datum, ReviewName := Review Name, Display Review Page := False, Skip Tests := False, Suppress Notification := True, Suppress Notification Mail := True, Suppress Notification Paragon := True, Edit Params := Edit Params ) : CR_Ex; }} : {{ Diffs = Scripts Diff Datum; }};',
        'Print( Sprint( "STEP=create_review is_error=", If( IsError( Diffs ), "YES", "NO" ) ) );',
        'If( IsError( Diffs ) ) { Print( Sprint( "DIFFS_ERROR=", String( Diffs ) ) ); } : { New Ver = Try() Diffs.Latest Version Number() : "?"; Print( Sprint( "REFRESH_NEW_VERSION=", String( New Ver ) ) ); CN = Try() Diffs.ContainerName : String( Diffs ); Print( Sprint( "REVIEW_URL=", CN ) ); };',
    ]
    slang = "\n".join(lines) + "\n"
    slang = _add_newlines_to_prints(slang)
    _validate_line_lengths(slang, "build_refresh_slang")
    return slang


def build_metadata_slang(
    review_name: str,
    mail_subject: str = "",
    description: str = "",
    driver_for_change: str = "",
    testing_description: str = "",

) -> str:
    """Slang for updating review metadata only (no diff refresh — much faster)."""
    review_expr = _slang_str(review_name)
    update_args = []
    if mail_subject:
        update_args.append(f'Mail Subject := "{slang_escape(mail_subject)}"')
    if description:
        update_args.append(f'Description := "{slang_escape(description)}"')
    if driver_for_change:
        update_args.append(f'Driver for Change Stored := "{slang_escape(driver_for_change)}"')
    if testing_description:
        update_args.append(f'Testing Description := "{slang_escape(testing_description)}"')
    update_args.append('Tested := True')
    update_args.append('Is HRA FI Change := False')
    update_args_inline = ", ".join(update_args)

    lines = [
        'Link( "_LIB Script Review Load Fns" );',
        'Link( "_Const Controls CM" );',
        'Print( "PHASE=libs_linked" );',
        (
            f'Try( TopEx ) {{ '
            f'Review Name = {review_expr}; '
            f'Print( Sprint( "STEP=loading_review name=", Review Name ) ); '
            f'Diffs = @Script Review::Load Review( Review Name, Use RW Db := True ); '
            f'Print( Sprint( "STEP=load_done is_error=", If( IsError( Diffs ), "YES", "NO" ) ) ); '
            f'If( IsError( Diffs ) ) '
            f'{{ Print( Sprint( "LOAD_ERROR=", String( Diffs ) ) ) }} '
            f': '
            f'{{ '
            f'CN = Try() Diffs.ContainerName : String( Diffs ); '
            f'Print( Sprint( "LOADED_REVIEW=", CN ) ); '
            f'Print( "STEP=updating_metadata" ); '
            f'Try() Diffs.Update Review Details( LoginName(), {update_args_inline} ) : Print( "WARNING=Update Review Details failed" ); '
            f'Print( Sprint( "STEP=metadata_done" ) ); '
            f'Print( Sprint( "REVIEW_URL=", CN ) ) '
            f'}}; '
            f'}} : {{ Print( Sprint( "FATAL_EXCEPTION=", String( TopEx ) ) ); }};'
        ),
    ]
    slang = "\n".join(lines) + "\n"
    return _add_newlines_to_prints(slang)


# ---------------------------------------------------------------------------
# Execution engine  (stdin ONLY — no scratch scripts)
# ---------------------------------------------------------------------------

# CoreData is the session DB for ScriptReview index access.
_COREDATA_DB = "CoreData RW"  # noqa: hardcoded-db (shared system DB, not user-specific)


def run_slang(
    db: str,
    slang_path: str,
    source: str,
    log_dir: str,
    debug_id: str,
    timeout: int = 300,
) -> tuple[int, str, str]:
    """Pipe a Slang file to secexpr via stdin.  Returns (rc, stdout, stderr).

    Session DB is CoreData RW so ScriptReview can access its indexes.
    The user DB is prepended to --source so scripts resolve from there.
    SourceDb in the Slang uses SourceDatabase().Left (matching IDE behavior)
    to avoid contaminating the lint baseline with the user DB.

    NOTE: -w flag is intentionally NOT used. Without -w, secexpr writes
    Print() output to stdout which subprocess.run() captures correctly.
    With -w, output goes to a Slang window and stdout is empty.
    """
    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="review_run_")
    stderr_path = os.path.join(log_dir, f"{debug_id}__stderr.txt")
    try:
        # Session DB = CoreData (needed for ScriptReview By Expiry index).
        # User DB prepended to source so scripts resolve from there.
        user_db = _expand_db(db)
        secexpr_db = _COREDATA_DB
        full_source = f"{user_db};{source}"
        with os.fdopen(fd, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(_cmd_preamble())
            # Redirect stderr to file to avoid capturing massive 3001 noise
            # (50K+ lines) that can overwhelm subprocess output buffers and
            # obscure stdout markers.
            f.write(f'"%SECEXPR_CMD%" "{secexpr_db}" --safe --source "{full_source}" -t < "{slang_path}" 2>"{stderr_path}"\n')

        _info(f"batch       : {batch_path}")
        _info(f"slang       : {slang_path} ({os.path.getsize(slang_path)} B)")
        _info(f"session_db  : {secexpr_db}  (CoreData — for ScriptReview index access)")
        _info(f"user_db     : {user_db}  (in source chain)")
        _info(f"full_source : {full_source}")
        _info(f"stderr_file : {stderr_path}")
        _info(f"timeout     : {timeout}s")

        t0 = time.time()
        try:
            proc = run_cmd(
                ["cmd", "/c", batch_path],
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - t0
            stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
            stderr = ""
            if os.path.isfile(stderr_path):
                try:
                    with open(stderr_path, "r", encoding="utf-8", errors="replace") as sf:
                        stderr = sf.read()
                except OSError:
                    pass
            _write_text(os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout)
            # stderr already written to file by secexpr redirect
            _warn(f"secexpr TIMED OUT after {elapsed:.0f}s")
            _info("Increase --timeout if the review generation is legitimately slow.")
            _info(f"Partial stdout ({len(stdout)} B): {stdout[:300]}")
            return -1, stdout, stderr

        elapsed = time.time() - t0
        stdout = proc.stdout.decode("utf-8", errors="replace")
        # Read stderr from the redirect file (not from subprocess)
        stderr = ""
        if os.path.isfile(stderr_path):
            try:
                with open(stderr_path, "r", encoding="utf-8", errors="replace") as sf:
                    stderr = sf.read()
            except OSError:
                pass

        _write_text(os.path.join(log_dir, f"{debug_id}__stdout.txt"), stdout)

        _info(f"elapsed : {elapsed:.1f}s")
        _info(f"exit_rc : {proc.returncode}")
        _info(f"stdout  : {len(stdout)} B  ->  {log_dir}/{debug_id}__stdout.txt")
        _info(f"stderr  : {len(stderr)} B  ->  {log_dir}/{debug_id}__stderr.txt")
        return proc.returncode, stdout, stderr
    finally:
        try:
            os.unlink(batch_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

def _parse_review_url(stdout: str) -> Optional[str]:
    """Extract REVIEW_URL value from concatenated Print() output."""
    # Split on any known marker prefix so we can isolate the value
    tokens = re.split(
        r"(?=PHASE=|STEP=|REVIEW_URL=|REFRESH_|LOADED_|LOAD_ERROR=|DIFFS_ERROR=|FATAL_EXCEPTION=|WARNING=)",
        stdout,
    )
    candidates = []
    for t in tokens:
        if t.startswith("REVIEW_URL="):
            val = t[len("REVIEW_URL="):].strip()
            m = re.search(r"Review\s+\d{8}\s+6010-\d+S\*", val)
            candidates.append(m.group(0) if m else val)
    return candidates[-1] if candidates else None


def _extract_marker(stdout: str, marker: str) -> Optional[str]:
    """Extract value after marker in concatenated stdout."""
    tokens = re.split(
        r"(?=PHASE=|STEP=|REVIEW_URL=|REFRESH_|LOADED_|LOAD_ERROR=|DIFFS_ERROR=|FATAL_EXCEPTION=|WARNING=)",
        stdout,
    )
    for t in tokens:
        if t.startswith(marker):
            return t[len(marker):].strip()
    return None


def _report_stdout_markers(stdout: str) -> None:
    """Print each recognized marker from the (concatenated) stdout."""
    tokens = re.split(
        r"(?=PHASE=|STEP=|REVIEW_URL=|REFRESH_OLD|REFRESH_NEW|LOADED_REVIEW=|"
        r"LOAD_ERROR=|DIFFS_ERROR=|FATAL_EXCEPTION=|WARNING=)",
        stdout,
    )
    for t in tokens:
        t = t.strip()
        if t:
            _info(f">> {t[:300]}")


def _detect_safe_mode(stderr: str) -> bool:
    return "SAFE mode will be enabled" in stderr or "NON-PRODUCTION CHECK" in stderr


def _actionable_errors(stdout: str, stderr: str) -> list[str]:
    """Collect the most useful diagnostic lines."""
    result: list[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        key = line.strip()
        if key and key not in seen:
            seen.add(key)
            result.append(key)

    # Explicit markers from our Slang
    for marker in ("FATAL_EXCEPTION=", "DIFFS_ERROR=", "LOAD_ERROR="):
        val = _extract_marker(stdout, marker)
        if val:
            add(f"{marker}{val[:400]}")

    # High-priority stderr patterns
    for line in stderr.splitlines():
        if re.search(
            r"Slang Error encountered|Container is a gob|Unsupported Operation|"
            r"GsException|SAFE mode|NON-PRODUCTION|SecDbIndexFromName",
            line,
        ):
            add(line.strip())

    # Non-noise stderr errors
    for line in stderr.splitlines():
        if "ERROR:" in line and "(3001)" not in line and "(2000)" not in line and "WARNING" not in line:
            add(line.strip())
        if len(result) >= 20:
            break

    return result


# ---------------------------------------------------------------------------
# Post-success validation
# ---------------------------------------------------------------------------

def validate_review(db: str, source: str, review_name: str, log_dir: str, debug_id: str) -> None:
    """Run SLANG_REVIEW_INSPECT to confirm the review is reachable (best-effort)."""
    inspect_py = os.path.join(SKILL_DIR, "..", "..", "SLANG_REVIEW_INSPECT", "src", "inspect.py")
    if not os.path.isfile(inspect_py):
        _info("(SLANG_REVIEW_INSPECT not found; skipping validation)")
        return

    _phase("Post-run inspect — confirming review is reachable")
    cmd = [sys.executable, inspect_py, "--db", db, "--review", review_name,
           "--source", source]
    try:
        proc = run_cmd(cmd, capture_output=True, timeout=180)
    except Exception as exc:
        _warn(f"inspect failed to launch: {exc}")
        return

    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    _write_text(os.path.join(log_dir, f"{debug_id}__inspect_stdout.txt"), out)
    _write_text(os.path.join(log_dir, f"{debug_id}__inspect_stderr.txt"), err)

    marker_prefixes = (
        "INSPECT_LOAD_FAILED=", "REVIEW_CONTAINER=", "LATEST_VERSION=",
        "NUM_SCRIPTS=", "SCRIPT=", "SCRIPT_CVS_REV=", "REVIEW_URL=",
        "HAS_TEST_SCRIPT=", "HAS_TEST_SCRIPT_HEADER=", "WEB_",
    )
    for ln in out.splitlines():
        if any(ln.startswith(p) for p in marker_prefixes) or ln.startswith("Logs:"):
            _info(ln)

    if "WEB_PROBLEM=1" in out:
        _warn("ScriptReview web page reports problems (see WEB_* markers above).")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Submit or update Slang script code reviews (stdin-only execution).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--db", required=False, default="",
                    help='SecDB session DB (e.g. "~{kerberos}!clean")')
    ap.add_argument("--scripts", nargs="+", required=False, default=None,
                    help="Script names (always required — full list for both create and refresh)")
    ap.add_argument("--review",
                    help="Existing review name — refresh it (omit to create a new review)")
    ap.add_argument("--subject", default="", help="Mail subject / title")
    ap.add_argument("--description", default="", help="Change description")
    ap.add_argument("--driver-for-change", default="", dest="driver_for_change")
    ap.add_argument("--testing-description", default="", dest="testing_description")
    ap.add_argument("--metadata-only", action="store_true",
                    help="With --review: update metadata only (no diff refresh)")
    ap.add_argument("--source", default=None,
                    help=f"secexpr --source override (default: {DEFAULT_SOURCE})")
    ap.add_argument("--timeout", type=int, default=300,
                    help="secexpr timeout in seconds (default: 300)")
    # --- Task-based execution (zero Allow) ---
    ap.add_argument("--args-file", default=None, metavar="PATH",
                    help="JSON file with review arguments (keys mirror CLI flags)")
    ap.add_argument("--output-json", default=None, metavar="PATH",
                    help="Write machine-readable JSON results to PATH (with sentinel)")
    args = ap.parse_args()

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8-sig") as af:
            af_data = json.load(af)
        if af_data.get("db") and not args.db:
            args.db = af_data["db"]
        elif af_data.get("db"):
            args.db = af_data["db"]
        if af_data.get("scripts") and not args.scripts:
            args.scripts = af_data["scripts"]
        if af_data.get("review") and not args.review:
            args.review = af_data["review"]
        if af_data.get("subject") and not args.subject:
            args.subject = af_data["subject"]
        if af_data.get("description") and not args.description:
            args.description = af_data["description"]
        if af_data.get("driver_for_change") and not args.driver_for_change:
            args.driver_for_change = af_data["driver_for_change"]
        if af_data.get("testing_description") and not args.testing_description:
            args.testing_description = af_data["testing_description"]
        if af_data.get("metadata_only"):
            args.metadata_only = True
        if af_data.get("source") and not args.source:
            args.source = af_data["source"]
        if af_data.get("timeout") and args.timeout == 300:
            args.timeout = af_data["timeout"]
        if af_data.get("output_json") and not args.output_json:
            args.output_json = af_data["output_json"]
        if af_data.get("run_id"):
            args.run_id = af_data["run_id"]

    run_id = getattr(args, "run_id", None) or ""

    if not args.scripts:
        ap.error("--scripts is required (either via CLI or --args-file)")
    if not args.db:
        ap.error("--db is required (either via CLI or --args-file)")

    # --- Mandatory metadata on create ---
    if not args.review:
        missing = []
        if not args.subject:
            missing.append("--subject")
        if not args.description:
            missing.append("--description")
        if not args.driver_for_change:
            missing.append("--driver-for-change")
        if missing:
            ap.error(f"the following arguments are required for new reviews: {', '.join(missing)}")

    # --- Quality gate: minimum length & word count for key fields ---
    _MIN_CHARS = 20
    _MIN_WORDS = 3
    _quality_fields = {
        "--subject (title)": args.subject,
        "--description": args.description,
        "--driver-for-change": args.driver_for_change,
    }
    quality_errors = []
    for label, value in _quality_fields.items():
        if not value:
            continue  # already caught by the missing-field check above
        stripped = value.strip()
        if len(stripped) < _MIN_CHARS:
            quality_errors.append(
                f"{label} must be at least {_MIN_CHARS} characters (got {len(stripped)})"
            )
        if len(stripped.split()) < _MIN_WORDS:
            quality_errors.append(
                f"{label} must have at least {_MIN_WORDS} words (got {len(stripped.split())})"
            )
    if quality_errors:
        ap.error("field quality checks failed:\n  " + "\n  ".join(quality_errors))

    # --- No two fields may share the same value ---
    _dedup_fields = [
        ("--subject (title)", args.subject.strip()),
        ("--description", args.description.strip()),
        ("--driver-for-change", args.driver_for_change.strip()),
    ]
    for i in range(len(_dedup_fields)):
        for j in range(i + 1, len(_dedup_fields)):
            a_label, a_val = _dedup_fields[i]
            b_label, b_val = _dedup_fields[j]
            if a_val and b_val and a_val == b_val:
                ap.error(f"{a_label} and {b_label} must not have the same value")

    source = args.source or DEFAULT_SOURCE
    debug_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ld = _log_dir()

    # ---------- Write running sentinel ----------
    json_path = args.output_json
    if not json_path:
        # Use run_id in filename to avoid collisions between concurrent sessions
        suffix = f"_{run_id}" if run_id else ""
        json_path = os.path.join(_REPO_ROOT, "workspace", "tmp",
                                  f"slang_review_results{suffix}.json")
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"status": "running", "run_id": run_id,
                   "debug_id": debug_id}, jf)

    # ---------- Startup banner ----------
    _phase("review.py — startup")
    user_db_expanded = _expand_db(args.db)
    _info(f"db (user)   : {args.db}  (expanded: {user_db_expanded})")
    _info(f"session_db  : {_COREDATA_DB}  (CoreData \u2014 for ScriptReview index access)")
    _info(f"source      : {user_db_expanded};{source}")
    mode_str = "create" if not args.review else ("metadata-only" if args.metadata_only else "refresh")
    _info(f"mode        : {mode_str}")
    _info(f"scripts     : {args.scripts}")
    if args.review:
        _info(f"review      : {args.review}")
    _info(f"debug_id    : {debug_id}")
    _info(f"log_dir     : {ld}")

    # ---------- User config ----------
    rcfg = _load_review_config()
    cfg_source = _USER_CONFIG_PATH if os.path.isfile(_USER_CONFIG_PATH) else "defaults"
    _info(f"user_config : {cfg_source}")
    _info(f"auto_submit={rcfg['auto_submit']}  auto_commit={rcfg['auto_commit']}  auto_push={rcfg['auto_push']}")

    # ---------- Build Slang ----------
    _phase("Building Slang expression")
    if not args.review:
        slang = build_review_slang(
            args.scripts,
            mail_subject=args.subject,
            description=args.description,
            driver_for_change=args.driver_for_change,
            testing_description=args.testing_description,
            user_db=user_db_expanded,
            source=source,
        )
    elif args.metadata_only:
        slang = build_metadata_slang(
            args.review,
            mail_subject=args.subject,
            description=args.description,
            driver_for_change=args.driver_for_change,
            testing_description=args.testing_description,
        )
    else:
        slang = build_refresh_slang(
            args.review,
            script_names=args.scripts,
            mail_subject=args.subject,
            description=args.description,
            driver_for_change=args.driver_for_change,
            testing_description=args.testing_description,
            user_db=user_db_expanded,
            source=source,
        )

    slang_path = os.path.join(ld, f"{debug_id}__review_slang.slang")
    _write_text(slang_path, slang)
    _info(f"saved: {slang_path} ({len(slang)} B)")

    # ---------- Execute ----------
    _phase("Running secexpr (stdin — NO scratch scripts)")
    rc, stdout, stderr = run_slang(
        db=args.db,
        slang_path=slang_path,
        source=source,
        log_dir=ld,
        debug_id=debug_id,
        timeout=args.timeout,
    )

    # ---------- Parse ----------
    _phase("Parsing secexpr output")
    _report_stdout_markers(stdout)

    review_name = _parse_review_url(stdout)

    # ---------- Result ----------
    result_data = {
        "status": "done",
        "run_id": run_id,
        "debug_id": debug_id,
        "mode": mode_str,
        "scripts": args.scripts,
    }
    if review_name:
        _phase("SUCCESS")
        _info(f"REVIEW_URL={review_name}")
        old_v = _extract_marker(stdout, "REFRESH_OLD_VERSION=")
        new_v = _extract_marker(stdout, "REFRESH_NEW_VERSION=")
        if old_v or new_v:
            _info(f"version: {old_v or '?'} -> {new_v or '?'}")

        validate_review(args.db, source, review_name, ld, debug_id)

        url = _script_review_url(review_name)
        _info(f"BROWSER_URL={url}")
        webbrowser.open(url)

        result_data["gate"] = "PASS"
        result_data["review_name"] = review_name
        result_data["review_url"] = url
        if old_v:
            result_data["old_version"] = old_v
        if new_v:
            result_data["new_version"] = new_v
    else:
        _phase("FAILURE — no REVIEW_URL in output")

        diags = _actionable_errors(stdout, stderr)
        safe_mode = _detect_safe_mode(stderr)

        if safe_mode:
            print()
            _info("*** SAFE MODE DETECTED ***")
            _info("  The UserDB session blocks writes to production CoreData containers.")
            _info("  This prevents creating NEW reviews programmatically.")
            _info("  FIX for NEW reviews:")
            _info("    1. Create the review manually in the Slang IDE.")
            _info("    2. Note the review name (e.g. 'Review 20260407 6010-XXXXS*').")
            _info("    3. Re-run: python review.py --review \"Review ...\" (refresh mode).")

        print()
        _info("Diagnostics:")
        for e in diags:
            _info(f"  {e}")

        print()
        _info(f"stdout preview: {stdout[:500]!r}")
        print()
        _info(f"Full logs:")
        _info(f"  stdout -> {ld}/{debug_id}__stdout.txt")
        _info(f"  stderr -> {ld}/{debug_id}__stderr.txt")
        _info(f"  slang  -> {slang_path}")

        result_data["gate"] = "FAIL"
        result_data["safe_mode"] = safe_mode
        result_data["diagnostics"] = diags[:10]

    # ---------- Write final results ----------
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(result_data, jf, indent=2)

    if not review_name:
        sys.exit(1)


if __name__ == "__main__":
    main()
