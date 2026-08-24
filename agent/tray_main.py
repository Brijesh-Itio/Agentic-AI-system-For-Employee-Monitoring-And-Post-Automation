"""
MODULE 23.5 — First-run setup + system tray entry point for the packaged
.exe (module 23.1-23.4 build the .exe itself; this is what actually runs
inside it, in place of `python -m agent.main`).

Order matters here: workpulse-config.json must be loaded/created and its
values pushed into the environment *before* `agent.main` (or anything it
imports, e.g. `agent.config`) is imported for the first time, since those
modules read their settings from `os.environ` at import time. That's why
every workpulse.* import below is deferred inside functions instead of
sitting at module level.
"""
import logging
import sys
import threading
import time
import webbrowser


def _first_run_setup():
    """Blocking tkinter prompts for API URL + user name, run once."""
    import tkinter as tk
    from tkinter import simpledialog

    from agent.runtime_config import RuntimeConfig

    root = tk.Tk()
    root.withdraw()

    api_url = simpledialog.askstring(
        "WorkPulse AI Setup",
        "API server URL:",
        initialvalue="http://localhost:8000",
        parent=root,
    ) or "http://localhost:8000"

    user_name = simpledialog.askstring(
        "WorkPulse AI Setup",
        "Your name (used as your tracking ID):",
        parent=root,
    ) or "local"

    root.destroy()

    user_id = user_name.strip().lower().replace(" ", ".") or "local"
    return RuntimeConfig(api_url=api_url.strip(), user_id=user_id, user_name=user_name.strip())


def _make_icon_image():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(70, 95, 255, 255))
    draw.ellipse((size // 3, size // 3, size - size // 3, size - size // 3), fill=(255, 255, 255, 255))
    return img


def run() -> None:
    from agent.runtime_config import apply_to_environment, load_runtime_config, save_runtime_config

    config = load_runtime_config()
    if config is None:
        config = _first_run_setup()
        save_runtime_config(config)

    apply_to_environment(config)

    # Only safe to import agent.main/agent.config (or anything that
    # transitively imports agent.config, e.g. agent.logging_config) from
    # this point on — agent.config reads WORKPULSE_USER_ID etc. from
    # os.environ at *import* time, so importing any of this earlier would
    # silently bake in the pre-apply_to_environment defaults (this was a
    # real bug: USER_ID landed as "local" no matter what the config file
    # said, because agent.logging_config used to be imported above).
    from agent.logging_config import setup_logging
    from agent import autostart
    from agent.main import start_components, stop_components

    setup_logging()
    logger = logging.getLogger(__name__)

    if autostart.is_frozen():
        autostart.enable_autostart(sys.executable)

    components = start_components()
    logger.info("Tray agent running for user_id=%s, API=%s", config.user_id, config.api_url)

    import pystray

    stop_event = threading.Event()

    def on_open_dashboard(icon, item):
        # The dashboard is a separate Vercel/Vite deployment, not served by
        # this API — best guess is the API host on the dashboard's default
        # dev port, which is right for the common local-agent-plus-local-
        # dashboard setup this packaging targets.
        dashboard_url = config.api_url.replace(":8000", ":5173")
        webbrowser.open(dashboard_url)

    def on_exit(icon, item):
        stop_event.set()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(f"WorkPulse AI — {config.user_name or config.user_id}", None, enabled=False),
        pystray.MenuItem("Open Dashboard", on_open_dashboard),
        pystray.MenuItem("Exit", on_exit),
    )
    icon = pystray.Icon("WorkPulseAgent", _make_icon_image(), "WorkPulse AI — Running", menu)

    def _run_icon() -> None:
        try:
            icon.run()
        except Exception:
            logger.exception("Tray icon failed — tracking continues without it")
        finally:
            stop_event.set()

    # Tracking must never depend on the tray icon succeeding: icon.run()
    # drives a native Windows message pump that can block indefinitely (or
    # even appear to starve other threads) in some session contexts — e.g.
    # observed hanging forever with zero tracking activity when there's no
    # normal interactive window station available. Running it on its own
    # thread means a hung/failed tray icon costs you the icon, never the
    # actual tracking, which keeps working from the plain wait loop below.
    tray_thread = threading.Thread(target=_run_icon, name="TrayIconThread", daemon=True)
    tray_thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        stop_components(components)


if __name__ == "__main__":
    run()
