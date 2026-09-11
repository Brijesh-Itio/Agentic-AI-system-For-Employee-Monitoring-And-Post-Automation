"""
MODULE 26.2 — Webflow adapter.

Talks to the Webflow CMS API v2 (api.webflow.com/v2) over plain
`requests` with a Bearer API token — same external-call convention as
wordpress_client.py. Webflow CMS collections have no fixed field names
(unlike WordPress's title/excerpt/content), so this adapter maps
CmsClient's generic title/excerpt/content onto configurable field slugs
(settings.WEBFLOW_FIELD_TITLE/EXCERPT/CONTENT, defaulting to Webflow's
own Blog template's field names).
"""
import logging
import re
import time
from typing import List, Optional

import requests

from api.config import settings
from automation.seo.cms.base import CmsClient, CmsPost, CmsResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 20
API_BASE = "https://api.webflow.com/v2"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{slug}-{int(time.time())}"  # timestamp suffix avoids a slug collision on retry


class WebflowClient(CmsClient):
    name = "webflow"

    def __init__(
        self,
        api_token: Optional[str] = None,
        collection_id: Optional[str] = None,
    ):
        self._api_token = api_token or settings.WEBFLOW_API_TOKEN
        self._collection_id = collection_id or settings.WEBFLOW_COLLECTION_ID

    def _credentials_configured(self) -> bool:
        return bool(self._api_token and self._collection_id)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_token}", "Accept": "application/json"}

    def _parse_item(self, raw: dict) -> CmsPost:
        field_data = raw.get("fieldData") or {}
        if raw.get("isArchived"):
            status = "archived"
        elif raw.get("isDraft"):
            status = "draft"
        else:
            status = "publish"
        return CmsPost(
            id=str(raw.get("id")),
            title=field_data.get(settings.WEBFLOW_FIELD_TITLE, ""),
            slug=field_data.get("slug", ""),
            status=status,
            excerpt=field_data.get(settings.WEBFLOW_FIELD_EXCERPT),
            content=field_data.get(settings.WEBFLOW_FIELD_CONTENT),
            modified_at=raw.get("lastUpdated"),
        )

    def list_posts(self, *, status: str = "publish", per_page: int = 20, page: int = 1) -> List[CmsPost]:
        if not self._credentials_configured():
            logger.error(
                "Webflow not configured — set WEBFLOW_API_TOKEN/WEBFLOW_COLLECTION_ID in .env"
            )
            return []
        try:
            response = requests.get(
                f"{API_BASE}/collections/{self._collection_id}/items",
                params={"limit": per_page, "offset": (page - 1) * per_page},
                headers=self._headers(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            items = response.json().get("items", [])
            posts = [self._parse_item(raw) for raw in items]
            return [p for p in posts if status is None or p.status == status]
        except Exception:
            logger.exception("Webflow list_posts() failed (collection_id=%s)", self._collection_id)
            return []

    def list_pages(self, *, status: str = "publish", per_page: int = 20, page: int = 1) -> List[CmsPost]:
        # Webflow has no separate "page" content type distinct from a
        # collection item — list_posts() above already covers everything
        # this collection has, so there's nothing additional here.
        return []

    def get_post(self, post_id: str, *, kind: str = "post") -> Optional[CmsPost]:
        if not self._credentials_configured():
            logger.error(
                "Webflow not configured — set WEBFLOW_API_TOKEN/WEBFLOW_COLLECTION_ID in .env"
            )
            return None
        try:
            response = requests.get(
                f"{API_BASE}/collections/{self._collection_id}/items/{post_id}",
                headers=self._headers(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return self._parse_item(response.json())
        except Exception:
            logger.exception("Webflow get_post(%s) failed (collection_id=%s)", post_id, self._collection_id)
            return None

    def update_post(
        self,
        post_id: str,
        *,
        title: Optional[str] = None,
        excerpt: Optional[str] = None,
        content: Optional[str] = None,
        meta: Optional[dict] = None,
        kind: str = "post",
    ) -> CmsResult:
        if not self._credentials_configured():
            return CmsResult(ok=False, detail="Webflow credentials not configured")
        if meta is not None:
            # Webflow has no generic "meta" concept — SEO fields are
            # either real Webflow-native settings or plain fieldData
            # entries, never SEO-plugin postmeta the way WordPress has.
            # Failing closed here rather than silently dropping it.
            return CmsResult(ok=False, detail="Setting arbitrary meta fields isn't supported on Webflow")

        field_data = {}
        if title is not None:
            field_data[settings.WEBFLOW_FIELD_TITLE] = title
        if excerpt is not None:
            field_data[settings.WEBFLOW_FIELD_EXCERPT] = excerpt
        if content is not None:
            field_data[settings.WEBFLOW_FIELD_CONTENT] = content
        if not field_data:
            return CmsResult(ok=False, detail="No fields to update")

        try:
            response = requests.patch(
                f"{API_BASE}/collections/{self._collection_id}/items/{post_id}",
                json={"fieldData": field_data},
                headers=self._headers(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            post = self._parse_item(response.json())
            logger.info("Webflow item %s updated: %s", post_id, list(field_data.keys()))
            return CmsResult(ok=True, detail=f"Updated fields: {', '.join(field_data.keys())}", post=post)
        except Exception as exc:
            logger.exception("Webflow update_post(%s) failed (collection_id=%s)", post_id, self._collection_id)
            return CmsResult(ok=False, detail=str(exc))

    def is_reachable(self) -> bool:
        if not self._credentials_configured():
            return False
        try:
            response = requests.get(
                f"{API_BASE}/collections/{self._collection_id}", headers=self._headers(), timeout=TIMEOUT_SECONDS
            )
            return response.status_code == 200
        except Exception:
            return False

    def create_post(self, *, title: str, content: str, excerpt: Optional[str] = None) -> CmsResult:
        if not self._credentials_configured():
            return CmsResult(ok=False, detail="Webflow credentials not configured")

        field_data = {settings.WEBFLOW_FIELD_TITLE: title, "slug": _slugify(title), settings.WEBFLOW_FIELD_CONTENT: content}
        if excerpt is not None:
            field_data[settings.WEBFLOW_FIELD_EXCERPT] = excerpt

        try:
            response = requests.post(
                f"{API_BASE}/collections/{self._collection_id}/items",
                json={"isDraft": True, "fieldData": field_data},
                headers=self._headers(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            post = self._parse_item(response.json())
            logger.info("Webflow draft item created: id=%s", post.id)
            return CmsResult(ok=True, detail=f"Draft created (id={post.id})", post=post)
        except Exception as exc:
            logger.exception("Webflow create_post() failed (collection_id=%s)", self._collection_id)
            return CmsResult(ok=False, detail=str(exc))
