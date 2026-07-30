@echo off
set "_PY_SCRIPT=%~dp0backtest_entry.py" & set "_SKILL=BACKTEST"
call "%~dp0..\..\_shared\_run.cmd" %*
