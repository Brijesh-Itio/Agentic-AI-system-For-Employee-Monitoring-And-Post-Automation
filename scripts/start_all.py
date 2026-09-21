#!/usr/bin/env python3
"""
WorkPulse AI - start the backend and the dashboard together.

    Windows        : double-click start.bat   (or: python scripts/start_all.py)
    macOS / Linux  : python3 scripts/start_all.py

Runs:   API        http://localhost:8000   (FastAPI / uvicorn)
        Dashboard  http://localhost:5173   (Vite)
Press Ctrl+C once to stop everything.

Options:
    --agent           also run the desktop tracking agent (Windows only)
    --host HOST       address the API listens on (default 127.0.0.1; use 0.0.0.0 to
                      expose it to your network)
    --api-port PORT   API port (default 8000). The dashboard is pointed at it
                      automatically. Leave the dashboard on 5173: the API's CORS
                      setting only allows http://localhost:5173 by default.

Run the setup first (setup.bat / scripts/setup.py) - this only starts things.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"
VENV_PY = ROOT / ".venv" / ("Scripts" if IS_WINDOWS else "bin") / ("python.exe" if IS_WINDOWS else "python")


def pump(proc: subprocess.Popen, label: str) -> None:
    """Copies a child's output to this console, tagged so the streams stay readable."""
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"[{label}] {line.rstrip()}", flush=True)


def kill_tree(proc: subprocess.Popen) -> None:
    """Stops a process and its children (npm spawns node underneath it)."""
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        subprocess.call(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


def wait_until_up(url: str, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3):
                return True
        except Exception:
            time.sleep(1.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the WorkPulse AI backend and dashboard.")
    parser.add_argument("--agent", action="store_true", help="also run the desktop agent (Windows only)")
    parser.add_argument("--host", default="127.0.0.1", help="API listen address (default 127.0.0.1)")
    parser.add_argument("--api-port", type=int, default=8000, help="API port (default 8000)")
    args = parser.parse_args()

    # Vite prints characters (e.g. the arrow in "Local: ...") that legacy Windows consoles
    # (cp1252) can't encode; without this, the output-copying thread would crash on them.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    if not VENV_PY.exists():
        print("The virtual environment is missing - run the setup first:")
        print("    " + ("setup.bat" if IS_WINDOWS else "python3 scripts/setup.py"))
        return 1
    npm = shutil.which("npm")
    if not (FRONTEND / "node_modules").exists() or not npm:
        print("The dashboard packages are missing (or Node.js isn't installed) - run the setup first.")
        return 1

    api_url = f"http://localhost:{args.api_port}"
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"

    web_env = dict(env)
    web_env["VITE_API_URL"] = api_url  # a real env var beats frontend/.env

    procs: list[tuple[str, subprocess.Popen]] = []

    def launch(label: str, cmd: list, cwd: Path, e: dict) -> None:
        p = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=e, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        procs.append((label, p))
        threading.Thread(target=pump, args=(p, label), daemon=True).start()

    try:
        launch("api", [VENV_PY, "-m", "uvicorn", "api.main:app", "--host", args.host, "--port", args.api_port], ROOT, env)
        launch("web", [npm, "run", "dev"], FRONTEND, web_env)
        if args.agent:
            if IS_WINDOWS:
                launch("agent", [VENV_PY, "-m", "agent.main"], ROOT, env)
            else:
                print("(--agent ignored: the desktop agent only runs on Windows)")

        if wait_until_up(f"http://127.0.0.1:{args.api_port}/openapi.json"):
            print(f"\n>>> API ready:        {api_url}", flush=True)
        else:
            print("\n>>> The API did not come up within 90s - check the [api] lines above.", flush=True)
        print(">>> Dashboard:        http://localhost:5173  (first account you create becomes the admin)")
        print(">>> Press Ctrl+C to stop everything.\n", flush=True)

        while True:
            for label, p in procs:
                if p.poll() is not None:
                    print(f"\n[{label}] exited with code {p.returncode} - stopping the rest.", flush=True)
                    return p.returncode or 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...", flush=True)
        return 0
    finally:
        for _, p in procs:
            kill_tree(p)


if __name__ == "__main__":
    sys.exit(main())
