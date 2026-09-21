@echo off
REM WorkPulse AI - one-click setup (Windows).
REM Double-click this file after cloning the repo. It finds a suitable Python
REM and hands over to scripts\setup.py, which installs everything.
REM Extra options are passed through, e.g.:  setup.bat --skip-models
REM                                          setup.bat --check
setlocal EnableExtensions
title WorkPulse AI - Setup
cd /d "%~dp0"

REM Was this launched by double-clicking (so the window would vanish at the end)?
REM (Full path to find.exe: with Git's Unix tools on PATH, a bare "find" is the wrong program.)
set "DBLCLICK="
echo %cmdcmdline% | "%SystemRoot%\System32\find.exe" /i "%~nx0" >nul && set "DBLCLICK=1"

REM Prefer 3.12 (what the project is developed on), then 3.11, then 3.13.
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
    echo  Install it, then double-click setup.bat again:
    echo      - Download: https://www.python.org/downloads/   ^(tick "Add python.exe to PATH"^)
    echo      - or, in a terminal:  winget install -e --id Python.Python.3.12
    echo.
    set "RC=1"
    goto :done
)

echo Using: %PYEXE%
echo.
%PYEXE% scripts\setup.py %*
set "RC=%ERRORLEVEL%"

:done
if defined DBLCLICK (
    echo.
    echo Press any key to close this window...
    pause >nul
)
exit /b %RC%
