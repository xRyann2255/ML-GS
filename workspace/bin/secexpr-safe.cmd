@echo off
REM Usage: secexpr-safe.cmd <expression-file>
REM Reads the Slang expression from the specified file (one line, "" for inner quotes)
REM and executes it via secexpr --safe.
setlocal DisableDelayedExpansion
call H:\all-languages-env.cmd >nul 2>&1
for /f "usebackq delims=" %%a in ("%~1") do set "EXPR=%%a"
secexpr "PS" --safe -e "%EXPR%"
