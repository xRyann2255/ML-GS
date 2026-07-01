@echo off
REM Feature computation wrapper. Reads --args-file JSON and calls Python feature module.
REM
REM Usage: feature_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "layer": 0,
REM     "symbols": ["SPY"],
REM     "start_date": "2020-01-01",
REM     "end_date": "2024-12-31",
REM     "input_dir": "workspace/tmp/data",
REM     "out_file": "workspace/tmp/features/layer0_SPY.parquet"
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

python -m volforecast.features.build --args-file "%ARGS_FILE%"
