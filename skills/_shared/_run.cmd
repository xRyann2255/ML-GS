@echo off
REM _run.cmd — Shared bootstrap for Python-based VS Code tasks.
REM
REM The calling wrapper must set two env vars before calling:
REM   _PY_SCRIPT  = absolute path to the Python entry point
REM   _SKILL      = uppercase skill name for usage logging
REM
REM Example wrapper (3 lines):
REM   @echo off
REM   set "_PY_SCRIPT=%~dp0query.py" & set "_SKILL=CANVAS"
REM   call "%~dp0..\..\_shared\_run.cmd" %*
REM
REM This script handles:
REM   1. Environment setup (H:\all-languages-env.cmd)
REM   2. Python venv auto-detection (H:\venv315..38)
REM   3. Args-file existence validation (fail fast)
REM   4. Stale output cleanup (deletes out_file/output_json before run)
REM   5. Python script execution with exit code capture
REM   6. Usage logging via log_usage.cmd

if not defined _PY_SCRIPT (
    echo ERROR: _PY_SCRIPT not set >&2
    exit /b 1
)

REM ---- Environment ----
call H:\all-languages-env.cmd >nul 2>&1

REM ---- Python venv auto-detect ----
set "PY="
for %%V in (315 314 313 312 311 310 39 38) do (
    if not defined PY if exist "H:\venv%%V\Scripts\python.exe" set "PY=H:\venv%%V\Scripts\python.exe"
)
if not defined PY (
    echo ERROR: No Python venv found in H:\venv*
    exit /b 1
)

REM ---- Locate --args-file value ----
set "_AF="
call :_findaf %*

REM ---- Validate args-file & clean stale output ----
if defined _AF (
    if not exist "%_AF%" (
        echo ERROR: args file not found: %_AF%
        exit /b 1
    )
    REM Delete stale output so agent never reads old data on failure
    "%PY%" -c "import json,os,sys;a=json.load(open(sys.argv[1]));[os.remove(f) for k in ('out_file','output_json') for f in [a.get(k,'')] if f and os.path.isfile(f)]" "%_AF%" 2>nul
)

REM ---- Run ----
"%PY%" "%_PY_SCRIPT%" %*
set "_EC=%ERRORLEVEL%"
call "%~dp0log_usage.cmd" %_SKILL%
REM Always exit 0 so VS Code's close:true disposes the terminal.
REM Actual success/failure is communicated via out_file content.
exit /b 0

:_findaf
if "%~1"=="" exit /b
if /I "%~1"=="--args-file" ( set "_AF=%~2" & exit /b )
shift
goto :_findaf
