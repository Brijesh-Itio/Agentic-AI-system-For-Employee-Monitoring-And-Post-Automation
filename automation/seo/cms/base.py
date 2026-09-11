"""
MODULE 26.1 — Generic CMS client interface.

Every CMS adapter (WordPressClient today, WebflowClient in 26.2)
implements this so pipelines (module 27 onward) call a site's CMS
through one interface without branching on cms_type — the same pattern
ai/llm/base.py established for LLM providers. Scope is deliberately
limited to what module 26 actually proves (read posts, update one)
rather than every CMS operation later modules will need (image upload,
OG tag fields, schema markup) — those extend this interface when a
pipeline actually needs them, not ahead of need.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CmsPost:
    id: str
    title: str
    slug: str
    status: str
    link: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    modified_at: Optional[str] = None
    # "post" or "page" — WordPress's REST API treats these as genuinely
    # separate content types with separate endpoints (/wp/v2/posts vs
    # /wp/v2/pages); a caller updating this post back needs to know
    # which. Real, demonstrated need, not speculative: a live audit of a
    # real WordPress business site found its missing-meta-description
    # issues on /about, /packages, /contact-us — ordinary pages, not
    # blog posts — so a resolver that only ever checked list_posts()
    # never found a match for any of them. Defaults to "post" since
    # every pre-existing caller only ever dealt with posts.
    kind: str = "post"


@dataclass
class CmsResult:
    ok: bool
    detail: str
    post: Optional[CmsPost] = None
    # Module 35 — whatever the CMS echoed back for the `meta` dict passed
    # to update_post, if any. Callers use this to verify an SEO-plugin
    # meta key actually got set rather than silently ignored (WordPress
    # doesn't reject an unregistered meta key, it just drops it) — see
    # automation/seo/issue_applier.py.
    meta: Optional[dict] = None


class CmsClient(ABC):
    """name identifies the adapter in logs — must match a seo_sites.cms_type
    value (see automation/seo/cms/factory.py)."""

    name: str

    @abstractmethod
    def list_posts(self, *, status: str = "publish", per_page: int = 20, page: int = 1) -> List[CmsPost]:
        """Never raises — returns an empty list on failure, same
        graceful-degrade convention as ai/ollama_client.py."""
        raise NotImplementedError

    @abstractmethod
    def list_pages(self, *, status: str = "publish", per_page: int = 20, page: int = 1) -> List[CmsPost]:
        """Module 35 — ordinary WordPress Pages (About, Contact, ...),
        a separate content type from Posts. Never raises — returns an
        empty list on failure, or on a CMS (Webflow) with no such
        distinction: Webflow's list_posts() already covers everything
        Webflow has, so there's nothing separate to return here."""
        raise NotImplementedError

    @abstractmethod
    def get_post(self, post_id: str, *, kind: str = "post") -> Optional[CmsPost]:
        raise NotImplementedError

    @abstractmethod
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
        """Updates only the fields actually passed (None = leave
        untouched). meta is a generic passthrough to whatever custom-
        field system the CMS has (WordPress's REST `meta` object; not
        supported on Webflow, whose SEO fields work differently — see
        WebflowClient's implementation) — this method doesn't itself
        know or guess SEO-plugin-specific key names, it just forwards
        what the caller supplies. kind selects which REST endpoint a
        WordPress post_id resolves against ("post" -> /wp/v2/posts,
        "page" -> /wp/v2/pages) — pass through whatever CmsPost.kind the
        post/page came from list_posts()/list_pages(); meaningless for
        Webflow, which has only one content type. Never raises —
        failures come back as CmsResult(ok=False, detail=...)."""
        raise NotImplementedError

    @abstractmethod
    def is_reachable(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_post(self, *, title: str, content: str, excerpt: Optional[str] = None) -> CmsResult:
        """Module 34 — creates a genuinely new post, always as a draft
        (never published outright): WordPress gets `status: "draft"`,
        Webflow gets `isDraft: true`. A human still has to hit Publish in
        the CMS itself — this method never puts a page live on its own.
        Never raises — failures come back as CmsResult(ok=False, ...)."""
        raise NotImplementedError
