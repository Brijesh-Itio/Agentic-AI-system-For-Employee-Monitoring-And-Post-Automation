@echo off
REM MODULE 23.2 — Build script for the packaged desktop agent .exe.
REM Run from the project root: scripts\build_exe.bat

cd /d "%~dp0\.."

echo [1/3] Ensuring build tools are installed...
python -m pip install --quiet pyinstaller pystray

echo [2/3] Generating icon.ico (skipped if it already exists)...
python scripts\generate_icon.py

echo [3/3] Building WorkPulseAgent.exe...
python -m PyInstaller workpulse-agent.spec --clean --noconfirm

if not exist dist\WorkPulseAgent.exe (
    echo.
    echo Build failed — see output above.
    exit /b 1
)

REM For the co-located single-machine setup (agent + API sharing one
REM workpulse.db — see docs/DEPLOYMENT.md), the .exe needs to run from the
REM project root, not dist/: agent/config.py anchors DATA_DIR/LOCAL_DB_PATH
REM at "the folder containing the .exe" once frozen, since __file__-based
REM paths resolve into a temp extraction dir inside a frozen build and
REM can't be used. Copy it up next to workpulse.db so that folder is right.
copy /y dist\WorkPulseAgent.exe . >nul

echo.
echo Build succeeded: WorkPulseAgent.exe (copied to project root)
echo First run: double-click it, or place a workpulse-config.json next to
echo it to skip the setup dialog (see agent/runtime_config.py).
