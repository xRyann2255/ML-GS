@echo off
REM Generic git command wrapper. Reads --args-file JSON and runs git.
REM Used by VS Code Tasks to avoid Copilot "Allow" prompt.
REM
REM Usage: git_task.cmd --args-file path\to\args.json
REM
REM Args JSON (single command):
REM   { "args": ["status", "--short"], "out_file": "workspace/tmp/git_out.txt" }
REM
REM Args JSON (compound — multiple commands in sequence):
REM   { "steps": [["add","-A"],["commit","-m","msg"],["push"]], "out_file": "..." }
REM
REM   args     - array of git arguments for a single command
REM   steps    - array of arrays; each sub-array is a git command (runs sequentially, stops on first failure)
REM   out_file - optional path to write stdout (if omitted, only prints to console)

setlocal

REM ---- Environment ----
call H:\all-languages-env.cmd >nul 2>&1

REM ---- Prevent editor-blocking on rebase/merge/commit --amend ----
set "GIT_MERGE_AUTOEDIT=no"
set "GIT_EDITOR=H:/ml-vol-estimator/skills/GIT/src/noop_editor.cmd"
set "GIT_SEQUENCE_EDITOR=H:/ml-vol-estimator/skills/GIT/src/noop_editor.cmd"

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

REM Delete stale output so agent never reads old data on failure
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$a = Get-Content '%ARGS_FILE%' -Raw | ConvertFrom-Json; " ^
  "if ($a.out_file -and (Test-Path $a.out_file)) { Remove-Item $a.out_file -Force }"

REM Use PowerShell to parse JSON, handle single or compound mode, run git
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$a = Get-Content '%ARGS_FILE%' -Raw | ConvertFrom-Json; " ^
  "$allOut = @(); " ^
  "$ec = 0; " ^
  "if ($a.steps) { " ^
  "  $i = 0; " ^
  "  foreach ($step in $a.steps) { " ^
  "    $i++; " ^
  "    $gitArgs = @($step); " ^
  "    $header = \"--- step $i`: git $($gitArgs -join ' ') ---\"; " ^
  "    Write-Host $header; " ^
  "    $allOut += $header; " ^
  "    $out = & git @gitArgs 2>&1; " ^
  "    $text = $out | Out-String; " ^
  "    Write-Host $text; " ^
  "    $allOut += $text; " ^
  "    $ec = $LASTEXITCODE; " ^
  "    if ($ec -ne 0) { " ^
  "      $allOut += \"--- FAILED (exit $ec) at step $i ---\"; " ^
  "      Write-Host \"--- FAILED (exit $ec) at step $i ---\"; " ^
  "      break " ^
  "    } " ^
  "  } " ^
  "} else { " ^
  "  $gitArgs = @($a.args); " ^
  "  $out = & git @gitArgs 2>&1; " ^
  "  $text = $out | Out-String; " ^
  "  Write-Host $text; " ^
  "  $allOut += $text; " ^
  "  $ec = $LASTEXITCODE; " ^
  "} " ^
  "if ($a.out_file) { " ^
  "  [System.IO.File]::WriteAllText($a.out_file, ($allOut -join \"`n\")); " ^
  "} " ^
  "exit $ec"
set "_EC=%ERRORLEVEL%"
set "_LOG=%~dp0..\..\_shared\log_usage.cmd"
if exist "%_LOG%" call "%_LOG%" GIT
REM Always exit 0 so VS Code's close:true disposes the terminal.
exit /b 0
