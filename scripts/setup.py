#!/usr/bin/env python3
"""
WorkPulse AI - one-command setup.

After cloning the repo:
    Windows        : double-click setup.bat   (or: python scripts/setup.py)
    macOS / Linux  : python3 scripts/setup.py

What it does (every step is safe to re-run; finished work is skipped):
    1. Checks Python 3.11+ and Node 18+
    2. Creates the .venv virtual environment
    3. Installs every Python library from requirements.txt
    4. Downloads the Playwright browser (LinkedIn / browser automation)
    5. Creates .env from .env.example with a freshly generated SECRET_KEY
    6. Installs the dashboard's npm packages
    7. Creates the database and smoke-tests that the backend imports cleanly
    8. Pulls the Ollama AI models the project uses
    9. Creates workpulse-config.json for the desktop agent

Install AND run in one go:
    Windows        : double-click start.bat   (or: python scripts/setup.py --start)
    macOS / Linux  : python3 scripts/setup.py --start
    -> installs whatever is missing, then starts the API + dashboard. Once
       everything is installed it skips straight to starting (a few seconds).

Options:
    --start            after setup, start the API + dashboard (see above)
    --agent            with --start: also run the desktop agent (Windows only)
    --check            report what is / isn't installed; change nothing
    --skip-models      don't pull the Ollama models (about 4 GB of downloads)
    --skip-playwright  don't download the Playwright browser
    --skip-frontend    don't run npm
    --build-agent      also build WorkPulseAgent.exe (Windows only, takes minutes)

Uses the standard library only, so it runs before anything else is installed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"

VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin") / ("python.exe" if IS_WINDOWS else "python")

MIN_PYTHON = (3, 11)
MIN_NODE = 18

# The models the code actually references (ai/ and automation/). Keep in sync
# with the "Tech stack" table in README.md.
OLLAMA_MODELS = ("qwen3:1.7b", "phi3:mini", "nomic-embed-text")

# pip package -> import name, for the post-install verification.
IMPORT_CHECKS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "pydantic-settings": "pydantic_settings",
    "python-jose": "jose",
    "python-multipart": "multipart",
    "bcrypt": "bcrypt",
    "ollama": "ollama",
    "chromadb": "chromadb",
    "langgraph": "langgraph",
    "langchain-core": "langchain_core",
    "apscheduler": "apscheduler",
    "playwright": "playwright",
    "python-docx": "docx",
    "reportlab": "reportlab",
    "openpyxl": "openpyxl",
    "python-dotenv": "dotenv",
    "beautifulsoup4": "bs4",
    "paramiko": "paramiko",
    "requests": "requests",
    "Pillow": "PIL",
    "psutil": "psutil",
    "watchdog": "watchdog",
    "icalendar": "icalendar",
    "schedule": "schedule",
    # Desktop-agent-only libraries (Windows).
    "pywin32": "win32api",
    "plyer": "plyer",
    "pystray": "pystray",
    "keyboard": "keyboard",
}
AGENT_ONLY = {"pywin32", "plyer", "pystray", "keyboard"}

RESULTS: list[tuple[str, str, str]] = []  # (status, step, detail)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def record(status: str, step: str, detail: str = "") -> None:
    RESULTS.append((status, step, detail))
    print(f"[{status:^4}] {step}" + (f" - {detail}" if detail else ""), flush=True)


def heading(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def run(cmd: list, cwd: Path | None = None, env: dict | None = None) -> int:
    """Runs a command with its output streamed live (pip / npm progress)."""
    print("  $ " + " ".join(str(c) for c in cmd), flush=True)
    try:
        return subprocess.call([str(c) for c in cmd], cwd=str(cwd or ROOT), env=env)
    except FileNotFoundError:
        return 127


def capture(cmd: list, cwd: Path | None = None, timeout: int = 90) -> tuple[int, str]:
    try:
        p = subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def parse_version(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(x) for x in m.groups() if x is not None) if m else ()


def venv_python_version() -> tuple[int, ...]:
    code, out = capture([VENV_PY, "--version"])
    return parse_version(out) if code == 0 else ()


def read_env_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    m = re.search(rf"(?m)^{re.escape(key)}\s*=\s*(.*?)\s*$", path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1).strip("\"'") if m else None


def node_info() -> tuple[str | None, str | None, int | None]:
    node, npm = shutil.which("node"), shutil.which("npm")
    major = None
    if node:
        code, out = capture([node, "--version"])
        v = parse_version(out) if code == 0 else ()
        major = v[0] if v else None
    return node, npm, major


def ollama_installed_models() -> tuple[bool, set[str], str]:
    """(reachable, model names, message)."""
    exe = shutil.which("ollama")
    if not exe:
        return False, set(), "Ollama is not installed"
    code, out = capture([exe, "list"], timeout=30)
    if code != 0:
        return False, set(), "Ollama is installed but not responding (start the Ollama app, then re-run)"
    names = set()
    for line in out.splitlines()[1:]:
        if line.strip():
            names.add(line.split()[0])
    return True, names, ""


def model_present(model: str, installed: set[str]) -> bool:
    return model in installed or (":" not in model and f"{model}:latest" in installed)


def missing_imports() -> list[str]:
    """Which pip packages fail to import inside the venv."""
    wanted = {pkg: mod for pkg, mod in IMPORT_CHECKS.items() if IS_WINDOWS or pkg not in AGENT_ONLY}
    script = (
        "import importlib, json\n"
        f"wanted = {wanted!r}\n"
        "bad = []\n"
        "for pkg, mod in wanted.items():\n"
        "    try:\n"
        "        importlib.import_module(mod)\n"
        "    except Exception:\n"
        "        bad.append(pkg)\n"
        "print(json.dumps(bad))\n"
    )
    code, out = capture([VENV_PY, "-c", script], timeout=180)
    if code != 0:
        return ["(could not run the import check)"]
    try:
        return json.loads(out.splitlines()[-1])
    except (ValueError, IndexError):
        return ["(could not read the import check output)"]


# --------------------------------------------------------------------------
# steps
# --------------------------------------------------------------------------
def step_prerequisites() -> bool:
    heading("1/9  Checking prerequisites")
    ok = True

    if sys.version_info >= MIN_PYTHON:
        record("OK", "Python", f"{sys.version.split()[0]} ({sys.executable})")
    else:
        record("FAIL", "Python", f"need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ but this is {sys.version.split()[0]} - "
                                 "install Python 3.12 from https://www.python.org/downloads/ and re-run")
        ok = False

    node, npm, major = node_info()
    if node and npm and major and major >= MIN_NODE:
        record("OK", "Node.js", f"v{major} + npm")
    elif node and npm and major:
        record("WARN", "Node.js", f"v{major} found, but {MIN_NODE}+ is needed for the dashboard - "
                                  "install the LTS from https://nodejs.org")
    else:
        record("WARN", "Node.js", "not found - the dashboard can't be installed without it "
                                  "(install the LTS from https://nodejs.org, then re-run)")

    if shutil.which("git"):
        record("OK", "Git", "found")
    else:
        record("WARN", "Git", "not found (only needed to update the project later)")
    return ok


def step_venv() -> bool:
    heading("2/9  Python virtual environment (.venv)")
    if VENV_PY.exists():
        v = venv_python_version()
        if v and v[:2] >= MIN_PYTHON:
            record("OK", "Virtual environment", f"reusing existing .venv (Python {'.'.join(map(str, v))})")
            return True
        record("FAIL", "Virtual environment",
               f"the existing .venv uses Python {'.'.join(map(str, v)) or 'unknown'}, need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
               "- delete the .venv folder and re-run")
        return False
    if run([sys.executable, "-m", "venv", VENV_DIR]) != 0 or not VENV_PY.exists():
        record("FAIL", "Virtual environment",
               "could not create .venv (on Debian/Ubuntu: sudo apt install python3-venv)")
        return False
    record("OK", "Virtual environment", "created .venv")
    return True


def step_python_libraries() -> bool:
    heading("3/9  Installing Python libraries (this is the slow one - a few minutes)")
    req = ROOT / "requirements.txt"
    if not req.exists():
        record("FAIL", "Python libraries", "requirements.txt not found")
        return False

    to_install = req
    if not IS_WINDOWS:
        # pywin32 exists only on Windows; without this filter pip fails the
        # whole install on macOS/Linux. The desktop agent is Windows-only.
        to_install = VENV_DIR / "requirements.nonwindows.txt"
        lines = [ln for ln in req.read_text(encoding="utf-8").splitlines() if not ln.strip().lower().startswith("pywin32")]
        to_install.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  (skipping pywin32 - Windows-only, needed just for the desktop agent)")

    run([VENV_PY, "-m", "pip", "install", "--upgrade", "pip", "--disable-pip-version-check"])
    if run([VENV_PY, "-m", "pip", "install", "-r", to_install, "--disable-pip-version-check"]) != 0:
        record("FAIL", "Python libraries", "pip reported an error - scroll up for the package that failed, "
                                          "fix it, and re-run")
        return False

    bad = missing_imports()
    if bad:
        record("FAIL", "Python libraries", "installed, but these won't import: " + ", ".join(bad))
        return False
    record("OK", "Python libraries", "all installed and importable")
    return True


def step_playwright(skip: bool) -> None:
    heading("4/9  Playwright browser (LinkedIn / browser automation)")
    if skip:
        record("SKIP", "Playwright browser", "--skip-playwright")
        return
    if run([VENV_PY, "-m", "playwright", "install", "chromium"]) == 0:
        record("OK", "Playwright browser", "Chromium ready")
    else:
        record("WARN", "Playwright browser", "download failed - LinkedIn posting won't work until you run: "
                                             ".venv python -m playwright install chromium")


def step_env_files() -> None:
    heading("5/9  Configuration files (.env)")
    example, env = ROOT / ".env.example", ROOT / ".env"
    placeholder = read_env_value(example, "SECRET_KEY")

    if env.exists():
        current = read_env_value(env, "SECRET_KEY")
        if not current or current == placeholder:
            record("WARN", ".env", "already exists but SECRET_KEY is still the public default from .env.example - "
                                   "anyone can forge login tokens. Replace it with a long random string, e.g.: "
                                   'python -c "import secrets; print(secrets.token_urlsafe(48))"')
        else:
            record("OK", ".env", "already exists - left untouched")
    elif not example.exists():
        record("WARN", ".env", ".env.example is missing, so .env could not be created")
    else:
        raw = example.read_bytes().decode("utf-8", errors="replace")
        key = secrets.token_urlsafe(48)
        # Preserves the file's own line endings (CRLF on Windows checkouts).
        new_raw, n = re.subn(r"(?m)^SECRET_KEY=.*?(\r?)$", lambda m: f"SECRET_KEY={key}{m.group(1)}", raw)
        env.write_bytes((new_raw if n else raw + f"\nSECRET_KEY={key}\n").encode("utf-8"))
        record("OK", ".env", "created from .env.example with a freshly generated SECRET_KEY "
                             "(Gmail, LinkedIn, WordPress, Google keys are optional - fill in what you need)")

    fe_example, fe_env = FRONTEND / ".env.example", FRONTEND / ".env"
    if fe_env.exists():
        record("OK", "frontend/.env", "already exists - left untouched")
    elif fe_example.exists():
        shutil.copyfile(fe_example, fe_env)
        record("OK", "frontend/.env", "created (points the dashboard at http://localhost:8000)")


def step_frontend(skip: bool) -> None:
    heading("6/9  Dashboard packages (npm)")
    if skip:
        record("SKIP", "Dashboard packages", "--skip-frontend")
        return
    node, npm, major = node_info()
    if not (node and npm):
        record("FAIL", "Dashboard packages", "Node.js/npm not found - install Node 18+ from https://nodejs.org and re-run")
        return
    if major and major < MIN_NODE:
        record("WARN", "Dashboard packages", f"Node v{major} is older than {MIN_NODE} - trying anyway")

    lock = FRONTEND / "package-lock.json"
    installed_marker = FRONTEND / "node_modules" / ".package-lock.json"
    if lock.exists() and installed_marker.exists() and installed_marker.stat().st_mtime >= lock.stat().st_mtime:
        record("OK", "Dashboard packages", "already installed and up to date")
        return

    cmd = [npm, "ci" if lock.exists() else "install", "--no-audit", "--no-fund"]
    if run(cmd, cwd=FRONTEND) == 0:
        record("OK", "Dashboard packages", "installed")
    else:
        record("FAIL", "Dashboard packages", "npm reported an error - scroll up, fix it, and re-run")


def step_database_and_smoke_test() -> None:
    heading("7/9  Database + backend smoke test")
    code = (
        "import api.main\n"
        "from api.database import init_db\n"
        "init_db()\n"
        "print('backend imports OK and database schema is ready')\n"
    )
    rc = run([VENV_PY, "-c", code])
    if rc == 0:
        record("OK", "Backend", "imports cleanly; database created/up to date (workpulse.db)")
    else:
        record("FAIL", "Backend", "the backend failed to start up - the error is printed above")


def step_ollama(skip: bool) -> None:
    heading("8/9  Ollama AI models")
    if skip:
        record("SKIP", "Ollama models", "--skip-models")
        return
    reachable, installed, message = ollama_installed_models()
    if not reachable:
        hint = ("install it from https://ollama.com (Windows: winget install Ollama.Ollama), open it once, "
                "then re-run this script")
        record("WARN", "Ollama models", f"{message} - {hint}")
        return
    missing = [m for m in OLLAMA_MODELS if not model_present(m, installed)]
    if not missing:
        record("OK", "Ollama models", "all present: " + ", ".join(OLLAMA_MODELS))
        return
    print(f"  Pulling {len(missing)} model(s): {', '.join(missing)} (about 4 GB in total for a fresh install)")
    failed = [m for m in missing if run([shutil.which("ollama"), "pull", m]) != 0]
    if failed:
        record("WARN", "Ollama models", "could not pull: " + ", ".join(failed) + " - re-run to retry")
    else:
        record("OK", "Ollama models", "pulled: " + ", ".join(missing))


def step_agent_config() -> None:
    heading("9/9  Desktop agent config")
    if not IS_WINDOWS:
        record("SKIP", "Desktop agent", "Windows-only (it tracks the Windows desktop)")
        return
    cfg = ROOT / "workpulse-config.json"
    if cfg.exists():
        record("OK", "workpulse-config.json", "already exists - left untouched")
        return
    # Same fields as agent/runtime_config.py's RuntimeConfig defaults.
    cfg.write_text(json.dumps({"api_url": "http://localhost:8000", "user_id": "local", "user_name": ""}, indent=2) + "\n",
                   encoding="utf-8")
    record("OK", "workpulse-config.json", "created with defaults - set user_id / user_name to the real employee "
                                          "before rolling the agent out")


def step_build_agent() -> None:
    heading("Extra: building WorkPulseAgent.exe")
    if not IS_WINDOWS:
        record("SKIP", "Agent .exe", "Windows-only")
        return
    if run([VENV_PY, "-m", "pip", "install", "-r", ROOT / "requirements-build.txt", "--disable-pip-version-check"]) != 0:
        record("FAIL", "Agent .exe", "could not install PyInstaller")
        return
    # scripts\build_exe.bat calls plain `python`, so put the venv first on PATH.
    env = dict(os.environ)
    env["PATH"] = str(VENV_PY.parent) + os.pathsep + env.get("PATH", "")
    rc = run(["cmd", "/c", str(ROOT / "scripts" / "build_exe.bat")], env=env)
    if rc == 0 and (ROOT / "WorkPulseAgent.exe").exists():
        record("OK", "Agent .exe", "built: WorkPulseAgent.exe (project root)")
    else:
        record("FAIL", "Agent .exe", "build failed - see the output above")


def looks_installed() -> bool:
    """Fast-path test for `--start`: the heavy setup has already been done."""
    return VENV_PY.exists() and (FRONTEND / "node_modules").exists() and (ROOT / ".env").exists()


def start_servers(agent: bool, api_port: int = 8000) -> int:
    heading("Starting WorkPulse AI")
    cmd = [VENV_PY, ROOT / "scripts" / "start_all.py", "--api-port", api_port] + (["--agent"] if agent else [])
    try:
        return run(cmd)
    except KeyboardInterrupt:  # Ctrl+C is the normal way to stop the servers
        return 0


# --------------------------------------------------------------------------
# --check (read-only)
# --------------------------------------------------------------------------
def doctor() -> int:
    print("WorkPulse AI - environment check (nothing will be changed)")
    step_prerequisites()

    heading("Project state")
    if VENV_PY.exists():
        v = venv_python_version()
        record("OK", ".venv", f"Python {'.'.join(map(str, v))}")
        bad = missing_imports()
        record("OK" if not bad else "WARN", "Python libraries",
               "all importable" if not bad else "missing / broken: " + ", ".join(bad))
    else:
        record("WARN", ".venv", "not created yet - run the setup")

    record("OK" if (FRONTEND / "node_modules").exists() else "WARN", "Dashboard packages",
           "installed" if (FRONTEND / "node_modules").exists() else "not installed yet")

    env = ROOT / ".env"
    if not env.exists():
        record("WARN", ".env", "missing")
    else:
        current = read_env_value(env, "SECRET_KEY")
        default = read_env_value(ROOT / ".env.example", "SECRET_KEY")
        if not current or current == default:
            record("WARN", ".env", "present, but SECRET_KEY is still the public default")
        else:
            record("OK", ".env", "present with a custom SECRET_KEY")
    record("OK" if (ROOT / "workpulse.db").exists() else "WARN", "Database",
           "workpulse.db exists" if (ROOT / "workpulse.db").exists() else "not created yet (created on first setup/start)")

    reachable, installed, message = ollama_installed_models()
    if not reachable:
        record("WARN", "Ollama", message)
    else:
        missing = [m for m in OLLAMA_MODELS if not model_present(m, installed)]
        record("OK" if not missing else "WARN", "Ollama models",
               "all present" if not missing else "missing: " + ", ".join(missing))

    if IS_WINDOWS:
        has = (ROOT / "workpulse-config.json").exists()
        record("OK" if has else "WARN", "Agent config", "workpulse-config.json present" if has else "not created yet")
    return summary()


# --------------------------------------------------------------------------
def summary() -> int:
    print("\n" + "=" * 64 + "\nSUMMARY\n" + "=" * 64)
    for status, step, detail in RESULTS:
        print(f"[{status:^4}] {step}" + (f" - {detail}" if detail else ""))
    failed = [r for r in RESULTS if r[0] == "FAIL"]
    warned = [r for r in RESULTS if r[0] == "WARN"]
    print("-" * 64)
    if failed:
        print(f"{len(failed)} step(s) FAILED - fix the message(s) above and run the setup again (it resumes safely).")
    elif warned:
        print(f"Finished with {len(warned)} warning(s) - the project runs, but read the WARN lines above.")
    else:
        print("Everything is set up.")
    return 1 if failed else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # never crash on a console codepage
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="One-command setup for WorkPulse AI.")
    parser.add_argument("--start", action="store_true", help="after setup, start the API + dashboard")
    parser.add_argument("--agent", action="store_true", help="with --start: also run the desktop agent (Windows)")
    parser.add_argument("--api-port", type=int, default=8000, help="with --start: API port (default 8000)")
    parser.add_argument("--check", action="store_true", help="only report what is installed; change nothing")
    parser.add_argument("--skip-models", action="store_true", help="don't pull the Ollama models")
    parser.add_argument("--skip-playwright", action="store_true", help="don't download the Playwright browser")
    parser.add_argument("--skip-frontend", action="store_true", help="don't run npm")
    parser.add_argument("--build-agent", action="store_true", help="also build WorkPulseAgent.exe (Windows)")
    args = parser.parse_args()

    if args.check:
        return doctor()

    if args.start and looks_installed():
        print("WorkPulse AI - already set up, starting...")
        return start_servers(args.agent, args.api_port)

    print("WorkPulse AI - setup")
    print(f"Project folder: {ROOT}")

    if not step_prerequisites():
        return summary()

    if step_venv() and step_python_libraries():
        step_playwright(args.skip_playwright)
        step_env_files()
        step_frontend(args.skip_frontend)
        step_database_and_smoke_test()
        step_ollama(args.skip_models)
        step_agent_config()
        if args.build_agent:
            step_build_agent()
    else:
        # Still useful to lay down the config files even if the libraries failed.
        step_env_files()

    code = summary()
    if code != 0:
        if args.start:
            print("\nNot starting the servers because setup reported errors (see above).")
        return code

    if args.start:
        print("\nTip: open .env later to add Gmail / LinkedIn / WordPress / Google keys (all optional).")
        return start_servers(args.agent, args.api_port)

    print("\nNEXT STEPS")
    print("  1. Open .env and fill in the optional sections you need (Gmail, LinkedIn, WordPress,")
    print("     GOOGLE_SERVICE_ACCOUNT_JSON_PATH, ...). The app runs without them.")
    print("  2. Start everything:  " + ("start.bat" if IS_WINDOWS else "python3 scripts/setup.py --start"))
    print("  3. Open http://localhost:5173 - the first account you create becomes the admin.")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled. Re-run any time - finished steps are skipped.")
        sys.exit(130)
