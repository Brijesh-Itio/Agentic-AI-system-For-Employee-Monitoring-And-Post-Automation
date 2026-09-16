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
import urllib.parse
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

    def _resolve_or_create_terms(self, taxonomy: str, names: List[str]) -> List[int]:
        """taxonomy is the REST base ("categories" or "tags"). Each name
        is looked up via ?search=; an exact case-insensitive match reuses
        that term's id, otherwise a new term is created. Requires the
        create_categories/create_tags capability — the same Application
        Password already used for posts has this on an Administrator/
        Editor account, no separate setup needed. Never raises — a name
        that can't be resolved or created is logged and skipped rather
        than failing the whole post."""
        ids: List[int] = []
        for raw_name in names:
            name = raw_name.strip()
            if not name:
                continue
            try:
                search_resp = requests.get(
                    f"{self._base_url}/wp-json/wp/v2/{taxonomy}",
                    params={"search": name, "per_page": 20},
                    auth=self._auth(),
                    headers=_HEADERS,
                    timeout=TIMEOUT_SECONDS,
                )
                search_resp.raise_for_status()
                matches = json_module.loads(search_resp.text.lstrip("﻿"))
                exact = next((t for t in matches if t.get("name", "").lower() == name.lower()), None)
                if exact:
                    ids.append(exact["id"])
                    continue

                create_resp = requests.post(
                    f"{self._base_url}/wp-json/wp/v2/{taxonomy}",
                    json={"name": name},
                    auth=self._auth(),
                    headers=_HEADERS,
                    timeout=TIMEOUT_SECONDS,
                )
                create_resp.raise_for_status()
                ids.append(json_module.loads(create_resp.text.lstrip("﻿"))["id"])
            except Exception:
                logger.exception("Could not resolve/create WordPress %s term %r", taxonomy, name)
        return ids

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

    def find_post_by_url(self, url: str) -> Optional[CmsPost]:
        if not self._credentials_configured():
            return None

        parsed = urllib.parse.urlsplit(url)
        site_netloc = urllib.parse.urlsplit(self._base_url).netloc
        if parsed.netloc and parsed.netloc != site_netloc:
            return None  # not this site at all — never guess across domains

        # WordPress's default "plain" permalink structure exposes the
        # post id directly as ?p=123 — check that before falling back
        # to slug lookup, since it's an exact id match with no
        # ambiguity, unlike a slug that could theoretically collide
        # between a post and a page.
        query = urllib.parse.parse_qs(parsed.query)
        if "p" in query and query["p"][0].isdigit():
            return self.get_post(query["p"][0], kind="post")

        slug = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        if not slug:
            return None

        for kind in ("post", "page"):
            try:
                response = requests.get(
                    f"{self._base_url}/wp-json/wp/v2/{_rest_base(kind)}",
                    params={"slug": slug},
                    auth=self._auth(),
                    headers=_HEADERS,
                    timeout=TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                matches = json_module.loads(response.text.lstrip("﻿"))
                if matches:
                    return _parse_post(matches[0], kind=kind)
            except Exception:
                logger.exception("WordPress find_post_by_url slug lookup failed (url=%s, kind=%s)", url, kind)
        return None

    def get_post_raw_content(self, post_id: str, *, kind: str = "post") -> Optional[str]:
        if not self._credentials_configured():
            return None
        try:
            response = requests.get(
                f"{self._base_url}/wp-json/wp/v2/{_rest_base(kind)}/{post_id}",
                params={"context": "edit"},
                auth=self._auth(),
                headers=_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            raw = _parse_json(response)
            return (raw.get("content") or {}).get("raw")
        except Exception:
            logger.exception("WordPress get_post_raw_content(%s, kind=%s) failed (base_url=%s)", post_id, kind, self._base_url)
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
        status: Optional[str] = None,
        slug: Optional[str] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
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
        if slug is not None:
            payload["slug"] = slug
        if tags:
            payload["tags"] = self._resolve_or_create_terms("tags", tags)
        if categories:
            payload["categories"] = self._resolve_or_create_terms("categories", categories)
        if status is not None:
            payload["status"] = status
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

    def admin_edit_url(self, post_id: str, *, kind: str = "post") -> Optional[str]:
        # WordPress's block editor uses the same post.php?action=edit
        # screen for both Posts and Pages — the "kind" only matters for
        # which REST endpoint a request goes to, not which admin screen
        # opens, so there's nothing to branch on here.
        return f"{self._base_url}/wp-admin/post.php?post={post_id}&action=edit"

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
            return CmsResult(ok=False, detail="WordPress credentials not configured")

        payload = {"title": title, "content": content, "status": "draft"}
        if excerpt is not None:
            payload["excerpt"] = excerpt
        if slug is not None:
            payload["slug"] = slug
        if tags:
            payload["tags"] = self._resolve_or_create_terms("tags", tags)
        if categories:
            payload["categories"] = self._resolve_or_create_terms("categories", categories)

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
