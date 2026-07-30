@echo off
set "_PY_SCRIPT=%~dp0..\..\_shared\vf_entry.py" & set "_SKILL=DATA_INGEST" & set "_VF_MODULE=volforecast.cli.ingest"
call "%~dp0..\..\_shared\_run.cmd" %*
