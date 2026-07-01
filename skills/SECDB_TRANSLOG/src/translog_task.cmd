@echo off
set "_PY_SCRIPT=%~dp0translog.py" & set "_SKILL=SECDB_TRANSLOG"
call "%~dp0..\..\_shared\_run.cmd" %*
