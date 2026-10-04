@echo off
rem preflight.bat - controlli prima di lanciare uno studio HEEDS (non lancia FlightStream).
rem Usa lo stesso interprete Python di run_fs.bat: esegue la sua riga  set "PY=..." .
for /f "usebackq delims=" %%L in (`findstr /b /i /c:"set " "%~dp0run_fs.bat"`) do %%L
if not exist "%PY%" (
  echo ERRORE  Python di run_fs.bat non trovato: "%PY%"
  exit /b 1
)
"%PY%" "%~dp0preflight.py" %*
exit /b %ERRORLEVEL%
