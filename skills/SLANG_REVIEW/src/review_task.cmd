@echo off
set "_PY_SCRIPT=%~dp0review.py" & set "_SKILL=SLANG_REVIEW"
call "%~dp0..\..\_shared\_run.cmd" %*
