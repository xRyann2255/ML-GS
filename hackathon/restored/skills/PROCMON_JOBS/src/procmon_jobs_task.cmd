@echo off
set "_PY_SCRIPT=%~dp0fetch_process_list.py" & set "_SKILL=PROCMON_JOBS"
call "%~dp0..\..\_shared\_run.cmd" %*
