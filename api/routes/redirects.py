"""URL Redirection manager — permanent (301) and temporary (302) redirect rules.

A rule maps a source URL ("Url 1") to a target URL ("Url 2"). The source may
be a bare path ("/old-page", matches any Host header) or a full URL
("https://old.example.com/old-page", matches only that Host — useful once
that domain's DNS points at this server).

A source on a domain that does NOT point at this server (e.g. the user's real
website) can't be answered here at all — visitors never reach us. If that
domain matches a SEO site that has server access saved, the rule is written
into the site's own .htaccess instead (automation/seo/htaccess_redirects.py),
backed up, verified with a real request, and rolled back if anything is off.

Rules are enforced by `serve_redirect`, which api/main.py wires in as the
404 fallback: a request only reaches it when no real route matched, so a
rule can never shadow an actual endpoint (and `/api`, docs paths and "/" are
rejected as sources up front). Lookup is one indexed query per 404 — no
in-process cache, so several uvicorn workers can never disagree after an edit.

Management endpoints require a logged-in user (any role), matching the SEO
tab they live in. Rules change what a publicly reachable URL does and the
Test action makes a server-side request, so they are never anonymous.
"""
import logging
import re
import threading
import time
from datetime import datetime
from typing import Optional
from urllib.parse import unquote, urlsplit

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agent import database as agent_db
from api.auth import get_current_user
from api.database import SeoSite, SessionLocal, UrlRedirect, User, get_db
from api.schemas import RedirectCreate, RedirectOut, RedirectTestResult, RedirectUpdate
from automation.seo.htaccess_redirects import (
    HTACCESS_PATH,
    SiteRedirect,
    SyncResult,
    same_url,
    sync_site_redirects,
)
from automation.seo.server_access import client_for_site

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/redirects", tags=["redirects"])

MAX_URL_LENGTH = 2048
MAX_CHAIN_HOPS = 10
# Sent by the Test action so its probe isn't counted as a real visitor hit.
TEST_PROBE_HEADER = "X-Redirect-Test"
# Paths owned by the app itself — a redirect from any of these could never
# fire (a real route answers first) or would break the API if it could.
_RESERVED_PREFIXES = ("/api", "/docs", "/redoc", "/openapi.json")
_CONTROL_OR_SPACE = re.compile(r"[\s\x00-\x1f\x7f]")
# Characters that would break out of (or be reinterpreted inside) the quoted
# Apache directive a rule can be written as — see htaccess_redirects.py.
_UNSAFE_CHARS = re.compile(r'["\\<>`$]')
_UNSAFE_MESSAGE = 'must not contain any of these characters: " \\ < > ` $'
_site_locks: dict[int, threading.Lock] = {}
_site_locks_guard = threading.Lock()


def _is_reserved(path: str) -> bool:
    lowered = path.lower()
    return any(lowered == p or lowered.startswith(p + "/") for p in _RESERVED_PREFIXES)


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _normalise_path(path: str) -> str:
    path = unquote(path or "/")
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    return path


def _normalise_host(parts) -> Optional[str]:
    """Lower-cased host[:port], with the scheme's default port dropped —
    browsers omit it from the Host header, so it must not be stored either."""
    if not parts.hostname:
        return None
    host = parts.hostname.lower()
    port = parts.port
    if port and not ((parts.scheme == "http" and port == 80) or (parts.scheme == "https" and port == 443)):
        return f"{host}:{port}"
    return host


def _parse_source(raw: str) -> tuple[str, Optional[str], str]:
    """Returns (source_url as stored, host or None, normalised path)."""
    raw = (raw or "").strip()
    if not raw:
        raise _bad("Source URL (Url 1) is required")
    if len(raw) > MAX_URL_LENGTH:
        raise _bad(f"Source URL is too long (max {MAX_URL_LENGTH} characters)")
    if _CONTROL_OR_SPACE.search(raw):
        raise _bad("Source URL must not contain spaces or control characters")
    if _UNSAFE_CHARS.search(raw):
        raise _bad(f"Source URL {_UNSAFE_MESSAGE}")

    if raw.startswith("/"):
        parts = urlsplit(raw)
        host = None
    else:
        parts = urlsplit(raw)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise _bad("Source URL must be a path starting with '/' or a full http(s):// URL")
        try:
            host = _normalise_host(parts)
        except ValueError:
            raise _bad("Source URL has an invalid port")
        if host is None:
            raise _bad("Source URL has no host name")
    if parts.query or parts.fragment:
        raise _bad("Source URL must not contain a query string or #fragment — match on the path only")

    path = _normalise_path(parts.path)
    if path == "/":
        raise _bad("The site root '/' can't be a redirect source — the API's own root endpoint answers it")
    if _is_reserved(path):
        raise _bad(f"Paths under {', '.join(_RESERVED_PREFIXES)} are reserved for the app itself")
    return raw, host, path


