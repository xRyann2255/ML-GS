@echo off
REM Wrapper for GSSSO_AUTH: obtains a GSSSO cookie via PowerShell + DefaultCredentials.
REM Used by VS Code Tasks to avoid Allow prompts.
REM
REM Usage: get-cookie_task.cmd [--out-file path\to\cookie.txt]
REM
REM Prints the GSSSO cookie value to stdout.
REM If --out-file is given, also writes it to the specified file.

setlocal enabledelayedexpansion

set "OUT_FILE="
:parse_args
if "%~1"=="" goto run
if /I "%~1"=="--out-file" (
    set "OUT_FILE=%~2"
    shift & shift
    goto parse_args
)
shift
goto parse_args

:run
REM Delete stale cookie file so agent never reads old data on failure
if defined OUT_FILE if exist "%OUT_FILE%" del "%OUT_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; " ^
  "$url='https://authn.web.gs.com/desktopsso/Login'; " ^
  "try { " ^
  "  $r = Invoke-WebRequest -Uri $url -UseDefaultCredentials -UseBasicParsing -MaximumRedirection 5 -TimeoutSec 30 -SessionVariable s; " ^
  "  $c = $s.Cookies.GetCookies($url) | Where-Object { $_.Name -eq 'GSSSO' }; " ^
  "  if (-not $c) { Write-Error 'No GSSSO cookie returned'; exit 1 }; " ^
  "  $v = $c.Value; " ^
  "  [Console]::Out.Write($v); " ^
  "  if ('%OUT_FILE%' -ne '') { [System.IO.File]::WriteAllText('%OUT_FILE%', $v) }; " ^
  "} catch { Write-Error $_.Exception.Message; exit 1 }"
set "_EC=%ERRORLEVEL%"
call "%~dp0..\..\_shared\log_usage.cmd" GSSSO_AUTH
REM Always exit 0 so VS Code's close:true disposes the terminal.
exit /b 0
