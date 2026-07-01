@echo off
REM Model training wrapper. Reads --args-file JSON and calls Python training module.
REM
REM Usage: train_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "model_type": "lightgbm",
REM     "feature_config": { "layers": [0,1,2], "feature_file": "..." },
REM     "cv_strategy": "purged_kfold",
REM     "cv_params": { "n_splits": 5, "purge_gap": 22 },
REM     "target": "log_rv_1d",
REM     "covid_handling": "exclude",
REM     "out_file": "workspace/tmp/train_out.txt"
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

python -m volforecast.models.train --args-file "%ARGS_FILE%"
