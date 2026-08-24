"""
Desktop agent entry point — starts every Module 1-4 + 14-15 tracker
together: app tracking, time intelligence (idle/breaks/focus scoring),
screenshots, browser/website tracking, smart alert monitoring, and the
LangGraph Master Agent's daily scheduler. Each runs on its own thread.

Note: module 7 also defines a standalone DarScheduler (18:00 trigger), but
it's intentionally NOT started here — module 15's MasterAgentScheduler
already triggers DAR generation via its reporting_node at the same time
(its completion cycle), and running both would double-generate. Manual
"Generate Now" (the API endpoint) still calls the DAR generator directly,
unaffected either way.

`start_components()`/`stop_components()` are factored out so module 23's
packaged tray entry point (`agent/tray_main.py`) can reuse the exact same
startup/shutdown sequence instead of duplicating it.
"""
import logging
import signal
import time

from agent.app_tracker import AppTracker
from agent.browser_tracker import BrowserTracker
from agent.database import init_db
from agent.logging_config import setup_logging
from agent.screenshot import ScreenshotScheduler
from agent.time_intelligence import TimeIntelligenceEngine
from ai.master_agent import MasterAgentScheduler
from ai.productivity_scorer import LiveScoringScheduler
from ai.tools.activity_tools import AlertMonitor

logger = logging.getLogger(__name__)


def start_components() -> list:
    """Starts every tracker component and returns them (reverse order stops them)."""
    init_db()

    components = [
        AppTracker(),
        TimeIntelligenceEngine(),
        ScreenshotScheduler(),
        BrowserTracker(),
        AlertMonitor(),
        MasterAgentScheduler(),
        LiveScoringScheduler(),
    ]
    for component in components:
        component.start()

    logger.info(
        "WorkPulse desktop agent running (app tracker, time intelligence, "
        "screenshots every 5min, browser tracker (window-title based), alert monitor, "
        "master agent scheduler, live scoring every 60s)."
    )
    return components


def stop_components(components: list) -> None:
    logger.info("Shutting down agent...")
    for component in reversed(components):
        try:
            component.stop()
        except Exception:
            logger.exception("Error stopping %s", component.__class__.__name__)
    logger.info("Agent stopped cleanly")


def main() -> None:
    setup_logging()
    components = start_components()
    logger.info("Ctrl+C to stop.")

    stop = False

    def handle_signal(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while not stop:
            time.sleep(1)
    finally:
        stop_components(components)


if __name__ == "__main__":
    main()
