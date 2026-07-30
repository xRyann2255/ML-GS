@echo off
set "_PY_SCRIPT=%~dp0fetch_pipeline.py" & set "_SKILL=GITLAB_PIPELINES"
call "%~dp0..\..\_shared\_run.cmd" %*
