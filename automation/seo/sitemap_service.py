"""
Sitemap service — runs the generator (sitemap_generator.py), keeps the result,
publishes it to the site's server and tells Google.

What "automatic" means here:
  * Full regeneration once a day (and shortly after the app starts if the last
    one is over a day old — this app is often started by hand, so a fixed
    clock time alone would keep getting missed). The crawl notices new pages
    and changed pages (content hash) and updates <lastmod> accordingly.
  * Instant incremental update when a blog post goes live: the new URL is
    added to the stored list and the files are rebuilt and republished in
    seconds, without re-crawling the whole site.

State is one JSON blob per site in app_settings; the XML files and the entry
list live on disk under <project>/sitemaps/<site_id>/.
"""
import json
import logging
import threading
import urllib.parse
import zipfile
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

from agent import database
from agent.config import LOCAL_DB_PATH
from automation.seo import sitemap_generator as gen
from automation.seo.server_access import client_for_site

logger = logging.getLogger(__name__)

SITEMAP_DIR = Path(LOCAL_DB_PATH).parent / "sitemaps"
STALE_AFTER = timedelta(hours=23)
INCREMENTAL_DEBOUNCE_SECONDS = 20
_WEB_ROOT_CANDIDATES = ("", "/public_html", "/www", "/htdocs", "/public", "/httpdocs")
_ROOT_MARKERS = {"wp-content", "wp-config.php", "index.php", "index.html", "index.htm", ".htaccess", "robots.txt"}

_locks: Dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()
_timers: Dict[int, threading.Timer] = {}
_pending_urls: Dict[int, set] = {}


def _lock_for(site_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(site_id, threading.Lock())


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ── state ──


def _state_key(site_id: int) -> str:
    return f"seo_sitemap_state_{site_id}"


def get_state(site_id: int) -> dict:
    raw = database.get_app_setting(_state_key(site_id))
    state = {"auto_update": True, "status": "idle"}
    if raw:
        try:
            state.update(json.loads(raw))
        except ValueError:
            pass
    # A run can't still be going if this process didn't start it.
    if state.get("status") == "running" and not _lock_for(site_id).locked():
        state["status"] = "idle"
    state["has_files"] = bool(list(_site_dir(site_id).glob("*.xml"))) if _site_dir(site_id).exists() else False
    return state


def _save_state(site_id: int, **changes) -> dict:
    state = get_state(site_id)
    state.pop("has_files", None)
    state.update(changes)
    database.set_app_setting(_state_key(site_id), json.dumps(state))
    return state


def set_auto_update(site_id: int, enabled: bool) -> dict:
    return _save_state(site_id, auto_update=bool(enabled))


# ── storage ──


def _site_dir(site_id: int) -> Path:
    return SITEMAP_DIR / str(site_id)


def _load_entries(site_id: int) -> Dict[str, gen.SitemapEntry]:
    path = _site_dir(site_id) / "entries.json"
    if not path.exists():
        return {}
    try:
        return {gen._key(d["url"]): gen.SitemapEntry.from_json(d) for d in json.loads(path.read_text(encoding="utf-8"))}
    except Exception:
        logger.exception("Could not read stored sitemap entries for site %s — starting fresh", site_id)
        return {}


def _write_outputs(site_id: int, entries: List[gen.SitemapEntry], files: Dict[str, str]) -> None:
    d = _site_dir(site_id)
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.xml"):
        old.unlink()
    for name, xml in files.items():
        (d / name).write_text(xml, encoding="utf-8")
    (d / "entries.json").write_text(json.dumps([e.to_json() for e in entries]), encoding="utf-8")


def read_file(site_id: int, name: str) -> Optional[str]:
    if "/" in name or "\\" in name or not name.endswith(".xml"):
        return None
    path = _site_dir(site_id) / name
    return path.read_text(encoding="utf-8") if path.exists() else None


def zip_files(site_id: int) -> Optional[bytes]:
    d = _site_dir(site_id)
    xmls = sorted(d.glob("*.xml")) if d.exists() else []
    if not xmls:
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in xmls:
            z.write(p, p.name)
    return buf.getvalue()


# ── blog posts published through this app ──


def _blog_entries(site_id: int, base_url: str) -> List[gen.SitemapEntry]:
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT title, cms_post_link, image_url, published_at FROM seo_blog_posts "
        "WHERE site_id = ? AND status = 'live' AND cms_post_link IS NOT NULL AND cms_post_link != ''",
        (site_id,),
    ).fetchall()
    netloc = urllib.parse.urlsplit(base_url).netloc.lower()
    out = []
    for r in rows:
        link = r["cms_post_link"]
        if urllib.parse.urlsplit(link).netloc.lower() != netloc or "?" in link:
            continue  # a draft's ?p=123 preview link isn't a public URL
        out.append(
            gen.SitemapEntry(
                url=link, kind="post", lastmod=gen._to_w3c(r["published_at"]), source="blog",
                images=[r["image_url"]] if r["image_url"] else [],
            )
        )
    return out