def _parse_target(raw: str) -> tuple[str, Optional[str], str]:
    """Returns (target_url as stored, host, normalised path)."""
    raw = (raw or "").strip()
    if not raw:
        raise _bad("Target URL (Url 2) is required")
    if len(raw) > MAX_URL_LENGTH:
        raise _bad(f"Target URL is too long (max {MAX_URL_LENGTH} characters)")
    if _CONTROL_OR_SPACE.search(raw):
        raise _bad("Target URL must not contain spaces or control characters")
    if _UNSAFE_CHARS.search(raw):
        raise _bad(f"Target URL {_UNSAFE_MESSAGE}")
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise _bad("Target URL must be a full http:// or https:// URL")
    try:
        host = _normalise_host(parts)
    except ValueError:
        raise _bad("Target URL has an invalid port")
    if host is None:
        raise _bad("Target URL has no host name")
    return raw, host, _normalise_path(parts.path)


def _find_rule(
    db: Session, host: Optional[str], path: str, exclude_id: Optional[int] = None, include_hostless: bool = True
) -> Optional[UrlRedirect]:
    """Host-specific rule wins over a host-less (any Host) one."""
    for candidate_host in ([host] if host else []) + ([None] if include_hostless else []):
        query = db.query(UrlRedirect).filter(UrlRedirect.source_path == path)
        query = query.filter(
            UrlRedirect.source_host.is_(None) if candidate_host is None else UrlRedirect.source_host == candidate_host
        )
        if exclude_id is not None:
            query = query.filter(UrlRedirect.id != exclude_id)
        row = query.first()
        if row is not None:
            return row
    return None


def _check_no_loop(
    db: Session, source_host: Optional[str], source_path: str, target_host: str, target_path: str,
    own_host: Optional[str], exclude_id: Optional[int],
) -> None:
    """Follows the chain target -> next rule's target -> ... A redirect that
    eventually lands back on the new rule's own source would loop forever in
    the browser ("too many redirects"), so it's refused when it's created.

    A host-less source only ever fires for requests arriving at this server,
    so for loop purposes its host is this server's own host (`own_host`) —
    that way "/blog -> https://other.com/blog" is fine but
    "/blog -> http://<this server>/blog" is caught."""
    effective_source_host = source_host or own_host
    host, path = target_host, target_path
    for hop in range(MAX_CHAIN_HOPS):
        if path == source_path and host == effective_source_host:
            raise _bad(
                "Target URL is the same as the source — that would redirect to itself"
                if hop == 0
                else "This would create a redirect loop (the target eventually redirects back to this source)"
            )
        rule = _find_rule(db, host, path, exclude_id, include_hostless=(host == own_host))
        if rule is None:
            return
        _, host, path = _parse_target(rule.target_url)
    raise _bad(f"Redirect chain is longer than {MAX_CHAIN_HOPS} hops — point Url 2 at the final destination")


def _bare_host(host: Optional[str]) -> Optional[str]:
    return host[4:] if host and host.startswith("www.") else host


def _site_hosts(site: SeoSite) -> set[str]:
    """Hosts this SEO site answers for (www-insensitive), from its base URL
    and Search Console property."""
    hosts = set()
    for raw in (site.base_url, site.gsc_site_url):
        if not raw:
            continue
        raw = raw.strip()
        if raw.startswith("sc-domain:"):
            raw = "https://" + raw[len("sc-domain:"):]
        try:
            host = _normalise_host(urlsplit(raw))
        except ValueError:
            continue
        if host:
            hosts.add(_bare_host(host))
    return hosts


