@echo off
set "_PY_SCRIPT=%~dp0read_pdf.py" & set "_SKILL=PDF_READER"
call "%~dp0..\..\_shared\_run.cmd" %*
