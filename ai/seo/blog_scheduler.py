"""
MODULE 59 — Scheduled blog post auto-publishing.

Same shape as ai/seo/social_scheduler.py (module 41): the scheduler job
below finds every due blog post and acts on it for real, one post's
failure never stopping the rest. "Due" covers two genuinely different
starting states (see agent/database.py's list_due_scheduled_blog_posts):

  - status='approved': never published — creates the CMS draft AND
    takes it live in one pass (_do_publish_blog_post(go_live=True)).
  - status='published': already sitting as a CMS draft from an earlier
    manual Publish; a human then scheduled just the go-live moment for
    it. Only the go-live step runs (_do_go_live_blog_post) — creating a
    second CMS post would duplicate it.

Both cases end with the same "make it actually public" step, matching
the manual Publish-then-Go-Live flow, just automated. Unlike social
posts (a single platform-API call, done with raw agent/database.py
access), publishing/going-live a blog post is a genuinely bigger
orchestration — CMS client resolution, auto image generation, interlink
injection, post-publish OG-tag/indexing automation — already implemented
once in api/routes/seo.py so the manual routes, /blog/bulk-publish, and
this scheduler all share the exact same code paths rather than copies
that could drift. Those functions take a SQLAlchemy Session; this
module opens its own short-lived one (no FastAPI request in scope here)
and closes it when done, the standard pattern for using a request-scoped
ORM from a background job.
"""
import logging

logger = logging.getLogger(__name__)


def run_due_scheduled_posts() -> None:
    """The scheduler job itself (registered in api/main.py)."""
    from agent import database
    from api.database import SessionLocal
    from api.routes.seo import _do_go_live_blog_post, _do_publish_blog_post

    due = database.list_due_scheduled_blog_posts()
    if not due:
        return
    logger.info("Scheduled blog posts: %d due", len(due))

    # These only ever read through this Session — every actual write
    # goes through agent/database.py's own connection (its
    # write_cursor() commits per-call), same split every route in
    # api/routes/seo.py already relies on — so there's nothing to
    # db.commit() here, only to close when done.
    db = SessionLocal()
    try:
        for row in due:
            try:
                if row["status"] == "published":
                    ok, detail = _do_go_live_blog_post(row["id"], db)
                else:
                    ok, detail = _do_publish_blog_post(row["id"], db, go_live=True)
                if ok:
                    logger.info("Scheduled blog post %s is now live", row["id"])
                else:
                    logger.warning("Auto go-live failed for scheduled blog post %s: %s", row["id"], detail)
            except Exception:
                logger.exception("Unexpected error auto-publishing scheduled blog post %s", row["id"])
    finally:
        db.close()
