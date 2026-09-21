"""Applies URL Redirection rules to a real site's own .htaccess.

api/routes/redirects.py can only answer a redirect itself when the visited
domain points at this API server. A rule like
https://webpays.com/old-page -> https://webpays.com/new-page never reaches
us — the visitor's browser talks to webpays.com's own web server. So for a
domain that has a SEO site with server access (FTP/FTPS/SFTP, see
server_access.py), the rule is written into that site's .htaccess instead.

Everything we write lives between two marker comments, so the rest of the
file — which a human/cPanel/WordPress also edits — is never touched:

    # BEGIN WorkPulse Redirects
    <IfModule mod_alias.c>
    RedirectMatch 301 "^/old-page/?$" "https://example.com/new-page"
    </IfModule>
    # END WorkPulse Redirects

The block is always regenerated from the full rule list (idempotent — applying
twice is a no-op, removing a rule is just applying the shorter list). It goes
at the top of the file so it is read before anything else.

Safety, because a broken .htaccess takes a whole site down (HTTP 500):
  * the previous file content is backed up before writing,
  * afterwards the site's homepage must not have turned into a 5xx and the
    rule must really answer with the expected status/Location, checked with a
    real HTTP request,
  * on any failure the original bytes are written straight back.
The file is handled as raw bytes (latin-1 round-trips every byte), so parts of
it we don't understand are never altered.
"""
import logging
import re
import time
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import unquote, urljoin, urlsplit

import requests

logger = logging.getLogger(__name__)

BEGIN_MARKER = "# BEGIN WorkPulse Redirects"
END_MARKER = "# END WorkPulse Redirects"
HTACCESS_PATH = "/.htaccess"
PROBE_TIMEOUT_SECONDS = 10
PROBE_USER_AGENT = "WorkPulse-Redirect-Verify/1.0"
_REGEX_SPECIALS = re.compile(r"([.^$*+?()\[\]{}|\\])")
_BLOCK_RE = re.compile(
    rf"[ \t]*{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}[ \t]*(?:\r?\n)?", re.DOTALL
)


@dataclass(frozen=True)
class SiteRedirect:
    source_path: str  # normalised: leading "/", no trailing "/"
    target_url: str
    status_code: int  # 301 | 302


@dataclass
class SyncResult:
    ok: bool
    message: str
    changed: bool = False
    proposed_text: Optional[str] = None  # only filled for a dry run


def render_block(rules: list[SiteRedirect], eol: str = "\n") -> str:
    """The marker-delimited block for these rules ("" when there are none)."""
    if not rules:
        return ""
    lines = [BEGIN_MARKER, "<IfModule mod_alias.c>"]
    for rule in sorted(rules, key=lambda r: r.source_path):
        pattern = _REGEX_SPECIALS.sub(r"\\\1", rule.source_path)
        lines.append(f'RedirectMatch {rule.status_code} "^{pattern}/?$" "{rule.target_url}"')
    lines += ["</IfModule>", END_MARKER]
    return eol.join(lines) + eol


def upsert_block(text: str, block: str) -> str:
    """Replaces our existing block, or puts it at the top; an empty `block`
    removes ours entirely. Everything outside the markers is left as-is."""
    if _BLOCK_RE.search(text):
        return _BLOCK_RE.sub(lambda _m: block, text, count=1)
    return block + text if block else text


def _probe(url: str) -> tuple[Optional[int], Optional[str]]:
    """(status, absolute Location) of `url` without following redirects; a
    throwaway query string keeps a CDN from answering out of its cache."""
    sep = "&" if "?" in url else "?"
    resp = requests.get(
        f"{url}{sep}wp_redirect_check={int(time.time() * 1000)}",
        allow_redirects=False,
        timeout=PROBE_TIMEOUT_SECONDS,
        headers={"User-Agent": PROBE_USER_AGENT},
    )
    location = resp.headers.get("Location")
    return resp.status_code, urljoin(url, location) if location else None


def same_url(a: str, b: str) -> bool:
    """Compares two URLs ignoring any query string and a trailing slash."""
    def norm(u: str) -> str:
        p = urlsplit(u)
        return f"{p.scheme}://{p.netloc.lower()}{unquote(p.path).rstrip('/')}"

    return norm(a) == norm(b)


