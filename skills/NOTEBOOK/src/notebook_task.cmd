@echo off
REM Notebook creation wrapper. Reads --args-file JSON and creates a Jupyter notebook.
REM
REM Usage: notebook_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "name": "har_baseline_exploration",
REM     "kernel": "python3",
REM     "template": "research|feature_exploration|model_comparison|blank",
REM     "out_dir": "workspace/notebooks",
REM     "out_file": "workspace/tmp/notebook_out.txt"
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

python -m volforecast.pipeline.notebook --args-file "%ARGS_FILE%"
