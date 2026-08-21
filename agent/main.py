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
from ai.tools.activity_tools import AlertMonitor

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    init_db()

    app_tracker = AppTracker()
    time_intelligence = TimeIntelligenceEngine()
    screenshot_scheduler = ScreenshotScheduler()
    browser_tracker = BrowserTracker()
    alert_monitor = AlertMonitor()
    master_agent_scheduler = MasterAgentScheduler()

    components = [
        app_tracker, time_intelligence, screenshot_scheduler,
        browser_tracker, alert_monitor, master_agent_scheduler,
    ]

    for component in components:
        component.start()

    logger.info("WorkPulse desktop agent running (app tracker, time intelligence, "
                "screenshots every 5min, browser tracker on port 8001, alert monitor, "
                "master agent scheduler). Ctrl+C to stop.")

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
        logger.info("Shutting down agent...")
        for component in reversed(components):
            try:
                component.stop()
            except Exception:
                logger.exception("Error stopping %s", component.__class__.__name__)
        logger.info("Agent stopped cleanly")


if __name__ == "__main__":
    main()