# ── publishing ──


def _resolve_remote_dir(client, url_path: str) -> Optional[str]:
    """The directory on the server that the site's URL root maps to."""
    for prefix in _WEB_ROOT_CANDIDATES:
        base = f"{prefix}{url_path}".rstrip("/") or "/"
        try:
            names = {e.name for e in client.list_dir(base)}
        except Exception:
            continue
        if names & _ROOT_MARKERS:
            return base
    return None


def publish(site, files: Dict[str, str], state: dict) -> dict:
    """Writes the files to the site's document root. Returns state changes;
    never raises."""
    client = client_for_site(site)
    if client is None:
        return {"publish_error": "No server access saved for this site — download the files and upload them yourself, "
                                 "or add SFTP/FTP details in Server Access so they can be published automatically."}
    url_path = urllib.parse.urlsplit(site.base_url).path.rstrip("/")
    try:
        remote_dir = state.get("remote_dir") or _resolve_remote_dir(client, url_path)
        if not remote_dir:
            return {"publish_error": "Connected to the server but couldn't find the website's document root "
                                     "(looked for public_html/www/htdocs). Use Download and upload manually."}
        prev_index = None
        try:
            prev_index = client.read_file(f"{remote_dir}/sitemap.xml")
        except Exception:
            pass
        database.create_server_file_backup(site.id, f"{remote_dir}/sitemap.xml", "write", prev_index)
        for name, xml in files.items():
            client.write_file(f"{remote_dir}/{name}", xml)
        for stale in set(state.get("published_files") or []) - set(files):
            try:
                client.delete_file(f"{remote_dir}/{stale}")
            except Exception:
                pass
    except Exception as exc:
        logger.exception("Sitemap publish failed for site %s", site.id)
        return {"publish_error": f"Uploading to the server failed: {exc}"}

    live_url = site.base_url.rstrip("/") + "/sitemap.xml"
    live_ok, live_note = False, None
    try:
        resp = requests.get(live_url, timeout=20, headers={"User-Agent": gen.USER_AGENT})
        live_ok = resp.status_code == 200 and ("<urlset" in resp.text or "<sitemapindex" in resp.text)
        if not live_ok:
            live_note = f"Uploaded, but {live_url} returned HTTP {resp.status_code} — check the document root."
    except requests.RequestException as exc:
        live_note = f"Uploaded, but couldn't load {live_url}: {exc}"
    return {
        "publish_error": live_note, "published_at": _now(), "published_to": remote_dir, "remote_dir": remote_dir,
        "published_files": list(files), "live_verified": live_ok,
    }


def _submit_to_google(site, state: dict) -> dict:
    from api.routes.seo import _effective_gsc_url  # same per-site GSC property rule the manual button uses
    from automation.seo.sitemap_client import submit_sitemap

    gsc = _effective_gsc_url(site)
    if not gsc:
        return {"submit_note": "No Search Console property set for this site, so it wasn't submitted to Google."}
    result = submit_sitemap(gsc, site.base_url.rstrip("/") + "/sitemap.xml")
    return {"submitted_at": _now() if result.ok else state.get("submitted_at"),
            "submit_note": None if result.ok else result.detail}


def _robots_note(site) -> Optional[str]:
    try:
        origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(site.base_url))
        r = requests.get(origin + "/robots.txt", timeout=10, headers={"User-Agent": gen.USER_AGENT})
        if r.status_code == 200 and "sitemap:" not in r.text.lower():
            return "robots.txt doesn't mention the sitemap — add the line: Sitemap: " + site.base_url.rstrip("/") + "/sitemap.xml"
        if r.status_code == 404:
            return "The site has no robots.txt — add one containing: Sitemap: " + site.base_url.rstrip("/") + "/sitemap.xml"
    except requests.RequestException:
        pass
    return None


def _finish(site, entries: List[gen.SitemapEntry], reason: str, started_state: dict) -> dict:
    files = gen.build_files(site.base_url, entries)
    _write_outputs(site.id, entries, files)
    summary = gen.summarize(entries, files)
    state = _save_state(site.id, **summary, generated_at=_now(), last_reason=reason, error=None, message="Publishing…", phase="publishing")
    pub = publish(site, files, state)
    state = _save_state(site.id, **pub)
    sub = _submit_to_google(site, state) if pub.get("published_at") and pub.get("live_verified") else {}
    return _save_state(site.id, **sub, robots_note=_robots_note(site), status="idle", phase=None, message=None)


# ── entry points ──


