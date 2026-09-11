"""
MODULE 25.5 — SEO Agentic AI: site registry, job-run history, LLM usage
log, and a manual trigger endpoint that exercises the whole module-25
chain (job idempotency tracking + generic LLM provider factory + usage
logging) end-to-end. No real SEO pipeline exists yet — that's module 26
onward; this is the foundation those pipelines will be built on.
"""
import json
import logging
from datetime import date as date_cls, datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from agent import database
from ai.llm.factory import get_provider
from api.config import settings
from ai.seo.og_tag_generator import generate_og_tags
from api.database import (
    LlmUsageLog,
    SeoBacklinkMention,
    SeoBlogPost,
    SeoDailyDigest,
    SeoGa4Page,
    SeoGscQuery,
    SeoIndexingSubmission,
    SeoIndexStatus,
    SeoJobRun,
    SeoOgTags,
    SeoPagespeedResult,
    SeoSemrushMetric,
    SeoServerFileBackup,
    SeoSite,
    SeoSocialPost,
    SeoTechnicalIssue,
    get_db,
)
from api.schemas import (
    BlogGenerateRequest,
    BlogPostOut,
    BlogPostUpdate,
    CmsPostOut,
    CmsStatusOut,
    ContentAnalyzeRequest,
    DigestGenerateRequest,
    DigestOut,
    FaqPairOut,
    FaqRequest,
    Ga4PageRowOut,
    Ga4PullRequest,
    GscPullRequest,
    GscQueryRowOut,
    IndexingSubmissionOut,
    IndexingSubmitRequest,
    IndexStatusOut,
    InterlinkPage,
    InterlinkSuggestRequest,
    LlmUsageLogOut,
    OgTagsGenerateRequest,
    OgTagsOut,
    PageSpeedCheckRequest,
    PageSpeedOpportunityOut,
    PageSpeedResultOut,
    ResourceAuditReportOut,
    RelatedPageOut,
    BacklinkMentionOut,
    BacklinkPullRequest,
    OutreachDraftRequest,
    SeoJobRunOut,
    SeoJobRunTrigger,
    SemrushBacklinkGapRequest,
    SemrushBacklinkRowOut,
    SemrushGapRowOut,
    SemrushMetricsCheckRequest,
    SemrushMetricsOut,
    SemrushReferringDomainOut,
    ServerDirEntryOut,
    ServerFileBackupCreate,
    ServerFileBackupOut,
    ServerFileBackupSummaryOut,
    ServerDirListingOut,
    ServerFileContentOut,
    ServerFileRenameRequest,
    ServerFileWriteRequest,
    SeoSiteCreate,
    SeoSiteCmsConfigUpdate,
    SeoSiteGoogleConfigUpdate,
    SeoSiteOut,
    SeoSiteSshConfigUpdate,
    SshStatusOut,
    SocialGenerateRequest,
    SocialPostOut,
    StructureReportOut,
    TechnicalAuditRequest,
    TechnicalIssueOut,
    TechnicalIssueReview,
    UrlInspectRequest,
)
from ai.seo.blog_content import generate_blog_post
from ai.seo.content_structure import analyze_structure, generate_faq
from ai.seo.daily_digest import generate_daily_digest
from ai.seo.interlink_engine import find_related_pages, index_page
from ai.seo.issue_remediation import generate_fix_value
from ai.seo.outreach_drafter import draft_outreach_email
from ai.seo.social_content import generate_social_post
from automation.seo.backlinks.factory import get_provider as get_backlink_provider
from automation.seo.cms.factory import get_cms_client
from automation.seo.crawler import crawl_site, fetch_sitemap_urls
from automation.seo.ga4_client import fetch_traffic_by_page
from automation.seo.gsc_client import fetch_search_analytics
from automation.seo.indexing_client import fetch_url_inspection, submit_url_for_indexing
from automation.seo.issue_applier import apply_fix as apply_issue_fix
from automation.seo.issue_applier import apply_fix_to_static_file
from automation.seo.pagespeed_client import extract_resource_report, fetch_page_speed
from automation.seo.semrush_client import (
    fetch_backlink_gap as fetch_semrush_backlink_gap,
    fetch_backlinks_list as fetch_semrush_backlinks_list,
    fetch_domain_metrics as fetch_semrush_domain_metrics,
    fetch_referring_domains as fetch_semrush_referring_domains,
)
from automation.seo.server_access import client_for_site as sftp_client_for_site
from automation.seo.slack_notifier import send_slack_message
from automation.seo.social_poster import publish_social_post
from automation.seo.technical_audit import run_all_detectors
from automation.seo.url_safety import UnsafeUrlError, assert_public_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/seo", tags=["seo"])


def _effective_gsc_url(site: SeoSite) -> Optional[str]:
    """.env's GSC_SITE_URL only unambiguously describes 'the one site'
    when there's exactly one active site — see agent.database.
    count_active_seo_sites' docstring for the real bug this guards
    against (a second site silently inheriting the first site's data)."""
    if site.gsc_site_url:
        return site.gsc_site_url
    return settings.GSC_SITE_URL if database.count_active_seo_sites() <= 1 else None


def _effective_ga4_property(site: SeoSite) -> Optional[str]:
    if site.ga4_property_id:
        return site.ga4_property_id
    return settings.GA4_PROPERTY_ID if database.count_active_seo_sites() <= 1 else None


def _cms_client_for(site: SeoSite):
    """Same "fall back to .env only when unambiguous" rule as
    _effective_gsc_url/_effective_ga4_property above — see
    automation/seo/cms/factory.py's module docstring."""
    only_site = database.count_active_seo_sites() <= 1
    return get_cms_client(
        site.cms_type,
        base_url=site.cms_base_url or (settings.WORDPRESS_URL if only_site else None),
        username=site.cms_username or (settings.WORDPRESS_USERNAME if only_site else None),
        app_password=site.cms_app_password or (settings.WORDPRESS_APP_PASSWORD if only_site else None),
        api_token=site.cms_api_token or (settings.WEBFLOW_API_TOKEN if only_site else None),
        collection_id=site.cms_collection_id or (settings.WEBFLOW_COLLECTION_ID if only_site else None),
    )


