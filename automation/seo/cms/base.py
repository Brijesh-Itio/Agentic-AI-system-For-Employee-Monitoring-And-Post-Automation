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


@dataclass
class CmsResult:
    ok: bool
    detail: str
    post: Optional[CmsPost] = None


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
    def get_post(self, post_id: str) -> Optional[CmsPost]:
        raise NotImplementedError

    @abstractmethod
    def update_post(
        self,
        post_id: str,
        *,
        title: Optional[str] = None,
        excerpt: Optional[str] = None,
        content: Optional[str] = None,
    ) -> CmsResult:
        """Updates only the fields actually passed (None = leave
        untouched). Never raises — failures come back as
        CmsResult(ok=False, detail=...)."""
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
