"""
MODULE 26.1 — WordPress adapter.

Talks to the built-in WordPress REST API (wp-json/wp/v2) over plain
`requests` with HTTP Basic auth via an Application Password — no
WordPress SDK needed. Follows the codebase's existing external-call
convention exactly (automation/email/sender.py, automation/linkedin/poster.py):
check credentials first, wrap the call in try/except, log on failure,
never raise past this class's own boundary.
"""
import json as json_module
import logging
from typing import List, Optional

import requests
from requests.auth import HTTPBasicAuth

from api.config import settings
from automation.seo.cms.base import CmsClient, CmsPost, CmsResult
from automation.seo.crawler import USER_AGENT

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 20
# Verified live: a real WordPress site's bot-protection returned a
# blanket 403 for every request python's `requests` sent with its
# default User-Agent string, while curl (and the crawler, which already
# sends this exact UA) got through fine — this isn't evasion, it's the
# same self-identifying UA crawler.py already uses successfully against
# real sites, just applied here too since this module went without one
# entirely until this bug surfaced it.
_HEADERS = {"User-Agent": USER_AGENT}


def _parse_json(response: requests.Response) -> dict:
    """response.json() raises on a leading UTF-8 BOM — verified live
    against a real site whose PHP output has one (a common WordPress
    misconfiguration: a plugin/theme file saved with a byte-order-mark
    that gets echoed before any real output), which silently broke
    every single call in this module until this was added. Stripping
    it is safe: a BOM carries no data, and its absence on a normal site
    leaves this a no-op."""
    return json_module.loads(response.text.lstrip("﻿"))


def _parse_post(raw: dict, kind: str = "post") -> CmsPost:
    return CmsPost(
        id=str(raw.get("id")),
        title=(raw.get("title") or {}).get("rendered", ""),
        slug=raw.get("slug", ""),
        status=raw.get("status", ""),
        link=raw.get("link"),
        excerpt=(raw.get("excerpt") or {}).get("rendered"),
        content=(raw.get("content") or {}).get("rendered"),
        modified_at=raw.get("modified"),
        kind=kind,
    )


def _rest_base(kind: str) -> str:
    # "post" -> "posts", "page" -> "pages" — WordPress's own REST route
    # naming, not a guess: both are exactly the type name pluralized.
    return f"{kind}s"


class WordPressClient(CmsClient):
    name = "wordpress"

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
    ):
        self._base_url = (base_url or settings.WORDPRESS_URL).rstrip("/")
        self._username = username or settings.WORDPRESS_USERNAME
        self._app_password = app_password or settings.WORDPRESS_APP_PASSWORD

    def _credentials_configured(self) -> bool:
        return bool(self._base_url and self._username and self._app_password)

    def _auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self._username, self._app_password)

    def list_posts(self, *, status: str = "publish", per_page: int = 20, page: int = 1) -> List[CmsPost]:
        return self._list_content("post", status=status, per_page=per_page, page=page)

    def list_pages(self, *, status: str = "publish", per_page: int = 20, page: int = 1) -> List[CmsPost]:
        return self._list_content("page", status=status, per_page=per_page, page=page)

    def _list_content(self, kind: str, *, status: str, per_page: int, page: int) -> List[CmsPost]:
        if not self._credentials_configured():
            logger.error(
                "WordPress not configured — set WORDPRESS_URL/WORDPRESS_USERNAME/"
                "WORDPRESS_APP_PASSWORD in .env"
            )
            return []
        try:
            response = requests.get(
                f"{self._base_url}/wp-json/wp/v2/{_rest_base(kind)}",
                params={"status": status, "per_page": per_page, "page": page},
                auth=self._auth(),
                headers=_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return [_parse_post(raw, kind=kind) for raw in _parse_json(response)]
        except Exception:
            logger.exception("WordPress list %s() failed (base_url=%s)", _rest_base(kind), self._base_url)
            return []

    def get_post(self, post_id: str, *, kind: str = "post") -> Optional[CmsPost]:
        if not self._credentials_configured():
            logger.error(
                "WordPress not configured — set WORDPRESS_URL/WORDPRESS_USERNAME/"
                "WORDPRESS_APP_PASSWORD in .env"
            )
            return None
        try:
            response = requests.get(
                f"{self._base_url}/wp-json/wp/v2/{_rest_base(kind)}/{post_id}",
                auth=self._auth(),
                headers=_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return _parse_post(_parse_json(response), kind=kind)
        except Exception:
            logger.exception("WordPress get_post(%s, kind=%s) failed (base_url=%s)", post_id, kind, self._base_url)
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
            return CmsResult(ok=False, detail="WordPress credentials not configured")

        payload = {}
        if title is not None:
            payload["title"] = title
        if excerpt is not None:
            payload["excerpt"] = excerpt
        if content is not None:
            payload["content"] = content
        if meta is not None:
            payload["meta"] = meta
        if not payload:
            return CmsResult(ok=False, detail="No fields to update")

        try:
            response = requests.post(
                f"{self._base_url}/wp-json/wp/v2/{_rest_base(kind)}/{post_id}",
                json=payload,
                auth=self._auth(),
                headers=_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            raw = _parse_json(response)
            post = _parse_post(raw, kind=kind)
            logger.info("WordPress %s %s updated: %s", kind, post_id, list(payload.keys()))
            return CmsResult(
                ok=True, detail=f"Updated fields: {', '.join(payload.keys())}", post=post, meta=raw.get("meta")
            )
        except Exception as exc:
            logger.exception("WordPress update_post(%s, kind=%s) failed (base_url=%s)", post_id, kind, self._base_url)
            return CmsResult(ok=False, detail=str(exc))

    def is_reachable(self) -> bool:
        if not self._credentials_configured():
            return False
        try:
            response = requests.get(f"{self._base_url}/wp-json/", headers=_HEADERS, timeout=TIMEOUT_SECONDS)
            return response.status_code == 200
        except Exception:
            return False

    def create_post(self, *, title: str, content: str, excerpt: Optional[str] = None) -> CmsResult:
        if not self._credentials_configured():
            return CmsResult(ok=False, detail="WordPress credentials not configured")

        payload = {"title": title, "content": content, "status": "draft"}
        if excerpt is not None:
            payload["excerpt"] = excerpt

        try:
            response = requests.post(
                f"{self._base_url}/wp-json/wp/v2/posts",
                json=payload,
                auth=self._auth(),
                headers=_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            post = _parse_post(_parse_json(response))
            logger.info("WordPress draft post created: id=%s", post.id)
            return CmsResult(ok=True, detail=f"Draft created (id={post.id})", post=post)
        except Exception as exc:
            logger.exception("WordPress create_post() failed (base_url=%s)", self._base_url)
            return CmsResult(ok=False, detail=str(exc))
