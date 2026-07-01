@echo off
set "_PY_SCRIPT=%~dp0diff.py" & set "_SKILL=SECDB_DIFF"
call "%~dp0..\..\_shared\_run.cmd" %*
