"""
MODULE 41 — Scheduled social post auto-publishing.

publish_one() is the actual "resolve credentials, call the real platform
API, record the outcome" orchestration, shared by the manual
/social/{id}/publish route, /social/bulk-publish, and the recurring
scheduler job below — one code path, not copies that could drift.
Callers are responsible for their own existence/status validation (the
API routes do this via SQLAlchemy before calling in, matching their
existing 404/409 conventions); this module assumes that's already done
and just does the network call + DB write, using agent/database.py
directly (raw sqlite) rather than a SQLAlchemy session, so it can be
called from a plain APScheduler job with no FastAPI request in scope —
same pattern every other scheduled job in api/main.py already uses.
"""
import logging
from pathlib import Path

from agent import database
from automation.seo.social_poster import PublishResult, publish_social_post

logger = logging.getLogger(__name__)


def publish_one(post_id: int) -> PublishResult:
    row = database.get_social_post(post_id)
    if row is None:
        return PublishResult(ok=False, detail=f"No social post {post_id}")

    facebook_page_id = None
    facebook_access_token = None
    if row["platform"] == "facebook" and row["facebook_account_id"] is not None:
        account = database.get_facebook_account(row["facebook_account_id"])
        if account is None:
            detail = f"Facebook account {row['facebook_account_id']} was deleted"
            database.mark_social_post_failed(post_id, detail)
            return PublishResult(ok=False, detail=detail)
        facebook_page_id = account["page_id"]
        facebook_access_token = account["page_access_token"]

    linkedin_account_id = None
    linkedin_email = None
    linkedin_password = None
    linkedin_page_url = None
    linkedin_session_path = None
    if row["platform"] == "linkedin" and row["linkedin_account_id"] is not None:
        account = database.get_linkedin_account(row["linkedin_account_id"])
        if account is None:
            detail = f"LinkedIn account {row['linkedin_account_id']} was deleted"
            database.mark_social_post_failed(post_id, detail)
            return PublishResult(ok=False, detail=detail)
        if account["session_path"] is None:
            detail = f"LinkedIn account {account['label']!r} isn't connected yet — log in from the LinkedIn accounts card first"
            database.mark_social_post_failed(post_id, detail)
            return PublishResult(ok=False, detail=detail)
        linkedin_account_id = account["id"]
        linkedin_email = account["email"]
        linkedin_password = account["password"]
        linkedin_page_url = account["page_url"]
        linkedin_session_path = Path(account["session_path"])

    result = publish_social_post(
        row["platform"],
        row["content"],
        image_url=row["image_url"],
        facebook_page_id=facebook_page_id,
        facebook_access_token=facebook_access_token,
        linkedin_account_id=linkedin_account_id,
        linkedin_email=linkedin_email,
        linkedin_password=linkedin_password,
        linkedin_page_url=linkedin_page_url,
        linkedin_session_path=linkedin_session_path,
    )
    if result.ok:
        database.mark_social_post_posted(post_id, result.external_post_id)
    else:
        database.mark_social_post_failed(post_id, result.detail)
    return result


def run_due_scheduled_posts() -> None:
    """The scheduler job itself (registered in api/main.py): finds every
    approved post whose scheduled_for has arrived and publishes it for
    real. One post's failure (bad credentials, a transient API error)
    never stops the rest, same graceful-degrade-per-item convention as
    every other scheduled job in this codebase."""
    due = database.list_due_scheduled_social_posts()
    if not due:
        return
    logger.info("Scheduled social posts: %d due for auto-publish", len(due))
    for row in due:
        try:
            result = publish_one(row["id"])
            if result.ok:
                logger.info("Auto-published scheduled social post %s (%s)", row["id"], row["platform"])
            else:
                logger.warning("Auto-publish failed for scheduled social post %s: %s", row["id"], result.detail)
        except Exception:
            logger.exception("Unexpected error auto-publishing scheduled social post %s", row["id"])
