@echo off
set "_PY_SCRIPT=%~dp0commit_task.py" & set "_SKILL=GIT_COMMIT"
call "%~dp0..\..\_shared\_run.cmd" %*
