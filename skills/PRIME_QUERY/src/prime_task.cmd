@echo off
set "_PY_SCRIPT=%~dp0prime.py" & set "_SKILL=PRIME_QUERY"
call "%~dp0..\..\_shared\_run.cmd" %*
