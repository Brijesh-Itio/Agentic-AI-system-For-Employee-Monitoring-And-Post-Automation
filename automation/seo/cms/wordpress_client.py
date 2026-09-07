"""
MODULE 26.1 — WordPress adapter.

Talks to the built-in WordPress REST API (wp-json/wp/v2) over plain
`requests` with HTTP Basic auth via an Application Password — no
WordPress SDK needed. Follows the codebase's existing external-call
convention exactly (automation/email/sender.py, automation/linkedin/poster.py):
check credentials first, wrap the call in try/except, log on failure,
never raise past this class's own boundary.
"""
import logging
from typing import List, Optional

import requests
from requests.auth import HTTPBasicAuth

from api.config import settings
from automation.seo.cms.base import CmsClient, CmsPost, CmsResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 20


def _parse_post(raw: dict) -> CmsPost:
    return CmsPost(
        id=str(raw.get("id")),
        title=(raw.get("title") or {}).get("rendered", ""),
        slug=raw.get("slug", ""),
        status=raw.get("status", ""),
        link=raw.get("link"),
        excerpt=(raw.get("excerpt") or {}).get("rendered"),
        content=(raw.get("content") or {}).get("rendered"),
        modified_at=raw.get("modified"),
    )


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
        if not self._credentials_configured():
            logger.error(
                "WordPress not configured — set WORDPRESS_URL/WORDPRESS_USERNAME/"
                "WORDPRESS_APP_PASSWORD in .env"
            )
            return []
        try:
            response = requests.get(
                f"{self._base_url}/wp-json/wp/v2/posts",
                params={"status": status, "per_page": per_page, "page": page},
                auth=self._auth(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return [_parse_post(raw) for raw in response.json()]
        except Exception:
            logger.exception("WordPress list_posts() failed (base_url=%s)", self._base_url)
            return []

    def get_post(self, post_id: str) -> Optional[CmsPost]:
        if not self._credentials_configured():
            logger.error(
                "WordPress not configured — set WORDPRESS_URL/WORDPRESS_USERNAME/"
                "WORDPRESS_APP_PASSWORD in .env"
            )
            return None
        try:
            response = requests.get(
                f"{self._base_url}/wp-json/wp/v2/posts/{post_id}",
                auth=self._auth(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return _parse_post(response.json())
        except Exception:
            logger.exception("WordPress get_post(%s) failed (base_url=%s)", post_id, self._base_url)
            return None

    def update_post(
        self,
        post_id: str,
        *,
        title: Optional[str] = None,
        excerpt: Optional[str] = None,
        content: Optional[str] = None,
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
        if not payload:
            return CmsResult(ok=False, detail="No fields to update")

        try:
            response = requests.post(
                f"{self._base_url}/wp-json/wp/v2/posts/{post_id}",
                json=payload,
                auth=self._auth(),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            post = _parse_post(response.json())
            logger.info("WordPress post %s updated: %s", post_id, list(payload.keys()))
            return CmsResult(ok=True, detail=f"Updated fields: {', '.join(payload.keys())}", post=post)
        except Exception as exc:
            logger.exception("WordPress update_post(%s) failed (base_url=%s)", post_id, self._base_url)
            return CmsResult(ok=False, detail=str(exc))

    def is_reachable(self) -> bool:
        if not self._credentials_configured():
            return False
        try:
            response = requests.get(f"{self._base_url}/wp-json/", timeout=TIMEOUT_SECONDS)
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
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            post = _parse_post(response.json())
            logger.info("WordPress draft post created: id=%s", post.id)
            return CmsResult(ok=True, detail=f"Draft created (id={post.id})", post=post)
        except Exception as exc:
            logger.exception("WordPress create_post() failed (base_url=%s)", self._base_url)
            return CmsResult(ok=False, detail=str(exc))
