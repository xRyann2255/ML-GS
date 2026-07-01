@echo off
REM Evaluation suite wrapper. Reads --args-file JSON and calls Python evaluation module.
REM
REM Usage: eval_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "models": [{"name": "HAR", "predictions_file": "..."}],
REM     "actuals_file": "...",
REM     "target": "log_rv_1d",
REM     "metrics": ["qlike", "mse"],
REM     "tests": ["dm", "mcs"],
REM     "out_file": "workspace/tmp/eval_out.txt"
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

python -m volforecast.evaluation.evaluate --args-file "%ARGS_FILE%"
