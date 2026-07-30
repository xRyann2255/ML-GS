@echo off
set "_PY_SCRIPT=%~dp0query.py" & set "_SKILL=CANVAS"
call "%~dp0..\..\_shared\_run.cmd" %*
