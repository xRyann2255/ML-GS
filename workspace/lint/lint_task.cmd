@echo off
set "_PY_SCRIPT=%~dp0lint_all.py" & set "_SKILL=LINT"
call "%~dp0..\..\skills\_shared\_run.cmd" %*
