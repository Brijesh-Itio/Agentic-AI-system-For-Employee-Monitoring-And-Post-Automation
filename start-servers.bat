@echo off
REM ==========================================================================
REM  WorkPulse AI - one-click launcher for the backend + frontend servers.
REM
REM    Double-click this file.  It opens two windows:
REM        "WorkPulse API"        FastAPI backend   http://localhost:8000
REM        "WorkPulse Dashboard"  Vite frontend     http://localhost:5173
REM    and then opens the dashboard in your browser.
REM
REM  Close a window (or run stop-servers.bat) to stop that server.
REM  Needs the one-time install done first (start.bat / setup.bat does that).
REM  Ollama must be running for the AI features (the Ollama tray app is enough).
REM ==========================================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [!] The Python environment is not installed yet.
    echo     Run start.bat once - it installs everything, then starts the project.
    pause
    exit /b 1
)
if not exist "frontend\node_modules" (
    echo [!] The dashboard packages are not installed yet.
    echo     Run start.bat once - it installs everything, then starts the project.
    pause
    exit /b 1
)

REM Skip a server that is already listening, so double-clicking twice is harmless.
set "API_UP="
set "WEB_UP="
for /f %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do set "API_UP=1"
for /f %%p in ('netstat -ano ^| findstr /R /C:":5173 .*LISTENING"') do set "WEB_UP=1"

if defined API_UP (
    echo Backend already running on port 8000 - leaving it alone.
) else (
    echo Starting backend on http://localhost:8000 ...
    REM No --reload on purpose: it is unreliable here and can keep serving old code.
    start "WorkPulse API" cmd /k ".venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000"
)

if defined WEB_UP (
    echo Dashboard already running on port 5173 - leaving it alone.
) else (
    echo Starting dashboard on http://localhost:5173 ...
    start "WorkPulse Dashboard" /D "%~dp0frontend" cmd /k "npm run dev"
)

echo.
echo Waiting for the servers to come up...
set /a tries=0
:wait
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ -TimeoutSec 2).StatusCode | Out-Null; (Invoke-WebRequest -UseBasicParsing http://localhost:5173/ -TimeoutSec 2).StatusCode | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 45 goto timeout
timeout /t 2 /nobreak >nul
goto wait

:ready
echo.
echo  WorkPulse AI is running:
echo      Dashboard : http://localhost:5173
echo      API docs  : http://localhost:8000/docs
start "" http://localhost:5173
echo.
echo  You can close this window. Keep the two server windows open.
timeout /t 5 >nul
exit /b 0

:timeout
echo.
echo [!] The servers did not respond within 90 seconds.
echo     Look at the "WorkPulse API" and "WorkPulse Dashboard" windows for the error.
pause
exit /b 1