def _managed_sites(db: Session) -> list[SeoSite]:
    """Active SEO sites with complete server-access credentials — the only
    ones a redirect can be written into. Sites installed at the domain root
    come first (their .htaccess is the one at the FTP root)."""
    sites = (
        db.query(SeoSite)
        .filter(
            SeoSite.is_active == 1,
            SeoSite.ssh_host.isnot(None),
            SeoSite.ssh_username.isnot(None),
            SeoSite.ssh_password.isnot(None),
        )
        .order_by(SeoSite.id.asc())
        .all()
    )
    return sorted(sites, key=lambda site: (urlsplit(site.base_url or "").path.strip("/") != "", site.id))


def _match_site(sites: list[SeoSite], host: Optional[str]) -> Optional[SeoSite]:
    if not host:
        return None
    return next((site for site in sites if _bare_host(host) in _site_hosts(site)), None)


def _rules_for_site(
    db: Session, site: SeoSite, sites: list[SeoSite], exclude_id: Optional[int] = None
) -> list[UrlRedirect]:
    rows = db.query(UrlRedirect).filter(UrlRedirect.source_host.isnot(None)).all()
    return [r for r in rows if r.id != exclude_id and _match_site(sites, r.source_host) is site]


def _to_out(row: UrlRedirect, request: Request, sites: list[SeoSite]) -> RedirectOut:
    live_url = row.source_url if row.source_host else str(request.base_url).rstrip("/") + row.source_path
    out = RedirectOut.model_validate(row)
    out.live_url = live_url
    site = _match_site(sites, row.source_host)
    out.apply_site = site.name if site else None
    if row.sync_status in ("synced", "failed") and site is not None:
        out.sync_status, out.sync_message = row.sync_status, row.sync_message or ""
    elif not row.source_host or row.source_host == _own_host(request):
        out.sync_status, out.sync_message = "served", "Served by this API."
    elif site is not None:
        out.sync_status = "pending"
        out.sync_message = (
            f"Not applied on {site.name} yet — click “Apply to site” to write it to the site's .htaccess."
        )
    else:
        out.sync_status = "unmanaged"
        out.sync_message = (
            f"{row.source_host} doesn't point at this server and no SEO site with server access (FTP/SFTP) "
            "matches it, so nothing redirects yet."
        )
    return out


def _apply_to_site(
    db: Session, site: SeoSite, sites: list[SeoSite], row: Optional[UrlRedirect], exclude_id: Optional[int] = None
) -> SyncResult:
    """Rewrites `site`'s .htaccess redirect block from every rule that
    belongs to it, then records the outcome on `row` (the rule that
    triggered this, which is also the one verified with a live request).
    row=None means a rule is being removed: only the site's health is checked."""
    client = client_for_site(site)
    if client is None:
        return SyncResult(False, f"No server access credentials saved for {site.name}.")

    rules = [
        SiteRedirect(r.source_path, r.target_url, r.status_code) for r in _rules_for_site(db, site, sites, exclude_id)
    ]
    if row is not None:
        verify = [(row.source_url, SiteRedirect(row.source_path, row.target_url, row.status_code))]
        parts = urlsplit(row.source_url)
        homepage = f"{parts.scheme}://{parts.netloc}/"
    else:
        verify = []
        sample = next(iter(_rules_for_site(db, site, sites)), None)
        parts = urlsplit(sample.source_url if sample is not None else site.base_url or "")
        homepage = f"{parts.scheme or 'https'}://{parts.netloc}/"

    with _site_locks_guard:
        lock = _site_locks.setdefault(site.id, threading.Lock())
    with lock:  # one read-modify-write of a site's .htaccess at a time
        try:
            result = sync_site_redirects(
                client,
                rules,
                homepage_url=homepage,
                verify=verify,
                backup=lambda previous: agent_db.create_server_file_backup(
                    site.id, HTACCESS_PATH, "redirect-sync", previous
                ),
            )
        except Exception as exc:  # never let a server hiccup surface as a bare 500
            logger.exception("Redirect sync for site %s crashed", site.id)
            result = SyncResult(False, f"Unexpected error while updating the site: {exc}")

    if row is not None:
        row.sync_status = "synced" if result.ok else "failed"
        row.sync_message = result.message
        row.synced_at = datetime.now()
        db.commit()
        db.refresh(row)
    logger.info(
        "Redirect sync for %s (row %s): ok=%s %s", site.name, row.id if row is not None else None, result.ok, result.message
    )
    return result


def _own_host(request: Request) -> Optional[str]:
    return _normalise_host(urlsplit(str(request.base_url)))


