"""
MODULE 26.3 — CMS client factory.
MODULE 34.2 — per-site credential overrides.

Builds the right CmsClient adapter for a site's cms_type — same pattern
as ai/llm/factory.py's provider selection. Pipelines call
get_cms_client(cms_type, ...) and never branch on WordPress vs Webflow
themselves.

Every keyword defaults to None, and each adapter already falls back to
its own .env setting when its constructor arg is None (module 26.1/26.2)
— but that fallback is only safe when it's unambiguous which site the
.env value describes. Callers (api/routes/seo.py) are responsible for
only passing settings.WORDPRESS_*/WEBFLOW_* through when agent.database.
count_active_seo_sites() <= 1, same rule already applied to GSC_SITE_URL/
GA4_PROPERTY_ID — otherwise a second site would silently publish through
the first site's real CMS credentials."""
from typing import Optional

from automation.seo.cms.base import CmsClient
from automation.seo.cms.webflow_client import WebflowClient
from automation.seo.cms.wordpress_client import WordPressClient


def get_cms_client(
    cms_type: str,
    *,
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    app_password: Optional[str] = None,
    api_token: Optional[str] = None,
    collection_id: Optional[str] = None,
) -> CmsClient:
    if cms_type == "wordpress":
        return WordPressClient(base_url=base_url, username=username, app_password=app_password)
    if cms_type == "webflow":
        return WebflowClient(api_token=api_token, collection_id=collection_id)
    # Unlike ai/llm/factory.py's unknown-provider fallback, this raises:
    # cms_type is constrained to "wordpress"/"webflow" at the API layer
    # (api/schemas.py's SeoCmsType Literal), so reaching this means a
    # site row was created outside that validation — a programming error
    # worth surfacing loudly, not a routine runtime condition to degrade.
    raise ValueError(f"Unknown cms_type {cms_type!r} — expected 'wordpress' or 'webflow'")
