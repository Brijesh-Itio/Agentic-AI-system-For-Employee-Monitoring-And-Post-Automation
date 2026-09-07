"""
MODULE 31.1 — Generic backlink/mention provider interface.

Mirrors ai/llm/base.py's pattern. Real backlink data (domain rating,
anchor-text distribution, who links to a page) has no free public API —
Search Console's own Links report has never been exposed through the
public Search Console API, only the GSC website UI. So the free-tier
default here (google_alerts_provider.py) is brand-mention monitoring —
"who is talking about us," a real and genuinely useful signal, but not
the same thing as backlink DR/anchor data — with Ahrefs as the
documented paid extension point for when that's actually needed (see
factory.py for why it isn't guessed at and built here).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Mention:
    source_url: str
    source_title: Optional[str]
    discovered_at: Optional[str]
    # Only a true backlink-data provider (e.g. Ahrefs) can populate
    # these; a brand-mention provider like Google Alerts leaves them None.
    anchor_text: Optional[str] = None
    domain_rating: Optional[float] = None


class BacklinkProvider(ABC):
    """name identifies the provider in logs — must match the key used to
    select it in automation/seo/backlinks/factory.py's _build_provider()."""

    name: str

    @abstractmethod
    def fetch_mentions(self) -> List[Mention]:
        """Never raises — returns an empty list on failure or when
        unconfigured, matching this codebase's graceful-degrade
        convention."""
        raise NotImplementedError

    @abstractmethod
    def is_reachable(self) -> bool:
        raise NotImplementedError
