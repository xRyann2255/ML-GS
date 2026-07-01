@echo off
set "_PY_SCRIPT=%~dp0lint.py" & set "_SKILL=SLANG_LINT"
call "%~dp0..\..\_shared\_run.cmd" %*
