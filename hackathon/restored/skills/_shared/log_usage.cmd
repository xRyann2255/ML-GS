@echo off
REM Append a usage entry to the skill usage log.
REM Usage: log_usage.cmd SKILL_NAME [SOURCE]
REM   SKILL_NAME: uppercase skill identifier (e.g., GIT, SLANG_EDIT)
REM   SOURCE: "task" (default) or "manual"
setlocal
set "SKILL=%~1"
if "%SKILL%"=="" exit /b 0
set "SRC=%~2"
if "%SRC%"=="" set "SRC=task"
set "LOG=%~dp0..\..\workspace\tmp\skill_usage.log"
REM Native timestamp — no PowerShell subprocess (avoids hang in non-interactive terminals)
REM %DATE% format is locale-dependent (e.g. 28-Apr-26); just use raw date+time
set "TS=%DATE%T%TIME:~0,8%"
set "TS=%TS: =0%"
>> "%LOG%" echo %TS% ^| %SKILL% ^| %SRC%
endlocal
exit /b 0
