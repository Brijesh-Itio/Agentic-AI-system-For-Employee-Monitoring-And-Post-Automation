@echo off
REM Stops the backend (port 8000) and dashboard (port 5173) started by start-servers.bat.
REM Double-click to stop both, e.g. before restarting after a backend code change.
setlocal
echo Stopping WorkPulse AI servers...

for %%P in (8000 5173) do (
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        taskkill /F /T /PID %%I >nul 2>&1
    )
)
REM Close the launcher windows too, if they are still open.
taskkill /F /FI "WINDOWTITLE eq WorkPulse API*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq WorkPulse Dashboard*" >nul 2>&1

echo Done. Run start-servers.bat to start them again.
timeout /t 3 >nul
