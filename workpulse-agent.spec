# MODULE 23.1 — PyInstaller spec for the desktop tracking agent.
#
# Entry point is agent/tray_main.py (module 23.5's first-run + system tray
# wrapper around agent/main.py's tracker startup), not agent/main.py
# directly, so the packaged .exe never shows a console window and always
# runs through first-run setup + the tray icon.
#
# Build with: pyinstaller workpulse-agent.spec --clean
# (see scripts/build_exe.bat for the one-command version, which also
# generates icon.ico if it's missing).
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
PROJECT_ROOT = Path(SPECPATH)

hidden_imports = [
    # pywin32 — active window / idle detection (modules 1, 2)
    "win32gui", "win32process", "win32api", "win32con", "win32timezone",
    # tray icon backend on Windows
    "pystray._win32",
    # desktop notifications (module 14)
    "plyer.platforms.win.notification",
    # LangGraph Master Agent (module 15) + its LangChain core dependency
    "langgraph", "langgraph.graph", "langchain_core",
    # stdlib modules PyInstaller sometimes misses via indirect imports
    "sqlite3", "email.mime.text", "email.mime.multipart",
]

# chromadb (module 6's classification memory) is now a real, direct
# dependency of the packaged agent too: agent/main.py starts
# ai.productivity_scorer.LiveScoringScheduler (the live "Active Hours"
# fix), and that module imports chromadb at the top level. It used to be
# excluded below as API-only — that became stale and made every packaged
# build crash at import time with "No module named 'chromadb'", silently,
# behind a Tkinter error dialog with no console to show it. chromadb pulls
# in enough dynamic/plugin-style imports (onnxruntime, tokenizers, its own
# bundled migration SQL files) that plain hiddenimports isn't reliable —
# collect_all is PyInstaller's documented way to bundle packages like this.
chroma_datas, chroma_binaries, chroma_hiddenimports = collect_all("chromadb")
hidden_imports += chroma_hiddenimports

icon_path = PROJECT_ROOT / "icon.ico"

a = Analysis(
    [str(PROJECT_ROOT / "agent" / "tray_main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=chroma_binaries,
    datas=chroma_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # The agent process never needs these — they belong to the FastAPI
        # backend / automation modules, not the tracking agent. chromadb
        # was removed from this list (see collect_all("chromadb") above) —
        # the packaged agent genuinely imports it now via
        # ai.productivity_scorer.LiveScoringScheduler.
        "playwright", "fastapi", "uvicorn", "docx", "reportlab",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="WorkPulseAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_path) if icon_path.exists() else None,
)