def _verify(rule_urls: list[tuple[str, SiteRedirect]], homepage: str, baseline_home: Optional[int]) -> Optional[str]:
    """None when everything checks out, otherwise a plain-language reason."""
    try:
        home_status, _ = _probe(homepage)
    except requests.RequestException as exc:
        return f"the site stopped answering after the change ({type(exc).__name__})"
    if home_status is not None and home_status >= 500 and (baseline_home is None or baseline_home < 500):
        return f"the site started returning HTTP {home_status} after the change"

    for url, rule in rule_urls:
        last = "no response"
        for attempt in range(2):
            if attempt:
                time.sleep(2)
            try:
                status, location = _probe(url)
            except requests.RequestException as exc:
                last = f"{url} did not answer ({type(exc).__name__})"
                continue
            if status == rule.status_code and location and same_url(location, rule.target_url):
                last = ""
                break
            last = (
                f"{url} answered HTTP {status}" + (f" to {location}" if location else "")
                + f" instead of HTTP {rule.status_code} to {rule.target_url}"
            )
        if last:
            return last
    return None


def sync_site_redirects(
    client,
    rules: list[SiteRedirect],
    *,
    homepage_url: str,
    verify: list[tuple[str, SiteRedirect]],
    backup: Callable[[Optional[str]], Optional[int]],
    dry_run: bool = False,
    htaccess_path: str = HTACCESS_PATH,
) -> SyncResult:
    """Makes the site's .htaccess redirect block equal `rules` and proves it
    works. `verify` is the (live source URL, rule) pairs to check with a real
    request afterwards. `backup` receives the previous file text (None if the
    file didn't exist) and returns a backup id for the failure message."""
    try:
        names = {e.name.rsplit("/", 1)[-1] for e in client.list_dir(htaccess_path.rsplit("/", 1)[0] or "/")}
        existed = htaccess_path.rsplit("/", 1)[-1] in names
        original = client.read_binary_file(htaccess_path) if existed else b""
    except Exception as exc:
        logger.warning("Could not read %s over server access: %s", htaccess_path, exc)
        return SyncResult(False, f"Couldn't read {htaccess_path} on the server: {exc}")

    text = original.decode("latin-1")
    eol = "\r\n" if "\r\n" in text else "\n"
    # The block is UTF-8 (paths/targets may contain non-ASCII); decoding it as
    # latin-1 keeps those bytes intact when the whole text is encoded back.
    block = render_block(rules, eol).encode("utf-8").decode("latin-1")
    new_text = upsert_block(text, block)
    changed = new_text != text

    if dry_run:
        return SyncResult(True, "Dry run — nothing was written.", changed=changed, proposed_text=new_text)

    try:
        baseline_home, _ = _probe(homepage_url)
    except requests.RequestException:
        baseline_home = None

    if not changed:
        problem = _verify(verify, homepage_url, baseline_home)
        if problem:
            return SyncResult(False, f"The redirect is already in {htaccess_path} but doesn't work: {problem}.")
        return SyncResult(True, "Already applied — verified live.", changed=False)

    backup_id = backup(original.decode("utf-8", errors="replace") if existed else None)
    try:
        client.write_binary_file(htaccess_path, new_text.encode("latin-1"))
    except Exception as exc:
        logger.warning("Writing %s failed: %s", htaccess_path, exc)
        return SyncResult(False, f"Couldn't write {htaccess_path} on the server: {exc}")

    problem = _verify(verify, homepage_url, baseline_home)
    if problem is None:
        return SyncResult(True, f"Applied to {htaccess_path} and verified live.", changed=True)

    # Undo — a redirect that doesn't work isn't worth risking the site for.
    try:
        if existed:
            client.write_binary_file(htaccess_path, original)
        else:
            client.delete_file(htaccess_path)
        restored = "The original file was restored."
    except Exception as exc:
        restored = (
            f"WARNING: restoring the original failed ({exc}) — fix {htaccess_path} by hand or restore "
            f"server-file backup #{backup_id} from the SEO Server Files tool."
        )
        logger.error("Redirect rollback failed for %s: %s", htaccess_path, exc)
    hint = ""
    if "instead of" in problem:
        hint = " (This server may not read .htaccess — e.g. it runs nginx — or serves the site from a different folder.)"
    return SyncResult(False, f"Rolled back: {problem}.{hint} {restored}")
