@echo off
set "_PY_SCRIPT=%~dp0eval.py" & set "_SKILL=SLANG_EVAL"
call "%~dp0..\..\_shared\_run.cmd" %*
