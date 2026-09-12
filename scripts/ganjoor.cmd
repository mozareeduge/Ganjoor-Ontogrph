@echo off
rem ganjoor.cmd — thin Windows shim; forwards all args to scripts\ganjoor.py.
setlocal
where py >nul 2>nul && (py -3 "%~dp0ganjoor.py" %* & exit /b %ERRORLEVEL%)
where python >nul 2>nul && (python "%~dp0ganjoor.py" %* & exit /b %ERRORLEVEL%)
python3 "%~dp0ganjoor.py" %*
exit /b %ERRORLEVEL%
