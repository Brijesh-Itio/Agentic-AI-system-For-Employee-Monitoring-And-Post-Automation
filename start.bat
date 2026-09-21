@echo off
REM ==========================================================================
REM  WorkPulse AI - ONE script: installs anything that's missing, then runs
REM  everything (API on :8000 + dashboard on :5173).
REM
REM    First time : downloads/installs all libraries, browser, dashboard
REM                 packages, creates .env + the database  (a few minutes)
REM    After that : goes straight to starting              (a few seconds)
REM
REM  Options:  start.bat --agent          also run the desktop tracking agent
REM            start.bat --skip-models    don't pull the Ollama AI models
REM            start.bat --api-port 8100  run the API on another port
REM  Press Ctrl+C in this window to stop everything.
REM ==========================================================================
setlocal EnableExtensions
title WorkPulse AI
cd /d "%~dp0"

REM Once installed, the project's own Python is all that's needed.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\setup.py --start %*
    set "RC=%ERRORLEVEL%"
    goto :done
)

REM First run: find a suitable Python. Prefer 3.12 (what the project is
REM developed on), then 3.11, then 3.13.
set "PYEXE="
for %%V in (3.12 3.11 3.13) do (
    if not defined PYEXE (
        py -%%V --version >nul 2>&1 && set "PYEXE=py -%%V"
    )
)
if not defined PYEXE (
    python --version >nul 2>&1 && set "PYEXE=python"
)

if not defined PYEXE (
    echo.
    echo  Python 3.11 or newer was not found on this computer.
    echo.
    echo  Install it, then double-click start.bat again:
    echo      - Download: https://www.python.org/downloads/   ^(tick "Add python.exe to PATH"^)
    echo      - or, in a terminal:  winget install -e --id Python.Python.3.12
    echo.
    set "RC=1"
    goto :done
)

echo Using: %PYEXE%
echo.
%PYEXE% scripts\setup.py --start %*
set "RC=%ERRORLEVEL%"

:done
REM Keep the window open if something went wrong, so the message can be read.
if not "%RC%"=="0" (
    echo.
    echo Press any key to close this window...
    pause >nul
)
exit /b %RC%
