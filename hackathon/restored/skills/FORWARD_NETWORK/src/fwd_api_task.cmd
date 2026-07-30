@echo off
set "_PY_SCRIPT=%~dp0fwd_api.py" & set "_SKILL=FORWARD_NETWORK"
call "%~dp0..\..\_shared\_run.cmd" %*