def generate(site, reason: str = "manual", max_crawl_pages: int = gen.DEFAULT_MAX_CRAWL_PAGES) -> dict:
    """Full regeneration. Blocking — the API runs it in a background thread.
    Returns the final state; never raises."""
    lock = _lock_for(site.id)
    if not lock.acquire(blocking=False):
        return get_state(site.id)
    try:
        _save_state(site.id, status="running", phase="discovering", message="Starting…", error=None, started_at=_now())

        def progress(msg: str) -> None:
            _save_state(site.id, status="running", message=msg)

        previous = _load_entries(site.id)
        try:
            entries = gen.discover(
                site.base_url, _blog_entries(site.id, site.base_url), previous,
                max_crawl_pages=max_crawl_pages, progress=progress,
            )
        except gen.UnsafeUrlError as exc:
            return _save_state(site.id, status="error", error=f"Site URL isn't a public address: {exc}", phase=None, message=None)
        if not entries:
            return _save_state(site.id, status="error", phase=None, message=None,
                               error="No URLs found — the site couldn't be reached. Nothing was changed.")
        return _finish(site, entries, reason, {})
    except Exception as exc:
        logger.exception("Sitemap generation failed for site %s", site.id)
        return _save_state(site.id, status="error", error=str(exc), phase=None, message=None)
    finally:
        lock.release()


def republish(site) -> dict:
    """Uploads the already-generated files again (e.g. after server access was just added)."""
    files = {p.name: p.read_text(encoding="utf-8") for p in _site_dir(site.id).glob("*.xml")} if _site_dir(site.id).exists() else {}
    if not files:
        return _save_state(site.id, publish_error="Nothing generated yet — press Generate first.")
    state = get_state(site.id)
    state.pop("has_files", None)
    pub = publish(site, files, state)
    state = _save_state(site.id, **pub)
    sub = _submit_to_google(site, state) if pub.get("live_verified") else {}
    return _save_state(site.id, **sub)


def touch_urls(site, urls: List[str], reason: str) -> None:
    """Adds/refreshes specific URLs (new blog post, edited page) without a crawl."""
    lock = _lock_for(site.id)
    with lock:
        entries = _load_entries(site.id)
        if not entries:
            return  # nothing generated yet; the first full run will pick these up
        now = _now()
        netloc = urllib.parse.urlsplit(site.base_url).netloc.lower()
        for url in urls:
            if urllib.parse.urlsplit(url).netloc.lower() != netloc or "?" in url:
                continue
            k = gen._key(url)
            cur = entries.get(k)
            if cur:
                cur.lastmod = now
            else:
                entries[k] = gen.SitemapEntry(url=url, kind=gen.classify_url(url) if gen.classify_url(url) != "page" else "post", lastmod=now, source="blog")
        try:
            _finish(site, list(entries.values()), reason, {})
        except Exception:
            logger.exception("Incremental sitemap update failed for site %s", site.id)


def schedule_touch(site_id: int, url: Optional[str], reason: str = "new post") -> None:
    """Called when a post goes live. Debounced so publishing several posts in
    a row causes one rebuild, and runs in its own thread so the publish call
    that triggered it isn't slowed down."""
    if not url:
        return
    if not get_state(site_id).get("auto_update", True):
        return
    with _locks_guard:
        _pending_urls.setdefault(site_id, set()).add(url)
        timer = _timers.get(site_id)
        if timer:
            timer.cancel()
        timer = threading.Timer(INCREMENTAL_DEBOUNCE_SECONDS, _run_pending_touch, args=(site_id, reason))
        timer.daemon = True
        _timers[site_id] = timer
        timer.start()


def _run_pending_touch(site_id: int, reason: str) -> None:
    from api.database import SeoSite, SessionLocal

    with _locks_guard:
        urls = list(_pending_urls.pop(site_id, set()))
    if not urls:
        return
    db = SessionLocal()
    try:
        site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
        if site is not None:
            touch_urls(site, urls, reason)
    finally:
        db.close()


def run_due_sites() -> None:
    """Scheduler hook: full regeneration for every active site with auto-update
    on whose sitemap is missing or older than ~a day."""
    from api.database import SeoSite, SessionLocal

    db = SessionLocal()
    try:
        sites = db.query(SeoSite).filter(SeoSite.is_active == 1).all()
        for site in sites:
            state = get_state(site.id)
            if not state.get("auto_update", True) or state.get("status") == "running":
                continue
            last = state.get("generated_at")
            if not last:
                continue  # never generated here — the user hasn't opted this site in yet
            if last:
                try:
                    if datetime.now(timezone.utc) - datetime.fromisoformat(last) < STALE_AFTER:
                        continue
                except ValueError:
                    pass
            logger.info("Sitemap auto-update starting for site %s", site.id)
            generate(site, reason="scheduled")
    finally:
        db.close()
