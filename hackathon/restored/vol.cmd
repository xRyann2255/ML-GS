@echo off
REM vol.cmd — Windows (S-A) dev-loop shim for ./vol. Plan 03 / wfo-03-2.
REM Supported arms: test test-all testlf lint fmt typecheck exec bg jobs help.
REM Every other ./vol arm is Linux-only: exit 2 pointing at S-B.
REM Sentinel protocol (identical to ./vol exec/bg):
REM   prints OUTPUT_FILE=<workspace\tmp\exec\<ts>_<pid>.out>; file's last line is EXIT_CODE=<rc>.
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
set "SRC=%ROOT%src"

REM ---- Interpreter resolution (ledger order; shared with skills\_shared\_run.cmd) ----
set "PY="
REM 1) workspace\config\user.json python_path
if exist "%ROOT%workspace\config\user.json" (
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "try { (Get-Content -Raw '%ROOT%workspace\config\user.json' | ConvertFrom-Json).python_path } catch { '' }"`) do (
        if exist "%%P" set "PY=%%P"
    )
)
REM 2) H:\venv scan (newest first — same list as _run.cmd)
if not defined PY for %%V in (315 314 313 312 311 310 39 38) do (
    if not defined PY if exist "H:\venv%%V\Scripts\python.exe" set "PY=H:\venv%%V\Scripts\python.exe"
)
REM 3) repo-local venv
if not defined PY if exist "%SRC%\.venv\Scripts\python.exe" set "PY=%SRC%\.venv\Scripts\python.exe"
REM 4) PATH
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY (
    echo ERROR: no Python interpreter found. Checked: user.json python_path, H:\venv*, src\.venv, PATH. >&2
    echo Fallback: run this command via ./vol on S-B ^(GS Linux Coder workspace^). >&2
    exit /b 2
)

set "CMD=%~1"
if "%CMD%"=="" set "CMD=help"

REM ---- Collect args after the subcommand (%* cannot be shifted in cmd) ----
set "ARGS="
:collect
shift
if "%~1"=="" goto dispatch
set ARGS=!ARGS! "%~1"
goto collect

:dispatch
if /I "%CMD%"=="help"      goto do_help
if /I "%CMD%"=="test"      goto do_test
if /I "%CMD%"=="test-all"  goto do_testall
if /I "%CMD%"=="testlf"    goto do_testlf
if /I "%CMD%"=="lint"      goto do_lint
if /I "%CMD%"=="fmt"       goto do_fmt
if /I "%CMD%"=="typecheck" goto do_typecheck
if /I "%CMD%"=="exec"      goto do_exec
if /I "%CMD%"=="bg"        goto do_bg
if /I "%CMD%"=="jobs"      goto do_jobs
echo ERROR: "%CMD%" is GS Coder workspace only — run via ./vol on S-B. >&2
exit /b 2

:do_help
echo vol.cmd — Windows dev-loop shim for ./vol (S-A)
echo.
echo Usage: vol.cmd ^<command^> [args...]
echo.
echo   test [args]        pytest, skipping @pytest.mark.slow (mirror of ./vol test)
echo   test-all [args]    full pytest suite
echo   testlf [args]      re-run last-failed tests
echo   lint [args]        ruff check .
echo   fmt [args]         ruff format .
echo   typecheck [args]   mypy volforecast/
echo   exec ^<cmd...^>      run captured: prints OUTPUT_FILE=, file ends EXIT_CODE=
echo   bg ^<cmd...^>        fire-and-forget: poll OUTPUT_FILE for EXIT_CODE= sentinel
echo   jobs               list background jobs (RUNNING/DONE by sentinel presence)
echo.
echo All other ./vol commands (run, sync, ingest-*, kvar, present, ...) are
echo GS Coder workspace only — run via ./vol on S-B.
exit /b 0

:do_test
call :mk_out
pushd "%SRC%"
"%PY%" -m pytest tests/ -m "not slow" !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_testall
call :mk_out
pushd "%SRC%"
"%PY%" -m pytest tests/ !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_testlf
call :mk_out
pushd "%SRC%"
"%PY%" -m pytest tests/ --lf !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_lint
call :mk_out
pushd "%SRC%"
"%PY%" -m ruff check . !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_fmt
call :mk_out
pushd "%SRC%"
"%PY%" -m ruff format . !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_typecheck
call :mk_out
pushd "%SRC%"
"%PY%" -m mypy volforecast/ !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_exec
if "!ARGS!"=="" (
    echo ERROR: vol exec requires a command. Usage: vol.cmd exec ^<command^> [args...] >&2
    exit /b 1
)
call :mk_out
pushd "%SRC%"
cmd /c !ARGS! > "!_OUT_FILE!" 2>&1
set "_EC=!ERRORLEVEL!"
popd
goto finish

:do_bg
if "!ARGS!"=="" (
    echo ERROR: vol bg requires a command. Usage: vol.cmd bg ^<command^> [args...] >&2
    exit /b 1
)
call :mk_out
set "_RUNNER=!_OUT_FILE!.run.cmd"
>  "!_RUNNER!" echo @echo off
>> "!_RUNNER!" echo cd /d "%SRC%"
>> "!_RUNNER!" echo cmd /c !ARGS! ^> "!_OUT_FILE!" 2^>^&1
>> "!_RUNNER!" echo echo EXIT_CODE=%%ERRORLEVEL%%^>^> "!_OUT_FILE!"
>> "!_RUNNER!" echo del "%%~f0"
start "" /b cmd /c "!_RUNNER!"
echo ---
echo Launched. Poll OUTPUT_FILE for EXIT_CODE= sentinel.
exit /b 0

:do_jobs
set "_OUT_DIR=%ROOT%workspace\tmp\exec"
set "_FOUND=0"
if exist "%_OUT_DIR%" for %%F in ("%_OUT_DIR%\*.out") do (
    set "_FOUND=1"
    findstr /b /c:"EXIT_CODE=" "%%F" >nul 2>&1 && ( echo DONE     output=%%F ) || ( echo RUNNING  output=%%F )
)
if "!_FOUND!"=="0" echo No background jobs found.
exit /b 0

:mk_out
set "_OUT_DIR=%ROOT%workspace\tmp\exec"
if not exist "%_OUT_DIR%" mkdir "%_OUT_DIR%"
for /f %%I in ('powershell -NoProfile -Command "[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()"') do set "_TS=%%I"
for /f %%I in ('powershell -NoProfile -Command "$PID"') do set "_MYPID=%%I"
set "_OUT_FILE=%_OUT_DIR%\!_TS!_!_MYPID!.out"
echo OUTPUT_FILE=!_OUT_FILE!
exit /b 0

:finish
echo EXIT_CODE=!_EC!>> "!_OUT_FILE!"
echo EXIT_CODE=!_EC!
echo Done. Read: !_OUT_FILE!
exit /b !_EC!
