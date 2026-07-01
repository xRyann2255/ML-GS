@echo off
REM Backtest wrapper. Reads --args-file JSON and calls Python economic value module.
REM
REM Usage: backtest_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "signal_type": "iv_rv_gap|vol_targeting",
REM     "signal_file": "...",
REM     "backtest_window": {"start_date": "...", "end_date": "..."},
REM     "out_file": "workspace/tmp/backtest_out.txt"
REM   }

setlocal

REM ---- Environment ----
call H:\all-languages-env.cmd >nul 2>&1

set "ARGS_FILE="
:parse_args
if "%~1"=="" goto run
if /I "%~1"=="--args-file" (
    set "ARGS_FILE=%~2"
    shift & shift
    goto parse_args
)
shift
goto parse_args

:run
if not defined ARGS_FILE (
    echo ERROR: --args-file is required
    exit /b 1
)
if not exist "%ARGS_FILE%" (
    echo ERROR: args file not found: %ARGS_FILE%
    exit /b 1
)

python -m volforecast.evaluation.economic_value --args-file "%ARGS_FILE%"
