@echo off
setlocal

REM ── ETF 포트폴리오 자동 실행 (Windows 작업 스케줄러용) ─────────────────────
REM   평일 18:00 실행 가정. 운용사 PDF 갱신 후 수집.

set PROJ=C:\Users\Check\etf-portfolio
set PYTHON=C:\Users\Check\AppData\Local\Programs\Python\Python311\python.exe

REM 로그 디렉토리 생성 (없을 경우)
if not exist "%PROJ%\logs" mkdir "%PROJ%\logs"

REM scheduler.log에 실행 메타 기록 (main.py 날짜별 로그와 별도)
echo [%DATE% %TIME%] 파이프라인 시작 >> "%PROJ%\logs\scheduler.log"

REM 파이프라인 실행 (main.py 내부에서 logs\YYYYMMDD.log 생성)
cd /d "%PROJ%"
"%PYTHON%" "%PROJ%\main.py"
set EXITCODE=%ERRORLEVEL%

echo [%DATE% %TIME%] 파이프라인 종료 (종료코드: %EXITCODE%) >> "%PROJ%\logs\scheduler.log"

endlocal
exit /b %EXITCODE%
