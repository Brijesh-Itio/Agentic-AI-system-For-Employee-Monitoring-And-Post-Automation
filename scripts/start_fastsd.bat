@echo off
setlocal
rem Starts the FastSD CPU local image-generation server (module 18.3's
rem primary image source, used by automation/linkedin/image_generator.py).
rem It lives in a separate clone next to this repo (see DEVELOPMENT.md,
rem "Running the System Locally") — not part of workpulse-ai itself.

set "FASTSD_DIR=%~dp0..\..\fastsdcpu"

if not exist "%FASTSD_DIR%\env\Scripts\python.exe" (
    echo FastSD CPU environment not found at "%FASTSD_DIR%\env".
    echo Clone https://github.com/rupeshs/fastsdcpu next to this project and run its install.bat first.
    pause
    exit /b 1
)

echo Starting FastSD CPU API server on port 8100...
set "PATH=%PATH%;%FASTSD_DIR%\env\Lib\site-packages\openvino\libs"
"%FASTSD_DIR%\env\Scripts\python.exe" "%FASTSD_DIR%\src\app.py" --api --port 8100
