@echo off
set "_PY_SCRIPT=%~dp0cleanup.py" & set "_SKILL=KILL_ORPHANS"
call "%~dp0..\..\_shared\_run.cmd" %*
