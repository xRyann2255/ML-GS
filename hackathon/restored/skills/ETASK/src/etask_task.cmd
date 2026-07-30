@echo off
set "_PY_SCRIPT=%~dp0etask.py" & set "_SKILL=ETASK"
call "%~dp0..\..\_shared\_run.cmd" %*
