@echo off
set "_PY_SCRIPT=%~dp0fix_regtest.py" & set "_SKILL=SLANG_REGTEST_FIX"
call "%~dp0..\..\_shared\_run.cmd" %*
