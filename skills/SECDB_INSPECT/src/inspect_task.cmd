@echo off
set "_PY_SCRIPT=%~dp0inspect.py" & set "_SKILL=SECDB_INSPECT"
call "%~dp0..\..\_shared\_run.cmd" %*
