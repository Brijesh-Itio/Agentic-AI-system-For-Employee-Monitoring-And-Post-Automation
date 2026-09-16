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

    def find_post_by_url(self, url: str) -> Optional[CmsPost]:
        # No verified Webflow slug-filter query param to build against —
        # matches client-side over list_posts() instead of guessing one,
        # same "don't guess an unverified shape" rule as everywhere else
        # in this codebase. Fine at this collection's scale; a very
        # large collection would need real pagination here.
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if not slug:
            return None
        for post in self.list_posts(status=None, per_page=100):
            if post.slug == slug:
                return post
        return None

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

    def get_post_raw_content(self, post_id: str, *, kind: str = "post") -> Optional[str]:
        # No separate raw/rendered distinction on Webflow — fieldData's
        # content field already is the one true stored value.
        post = self.get_post(post_id, kind=kind)
        return post.content if post else None

    def update_post(
        self,
        post_id: str,
        *,
        title: Optional[str] = None,
        excerpt: Optional[str] = None,
        content: Optional[str] = None,
        meta: Optional[dict] = None,
        kind: str = "post",
        status: Optional[str] = None,
        slug: Optional[str] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
    ) -> CmsResult:
        if not self._credentials_configured():
            return CmsResult(ok=False, detail="Webflow credentials not configured")
        # tags/categories: see create_post's comment above — no generic
        # Webflow equivalent, silently ignored.
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
        if slug is not None:
            field_data["slug"] = slug
        # Webflow has no WordPress-style "publish" status string — going
        # live is isDraft: false on the item itself, separate from the
        # site-wide publish queue Webflow's own UI also has (out of
        # scope here, same as it was for create_post).
        body: dict = {"fieldData": field_data} if field_data else {}
        if status == "publish":
            body["isDraft"] = False
        if not body:
            return CmsResult(ok=False, detail="No fields to update")

        try:
            response = requests.patch(
                f"{API_BASE}/collections/{self._collection_id}/items/{post_id}",
                json=body,
                headers=self._headers(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            post = self._parse_item(response.json())
            updated_fields = list(field_data.keys()) + (["status"] if status else [])
            logger.info("Webflow item %s updated: %s", post_id, updated_fields)
            return CmsResult(ok=True, detail=f"Updated fields: {', '.join(updated_fields)}", post=post)
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

    def admin_edit_url(self, post_id: str, *, kind: str = "post") -> Optional[str]:
        # Webflow's Designer/CMS editor URLs are keyed by the site's own
        # workspace slug (webflow.com/dashboard/sites/<site-slug>/...),
        # which this client is never given — only a collection id and an
        # API token. Guessing a URL that's wrong is worse than admitting
        # there's no deep link available.
        return None

    def create_post(
        self,
        *,
        title: str,
        content: str,
        excerpt: Optional[str] = None,
        slug: Optional[str] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
    ) -> CmsResult:
        if not self._credentials_configured():
            return CmsResult(ok=False, detail="Webflow credentials not configured")
        # tags/categories have no generic Webflow equivalent (a
        # collection's schema is arbitrary, unlike WordPress's built-in
        # taxonomies) — silently ignored, same as meta above, rather than
        # guessing at a field mapping nothing here actually verified.

        field_data = {
            settings.WEBFLOW_FIELD_TITLE: title,
            "slug": slug or _slugify(title),
            settings.WEBFLOW_FIELD_CONTENT: content,
        }
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
