@echo off
setlocal

set PROJ=C:\Users\Check\etf-portfolio
set PYTHON=C:\Users\Check\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PROJ%\logs" mkdir "%PROJ%\logs"

echo [%DATE% %TIME%] pipeline start >> "%PROJ%\logs\scheduler.log"

cd /d "%PROJ%"
"%PYTHON%" "%PROJ%\main.py"
set EXITCODE=%ERRORLEVEL%

echo [%DATE% %TIME%] pipeline end (exit: %EXITCODE%) >> "%PROJ%\logs\scheduler.log"

endlocal
exit /b %EXITCODE%
