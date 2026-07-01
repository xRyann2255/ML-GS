@echo off
REM Research session wrapper. Reads --args-file JSON and prints session protocol.
REM This skill is primarily agent-driven — the .cmd wrapper loads context.
REM
REM Usage: research_task.cmd --args-file path\to\args.json
REM
REM Args JSON:
REM   {
REM     "topic": "HAR baseline reproduction",
REM     "depth": "quick|deep",
REM     "out_file": "workspace/tmp/research_out.txt"
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

python -m volforecast.pipeline.research --args-file "%ARGS_FILE%"
