@echo off
set "_PY_SCRIPT=%~dp0copilot_setup.py" & set "_SKILL=SLANG_COPILOT"
call "%~dp0..\..\_shared\_run.cmd" %*
