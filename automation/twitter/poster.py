"""
MODULE 36 — X/Twitter posting (API v2).

Real REST calls against POST https://api.twitter.com/2/tweets, no SDK —
same plain-requests convention as automation/instagram/poster.py.
Endpoint shape, auth requirements, and JSON body verified against
docs.x.com's current manage-Posts quickstart this session, not guessed.

Auth is OAuth 1.0a user context (API Key + API Secret + Access Token +
Access Token Secret, all four together) via requests_oauthlib — chosen
over OAuth 2.0 PKCE because it's four static credentials a user pastes
into .env once, not an interactive browser consent flow, matching how
every other credential-based integration in this codebase (Instagram,
Semrush, GSC service account) is configured.

ai/seo/social_content.py's Twitter prompt asks the LLM for a thread —
"a hook tweet, then 4-5 short follow-up tweets ... separated by a blank
line" — so post_to_twitter splits on blank lines and posts each part as
a reply to the previous one, building a real thread rather than losing
everything after the first paragraph.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import requests
from requests_oauthlib import OAuth1

from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

TWEETS_URL = "https://api.twitter.com/2/tweets"
TIMEOUT_SECONDS = 30


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def _credentials_configured() -> bool:
    return bool(
        settings.TWITTER_API_KEY
        and settings.TWITTER_API_SECRET
        and settings.TWITTER_ACCESS_TOKEN
        and settings.TWITTER_ACCESS_TOKEN_SECRET
    )


def _auth() -> OAuth1:
    return OAuth1(
        settings.TWITTER_API_KEY,
        client_secret=settings.TWITTER_API_SECRET,
        resource_owner_key=settings.TWITTER_ACCESS_TOKEN,
        resource_owner_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
    )


def _api_error_detail(response: Optional[requests.Response]) -> str:
    if response is None:
        return "no response"
    try:
        errors = response.json()
        detail = errors.get("detail") or errors.get("title")
        if detail:
            return detail
    except ValueError:
        pass
    return response.text[:300]


def _post_one_tweet(text: str, *, in_reply_to: Optional[str] = None) -> requests.Response:
    body = {"text": text}
    if in_reply_to:
        body["reply"] = {"in_reply_to_tweet_id": in_reply_to}
    response = requests.post(TWEETS_URL, json=body, auth=_auth(), timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response


def post_to_twitter(content: str) -> PublishResult:
    """Never raises — always returns a PublishResult, same graceful-
    degrade convention as every other dispatch target in
    automation/seo/social_poster.py. content may be a single tweet or a
    thread (parts separated by a blank line); returns the first tweet's
    id as external_post_id."""
    if not _credentials_configured():
        return PublishResult(
            ok=False,
            detail="TWITTER_API_KEY/TWITTER_API_SECRET/TWITTER_ACCESS_TOKEN/"
            "TWITTER_ACCESS_TOKEN_SECRET not all set in .env — cannot post",
        )

    parts = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not parts:
        return PublishResult(ok=False, detail="No tweet content to post")

    first_id: Optional[str] = None
    previous_id: Optional[str] = None
    for i, part in enumerate(parts):
        try:
            response = with_retry(
                lambda part=part, previous_id=previous_id: _post_one_tweet(part, in_reply_to=previous_id),
                max_attempts=3,
                retry_on=(requests.RequestException,),
            )
        except requests.RequestException as exc:
            detail = _api_error_detail(getattr(exc, "response", None))
            logger.error("Twitter post failed at part %d/%d: %s", i + 1, len(parts), detail)
            if first_id:
                # Partial thread already posted — report it as a partial
                # success rather than a clean failure, so a caller/human
                # knows something did go live.
                return PublishResult(
                    ok=True,
                    detail=f"Posted {i} of {len(parts)} tweet(s) — thread stopped early: {detail}",
                    external_post_id=first_id,
                )
            return PublishResult(ok=False, detail=f"Couldn't post tweet: {detail}")

        tweet_id = response.json().get("data", {}).get("id")
        if i == 0:
            first_id = tweet_id
        previous_id = tweet_id

    logger.info("Posted to Twitter successfully (%d tweet(s), first id=%s)", len(parts), first_id)
    return PublishResult(ok=True, detail="Posted successfully", external_post_id=first_id)
