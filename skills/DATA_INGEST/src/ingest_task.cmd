@echo off
REM Data ingestion wrapper. Reads --args-file JSON and calls Python ingest module.
REM
REM Usage: ingest_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "symbols": ["SPY", "AAPL"],
REM     "start_date": "2020-01-01",
REM     "end_date": "2024-12-31",
REM     "data_type": "tick|daily|iv",
REM     "out_dir": "workspace/tmp/data",
REM     "out_file": "workspace/tmp/ingest_out.txt"
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

python -m volforecast.data.ingest --args-file "%ARGS_FILE%"
