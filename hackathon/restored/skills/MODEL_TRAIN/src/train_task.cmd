@echo off
set "_PY_SCRIPT=%~dp0..\..\_shared\vf_entry.py" & set "_SKILL=MODEL_TRAIN" & set "_VF_MODULE=volforecast.__main__"
call "%~dp0..\..\_shared\_run.cmd" %*