@router.get("/sites", response_model=list[SeoSiteOut])
def list_sites(db: Session = Depends(get_db)):
    return db.query(SeoSite).order_by(SeoSite.created_at.desc()).all()


@router.post("/sites", response_model=SeoSiteOut, status_code=201)
def create_site(payload: SeoSiteCreate, db: Session = Depends(get_db)):
    try:
        assert_public_url(payload.base_url)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=400, detail=f"Unsafe base_url: {exc}")

    row = SeoSite(
        name=payload.name,
        base_url=payload.base_url,
        cms_type=payload.cms_type,
        cms_base_url=payload.cms_base_url,
        is_active=1,
        created_at=datetime.now(),
        gsc_site_url=payload.gsc_site_url,
        ga4_property_id=payload.ga4_property_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/sites/{site_id}/google-config", response_model=SeoSiteOut)
def update_site_google_config(site_id: int, payload: SeoSiteGoogleConfigUpdate, db: Session = Depends(get_db)):
    """Lets a site's Search Console property / Analytics property be set
    from the UI instead of editing GSC_SITE_URL/GA4_PROPERTY_ID in .env
    and restarting the backend every time a different site needs
    checking. An empty string clears the override back to the .env
    fallback (see gsc_client.py/ga4_client.py/indexing_client.py)."""
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")

    site.gsc_site_url = payload.gsc_site_url or None
    site.ga4_property_id = payload.ga4_property_id or None
    db.commit()
    db.refresh(site)
    return site


@router.patch("/sites/{site_id}/cms-config", response_model=SeoSiteOut)
def update_site_cms_config(site_id: int, payload: SeoSiteCmsConfigUpdate, db: Session = Depends(get_db)):
    """Lets a site's CMS publishing credentials (WordPress URL/username/
    app password, or Webflow API token/collection ID) be set from the
    UI instead of editing WORDPRESS_*/WEBFLOW_* in .env — same pattern as
    /sites/{id}/google-config. An empty string clears cms_base_url/
    cms_username/cms_collection_id back to the .env fallback (those are
    always shown pre-filled, so blank is a real, visible choice to clear
    them). cms_app_password/cms_api_token are different: the UI never
    shows a saved secret back, so it can't pre-fill the field — leaving
    one blank here means "didn't type a new one," not "clear it," and a
    blank submission leaves whatever's already saved untouched. There's
    deliberately no way to clear a saved secret back to the .env fallback
    through this endpoint; replacing it with a new value is the
    supported path, matching how every other secret in this codebase's
    .env is handled (overwritten, not blanked)."""
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")

    # .strip() defensively — a stray leading/trailing space (copy-paste,
    # an accidental keystroke) silently breaks Basic Auth/Bearer auth
    # with a confusing 401, not a validation error, since whitespace is
    # never legitimately part of a real credential.
    site.cms_base_url = (payload.cms_base_url or "").strip() or None
    site.cms_username = (payload.cms_username or "").strip() or None
    site.cms_collection_id = (payload.cms_collection_id or "").strip() or None
    if payload.cms_app_password and payload.cms_app_password.strip():
        site.cms_app_password = payload.cms_app_password.strip()
    if payload.cms_api_token and payload.cms_api_token.strip():
        site.cms_api_token = payload.cms_api_token.strip()
    db.commit()
    db.refresh(site)
    return site


@router.patch("/sites/{site_id}/ssh-config", response_model=SeoSiteOut)
def update_site_ssh_config(site_id: int, payload: SeoSiteSshConfigUpdate, db: Session = Depends(get_db)):
    """Direct server access (SFTP, FTP, or FTPS), for the files a CMS REST
    API can't reach (wp-content/mu-plugins/*.php, .htaccess). Same
    blank-clears/blank-keeps split as update_site_cms_config above."""
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")

    site.ssh_host = (payload.ssh_host or "").strip() or None
    site.ssh_port = (payload.ssh_port or "").strip() or None
    site.ssh_username = (payload.ssh_username or "").strip() or None
    site.ssh_protocol = (payload.ssh_protocol or "").strip().lower() or None
    if payload.ssh_password and payload.ssh_password.strip():
        site.ssh_password = payload.ssh_password.strip()
    db.commit()
    db.refresh(site)
    return site


@router.get("/sites/{site_id}/ssh-status", response_model=SshStatusOut)
def ssh_status(site_id: int, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")
    client = sftp_client_for_site(site)
    if client is None:
        return SshStatusOut(site_id=site_id, reachable=False, error="No SSH credentials saved for this site yet.")
    reachable, error = client.is_reachable()
    return SshStatusOut(site_id=site_id, reachable=reachable, error=error)


def _server_client_or_400(site: SeoSite):
    client = sftp_client_for_site(site)
    if client is None:
        raise HTTPException(status_code=400, detail="No server access credentials saved for this site yet.")
    return client


def _site_or_404(site_id: int, db: Session) -> SeoSite:
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")
    return site


@router.get("/server/list", response_model=ServerDirListingOut)
def server_list_dir(site_id: int, path: str, db: Session = Depends(get_db)):
    site = _site_or_404(site_id, db)
    client = _server_client_or_400(site)
    try:
        entries = client.list_dir(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Directory list failed: {exc}")
    return ServerDirListingOut(
        path=path,
        entries=[ServerDirEntryOut(name=e.name, is_dir=e.is_dir, size=e.size) for e in entries],
    )


@router.get("/server/file", response_model=ServerFileContentOut)
def server_read_file(site_id: int, path: str, db: Session = Depends(get_db)):
    site = _site_or_404(site_id, db)
    client = _server_client_or_400(site)
    try:
        content = client.read_file(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"File read failed: {exc}")
    return ServerFileContentOut(path=path, content=content)


def _backup_current_state(client, site_id: int, path: str, action: str, new_path: Optional[str] = None) -> None:
    """Snapshots whatever's at `path` right now, before a write/rename/
    delete changes or removes it. content=None (file didn't exist yet,
    or couldn't be read) is recorded as-is — a real, honest state, not
    an error; there's simply nothing to restore for that entry."""
    try:
        previous = client.read_file(path)
    except Exception:
        previous = None
    database.create_server_file_backup(site_id, path, action, previous, new_path=new_path)


@router.put("/server/file", response_model=ServerFileContentOut)
def server_write_file(payload: ServerFileWriteRequest, db: Session = Depends(get_db)):
    site = _site_or_404(payload.site_id, db)
    client = _server_client_or_400(site)
    _backup_current_state(client, payload.site_id, payload.path, "write")
    try:
        client.write_file(payload.path, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"File write failed: {exc}")
    return ServerFileContentOut(path=payload.path, content=payload.content)


@router.post("/server/rename", status_code=204)
def server_rename_file(payload: ServerFileRenameRequest, db: Session = Depends(get_db)):
    site = _site_or_404(payload.site_id, db)
    client = _server_client_or_400(site)
    _backup_current_state(client, payload.site_id, payload.path, "rename", new_path=payload.new_path)
    try:
        client.rename_file(payload.path, payload.new_path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"File rename failed: {exc}")


@router.delete("/server/file", status_code=204)
def server_delete_file(site_id: int, path: str, db: Session = Depends(get_db)):
    site = _site_or_404(site_id, db)
    client = _server_client_or_400(site)
    _backup_current_state(client, site_id, path, "delete")
    try:
        client.delete_file(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"File delete failed: {exc}")


@router.post("/server/backups", response_model=ServerFileBackupSummaryOut, status_code=201)
def create_server_file_backup_route(payload: ServerFileBackupCreate, db: Session = Depends(get_db)):
    """Lets the frontend record a backup the moment editing actually
    starts (the first real keystroke), not only at save time — so the
    original content is protected server-side even if the browser
    closes before Save is ever clicked. action='edit-start'
    distinguishes this from the write/rename/delete backups
    _backup_current_state creates automatically on an actual mutation."""
    _site_or_404(payload.site_id, db)
    backup_id = database.create_server_file_backup(payload.site_id, payload.path, "edit-start", payload.content)
    db.expire_all()
    return db.query(SeoServerFileBackup).filter(SeoServerFileBackup.id == backup_id).first()


@router.get("/server/backups", response_model=list[ServerFileBackupSummaryOut])
def list_server_file_backups_route(site_id: int, path: str, limit: int = 50, db: Session = Depends(get_db)):
    _site_or_404(site_id, db)
    return (
        db.query(SeoServerFileBackup)
        .filter(SeoServerFileBackup.site_id == site_id, SeoServerFileBackup.path == path)
        # id DESC as a tiebreaker — see list_server_file_backups in
        # agent/database.py for why created_at alone isn't reliable.
        .order_by(SeoServerFileBackup.created_at.desc(), SeoServerFileBackup.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/server/backups/{backup_id}", response_model=ServerFileBackupOut)
def get_server_file_backup_route(backup_id: int, db: Session = Depends(get_db)):
    row = db.query(SeoServerFileBackup).filter(SeoServerFileBackup.id == backup_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No backup {backup_id}")
    return row


@router.post("/server/backups/{backup_id}/restore", response_model=ServerFileContentOut)
def restore_server_file_backup_route(backup_id: int, db: Session = Depends(get_db)):
    """Writes a backup's content back to its original path. Itself
    creates a fresh backup of whatever was there immediately before the
    restore, same as any other write — restoring is undoable too, not a
    one-way door."""
    row = db.query(SeoServerFileBackup).filter(SeoServerFileBackup.id == backup_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No backup {backup_id}")
    if row.content is None:
        raise HTTPException(status_code=409, detail="This backup has no stored content to restore")

    site = _site_or_404(row.site_id, db)
    client = _server_client_or_400(site)
    _backup_current_state(client, row.site_id, row.path, "write")
    try:
        client.write_file(row.path, row.content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Restore failed: {exc}")
    return ServerFileContentOut(path=row.path, content=row.content)


@router.get("/jobs", response_model=list[SeoJobRunOut])
def list_jobs(site_id: Optional[int] = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(SeoJobRun)
    if site_id is not None:
        query = query.filter(SeoJobRun.site_id == site_id)
    return query.order_by(SeoJobRun.started_at.desc()).limit(limit).all()


@router.get("/llm-usage", response_model=list[LlmUsageLogOut])
def list_llm_usage(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(LlmUsageLog).order_by(LlmUsageLog.created_at.desc()).limit(limit).all()


@router.get("/cms/status", response_model=CmsStatusOut)
def cms_status(site_id: int, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")
    client = _cms_client_for(site)
    return CmsStatusOut(site_id=site_id, cms_type=site.cms_type, reachable=client.is_reachable())


@router.get("/cms/posts", response_model=list[CmsPostOut])
def cms_posts(site_id: int, status: str = "publish", db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")
    client = _cms_client_for(site)
    return client.list_posts(status=status)


@router.post("/semrush/check", response_model=SemrushMetricsOut, status_code=201)
def check_semrush_metrics(payload: SemrushMetricsCheckRequest, db: Session = Depends(get_db)):
    """Pulls Authority Score, organic/paid keywords, organic traffic,
    referring domains, and backlinks count for this site's domain — see
    automation/seo/semrush_client.py for why this is its own client/table
    rather than a BacklinkProvider, and why it's not a free call (spends
    real purchased Semrush API units)."""
    site = _site_or_404(payload.site_id, db)
    domain = urlparse(site.base_url).netloc or site.base_url
    metrics = fetch_semrush_domain_metrics(domain)
    if metrics is None:
        raise HTTPException(
            status_code=502,
            detail="Semrush fetch failed — check SEMRUSH_API_KEY is set and the account has API units left (see server logs).",
        )

    run_date = date_cls.today()
    database.upsert_semrush_metrics(
        site_id=payload.site_id,
        run_date=run_date,
        authority_score=metrics.authority_score,
        organic_traffic=metrics.organic_traffic,
        organic_keywords=metrics.organic_keywords,
        paid_keywords=metrics.paid_keywords,
        referring_domains=metrics.referring_domains,
        backlinks_total=metrics.backlinks_total,
        raw_json=json.dumps(metrics.raw),
        semrush_rank=metrics.semrush_rank,
    )

    db.expire_all()  # written through agent.database's raw connection, not this session
    row = (
        db.query(SeoSemrushMetric)
        .filter(SeoSemrushMetric.site_id == payload.site_id, SeoSemrushMetric.run_date == run_date)
        .first()
    )
    return row


@router.get("/semrush", response_model=list[SemrushMetricsOut])
def list_semrush_metrics(site_id: int, limit: int = 30, db: Session = Depends(get_db)):
    return (
        db.query(SeoSemrushMetric)
        .filter(SeoSemrushMetric.site_id == site_id)
        .order_by(SeoSemrushMetric.run_date.desc(), SeoSemrushMetric.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/semrush/backlinks", response_model=list[SemrushBacklinkRowOut])
def semrush_backlinks(site_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """On-demand, not persisted — a live proxy onto Semrush's `backlinks`
    report, same as /cms/posts proxies the CMS rather than storing a copy.
    Unit cost scales with rows returned (display_limit caps it)."""
    site = _site_or_404(site_id, db)
    domain = urlparse(site.base_url).netloc or site.base_url
    return fetch_semrush_backlinks_list(domain, limit=limit)


@router.get("/semrush/referring-domains", response_model=list[SemrushReferringDomainOut])
def semrush_referring_domains(site_id: int, limit: int = 50, db: Session = Depends(get_db)):
    site = _site_or_404(site_id, db)
    domain = urlparse(site.base_url).netloc or site.base_url
    return fetch_semrush_referring_domains(domain, limit=limit)


@router.post("/semrush/backlink-gap", response_model=list[SemrushGapRowOut])
def semrush_backlink_gap(payload: SemrushBacklinkGapRequest, db: Session = Depends(get_db)):
    """This site vs one or more competitor domains, aggregate backlink
    stats side by side (Semrush's `backlinks_comparison` report) — see
    automation/seo/semrush_client.fetch_backlink_gap's docstring for how
    this differs from Semrush's own richer Backlink Gap UI."""
    site = _site_or_404(payload.site_id, db)
    domain = urlparse(site.base_url).netloc or site.base_url
    targets = [domain, *[d.strip() for d in payload.competitor_domains if d.strip()]]
    return fetch_semrush_backlink_gap(targets)


@router.post("/pagespeed/check", response_model=PageSpeedResultOut, status_code=201)
def check_pagespeed(payload: PageSpeedCheckRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    result = fetch_page_speed(payload.url, strategy=payload.strategy)
    if result is None:
        raise HTTPException(status_code=502, detail="PageSpeed Insights fetch failed — see server logs")

    run_date = date_cls.today()
    database.upsert_pagespeed_result(
        site_id=payload.site_id,
        url=result.url,
        strategy=result.strategy,
        run_date=run_date,
        performance_score=result.performance_score,
        lcp_ms=result.lcp_ms,
        cls=result.cls,
        inp_ms=result.inp_ms,
        ttfb_ms=result.ttfb_ms,
        fcp_ms=result.fcp_ms,
        raw_json=json.dumps(result.raw),
    )

    db.expire_all()  # written through agent.database's raw connection, not this session
    row = (
        db.query(SeoPagespeedResult)
        .filter(
            SeoPagespeedResult.site_id == payload.site_id,
            SeoPagespeedResult.url == result.url,
            SeoPagespeedResult.strategy == result.strategy,
            SeoPagespeedResult.run_date == run_date,
        )
        .first()
    )
    return row


@router.get("/pagespeed", response_model=list[PageSpeedResultOut])
def list_pagespeed(site_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(SeoPagespeedResult)
        .filter(SeoPagespeedResult.site_id == site_id)
        .order_by(SeoPagespeedResult.run_date.desc(), SeoPagespeedResult.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/pagespeed/{result_id}/opportunities", response_model=ResourceAuditReportOut)
def pagespeed_opportunities(result_id: int, db: Session = Depends(get_db)):
    """Parses the fuller resource audit (request counts, total page
    weight, unused CSS/JS, a prioritized fix list) out of raw_json already
    stored by a prior /pagespeed/check call — no second PageSpeed API
    call, see automation.seo.pagespeed_client.extract_resource_report."""
    row = db.query(SeoPagespeedResult).filter(SeoPagespeedResult.id == result_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No PageSpeed result {result_id}")
    if not row.raw_json:
        raise HTTPException(status_code=404, detail=f"PageSpeed result {result_id} has no stored raw response")

    raw = json.loads(row.raw_json)
    report = extract_resource_report(raw)
    return ResourceAuditReportOut(
        total_requests=report.total_requests,
        total_byte_weight_kb=report.total_byte_weight_kb,
        unused_css_kb=report.unused_css_kb,
        unused_js_kb=report.unused_js_kb,
        render_blocking_requests=report.render_blocking_requests,
        opportunities=[
            PageSpeedOpportunityOut(
                audit_id=o.audit_id,
                title=o.title,
                description=o.description,
                savings_ms=o.savings_ms,
                savings_bytes=o.savings_bytes,
            )
            for o in report.opportunities
        ],
    )


@router.post("/gsc/pull", response_model=list[GscQueryRowOut], status_code=201)
def pull_gsc(payload: GscPullRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    end_date = date_cls.today()
    start_date = end_date - timedelta(days=payload.days_back)
    rows = fetch_search_analytics(start_date, end_date, site_url=_effective_gsc_url(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GSC fetch failed — see server logs")

    database.upsert_gsc_query_rows(payload.site_id, end_date, rows)

    db.expire_all()
    return (
        db.query(SeoGscQuery)
        .filter(SeoGscQuery.site_id == payload.site_id, SeoGscQuery.run_date == end_date)
        .order_by(SeoGscQuery.clicks.desc())
        .all()
    )


@router.get("/gsc", response_model=list[GscQueryRowOut])
def list_gsc(site_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SeoGscQuery)
        .filter(SeoGscQuery.site_id == site_id)
        .order_by(SeoGscQuery.run_date.desc(), SeoGscQuery.clicks.desc())
        .limit(limit)
        .all()
    )


@router.post("/ga4/pull", response_model=list[Ga4PageRowOut], status_code=201)
def pull_ga4(payload: Ga4PullRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    rows = fetch_traffic_by_page(payload.start_date, payload.end_date, property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 fetch failed — see server logs")

    run_date = date_cls.today()
    database.upsert_ga4_page_rows(payload.site_id, run_date, rows)

    db.expire_all()
    return (
        db.query(SeoGa4Page)
        .filter(SeoGa4Page.site_id == payload.site_id, SeoGa4Page.run_date == run_date)
        .order_by(SeoGa4Page.sessions.desc())
        .all()
    )


@router.get("/ga4", response_model=list[Ga4PageRowOut])
def list_ga4(site_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SeoGa4Page)
        .filter(SeoGa4Page.site_id == site_id)
        .order_by(SeoGa4Page.run_date.desc(), SeoGa4Page.sessions.desc())
        .limit(limit)
        .all()
    )


@router.post("/indexing/inspect", response_model=IndexStatusOut, status_code=201)
def inspect_url_route(payload: UrlInspectRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    result = fetch_url_inspection(payload.url, site_url=_effective_gsc_url(site))
    if result is None:
        raise HTTPException(status_code=502, detail="URL Inspection API call failed — see server logs")

    database.upsert_index_status(payload.site_id, payload.url, result)

    db.expire_all()
    return (
        db.query(SeoIndexStatus)
        .filter(SeoIndexStatus.site_id == payload.site_id, SeoIndexStatus.url == payload.url)
        .first()
    )


@router.get("/indexing/status", response_model=list[IndexStatusOut])
def list_index_status_route(site_id: int, limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(SeoIndexStatus)
        .filter(SeoIndexStatus.site_id == site_id)
        .order_by(SeoIndexStatus.checked_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/indexing/submit", response_model=IndexingSubmissionOut, status_code=201)
def submit_for_indexing_route(payload: IndexingSubmitRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    result = submit_url_for_indexing(payload.url, payload.notification_type)
    submission_id = database.save_indexing_submission(
        payload.site_id,
        payload.url,
        payload.notification_type,
        result.ok,
        json.dumps(result.raw) if result.raw is not None else None,
        result.error,
    )

    db.expire_all()
    return db.query(SeoIndexingSubmission).filter(SeoIndexingSubmission.id == submission_id).first()


@router.get("/indexing/submissions", response_model=list[IndexingSubmissionOut])
def list_indexing_submissions_route(site_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SeoIndexingSubmission)
        .filter(SeoIndexingSubmission.site_id == site_id)
        .order_by(SeoIndexingSubmission.submitted_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/og-tags/generate", response_model=OgTagsOut, status_code=201)
def generate_og_tags_route(payload: OgTagsGenerateRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    tags = generate_og_tags(payload.page_title, payload.content_excerpt, site_id=payload.site_id)
    if tags is None:
        raise HTTPException(status_code=502, detail="OG tag generation failed — see server logs")

    database.upsert_og_tags(
        payload.site_id, payload.page_url, payload.page_title, tags.og_title, tags.og_description
    )

    db.expire_all()
    row = (
        db.query(SeoOgTags)
        .filter(SeoOgTags.site_id == payload.site_id, SeoOgTags.page_url == payload.page_url)
        .first()
    )
    return row


@router.get("/og-tags", response_model=list[OgTagsOut])
def list_og_tags_route(site_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SeoOgTags)
        .filter(SeoOgTags.site_id == site_id)
        .order_by(SeoOgTags.generated_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/interlinks/index", status_code=201)
def index_page_route(payload: InterlinkPage, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    ok = index_page(payload.site_id, payload.url, payload.title, payload.content)
    if not ok:
        raise HTTPException(status_code=502, detail="Indexing failed — see server logs")
    return {"indexed": True, "url": payload.url}


@router.post("/interlinks/suggest", response_model=list[RelatedPageOut])
def suggest_interlinks_route(payload: InterlinkSuggestRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    return find_related_pages(
        payload.site_id, payload.url, payload.title, payload.content, n_results=payload.n_results
    )


@router.post("/content/analyze", response_model=StructureReportOut)
def analyze_content_route(payload: ContentAnalyzeRequest):
    report = analyze_structure(
        payload.content_html,
        primary_keyword=payload.primary_keyword,
        min_words=payload.min_words,
        max_words=payload.max_words,
    )
    return StructureReportOut(
        word_count=report.word_count,
        h1_count=report.h1_count,
        h2_count=report.h2_count,
        h3_count=report.h3_count,
        passed=report.passed,
        issues=[{"rule": i.rule, "severity": i.severity, "message": i.message} for i in report.issues],
    )


@router.post("/content/faq", response_model=list[FaqPairOut])
def generate_faq_route(payload: FaqRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    # Seeds the FAQ with this site's own real GSC search queries (module
    # 26.5) rather than requiring the caller to supply them — the
    # blueprint's "GSC query data" half of this feature, ties module 26's
    # data directly into module 27's content pipeline.
    gsc_rows = database.list_gsc_queries(payload.site_id, limit=15)
    seed_queries = [row["query"] for row in gsc_rows]

    faqs = generate_faq(payload.page_title, seed_queries, site_id=payload.site_id, max_pairs=payload.max_pairs)
    if faqs is None:
        raise HTTPException(status_code=502, detail="FAQ generation failed — see server logs")
    return faqs


@router.post("/technical/audit", response_model=list[TechnicalIssueOut], status_code=201)
def run_technical_audit_route(payload: TechnicalAuditRequest, db: Session = Depends(get_db)):
    """Synchronous by design (like the pagespeed/gsc/ga4 pull endpoints)
    — a real crawl of `max_pages` pages takes real time (politely
    rate-limited, see crawler.CRAWL_DELAY_SECONDS). Scheduling this as a
    background job through seo_job_runs belongs to a future module once
    ai/seo_master_agent.py grows a technical-audit pipeline node; this is
    the manual-trigger proof the detection logic itself works end-to-end."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    pages = crawl_site(site.base_url, max_pages=payload.max_pages)
    if not pages:
        raise HTTPException(status_code=502, detail="Crawl failed — see server logs")

    known_urls = fetch_sitemap_urls(site.base_url)
    issues = run_all_detectors(pages, known_urls=known_urls, base_url=site.base_url)

    run_date = date_cls.today()
    database.upsert_technical_issues(payload.site_id, run_date, issues)

    db.expire_all()
    return (
        db.query(SeoTechnicalIssue)
        .filter(SeoTechnicalIssue.site_id == payload.site_id)
        .order_by(SeoTechnicalIssue.severity.asc(), SeoTechnicalIssue.created_at.desc())
        .all()
    )


@router.get("/technical/issues", response_model=list[TechnicalIssueOut])
def list_technical_issues_route(
    site_id: int, status: Optional[str] = None, limit: int = 1000, db: Session = Depends(get_db)
):
    query = db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.site_id == site_id)
    if status is not None:
        query = query.filter(SeoTechnicalIssue.status == status)
    # Plain .asc() on the severity string sorts "critical" < "info" <
    # "warning" alphabetically — backwards from actual importance, and a
    # real bug: on a site with hundreds of low-value 'info' issues (e.g.
    # orphaned_page), those alphabetically beat every 'warning' issue for
    # a spot within the row limit, silently burying real, fixable
    # warnings (missing_meta_description, missing_canonical) off the end
    # of the list. This explicit rank fixes the order to what the
    # severity name actually means.
    severity_rank = case((SeoTechnicalIssue.severity == "critical", 0), (SeoTechnicalIssue.severity == "warning", 1), else_=2)
    return query.order_by(severity_rank, SeoTechnicalIssue.created_at.desc()).limit(limit).all()


@router.post("/technical/issues/{issue_id}/approve", response_model=TechnicalIssueOut)
def approve_technical_issue_route(issue_id: int, payload: TechnicalIssueReview, db: Session = Depends(get_db)):
    ok = database.set_technical_issue_status(issue_id, "approved", payload.reviewed_by)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")
    db.expire_all()
    return db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()


@router.post("/technical/issues/{issue_id}/reject", response_model=TechnicalIssueOut)
def reject_technical_issue_route(issue_id: int, payload: TechnicalIssueReview, db: Session = Depends(get_db)):
    ok = database.set_technical_issue_status(issue_id, "rejected", payload.reviewed_by)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")
    db.expire_all()
    return db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()


@router.post("/technical/issues/{issue_id}/generate-fix", response_model=TechnicalIssueOut)
def generate_technical_issue_fix_route(issue_id: int, db: Session = Depends(get_db)):
    """Module 35 — produces a real, ready-to-use replacement value (not
    just advice text) for the small set of rules where one is knowable
    at all. Read-only against the live site plus one LLM call; never
    writes anything — see /apply-fix for that, which additionally
    requires the issue to be approved first."""
    row = db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")

    result = generate_fix_value(row.rule, row.url, row.message, site_id=row.site_id)
    if result.value is None:
        raise HTTPException(status_code=422, detail=result.error or "Could not generate a fix for this issue")

    database.save_technical_issue_fix_value(issue_id, result.value)
    db.expire_all()
    return db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()


@router.post("/technical/issues/{issue_id}/apply-fix", response_model=TechnicalIssueOut)
def apply_technical_issue_fix_route(issue_id: int, db: Session = Depends(get_db)):
    """Writes the generated fix_value to the real CMS post — the one
    action in this whole feature that touches the live site. Requires
    the issue to already be 'approved' (the human checkpoint) and a
    fix_value to already exist (call /generate-fix first). Always
    re-reads the post afterward to confirm the write actually took —
    see automation/seo/issue_applier.py for why that check exists."""
    row = db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")
    if row.status != "approved":
        raise HTTPException(status_code=409, detail=f"Issue must be approved first (current status: {row.status})")
    if not row.fix_value:
        raise HTTPException(status_code=409, detail="No fix value generated yet — call generate-fix first")

    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")

    client = _cms_client_for(site)
    result = apply_issue_fix(client, row.rule, row.url, row.fix_value)
    if not result.ok and result.not_found:
        # No CMS post/page backs this URL at all — a real, verified case
        # (webpays.com's landing pages are static files, not WP content),
        # not just a fallback-of-last-resort. Try editing the file
        # directly if this site has Server Access credentials saved.
        server_client = sftp_client_for_site(site)
        if server_client is not None:
            result = apply_fix_to_static_file(server_client, row.url, row.rule, row.fix_value)
    if result.ok:
        database.mark_technical_issue_fix_applied(issue_id)
    else:
        database.mark_technical_issue_fix_failed(issue_id, result.detail)

    db.expire_all()
    return db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()


@router.post("/digest/generate", response_model=DigestOut, status_code=201)
def generate_digest_route(payload: DigestGenerateRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    digest = generate_daily_digest(payload.site_id, site.name)
    stats_json = json.dumps(
        {
            "pending_issues": digest.stats.pending_issues,
            "critical_issues": digest.stats.critical_issues,
            "latest_performance_score": digest.stats.latest_performance_score,
            "top_gsc_queries": digest.stats.top_gsc_queries,
            "top_ga4_pages": digest.stats.top_ga4_pages,
            "recent_job_failures": digest.stats.recent_job_failures,
        }
    )

    slack_delivered = False
    if payload.send_to_slack:
        slack_delivered = send_slack_message(f"*SEO Digest — {site.name}*\n{digest.narrative}")

    database.save_daily_digest(payload.site_id, date_cls.today(), digest.narrative, stats_json, slack_delivered)

    db.expire_all()
    return (
        db.query(SeoDailyDigest)
        .filter(SeoDailyDigest.site_id == payload.site_id, SeoDailyDigest.run_date == date_cls.today())
        .first()
    )


@router.get("/digest", response_model=list[DigestOut])
def list_digests_route(site_id: int, limit: int = 30, db: Session = Depends(get_db)):
    return (
        db.query(SeoDailyDigest)
        .filter(SeoDailyDigest.site_id == site_id)
        .order_by(SeoDailyDigest.run_date.desc())
        .limit(limit)
        .all()
    )


@router.post("/social/generate", response_model=list[SocialPostOut], status_code=201)
def generate_social_posts_route(payload: SocialGenerateRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    created_ids = []
    for platform in payload.platforms:
        draft = generate_social_post(platform, payload.page_title, payload.content_excerpt, site_id=payload.site_id)
        if draft is None:
            continue  # one platform failing shouldn't fail the whole batch
        post_id = database.create_social_post(
            payload.site_id, platform, draft.content, payload.source_url, payload.image_url
        )
        created_ids.append(post_id)

    if not created_ids:
        raise HTTPException(status_code=502, detail="Social content generation failed for every requested platform")

    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id.in_(created_ids)).all()


@router.get("/social", response_model=list[SocialPostOut])
def list_social_posts_route(site_id: int, status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(SeoSocialPost).filter(SeoSocialPost.site_id == site_id)
    if status is not None:
        query = query.filter(SeoSocialPost.status == status)
    return query.order_by(SeoSocialPost.created_at.desc()).limit(limit).all()


@router.post("/social/{post_id}/approve", response_model=SocialPostOut)
def approve_social_post_route(post_id: int, db: Session = Depends(get_db)):
    ok = database.set_social_post_status(post_id, "approved")
    if not ok:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.post("/social/{post_id}/reject", response_model=SocialPostOut)
def reject_social_post_route(post_id: int, db: Session = Depends(get_db)):
    ok = database.set_social_post_status(post_id, "rejected")
    if not ok:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.post("/social/{post_id}/publish", response_model=SocialPostOut)
def publish_social_post_route(post_id: int, db: Session = Depends(get_db)):
    row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    # 'failed' is retryable without a fresh approval, same reasoning as
    # publish_blog_post_route: a publish failure here is typically
    # transient (a LinkedIn selector/timing hiccup), not a reason to make
    # a human re-approve content they already approved once.
    if row.status not in ("approved", "failed"):
        raise HTTPException(status_code=409, detail=f"Post must be approved first (current status: {row.status})")

    result = publish_social_post(row.platform, row.content, image_url=row.image_url)
    if result.ok:
        database.mark_social_post_posted(post_id, result.external_post_id)
    else:
        database.mark_social_post_failed(post_id, result.detail)

    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.post("/backlinks/pull", response_model=list[BacklinkMentionOut], status_code=201)
def pull_backlinks_route(payload: BacklinkPullRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    provider = get_backlink_provider()
    mentions = provider.fetch_mentions()
    database.upsert_backlink_mentions(payload.site_id, mentions)

    db.expire_all()
    return (
        db.query(SeoBacklinkMention)
        .filter(SeoBacklinkMention.site_id == payload.site_id)
        .order_by(SeoBacklinkMention.created_at.desc())
        .all()
    )


@router.get("/backlinks", response_model=list[BacklinkMentionOut])
def list_backlinks_route(site_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SeoBacklinkMention)
        .filter(SeoBacklinkMention.site_id == site_id)
        .order_by(SeoBacklinkMention.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/backlinks/{mention_id}/draft-outreach", response_model=BacklinkMentionOut)
def draft_outreach_route(mention_id: int, payload: OutreachDraftRequest, db: Session = Depends(get_db)):
    mention = db.query(SeoBacklinkMention).filter(SeoBacklinkMention.id == mention_id).first()
    if mention is None:
        raise HTTPException(status_code=404, detail=f"No backlink mention {mention_id}")

    draft = draft_outreach_email(
        mention.source_url, mention.source_title, payload.site_name, payload.site_url, site_id=mention.site_id
    )
    if draft is None:
        raise HTTPException(status_code=502, detail="Outreach email drafting failed — see server logs")

    database.save_outreach_draft(mention_id, draft.subject, draft.body)
    db.expire_all()
    return db.query(SeoBacklinkMention).filter(SeoBacklinkMention.id == mention_id).first()


@router.post("/jobs/trigger", response_model=SeoJobRunOut, status_code=201)
def trigger_job(payload: SeoJobRunTrigger, db: Session = Depends(get_db)):
    """Manual trigger for testing the module-25 plumbing end-to-end —
    there's no real SEO pipeline behind job_type yet (module 26+ adds
    those), so this proves idempotent job tracking, the generic LLM
    provider factory, and automatic usage logging all work together
    before any pipeline is built on top of them."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    run_id = database.start_job_run(payload.site_id, payload.job_type, date_cls.today())
    if run_id is None:
        raise HTTPException(
            status_code=409,
            detail=f"A run already exists for site {payload.site_id}, job_type "
            f"{payload.job_type!r}, today",
        )

    provider = get_provider(task=payload.job_type, site_id=payload.site_id)
    result = provider.generate("Reply with exactly the word: OK")
    if result.ok:
        database.finish_job_run(run_id, "success")
    else:
        database.finish_job_run(run_id, "failed", error=result.error)

    db.expire_all()  # the row above was written through agent.database's raw connection
    row = db.query(SeoJobRun).filter(SeoJobRun.id == run_id).first()
    return row


@router.post("/jobs/run-daily-cycle")
def run_daily_cycle_now():
    """Module 33's real automated pipeline (technical audit -> GSC ->
    GA4 -> PageSpeed -> digest, per active site) normally fires on its
    own once a day via api/main.py's BackgroundScheduler. This lets it
    be run on demand — for testing, or to force today's cycle again
    without waiting for the scheduled hour — calling the exact same
    function the scheduler calls, so there's no separate code path to
    drift out of sync. Each step is independently idempotent (seo_
    job_runs' UNIQUE(site_id, job_type, run_date)), so calling this after
    the scheduled run already completed today just reports everything as
    already-done rather than re-running or erroring."""
    from ai.seo_master_agent import run_daily_cycle_for_all_sites

    results = run_daily_cycle_for_all_sites()
    return [
        {
            "site_id": state["site"]["id"],
            "site_name": state["site"]["name"],
            "completed": state["completed_tasks"],
            "failed": state["failed_tasks"],
            "report": state["final_report"],
        }
        for state in results
    ]


@router.post("/blog/generate", response_model=BlogPostOut, status_code=201)
def generate_blog_post_route(payload: BlogGenerateRequest, db: Session = Depends(get_db)):
    """Generates a full blog post draft, immediately runs it through
    module 27.5's own structure checker (analyze_structure) so a
    reviewer sees the H1/word-count/keyword findings right alongside the
    draft rather than as a separate manual step, and stores it as
    'draft' — no CMS call happens here. See /blog/{id}/publish for what
    approval leads to."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    draft = generate_blog_post(
        payload.topic, payload.primary_keyword, site_id=payload.site_id, min_words=payload.min_words
    )
    if draft is None:
        raise HTTPException(status_code=502, detail="Blog post generation failed — see server logs")

    structure = analyze_structure(
        draft.content_html, primary_keyword=payload.primary_keyword, min_words=payload.min_words
    )
    structure_issues_json = json.dumps(
        [{"rule": i.rule, "severity": i.severity, "message": i.message} for i in structure.issues]
    )

    post_id = database.create_blog_post(
        payload.site_id,
        payload.topic,
        payload.primary_keyword,
        draft.title,
        draft.excerpt,
        draft.content_html,
        structure.passed,
        structure_issues_json,
    )

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.get("/blog", response_model=list[BlogPostOut])
def list_blog_posts_route(site_id: int, status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(SeoBlogPost).filter(SeoBlogPost.site_id == site_id)
    if status is not None:
        query = query.filter(SeoBlogPost.status == status)
    return query.order_by(SeoBlogPost.created_at.desc()).limit(limit).all()


@router.patch("/blog/{post_id}", response_model=BlogPostOut)
def update_blog_post_route(post_id: int, payload: BlogPostUpdate, db: Session = Depends(get_db)):
    """Lets a reviewer fix a draft directly — tighten wording, clear a
    word-count minimum, adjust a heading — instead of only Approve/Reject
    on whatever the LLM produced. Re-runs the same structure checker
    generate_blog_post_route does, so the issue badges reflect the edit
    immediately rather than showing stale findings from the original
    draft. Only while still 'draft': once approved/published the content
    is either about to go out or already has, so this doesn't quietly
    rewrite it after the fact."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    if row.status != "draft":
        raise HTTPException(status_code=409, detail=f"Only a draft post can be edited (current status: {row.status})")

    structure = analyze_structure(payload.content, primary_keyword=row.primary_keyword)
    structure_issues_json = json.dumps(
        [{"rule": i.rule, "severity": i.severity, "message": i.message} for i in structure.issues]
    )
    database.update_blog_post(post_id, payload.title, payload.excerpt, payload.content, structure.passed, structure_issues_json)

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/{post_id}/approve", response_model=BlogPostOut)
def approve_blog_post_route(post_id: int, db: Session = Depends(get_db)):
    ok = database.set_blog_post_status(post_id, "approved")
    if not ok:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/{post_id}/reject", response_model=BlogPostOut)
def reject_blog_post_route(post_id: int, db: Session = Depends(get_db)):
    ok = database.set_blog_post_status(post_id, "rejected")
    if not ok:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/{post_id}/publish", response_model=BlogPostOut)
def publish_blog_post_route(post_id: int, db: Session = Depends(get_db)):
    """'Publish' means "create it as a draft in the CMS" — see
    automation/seo/cms/base.py's create_post docstring for why this
    deliberately never puts a page live on its own; a human still has to
    hit Publish inside WordPress/Webflow itself."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    # 'failed' is retryable without a fresh approval — a publish failure
    # is typically transient/config-related (e.g. CMS credentials just
    # weren't set yet), and the content was already approved once; only
    # 'draft'/'rejected' genuinely need a human decision first.
    if row.status not in ("approved", "failed"):
        raise HTTPException(status_code=409, detail=f"Post must be approved first (current status: {row.status})")

    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")

    client = _cms_client_for(site)
    result = client.create_post(title=row.title, content=row.content, excerpt=row.excerpt)
    if result.ok:
        link = result.post.link if result.post else None
        database.mark_blog_post_published(post_id, result.post.id if result.post else None, link)
    else:
        database.mark_blog_post_failed(post_id, result.detail)

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
