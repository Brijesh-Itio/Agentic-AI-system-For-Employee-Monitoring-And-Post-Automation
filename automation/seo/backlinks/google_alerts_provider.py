"""
MODULE 31.1 — Google Alerts RSS provider (free, default).

Google Alerts has no public API, but its RSS delivery option (in the
Alerts UI: create/edit an alert -> "Deliver to" -> RSS feed) gives a
real, keyless, pollable feed URL scoped to one saved search query. This
is the honest free substitute the blueprint itself names ("Without
Ahrefs (free): Google Alerts brand mentions") — real brand-mention
monitoring, not backlink DR/anchor-text data, which has no free API.
"""
import logging
from typing import List
from xml.etree import ElementTree

import requests

from api.config import settings
from automation.seo.backlinks.base import BacklinkProvider, Mention

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15


class GoogleAlertsProvider(BacklinkProvider):
    name = "google_alerts"

    def fetch_mentions(self) -> List[Mention]:
        # No query parameter here (unlike Ahrefs' provider): a Google
        # Alerts RSS feed is already scoped to one saved search at
        # creation time in Google's own UI — this provider polls
        # whichever feed URL is configured, it can't search on demand.
        if not settings.GOOGLE_ALERTS_RSS_URL:
            logger.info("GOOGLE_ALERTS_RSS_URL not configured — skipping brand-mention check")
            return []
        try:
            response = requests.get(settings.GOOGLE_ALERTS_RSS_URL, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
            mentions = []
            for item in root.findall(".//item"):
                link = item.findtext("link") or ""
                if not link:
                    continue
                mentions.append(
                    Mention(
                        source_url=link,
                        source_title=item.findtext("title"),
                        discovered_at=item.findtext("pubDate"),
                    )
                )
            return mentions
        except Exception:
            logger.exception("Google Alerts RSS fetch failed")
            return []

    def is_reachable(self) -> bool:
        return bool(settings.GOOGLE_ALERTS_RSS_URL)