def _validate(
    db: Session, request: Request, source_raw: str, target_raw: str, exclude_id: Optional[int] = None
) -> tuple[str, Optional[str], str, str]:
    source_url, source_host, source_path = _parse_source(source_raw)
    target_url, target_host, target_path = _parse_target(target_raw)
    clash = _find_rule(db, source_host, source_path, exclude_id)
    if clash is not None and clash.source_host == source_host:
        raise HTTPException(status_code=409, detail=f"A redirect for {source_url!r} already exists — edit it instead")
    _check_no_loop(db, source_host, source_path, target_host, target_path, _own_host(request), exclude_id)
    return source_url, source_host, source_path, target_url


@router.get("", response_model=list[RedirectOut])
def list_redirects(request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(UrlRedirect).order_by(UrlRedirect.created_at.desc(), UrlRedirect.id.desc()).all()
    sites = _managed_sites(db)
    return [_to_out(r, request, sites) for r in rows]


@router.post("", response_model=RedirectOut, status_code=201)
def create_redirect(
    payload: RedirectCreate, request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source_url, source_host, source_path, target_url = _validate(db, request, payload.source_url, payload.target_url)
    now = datetime.now()
    row = UrlRedirect(
        source_url=source_url, source_host=source_host, source_path=source_path, target_url=target_url,
        status_code=payload.status_code, hit_count=0, created_by=current_user.id, created_at=now, updated_at=now,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent create of the same source.
        db.rollback()
        raise HTTPException(status_code=409, detail=f"A redirect for {source_url!r} already exists — edit it instead")
    db.refresh(row)
    logger.info("Redirect %d created: %s -> %s (%d)", row.id, source_url, target_url, row.status_code)
    sites = _managed_sites(db)
    site = _match_site(sites, row.source_host)
    if site is not None and row.source_host != _own_host(request):
        _apply_to_site(db, site, sites, row)
    return _to_out(row, request, sites)


@router.put("/{redirect_id}", response_model=RedirectOut)
def update_redirect(
    redirect_id: int, payload: RedirectUpdate, request: Request, db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.query(UrlRedirect).filter(UrlRedirect.id == redirect_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No redirect {redirect_id}")

    source_url, source_host, source_path, target_url = _validate(
        db,
        request,
        payload.source_url if payload.source_url is not None else row.source_url,
        payload.target_url if payload.target_url is not None else row.target_url,
        exclude_id=row.id,
    )
    sites = _managed_sites(db)
    old_site = _match_site(sites, row.source_host)
    if (source_host, source_path) != (row.source_host, row.source_path):
        row.hit_count = 0
        row.last_hit_at = None
    row.source_url, row.source_host, row.source_path, row.target_url = source_url, source_host, source_path, target_url
    if payload.status_code is not None:
        row.status_code = payload.status_code
    row.updated_at = datetime.now()
    row.sync_status, row.sync_message, row.synced_at = None, None, None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"A redirect for {source_url!r} already exists")
    db.refresh(row)

    new_site = _match_site(sites, row.source_host)
    if new_site is not None and row.source_host != _own_host(request):
        _apply_to_site(db, new_site, sites, row)
    if old_site is not None and (new_site is None or old_site.id != new_site.id):
        # The rule moved off this site's domain — take it out of the old .htaccess.
        cleanup = _apply_to_site(db, old_site, sites, None)
        if not cleanup.ok:
            row.sync_message = (
                f"{row.sync_message or ''} (Couldn't remove the old rule from {old_site.name}: {cleanup.message})"
            ).strip()
            db.commit()
            db.refresh(row)
    return _to_out(row, request, sites)


@router.post("/{redirect_id}/apply", response_model=RedirectOut)
def apply_redirect(
    redirect_id: int, request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """(Re-)writes this rule into its site's .htaccess and verifies it live.
    A failed attempt is reported in the returned rule's sync_status/message
    (HTTP 200) so the page can show why and offer a retry."""
    row = db.query(UrlRedirect).filter(UrlRedirect.id == redirect_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No redirect {redirect_id}")
    sites = _managed_sites(db)
    site = _match_site(sites, row.source_host)
    if site is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "This redirect's source is served by this API, not a separate site — nothing to apply."
                if not row.source_host
                else f"No SEO site with server access (FTP/SFTP) matches {row.source_host} — add it in the site's settings first."
            ),
        )
    _apply_to_site(db, site, sites, row)
    return _to_out(row, request, sites)


@router.delete("/{redirect_id}", status_code=204)
def delete_redirect(
    redirect_id: int, request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    row = db.query(UrlRedirect).filter(UrlRedirect.id == redirect_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No redirect {redirect_id}")
    sites = _managed_sites(db)
    site = _match_site(sites, row.source_host)
    if site is not None and row.source_host != _own_host(request):
        # Take it out of the live site first; if that fails keep the rule so
        # it can be retried instead of leaving an orphan redirect on the site.
        result = _apply_to_site(db, site, sites, None, exclude_id=row.id)
        if not result.ok:
            raise HTTPException(
                status_code=502, detail=f"Redirect kept — couldn't remove it from {site.name}: {result.message}"
            )
    db.delete(row)
    db.commit()


@router.post("/{redirect_id}/test", response_model=RedirectTestResult)
def test_redirect(
    redirect_id: int, request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """Requests the rule's live source URL for real (without following the
    redirect) and checks the status code and Location it answers with."""
    row = db.query(UrlRedirect).filter(UrlRedirect.id == redirect_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No redirect {redirect_id}")

    probed_url = row.source_url if row.source_host else str(request.base_url).rstrip("/") + row.source_path
    # A real site may sit behind a CDN/cache — a throwaway query string makes
    # sure the answer comes from the site's current config, not a cached copy.
    request_url = f"{probed_url}{'&' if '?' in probed_url else '?'}wp_redirect_check={int(time.time() * 1000)}"
    try:
        resp = requests.get(
            request_url,
            allow_redirects=False,
            timeout=10,
            headers={"User-Agent": "WorkPulse-Redirect-Test/1.0", TEST_PROBE_HEADER: "1"},
        )
    except requests.RequestException as exc:
        return RedirectTestResult(
            ok=False, probed_url=probed_url, message=f"Could not reach {probed_url}: {type(exc).__name__}"
        )

    location = resp.headers.get("Location")
    if resp.status_code != row.status_code:
        message = f"Expected HTTP {row.status_code} but got HTTP {resp.status_code}"
    elif location is None or not same_url(location, row.target_url):
        message = f"Status is correct but Location is {location!r}, expected {row.target_url!r}"
    else:
        return RedirectTestResult(
            ok=True, probed_url=probed_url, status_code=resp.status_code, location=location,
            message=f"Working — responds HTTP {resp.status_code} to {location}",
        )
    return RedirectTestResult(
        ok=False, probed_url=probed_url, status_code=resp.status_code, location=location, message=message
    )


def _lookup_and_count(host: str, path: str, count_hit: bool = True) -> Optional[tuple[str, int]]:
    db = SessionLocal()
    try:
        row = _find_rule(db, host or None, _normalise_path(path))
        if row is None:
            return None
        target, code = row.target_url, row.status_code
        if count_hit:
            db.query(UrlRedirect).filter(UrlRedirect.id == row.id).update(
                {UrlRedirect.hit_count: UrlRedirect.hit_count + 1, UrlRedirect.last_hit_at: datetime.now()}
            )
            db.commit()
        return target, code
    except Exception:
        # A stats-write hiccup must not turn a valid redirect into an error page.
        logger.exception("Redirect lookup failed for %s%s", host, path)
        db.rollback()
        return None
    finally:
        db.close()


async def serve_redirect(request: Request) -> Optional[Response]:
    """Called from the 404 fallback in api/main.py. Returns the 301/302
    response when a rule matches this request, else None (real 404)."""
    if request.method not in ("GET", "HEAD"):
        return None
    path = request.url.path
    if path == "/" or _is_reserved(path):
        return None

    found = await run_in_threadpool(
        _lookup_and_count, (request.headers.get("host") or "").lower(), path, TEST_PROBE_HEADER.lower() not in request.headers
    )
    if found is None:
        return None
    target, status_code = found

    if request.url.query:
        target += ("&" if "?" in target else "?") + request.url.query
    headers = {}
    if status_code == 302:
        # Temporary means temporary — stop browsers/CDNs holding on to it.
        headers["Cache-Control"] = "no-store"
    return RedirectResponse(url=target, status_code=status_code, headers=headers)
