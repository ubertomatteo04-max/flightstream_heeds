@echo off
rem heeds_report.bat - lancia heeds_report.py con il Python incluso in HEEDS 2604.0, che ha matplotlib
rem (nel Python del progetto matplotlib non c'e'). Uso: heeds_report.bat --study "<cartella dello studio>"
set "HPY=C:\Program Files\Siemens\SimcenterHEEDS-2604.0\MDO\Python3"
set "PYTHONPATH=%HPY%\Lib\siemens"
"%HPY%\python.exe" "%~dp0heeds_report.py" %*
exit /b %ERRORLEVEL%
