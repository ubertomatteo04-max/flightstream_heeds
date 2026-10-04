@echo off
rem run_fs.bat - comando per HEEDS: lancia fs_driver.py con l'interprete Python del progetto.
rem Uso (Execution command di HEEDS):  "<cartella>\run_fs.bat" --config "<percorso assoluto del JSON>"
rem Gli argomenti vengono inoltrati tali e quali; il codice di uscita e' quello di fs_driver.py
rem (0 se lo status e' in heeds.success_statuses, altrimenti 1). Gli output vanno nella cartella
rem corrente (quella del design); fs_driver.py viene trovato accanto a questo file (%%~dp0).
rem Niente setlocal ne' call: non devono perdere l'errorlevel.

rem === Interprete Python del progetto: modificare qui se cambia ===
set "PY=C:\Users\UtenteLocale\AppData\Local\Programs\Python\Python313\python.exe"

"%PY%" "%~dp0fs_driver.py" %*
exit /b %ERRORLEVEL%
