@echo off
set "_PY_SCRIPT=%~dp0coverage.py" & set "_SKILL=SLANG_TEST_COVERAGE"
call "%~dp0..\..\_shared\_run.cmd" %*
