@echo off
set "_PY_SCRIPT=%~dp0mr_task.py" & set "_SKILL=GIT"
call "%~dp0..\..\_shared\_run.cmd" %*
