"""
MODULE 25.5 — SEO Agentic AI: site registry, job-run history, LLM usage
log, and a manual trigger endpoint that exercises the whole module-25
chain (job idempotency tracking + generic LLM provider factory + usage
logging) end-to-end. No real SEO pipeline exists yet — that's module 26
onward; this is the foundation those pipelines will be built on.
"""
import json
import logging
from datetime import date as date_cls, datetime, time, timedelta
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
    SeoDigestRollup,
    SeoGa4Page,
    SeoGscPage,
    SeoGscQuery,
    SeoIndexingSubmission,
    SeoIndexStatus,
    SeoJobRun,
    SeoMetaRewrite,
    SeoOgTags,
    SeoPagespeedResult,
    SeoSemrushMetric,
    SeoServerFileBackup,
    SeoSite,
    SeoSocialPost,
    SeoFacebookAccount,
    SeoTechnicalIssue,
    get_db,
)
from api.schemas import (
    BlogBulkActionResultOut,
    BlogBulkGenerateRequest,
    BlogBulkIdsRequest,
    BlogCalendarGenerateRequest,
    BlogExportRequest,
    BlogExportResult,
    BlogGenerateRequest,
    BlogPostOut,
    BlogPostUpdate,
    BlogScheduleRequest,
    BlogTaxonomyUpdate,
    CmsPostOut,
    CmsStatusOut,
    ContentAnalyzeRequest,
    ContentQualityCheckRequest,
    ContentQualityReportOut,
    DigestGenerateRequest,
    DigestRollupGenerateRequest,
    DigestOut,
    DigestRollupOut,
    FaqPairOut,
    FaqRequest,
    FlaggedPhraseOut,
    Ga4PageRowOut,
    Ga4PullRequest,
    GscPageRowOut,
    GscPullRequest,
    GscQueryRowOut,
    HumanizationReportOut,
    IndexingSubmissionOut,
    IndexingSubmitRequest,
    IndexStatusOut,
    ImageGenerateRequest,
    InterlinkPage,
    InterlinkSuggestRequest,
    LlmUsageLogOut,
    MetaRewriteOut,
    MetaRewriteUpdate,
    OgTagsGenerateRequest,
    OgTagsOut,
    RankChangeOut,
    BacklinkRowOut,
    BulkDomainAuthorityRequest,
    DomainAuthorityOut,
    DomainAuthorityRequest,
    GscDateRowOut,
    GscDimensionRequest,
    GscDimensionRowOut,
    GscExportAllRequest,
    GscExportRequest,
    GscExportResult,
    GscLivePageRowOut,
    GscLiveQueryRowOut,
    Ga4DateRowOut,
    Ga4DimensionRequest,
    Ga4DimensionRowOut,
    Ga4EventRowOut,
    Ga4ExportAllRequest,
    Ga4ExportResult,
    Ga4LivePageRowOut,
    Ga4RealtimeDimensionRowOut,
    Ga4RealtimeMinuteRowOut,
    Ga4RealtimeRowOut,
    OverviewExportRequest,
    OverviewExportResult,
    SitemapActionOut,
    SitemapActionRequest,
    SitemapInfoOut,
    SitemapListRequest,
    VerifiedSiteOut,
    KeywordDifficultyOut,
    KeywordDifficultyRequest,
    KeywordInsightOut,
    KeywordInsightRequest,
    TopBacklinksRequest,
    CompetitorAnalysisOut,
    CompetitorAnalysisRequest,
    WebsiteTrafficOut,
    WebsiteTrafficRequest,
    KeywordResearchRequest,
    KeywordResearchRowOut,
    PageSpeedCheckRequest,
    PageSpeedOpportunityItemOut,
    PageSpeedOpportunityOut,
    BulkConvertReportOut,
    ContentBackupOut,
    ContentBackupSummaryOut,
    RapidApiKeywordCheckRequest,
    WebpConvertRequest,
    WebpConvertUrlRequest,
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
    SheetsAdoptRequest,
    SheetsShareRequest,
    SheetsStatusOut,
    SeoSiteCreate,
    SeoSiteCmsConfigUpdate,
    SeoSiteGoogleConfigUpdate,
    SeoSiteOut,
    SeoSiteSshConfigUpdate,
    SshStatusOut,
    SocialGenerateRequest,
    SocialPostOut,
    SocialPostUpdate,
    SocialScheduleRequest,
    SocialBulkIdsRequest,
    SocialBulkActionResultOut,
    SocialBulkGenerateRequest,
    SocialCalendarGenerateRequest,
    SocialExportRequest,
    SocialExportResult,
    FacebookAccountCreate,
    FacebookAccountOut,
    StructureReportOut,
    TechnicalAuditRequest,
    PageTagAuditOut,
    PageTagAuditRequest,
    PageTagFindingOut,
    PlagiarismMatchOut,
    PlagiarismReportOut,
    TechnicalIssueEditTargetOut,
    TechnicalIssueOut,
    TechnicalIssueReview,
    UrlInspectRequest,
)
from ai.seo.blog_content import generate_blog_post
from ai.seo.content_quality import assess_humanization, check_plagiarism
from ai.seo.content_structure import analyze_structure, generate_faq
from ai.seo.daily_digest import generate_daily_digest
from ai.seo.image_pipeline import generate_and_publish_image, upload_image_bytes
from ai.seo.image_prompt import derive_image_prompt
from ai.seo.interlink_engine import find_related_pages, index_page
from ai.seo.issue_remediation import generate_ai_suggestion, generate_fix_value
from ai.seo.outreach_drafter import draft_outreach_email
from ai.seo.rank_alerts import compute_rank_changes, dropped_out_of_top_10, top_movers
from ai.seo.rollup_digest import generate_rollup_digest
from ai.seo.social_content import generate_social_post
from ai.seo.social_scheduler import publish_one as publish_one_social_post
from automation.seo.backlinks.factory import get_provider as get_backlink_provider
from automation.seo.cms.factory import get_cms_client
from automation.seo.crawler import crawl_site, fetch_sitemap_urls
from automation.seo.ga4_client import (
    fetch_events as ga4_fetch_events,
    fetch_realtime_active_users,
    fetch_realtime_active_users_by_minute,
    fetch_realtime_by_audience,
    fetch_realtime_by_device as ga4_fetch_realtime_by_device,
    fetch_realtime_by_page as ga4_fetch_realtime_by_page,
    fetch_traffic_by_country as ga4_fetch_by_country,
    fetch_traffic_by_date as ga4_fetch_by_date,
    fetch_traffic_by_device as ga4_fetch_by_device,
    fetch_traffic_by_page,
    fetch_traffic_by_source as ga4_fetch_by_source,
)
from automation.seo.gsc_client import fetch_search_analytics, fetch_search_analytics_by_page, today_with_lag
from automation.seo.indexing_client import fetch_url_inspection, submit_url_for_indexing
from automation.seo.issue_applier import apply_fix as apply_issue_fix
from automation.seo.issue_applier import apply_fix_to_static_file
from automation.seo.issue_applier import find_post_by_url as find_cms_post_by_url
from automation.seo.issue_applier import remote_path_for_url
from automation.seo.pagespeed_client import extract_resource_report, fetch_page_speed
from automation.seo.semrush_client import (
    fetch_backlink_gap as fetch_semrush_backlink_gap,
    fetch_backlinks_list as fetch_semrush_backlinks_list,
    fetch_domain_metrics as fetch_semrush_domain_metrics,
    fetch_referring_domains as fetch_semrush_referring_domains,
)
from automation.seo.server_access import client_for_site as sftp_client_for_site
from automation.seo.slack_notifier import send_slack_message
from automation.seo.page_tag_audit import extract_tag_values as extract_page_tag_values
from automation.seo.page_tag_audit import run_page_tag_audit
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


def _log_to_sheet_safe(sheet_name: str, row: list) -> None:
    """Module 36 — best-effort write to the Google Sheets command
    centre for actions triggered from a route (not the automated
    pipeline — see ai/seo_master_agent.py's own copy of this same
    pattern for that side). Never lets a Sheets failure affect the
    route's actual response."""
    try:
        from automation.seo.sheets_client import append_row, get_or_create_spreadsheet

        if get_or_create_spreadsheet():
            append_row(sheet_name, row)
    except Exception:
        logger.exception("Sheets logging failed for %r", sheet_name)


def _log_rows_to_sheet_safe(sheet_name: str, rows: list) -> None:
    """Module 45 — same best-effort contract as _log_to_sheet_safe, but
    for many rows in one call (e.g. one row per page from a whole-site
    audit) so this doesn't cost one HTTP round-trip per page."""
    try:
        from automation.seo.sheets_client import append_rows, get_or_create_spreadsheet

        if get_or_create_spreadsheet():
            append_rows(sheet_name, rows)
    except Exception:
        logger.exception("Sheets logging failed for %r", sheet_name)


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


@router.post("/keywords/rapidapi-check")
def check_rapidapi_keywords(payload: RapidApiKeywordCheckRequest, db: Session = Depends(get_db)):
    """Module 37 — a third-party RapidAPI keyword wrapper (NOT Semrush's
    own official API, see automation/seo/rapidapi_keyword_client.py's
    module docstring). Returns the provider's raw JSON response rather
    than a typed model: every live test this session returned their own
    generic error shape, not real data, so there's no verified success
    shape to model against yet — the frontend shows this as raw JSON
    until a real successful response has actually been observed."""
    from automation.seo.rapidapi_keyword_client import fetch_keyword_analysis, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_KEY is not set in .env")

    site = _site_or_404(payload.site_id, db)
    domain = urlparse(site.base_url).netloc or site.base_url
    result = fetch_keyword_analysis(domain, country=payload.country)
    if result is None:
        raise HTTPException(status_code=502, detail="RapidAPI request failed — see server logs")
    return result


@router.post("/keywords/research", response_model=list[KeywordResearchRowOut])
def keyword_research_route(payload: KeywordResearchRequest):
    """Module 37 follow-up — a DIFFERENT RapidAPI product ("Semrush
    Magic Tool", not the semrush-seo3 one above), verified live this
    session returning real data: search volume, CPC, competition,
    intent, and 12-month trends for hundreds of related keywords from
    one seed keyword."""
    from automation.seo.rapidapi_keyword_client import fetch_keyword_research, is_magic_tool_configured

    if not is_magic_tool_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")

    rows = fetch_keyword_research(payload.keyword, language=payload.language, country=payload.country)
    if rows is None:
        raise HTTPException(status_code=502, detail="Keyword research request failed — see server logs")
    return rows


@router.post("/keywords/difficulty", response_model=KeywordDifficultyOut)
def keyword_difficulty_route(payload: KeywordDifficultyRequest):
    """Module 37 follow-up — a THIRD distinct RapidAPI product/host
    (semrush-seo10.p.rapidapi.com), same key/application as the Magic
    Tool endpoint above. Verified live this session with real data for
    two different keywords/countries: difficulty score, volume,
    competition, CPC, and monthly trend."""
    from automation.seo.rapidapi_keyword_client import fetch_keyword_difficulty, is_magic_tool_configured

    if not is_magic_tool_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")

    result = fetch_keyword_difficulty(payload.keyword, country=payload.country)
    if result is None:
        raise HTTPException(status_code=502, detail="Keyword difficulty request failed — see server logs")
    return result


@router.post("/backlinks/top", response_model=list[BacklinkRowOut])
def top_backlinks_route(payload: TopBacklinksRequest, db: Session = Depends(get_db)):
    """Module 47 — real, page-level backlink detail (source URL, anchor
    text, follow/nofollow, spam score) from the semrush-seo3 RapidAPI
    product's /backlink.php, verified live this session against
    webpays.com and rapidapi.com. Distinct from SemrushLinkExplorer above
    (the official Semrush API, scoped to this site's own domain only) —
    this endpoint works for any domain, including a competitor's."""
    from automation.seo.rapidapi_domain_client import fetch_top_backlinks, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")
    _site_or_404(payload.site_id, db)

    rows = fetch_top_backlinks(payload.website)
    if rows is None:
        raise HTTPException(status_code=502, detail="Top backlinks request failed — see server logs")
    return rows


@router.post("/backlinks/domain-authority", response_model=DomainAuthorityOut)
def domain_authority_route(payload: DomainAuthorityRequest, db: Session = Depends(get_db)):
    """Module 47 — Domain/Page Authority, spam score, Domain Rating, and
    estimated organic traffic for one domain (semrush-seo3's /dapa.php),
    verified live this session."""
    from automation.seo.rapidapi_domain_client import fetch_domain_authority, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")
    _site_or_404(payload.site_id, db)

    result = fetch_domain_authority(payload.website)
    if result is None:
        raise HTTPException(status_code=502, detail="Domain authority request failed — see server logs")
    return result


@router.post("/backlinks/domain-authority/bulk", response_model=list[DomainAuthorityOut])
def bulk_domain_authority_route(payload: BulkDomainAuthorityRequest, db: Session = Depends(get_db)):
    """Module 47 — same metrics as /backlinks/domain-authority, for
    several domains in one call (semrush-seo3's /bulk-dapa.php),
    verified live this session with two real domains returning distinct,
    genuine values each."""
    from automation.seo.rapidapi_domain_client import fetch_bulk_domain_authority, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")
    _site_or_404(payload.site_id, db)

    domains = [d.strip() for d in payload.domains if d.strip()]
    if not domains:
        raise HTTPException(status_code=400, detail="At least one domain is required")

    rows = fetch_bulk_domain_authority(domains)
    if rows is None:
        raise HTTPException(status_code=502, detail="Bulk domain authority request failed — see server logs")
    return rows


@router.post("/keywords/insights", response_model=KeywordInsightOut)
def keyword_insights_route(payload: KeywordInsightRequest):
    """Module 47 — search volume/CPC/competition/intent for one keyword
    (semrush-seo3's /keyword-tool.php), verified live this session; the
    numbers matched exactly against the same keyword's Keyword Difficulty
    result, confirming both are reading real, consistent underlying data."""
    from automation.seo.rapidapi_domain_client import fetch_keyword_insights, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")

    result = fetch_keyword_insights(payload.keyword, country=payload.country)
    if result is None:
        raise HTTPException(status_code=502, detail="Keyword insights request failed — see server logs")
    return result


@router.post("/backlinks/website-traffic", response_model=WebsiteTrafficOut)
def website_traffic_route(payload: WebsiteTrafficRequest, db: Session = Depends(get_db)):
    """Module 47 — estimated organic traffic, ranked-keyword count,
    position distribution, and real sample ranking keywords for one
    domain (semrush-seo3's /webtraffic.php), verified live this session
    against webpays.com: 824 ranked keywords with real per-page URLs."""
    from automation.seo.rapidapi_domain_client import fetch_website_traffic, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")
    _site_or_404(payload.site_id, db)

    result = fetch_website_traffic(payload.website)
    if result is None:
        raise HTTPException(status_code=502, detail="Website traffic request failed — see server logs")
    return result


@router.post("/backlinks/competitor-analysis", response_model=CompetitorAnalysisOut)
def competitor_analysis_route(payload: CompetitorAnalysisRequest, db: Session = Depends(get_db)):
    """Module 47 — one-call competitor snapshot for any domain
    (semrush-seo3's /competitor.php): estimated visits, engagement, 12
    months of visit history, traffic-source split, top countries, and top
    keywords. This endpoint returned a provider-side 401 for every real
    domain when first tested; the provider has since fixed it and it was
    re-verified live against webpays.com (see rapidapi_domain_client.py)."""
    from automation.seo.rapidapi_domain_client import fetch_competitor_analysis, is_configured

    if not is_configured():
        raise HTTPException(status_code=400, detail="RAPIDAPI_SEMRUSH_MAGIC_KEY is not set in .env")
    _site_or_404(payload.site_id, db)

    result = fetch_competitor_analysis(payload.website)
    if result is None:
        raise HTTPException(status_code=502, detail="Competitor analysis request failed — see server logs")
    return result


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
                items=[
                    PageSpeedOpportunityItemOut(
                        url=item.url,
                        wasted_bytes=item.wasted_bytes,
                        wasted_ms=item.wasted_ms,
                        total_bytes=item.total_bytes,
                    )
                    for item in o.items
                ],
            )
            for o in report.opportunities
        ],
    )


@router.post("/gsc/pull", response_model=list[GscQueryRowOut], status_code=201)
def pull_gsc(payload: GscPullRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    end_date = today_with_lag()
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


@router.get("/gsc/rank-alerts", response_model=list[RankChangeOut])
def gsc_rank_alerts(site_id: int, only_drops: bool = False):
    """Diffs today's query positions against the last pull before it —
    see ai/seo/rank_alerts.py. Manual/on-demand read of the same
    computation the daily digest already runs; only_drops=true narrows to
    queries that fell out of the top 10, the specific alert the SEO
    blueprint calls out by name."""
    changes = compute_rank_changes(site_id)
    if only_drops:
        return dropped_out_of_top_10(changes)
    return top_movers(changes, limit=50)


@router.post("/gsc/pages/pull", response_model=list[GscPageRowOut], status_code=201)
def pull_gsc_pages(payload: GscPullRequest, db: Session = Depends(get_db)):
    """Page-dimension GSC pull ("CTR by page") — see /gsc/pull above for
    the query-dimension equivalent this mirrors."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    end_date = today_with_lag()
    start_date = end_date - timedelta(days=payload.days_back)
    rows = fetch_search_analytics_by_page(start_date, end_date, site_url=_effective_gsc_url(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GSC fetch failed — see server logs")

    database.upsert_gsc_page_rows(payload.site_id, end_date, rows)

    db.expire_all()
    return (
        db.query(SeoGscPage)
        .filter(SeoGscPage.site_id == payload.site_id, SeoGscPage.run_date == end_date)
        .order_by(SeoGscPage.impressions.desc())
        .all()
    )


@router.get("/gsc/pages", response_model=list[GscPageRowOut])
def list_gsc_pages(site_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SeoGscPage)
        .filter(SeoGscPage.site_id == site_id)
        .order_by(SeoGscPage.run_date.desc(), SeoGscPage.impressions.desc())
        .limit(limit)
        .all()
    )


def _gsc_dimension_route(payload: GscDimensionRequest, db: Session, fetch_fn):
    site = _site_or_404(payload.site_id, db)
    if payload.start_date and payload.end_date:
        start_date, end_date = payload.start_date, payload.end_date
    else:
        end_date = today_with_lag()
        # -1: both start_date and end_date are inclusive in Google's API,
        # so a naive `- timedelta(days=days_back)` spans days_back+1
        # calendar days — verified live this session that "7 days" was
        # actually returning 8 days' worth of data until this was fixed,
        # a real (if small) contributor to not matching the real Search
        # Console UI's own "7 days" chip exactly.
        start_date = end_date - timedelta(days=payload.days_back - 1)
    rows = fetch_fn(
        start_date,
        end_date,
        row_limit=payload.row_limit,
        site_url=_effective_gsc_url(site),
        country=payload.country,
        page=payload.page,
    )
    if rows is None:
        raise HTTPException(status_code=502, detail="GSC fetch failed — see server logs")
    return rows


@router.post("/gsc/timeseries", response_model=list[GscDateRowOut])
def gsc_timeseries_route(payload: GscDimensionRequest, db: Session = Depends(get_db)):
    """Module 50 — per-day clicks/impressions/CTR/position, the real
    trend-chart data Search Console's own Performance report shows,
    filterable by the same country/page drill-downs as every other live
    GSC route here."""
    from automation.seo.gsc_client import fetch_search_analytics_by_date

    return _gsc_dimension_route(payload, db, fetch_search_analytics_by_date)


@router.post("/gsc/export-to-sheet", response_model=GscExportResult)
def gsc_export_to_sheet_route(payload: GscExportRequest, db: Session = Depends(get_db)):
    """Module 50 — writes whatever rows the GSC Performance report
    currently has on screen (already fetched client-side — no second
    Google API call here) to the connected spreadsheet's own "GSC
    Performance Export" tab, one batched write rather than one row at a
    time."""
    from automation.seo.sheets_client import append_rows, get_or_create_spreadsheet, get_tab_url

    site = _site_or_404(payload.site_id, db)
    spreadsheet_id = get_or_create_spreadsheet("gsc")
    if not spreadsheet_id:
        return GscExportResult(ok=False, detail="No Google Sheets (Search Console) connection configured — see the Overview tab.")

    exported_at = datetime.utcnow().isoformat()
    sheet_rows = [
        [exported_at, site.name, payload.view, payload.date_range, r.label, r.clicks, r.impressions, r.ctr, r.position]
        for r in payload.rows
    ]
    ok = append_rows("GSC Performance Export", sheet_rows)
    if not ok:
        return GscExportResult(ok=False, detail="Sheets write failed — see server logs.")

    # A direct link straight into the tab the data actually landed in —
    # the bare spreadsheet URL opens whatever tab was last active, which
    # made a real, successful export look like "no data showing" simply
    # because this tab (the newest one, at the far end of the tab strip)
    # wasn't the one on screen.
    sheet_url = get_tab_url(spreadsheet_id, "GSC Performance Export")
    return GscExportResult(
        ok=True,
        detail=f"Exported {len(sheet_rows)} row(s) to the 'GSC Performance Export' tab.",
        sheet_url=sheet_url,
    )


_GSC_EXPORT_ALL_DIMENSIONS = [
    ("GSC Queries", "Query", "queries"),
    ("GSC Pages", "Page", "pages"),
    ("GSC Countries", "Country", "countries"),
    ("GSC Devices", "Device", "devices"),
    ("GSC Search Appearance", "Search Appearance", "search_appearance"),
]
_GSC_EXPORT_ALL_TAB_BY_VIEW = {"Queries": "GSC Queries", "Pages": "GSC Pages", "Countries": "GSC Countries", "Devices": "GSC Devices", "Search Appearance": "GSC Search Appearance"}


@router.post("/gsc/export-all-to-sheet", response_model=GscExportResult)
def gsc_export_all_to_sheet_route(payload: GscExportAllRequest, db: Session = Depends(get_db)):
    """Module 50 follow-up — one click writes EVERY GSC dimension
    (Queries/Pages/Countries/Devices/Search Appearance) into its own
    clean tab (Country | Clicks | Impressions | CTR | Position, etc.),
    matching the real Search Console UI's own per-dimension tables —
    instead of the earlier /gsc/export-to-sheet, which only wrote
    whichever single view a human happened to have open on screen."""
    from automation.seo.sheets_client import get_or_create_spreadsheet, get_tab_url, overwrite_rows, write_chart_tab

    _site_or_404(payload.site_id, db)
    spreadsheet_id = get_or_create_spreadsheet("gsc")
    if not spreadsheet_id:
        return GscExportResult(ok=False, detail="No Google Sheets (Search Console) connection configured — see the Overview tab.")

    written, failed = [], []

    if payload.timeseries:
        chart_header = ["Date", "Clicks", "Impressions", "CTR", "Avg. Position"]
        chart_rows = [[r.date, r.clicks, r.impressions, r.ctr, r.position] for r in payload.timeseries]
        if write_chart_tab("GSC Chart", chart_header, chart_rows, "Clicks & Impressions", series_cols=[1, 2]):
            written.append("GSC Chart")
        else:
            failed.append("GSC Chart")

    for tab_name, column_label, field_name in _GSC_EXPORT_ALL_DIMENSIONS:
        export_rows = getattr(payload, field_name)
        if not export_rows:
            continue
        header = [column_label, "Clicks", "Impressions", "CTR", "Avg. Position"]
        sheet_rows = [[r.label, r.clicks, r.impressions, r.ctr, r.position] for r in export_rows]
        if overwrite_rows(tab_name, header, sheet_rows):
            written.append(tab_name)
        else:
            failed.append(tab_name)

    if not written:
        detail = "Sheets write failed — see server logs." if failed else "No data to export yet — load a view first."
        return GscExportResult(ok=False, detail=detail)

    detail = f"Exported {', '.join(t.replace('GSC ', '') for t in written)} to their own tabs."
    if failed:
        detail += f" ({', '.join(t.replace('GSC ', '') for t in failed)} failed — see server logs.)"

    focus_tab = _GSC_EXPORT_ALL_TAB_BY_VIEW.get(payload.focus_view, "GSC Queries")
    sheet_url = get_tab_url(spreadsheet_id, focus_tab if focus_tab in written else written[0])
    return GscExportResult(ok=True, detail=detail, sheet_url=sheet_url)


@router.post("/gsc/queries/live", response_model=list[GscLiveQueryRowOut])
def gsc_queries_live_route(payload: GscDimensionRequest, db: Session = Depends(get_db)):
    """Module 50 — query-dimension breakdown, live (stateless — the
    persisted /gsc/pull + /gsc routes above feed the daily digest
    pipeline and stay untouched; this is the same data for the unified
    Performance-report UI, with the same country-drill-down filter the
    other live dimension routes below support)."""
    from automation.seo.gsc_client import fetch_search_analytics

    return _gsc_dimension_route(payload, db, fetch_search_analytics)


@router.post("/gsc/pages/live", response_model=list[GscLivePageRowOut])
def gsc_pages_live_route(payload: GscDimensionRequest, db: Session = Depends(get_db)):
    """Module 50 — page-dimension breakdown, live — see /gsc/queries/live
    above for why this is separate from the persisted /gsc/pages/pull."""
    from automation.seo.gsc_client import fetch_search_analytics_by_page

    return _gsc_dimension_route(payload, db, fetch_search_analytics_by_page)


@router.post("/gsc/country", response_model=list[GscDimensionRowOut])
def gsc_by_country_route(payload: GscDimensionRequest, db: Session = Depends(get_db)):
    """Module 48 — country-dimension breakdown, live (stateless, no local
    table — this data is cheap to re-fetch and isn't fed into any
    existing pipeline the way query/page dimensions are)."""
    from automation.seo.gsc_client import fetch_search_analytics_by_country

    return _gsc_dimension_route(payload, db, fetch_search_analytics_by_country)


@router.post("/gsc/device", response_model=list[GscDimensionRowOut])
def gsc_by_device_route(payload: GscDimensionRequest, db: Session = Depends(get_db)):
    """Module 48 — device-dimension breakdown (DESKTOP/MOBILE/TABLET)."""
    from automation.seo.gsc_client import fetch_search_analytics_by_device

    return _gsc_dimension_route(payload, db, fetch_search_analytics_by_device)


@router.post("/gsc/search-appearance", response_model=list[GscDimensionRowOut])
def gsc_by_search_appearance_route(payload: GscDimensionRequest, db: Session = Depends(get_db)):
    """Module 48 — search-appearance-dimension breakdown (which SERP
    feature type impressions came from)."""
    from automation.seo.gsc_client import fetch_search_analytics_by_search_appearance

    return _gsc_dimension_route(payload, db, fetch_search_analytics_by_search_appearance)


@router.post("/sitemaps", response_model=list[SitemapInfoOut])
def list_sitemaps_route(payload: SitemapListRequest, db: Session = Depends(get_db)):
    """Module 48 — real Search Console Sitemaps list for this property.
    An empty list is a genuine result (no sitemap submitted yet), not a
    failure; a 502 means the actual Google API call failed (commonly:
    the service account isn't a Search Console user on this property —
    the same permission gap every other GSC feature in this app hits for
    a not-yet-shared property)."""
    from automation.seo.sitemap_client import list_sitemaps

    site = _site_or_404(payload.site_id, db)
    site_url = _effective_gsc_url(site)
    if not site_url:
        raise HTTPException(status_code=400, detail="No GSC property configured for this site")

    sitemaps = list_sitemaps(site_url)
    if sitemaps is None:
        raise HTTPException(status_code=502, detail="Sitemaps request failed — see server logs")
    return sitemaps


@router.post("/sitemaps/submit", response_model=SitemapActionOut)
def submit_sitemap_route(payload: SitemapActionRequest, db: Session = Depends(get_db)):
    """Module 48 — registers a sitemap with Search Console. Needs the
    broader read-write "webmasters" scope, which needs the service
    account to be a Full user or Owner on this property in Search
    Console — a Restricted/read-only user (enough for every other GSC
    feature in this app) gets a real 403 here, surfaced as ok=false
    rather than a generic error."""
    from automation.seo.sitemap_client import submit_sitemap

    site = _site_or_404(payload.site_id, db)
    site_url = _effective_gsc_url(site)
    if not site_url:
        raise HTTPException(status_code=400, detail="No GSC property configured for this site")
    return submit_sitemap(site_url, payload.feedpath)


@router.post("/sitemaps/delete", response_model=SitemapActionOut)
def delete_sitemap_route(payload: SitemapActionRequest, db: Session = Depends(get_db)):
    """Module 48 — same permission requirement as /sitemaps/submit above."""
    from automation.seo.sitemap_client import delete_sitemap

    site = _site_or_404(payload.site_id, db)
    site_url = _effective_gsc_url(site)
    if not site_url:
        raise HTTPException(status_code=400, detail="No GSC property configured for this site")
    return delete_sitemap(site_url, payload.feedpath)


@router.get("/site-verification", response_model=list[VerifiedSiteOut])
def list_verified_sites_route():
    """Module 49 — properties this service account has itself verified
    ownership of via the Site Verification API — a genuinely separate
    Google permission system from "added as a Search Console user" (see
    automation/seo/site_verification_client.py's module docstring). Live-
    verified this session that this specific API call needs more than a
    bare service-account JWT can provide (Google returned
    ACCESS_TOKEN_SCOPE_INSUFFICIENT even with the correct scope
    requested) — surfaced as a real 502 rather than silently returning an
    empty list, so this honestly shows as broken instead of looking like
    "zero verified sites."""
    from automation.seo.site_verification_client import list_verified_sites

    sites = list_verified_sites()
    if sites is None:
        raise HTTPException(
            status_code=502,
            detail="Site Verification API call failed — Google rejected the service account's credentials for "
            "this specific API (verified live: ACCESS_TOKEN_SCOPE_INSUFFICIENT). This API generally requires "
            "Google Workspace domain-wide delegation for service-account access, not just enabling the API — "
            "see server logs for the exact error.",
        )
    return sites


@router.get("/meta-rewrites", response_model=list[MetaRewriteOut])
def list_meta_rewrites(site_id: int, status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    """The CTR-opportunity queue meta_opportunity_node fills — high-
    impression/low-CTR pages with an AI-drafted title/description rewrite
    waiting for human review (see ai/seo_master_agent.py's
    meta_opportunity_node and ai/seo/meta_rewrite_generator.py)."""
    query = db.query(SeoMetaRewrite).filter(SeoMetaRewrite.site_id == site_id)
    if status is not None:
        query = query.filter(SeoMetaRewrite.status == status)
    return query.order_by(SeoMetaRewrite.impressions.desc()).limit(limit).all()


@router.patch("/meta-rewrites/{item_id}", response_model=MetaRewriteOut)
def update_meta_rewrite_route(item_id: int, payload: MetaRewriteUpdate, db: Session = Depends(get_db)):
    """Lets a reviewer edit the AI-drafted title/description before
    approving it — the draft is a starting point, not the final copy."""
    ok = database.update_meta_rewrite_content(item_id, payload.suggested_title, payload.suggested_description)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No meta rewrite candidate {item_id}")
    db.expire_all()
    return db.query(SeoMetaRewrite).filter(SeoMetaRewrite.id == item_id).first()


@router.post("/meta-rewrites/{item_id}/approve", response_model=MetaRewriteOut)
def approve_meta_rewrite_route(item_id: int, db: Session = Depends(get_db)):
    """Marks a rewrite reviewed and approved. Deliberately doesn't push
    anything to the live site — see agent.database.upsert_meta_rewrite_
    candidate's docstring: WordPress's base REST API has no generic
    meta-title/description field (that's normally an SEO plugin's custom
    field, whose name varies per install), the same reason
    seo_og_tags never auto-applies either. Approving here just records the
    review decision so this item stops surfacing as a pending opportunity;
    applying the suggested copy on the live site stays a manual step."""
    ok = database.set_meta_rewrite_status(item_id, "approved")
    if not ok:
        raise HTTPException(status_code=404, detail=f"No meta rewrite candidate {item_id}")
    db.expire_all()
    return db.query(SeoMetaRewrite).filter(SeoMetaRewrite.id == item_id).first()


@router.post("/meta-rewrites/{item_id}/reject", response_model=MetaRewriteOut)
def reject_meta_rewrite_route(item_id: int, db: Session = Depends(get_db)):
    ok = database.set_meta_rewrite_status(item_id, "rejected")
    if not ok:
        raise HTTPException(status_code=404, detail=f"No meta rewrite candidate {item_id}")
    db.expire_all()
    return db.query(SeoMetaRewrite).filter(SeoMetaRewrite.id == item_id).first()


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


# ── Module 51 — GA4 live dimension/timeseries views and Sheets export,
# mirroring the GSC Performance dashboard's own live routes above
# (_gsc_dimension_route / /gsc/timeseries / /gsc/*/live /
# /gsc/export-all-to-sheet). Stateless — re-fetched live each time, no
# local table, same as those GSC routes. ──


def _ga4_dimension_route(payload: Ga4DimensionRequest, db: Session, fetch_fn):
    site = _site_or_404(payload.site_id, db)
    if payload.start_date and payload.end_date:
        start_date, end_date = payload.start_date, payload.end_date
    else:
        end_date = date_cls.today()
        start_date = end_date - timedelta(days=payload.days_back - 1)
    rows = fetch_fn(start_date, end_date, limit=payload.row_limit, property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 fetch failed — see server logs")
    return rows


@router.post("/ga4/timeseries", response_model=list[Ga4DateRowOut])
def ga4_timeseries_route(payload: Ga4DimensionRequest, db: Session = Depends(get_db)):
    """Module 51 — per-day sessions/bounce rate/conversions, the trend-
    chart data behind the Analytics Performance panel's chart, matching
    /gsc/timeseries above."""
    return _ga4_dimension_route(payload, db, ga4_fetch_by_date)


@router.post("/ga4/pages/live", response_model=list[Ga4LivePageRowOut])
def ga4_pages_live_route(payload: Ga4DimensionRequest, db: Session = Depends(get_db)):
    """Module 51 — page-dimension breakdown, live (stateless — the
    persisted /ga4/pull + /ga4 routes above feed the daily digest
    pipeline and stay untouched; this is the same data for the unified
    Analytics Performance panel, matching /gsc/pages/live above)."""
    return _ga4_dimension_route(payload, db, fetch_traffic_by_page)


@router.post("/ga4/sources/live", response_model=list[Ga4DimensionRowOut])
def ga4_sources_live_route(payload: Ga4DimensionRequest, db: Session = Depends(get_db)):
    return _ga4_dimension_route(payload, db, ga4_fetch_by_source)


@router.post("/ga4/countries/live", response_model=list[Ga4DimensionRowOut])
def ga4_countries_live_route(payload: Ga4DimensionRequest, db: Session = Depends(get_db)):
    return _ga4_dimension_route(payload, db, ga4_fetch_by_country)


@router.post("/ga4/devices/live", response_model=list[Ga4DimensionRowOut])
def ga4_devices_live_route(payload: Ga4DimensionRequest, db: Session = Depends(get_db)):
    return _ga4_dimension_route(payload, db, ga4_fetch_by_device)


@router.post("/ga4/events", response_model=list[Ga4EventRowOut])
def ga4_events_route(payload: Ga4DimensionRequest, db: Session = Depends(get_db)):
    """Module 55 — GA4's own "Events: Event name" report."""
    return _ga4_dimension_route(payload, db, ga4_fetch_events)


@router.get("/ga4/realtime", response_model=list[Ga4RealtimeRowOut])
def ga4_realtime_route(site_id: int, db: Session = Depends(get_db)):
    """Module 52 — active users right now, broken down by country,
    matching the real GA4 UI's own Home/Realtime report. No date range
    (GA4 itself defines "realtime" as the trailing ~30-minute window),
    so this is a GET unlike the dimension routes above."""
    site = _site_or_404(site_id, db)
    rows = fetch_realtime_active_users(property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 realtime fetch failed — see server logs")
    return rows


@router.get("/ga4/realtime/by-minute", response_model=list[Ga4RealtimeMinuteRowOut])
def ga4_realtime_by_minute_route(site_id: int, db: Session = Depends(get_db)):
    """The "Active users per minute" bar chart on GA4's own Realtime
    overview report."""
    site = _site_or_404(site_id, db)
    rows = fetch_realtime_active_users_by_minute(property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 realtime fetch failed — see server logs")
    return rows


@router.get("/ga4/realtime/by-device", response_model=list[Ga4RealtimeDimensionRowOut])
def ga4_realtime_by_device_route(site_id: int, db: Session = Depends(get_db)):
    """Active users right now by device category — GA4's own Realtime
    overview has no exact equivalent tile (its "First user source" tile
    isn't backed by a documented Data API realtime dimension), so this
    substitutes a real, verifiable breakdown instead of faking one."""
    site = _site_or_404(site_id, db)
    rows = ga4_fetch_realtime_by_device(property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 realtime fetch failed — see server logs")
    return rows


@router.get("/ga4/realtime/by-page", response_model=list[Ga4RealtimeDimensionRowOut])
def ga4_realtime_by_page_route(site_id: int, db: Session = Depends(get_db)):
    """GA4's own "Views by Page title and screen name" realtime tile."""
    site = _site_or_404(site_id, db)
    rows = ga4_fetch_realtime_by_page(property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 realtime fetch failed — see server logs")
    return rows


@router.get("/ga4/realtime/by-audience", response_model=list[Ga4RealtimeDimensionRowOut])
def ga4_realtime_by_audience_route(site_id: int, db: Session = Depends(get_db)):
    """GA4's own "Active users by Audience" realtime tile — empty when
    the property has no GA4 Audiences configured, same honest empty
    state the real GA4 UI shows."""
    site = _site_or_404(site_id, db)
    rows = fetch_realtime_by_audience(property_id=_effective_ga4_property(site))
    if rows is None:
        raise HTTPException(status_code=502, detail="GA4 realtime fetch failed — see server logs")
    return rows


_GA4_EXPORT_DIMENSIONS = [
    ("GA4 Pages", "Page", "pages"),
    ("GA4 Sources", "Source", "sources"),
    ("GA4 Countries", "Country", "countries"),
    ("GA4 Devices", "Device", "devices"),
]
_GA4_EXPORT_ALL_TAB_BY_VIEW = {
    "Pages": "GA4 Pages",
    "Sources": "GA4 Sources",
    "Countries": "GA4 Countries",
    "Devices": "GA4 Devices",
    "Events": "GA4 Events",
}


@router.post("/ga4/export-all-to-sheet", response_model=Ga4ExportResult)
def ga4_export_all_to_sheet_route(payload: Ga4ExportAllRequest, db: Session = Depends(get_db)):
    """Module 51 — one click writes every GA4 dimension (Pages/Sources/
    Countries/Devices) into its own clean tab, plus a chart tab for the
    timeseries — matches /gsc/export-all-to-sheet above exactly, just
    against GA4's own metric set (sessions/bounce rate/conversions
    instead of clicks/impressions/CTR/position). Module 55 added the
    Events tab (its own row shape, so it's handled separately from the
    generic _GA4_EXPORT_DIMENSIONS loop below). Module 56 — writes to
    its own dedicated "ga4" spreadsheet rather than the shared one GSC's
    export also used to write into."""
    from automation.seo.sheets_client import get_or_create_spreadsheet, get_tab_url, overwrite_rows, write_chart_tab

    _site_or_404(payload.site_id, db)
    spreadsheet_id = get_or_create_spreadsheet("ga4")
    if not spreadsheet_id:
        return Ga4ExportResult(ok=False, detail="No Google Sheets (Analytics) connection configured — see the Overview tab.")

    written, failed = [], []

    if payload.timeseries:
        chart_header = ["Date", "Sessions", "Bounce Rate", "Conversions"]
        chart_rows = [[r.date, r.sessions, r.bounce_rate, r.conversions] for r in payload.timeseries]
        if write_chart_tab("GA4 Chart", chart_header, chart_rows, "Sessions & Conversions", series_cols=[1, 3]):
            written.append("GA4 Chart")
        else:
            failed.append("GA4 Chart")

    for tab_name, column_label, field_name in _GA4_EXPORT_DIMENSIONS:
        export_rows = getattr(payload, field_name)
        if not export_rows:
            continue
        header = [column_label, "Sessions", "Bounce Rate", "Conversions"]
        sheet_rows = [[r.label, r.sessions, r.bounce_rate, r.conversions] for r in export_rows]
        if overwrite_rows(tab_name, header, sheet_rows):
            written.append(tab_name)
        else:
            failed.append(tab_name)

    if payload.events:
        header = ["Event Name", "Event Count", "Total Users", "Event Count Per Active User", "Total Revenue"]
        sheet_rows = [
            [e.event_name, e.event_count, e.total_users, round(e.event_count_per_active_user, 2), e.total_revenue]
            for e in payload.events
        ]
        if overwrite_rows("GA4 Events", header, sheet_rows):
            written.append("GA4 Events")
        else:
            failed.append("GA4 Events")

    if not written:
        detail = "Sheets write failed — see server logs." if failed else "No data to export yet — load a view first."
        return Ga4ExportResult(ok=False, detail=detail)

    detail = f"Exported {', '.join(t.replace('GA4 ', '') for t in written)} to their own tabs."
    if failed:
        detail += f" ({', '.join(t.replace('GA4 ', '') for t in failed)} failed — see server logs.)"

    focus_tab = _GA4_EXPORT_ALL_TAB_BY_VIEW.get(payload.focus_view, "GA4 Pages")
    sheet_url = get_tab_url(spreadsheet_id, focus_tab if focus_tab in written else written[0])
    return Ga4ExportResult(ok=True, detail=detail, sheet_url=sheet_url)


_OVERVIEW_EXPORTS = [
    ("top_queries", "Overview Top Queries", ["Query", "Clicks", "Impressions", "CTR", "Avg. Position"], lambda r: [r.query, r.clicks, r.impressions, r.ctr, r.position]),
    ("top_pages", "Overview Top Traffic Pages", ["Page", "Sessions", "Bounce Rate", "Conversions"], lambda r: [r.page_path, r.sessions, r.bounce_rate, r.conversions]),
    ("ctr_by_page", "Overview CTR by Page", ["Page", "Clicks", "Impressions", "CTR", "Avg. Position"], lambda r: [r.page, r.clicks, r.impressions, r.ctr, r.position]),
    ("rank_alerts", "Overview Rank Alerts", ["Query", "Previous Position", "Current Position", "Delta"], lambda r: [r.query, r.previous_position, r.current_position, r.delta]),
]


@router.post("/overview/export-to-sheet", response_model=OverviewExportResult)
def overview_export_to_sheet_route(payload: OverviewExportRequest, db: Session = Depends(get_db)):
    """Module 57 — the site Overview dashboard's own "download this
    report in Google Sheets" button: Top Search Queries, Top Traffic
    Pages, CTR by Page, and Rank Alerts, each in its own clean tab in its
    own dedicated "overview" spreadsheet — separate from "main"/"gsc"/
    "ga4" (this dashboard blends GSC and GA4 data, so it doesn't belong
    to either of those alone). Same overwrite-on-export convention as
    /gsc/export-all-to-sheet and /ga4/export-all-to-sheet."""
    from automation.seo.sheets_client import get_or_create_spreadsheet, get_tab_url, overwrite_rows

    _site_or_404(payload.site_id, db)
    spreadsheet_id = get_or_create_spreadsheet("overview")
    if not spreadsheet_id:
        return OverviewExportResult(
            ok=False, detail="No Overview report sheet connected yet — connect one on the Overview tab."
        )

    written, failed = [], []
    for field_key, tab_name, header, row_fn in _OVERVIEW_EXPORTS:
        export_rows = getattr(payload, field_key)
        if not export_rows:
            continue
        sheet_rows = [row_fn(r) for r in export_rows]
        if overwrite_rows(tab_name, header, sheet_rows):
            written.append(tab_name)
        else:
            failed.append(tab_name)

    if not written:
        detail = "Sheets write failed — see server logs." if failed else "No data to export yet — this dashboard is still empty."
        return OverviewExportResult(ok=False, detail=detail)

    detail = f"Exported {', '.join(t.replace('Overview ', '') for t in written)} to their own tabs."
    if failed:
        detail += f" ({', '.join(t.replace('Overview ', '') for t in failed)} failed — see server logs.)"

    sheet_url = get_tab_url(spreadsheet_id, written[0])
    return OverviewExportResult(ok=True, detail=detail, sheet_url=sheet_url)


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


# Module 60 — content plagiarism & humanization check. See
# ai/seo/content_quality.py's module docstring for what each check
# honestly does and doesn't cover.

def _load_quality_check_candidates(db: Session, site_id: int, exclude_blog_post_id=None, exclude_social_post_id=None):
    """Every other blog/social post for this site — the plagiarism
    comparison pool. Loaded once per request/batch by the caller (see
    _check_and_store_blog_quality's own comment) rather than per post."""
    candidates = []
    blog_q = db.query(SeoBlogPost).filter(SeoBlogPost.site_id == site_id)
    if exclude_blog_post_id is not None:
        blog_q = blog_q.filter(SeoBlogPost.id != exclude_blog_post_id)
    for row in blog_q.all():
        candidates.append(("blog", row.id, row.title, row.content))

    social_q = db.query(SeoSocialPost).filter(SeoSocialPost.site_id == site_id)
    if exclude_social_post_id is not None:
        social_q = social_q.filter(SeoSocialPost.id != exclude_social_post_id)
    for row in social_q.all():
        candidates.append(("social", row.id, f"{row.platform} post #{row.id}", row.content))

    return candidates


def _run_quality_check(content_html: str, candidates) -> ContentQualityReportOut:
    humanization = assess_humanization(content_html)
    plagiarism = check_plagiarism(content_html, candidates)
    return ContentQualityReportOut(
        humanization=HumanizationReportOut(
            score=humanization.score,
            band=humanization.band,
            word_count=humanization.word_count,
            avg_sentence_length=humanization.avg_sentence_length,
            sentence_length_variety=humanization.sentence_length_variety,
            lexical_diversity=humanization.lexical_diversity,
            flagged_phrases=[FlaggedPhraseOut(phrase=f.phrase, reason=f.reason) for f in humanization.flagged_phrases],
            notes=humanization.notes,
        ),
        plagiarism=PlagiarismReportOut(
            overall_similarity=plagiarism.overall_similarity,
            verdict=plagiarism.verdict,
            matches=[
                PlagiarismMatchOut(
                    source_type=m.source_type, source_id=m.source_id, source_title=m.source_title,
                    similarity=m.similarity, matched_snippet=m.matched_snippet,
                )
                for m in plagiarism.matches
            ],
        ),
        checked_at=datetime.utcnow(),
    )


def _check_and_store_blog_quality(db: Session, post_id: int, site_id: int, content_html: str, candidates=None) -> None:
    """Runs right after a blog draft is created (every generation path —
    single/bulk/calendar) so a reviewer sees originality/humanization
    alongside the draft, same "not a separate manual step" treatment
    module 27.5's structure checker gets. Never raises — a quality-check
    failure (a bug in the heuristics, an unexpected content shape) must
    never take down content generation itself; the post is simply left
    unchecked (quality_report_json stays NULL) and can be re-checked
    manually. `candidates` lets a bulk/calendar loop pass in one
    site-wide pool loaded ONCE rather than re-querying per post."""
    try:
        if candidates is None:
            candidates = _load_quality_check_candidates(db, site_id, exclude_blog_post_id=post_id)
        report = _run_quality_check(content_html, candidates)
        database.set_blog_post_quality(post_id, report.model_dump_json())
    except Exception:
        logger.exception("Quality check failed for blog post %s — post saved without one", post_id)


def _check_and_store_social_quality(db: Session, post_id: int, site_id: int, content_html: str, candidates=None) -> None:
    """Social-post counterpart to _check_and_store_blog_quality — see its
    own comment."""
    try:
        if candidates is None:
            candidates = _load_quality_check_candidates(db, site_id, exclude_social_post_id=post_id)
        report = _run_quality_check(content_html, candidates)
        database.set_social_post_quality(post_id, report.model_dump_json())
    except Exception:
        logger.exception("Quality check failed for social post %s — post saved without one", post_id)


@router.post("/content/quality-check", response_model=ContentQualityReportOut)
def check_content_quality_route(payload: ContentQualityCheckRequest, db: Session = Depends(get_db)):
    """General-purpose version of the same check the generation routes
    run automatically — lets any piece of content (e.g. something written
    directly in the CMS, or a draft re-checked after a manual edit) be
    assessed on demand, same relationship /content/analyze has to the
    structure checker."""
    candidates = _load_quality_check_candidates(
        db, payload.site_id,
        exclude_blog_post_id=payload.exclude_blog_post_id,
        exclude_social_post_id=payload.exclude_social_post_id,
    )
    return _run_quality_check(payload.content_html, candidates)


@router.post("/blog/{post_id}/quality-check", response_model=BlogPostOut)
def check_blog_post_quality_route(post_id: int, db: Session = Depends(get_db)):
    """Manual re-check — e.g. after editing a draft's content, since the
    automatic check only ran once, at generation time."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    _check_and_store_blog_quality(db, post_id, row.site_id, row.content)
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/social/{post_id}/quality-check", response_model=SocialPostOut)
def check_social_post_quality_route(post_id: int, db: Session = Depends(get_db)):
    """Manual re-check counterpart — see check_blog_post_quality_route."""
    row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    _check_and_store_social_quality(db, post_id, row.site_id, row.content)
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


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

    # Module 45 — one Meta Tag Audit row per successfully-fetched page,
    # reusing the HTML this crawl already downloaded (no second fetch per
    # page) and one batched Sheets write for the whole set (no per-page
    # HTTP round-trip).
    tag_rows = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        tv = extract_page_tag_values(BeautifulSoup(page.html, "html.parser"))
        tag_rows.append(
            [
                run_date.isoformat(),
                site.name,
                page.url,
                tv.get("title", ""),
                tv.get("description", ""),
                tv.get("keywords", ""),
                tv.get("author", ""),
                tv.get("publisher", ""),
                tv.get("copyright", ""),
                tv.get("subject", ""),
                tv.get("robots", ""),
                tv.get("canonical", ""),
                tv.get("og_tags", ""),
                tv.get("hreflang_x_default", ""),
                tv.get("json_ld", ""),
            ]
        )
    _log_rows_to_sheet_safe("Meta Tag Audit", tag_rows)

    db.expire_all()
    return (
        db.query(SeoTechnicalIssue)
        .filter(SeoTechnicalIssue.site_id == payload.site_id)
        .order_by(SeoTechnicalIssue.severity.asc(), SeoTechnicalIssue.created_at.desc())
        .all()
    )


@router.post("/technical/audit/page", response_model=PageTagAuditOut)
def run_page_tag_audit_route(payload: PageTagAuditRequest, db: Session = Depends(get_db)):
    """Module 44 — the single-page counterpart to /technical/audit above:
    one live fetch, classified into missing/existing/duplicate/invalid
    tags, instead of a full site crawl feeding the issue-approval queue.
    Stateless by design (nothing is written to seo_technical_issues) —
    this is a one-off "what does this page's <head> look like right now"
    check, not a recurring backlog item."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    report = run_page_tag_audit(payload.url)
    if report.fetch_error:
        raise HTTPException(status_code=502, detail=f"Could not fetch {payload.url}: {report.fetch_error}")

    tv = report.tag_values
    _log_to_sheet_safe(
        "Meta Tag Audit",
        [
            date_cls.today().isoformat(),
            site.name,
            report.url,
            tv.get("title", ""),
            tv.get("description", ""),
            tv.get("keywords", ""),
            tv.get("author", ""),
            tv.get("publisher", ""),
            tv.get("copyright", ""),
            tv.get("subject", ""),
            tv.get("robots", ""),
            tv.get("canonical", ""),
            tv.get("og_tags", ""),
            tv.get("hreflang_x_default", ""),
            tv.get("json_ld", ""),
        ],
    )

    def _out(findings):
        return [PageTagFindingOut(tag=f.tag, detail=f.detail, values=f.values) for f in findings]

    return PageTagAuditOut(
        url=report.url,
        missing_tags=_out(report.missing_tags),
        existing_tags=_out(report.existing_tags),
        duplicate_tags=_out(report.duplicate_tags),
        invalid_tags=_out(report.invalid_tags),
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


@router.post("/technical/issues/{issue_id}/resolve", response_model=TechnicalIssueOut)
def resolve_technical_issue_route(issue_id: int, payload: TechnicalIssueReview, db: Session = Depends(get_db)):
    """Module 41 — closes out an issue the human fixed themselves, outside
    this app (most technical-audit rules have no safe automatic CMS write
    at all — see issue_applier.py's docstring). Purely a status change, no
    live-site call: this is the app trusting a human's own confirmation,
    the same way /approve and /reject already do."""
    ok = database.set_technical_issue_status(issue_id, "resolved", payload.reviewed_by)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")
    db.expire_all()
    return db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()


def _resolve_edit_target(site: SeoSite, url: str) -> TechnicalIssueEditTargetOut:
    """Module 42 — resolves ANY url on a site to somewhere a human can
    actually go fix it. Shared by the technical-issue edit-target route
    below and the PageSpeed opportunity one (module 43) — same two real
    cases, tried in order: (1) a CMS post/page backs this URL
    (find_post_by_url — the same resolver /apply-fix already trusts) —
    return the real CMS admin edit screen for it. (2) no CMS post, but
    this site's Server Access connection can actually read a file at the
    URL's own path (a real, verified case: webpays.com's landing pages,
    and any external .css/.js asset PageSpeed points at, are static
    files with no CMS behind them at all) — return that exact path, only
    after confirming the read succeeds so this never sends someone to a
    file that isn't there. Otherwise says plainly that neither resolved,
    rather than guessing."""
    client = _cms_client_for(site)
    if client is not None:
        post = find_cms_post_by_url(client, url)
        if post is not None:
            edit_url = client.admin_edit_url(post.id, kind=post.kind)
            if edit_url:
                return TechnicalIssueEditTargetOut(
                    kind="cms",
                    edit_url=edit_url,
                    detail=f"Opens the real {client.name} editor for this {post.kind}.",
                )

    server_client = sftp_client_for_site(site)
    if server_client is not None:
        candidate_path = remote_path_for_url(url)
        try:
            server_client.read_file(candidate_path)
        except Exception:
            pass
        else:
            return TechnicalIssueEditTargetOut(
                kind="static_file",
                file_path=candidate_path,
                detail="Not a CMS post — this is a static file on your server.",
            )

    return TechnicalIssueEditTargetOut(
        kind="unavailable",
        detail="Couldn't find a CMS post or a matching file on the server for this URL.",
    )


@router.get("/technical/issues/{issue_id}/edit-target", response_model=TechnicalIssueEditTargetOut)
def get_technical_issue_edit_target_route(issue_id: int, db: Session = Depends(get_db)):
    """So "Mark as fixed manually" isn't a dead end — see
    _resolve_edit_target's docstring for how this resolves."""
    row = db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")
    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")
    return _resolve_edit_target(site, row.url)


@router.get("/edit-target", response_model=TechnicalIssueEditTargetOut)
def get_url_edit_target_route(site_id: int, url: str, db: Session = Depends(get_db)):
    """Module 43 — the same edit-target resolution, but for an arbitrary
    URL rather than a stored technical-issue row: PageSpeed's fix list
    points at specific resource files (a particular .css/.js Lighthouse
    measured wasted bytes on) that never went through the technical
    audit at all, so there's no issue id to key off of here."""
    site = db.query(SeoSite).filter(SeoSite.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {site_id}")
    return _resolve_edit_target(site, url)


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


@router.post("/technical/issues/{issue_id}/ai-suggestion", response_model=TechnicalIssueOut)
def generate_technical_issue_ai_suggestion_route(issue_id: int, db: Session = Depends(get_db)):
    """Module 41 — an Ollama-generated, page-specific explanation of how
    to fix this issue, available for EVERY rule (not gated by
    REMEDIABLE_RULES like /generate-fix is). Advisory only: unlike
    fix_value, nothing ever writes ai_suggestion to the live site — see
    ai/seo/issue_remediation.py's generate_ai_suggestion docstring for
    why that stays a human-only next step for structural issues."""
    row = db.query(SeoTechnicalIssue).filter(SeoTechnicalIssue.id == issue_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No technical issue {issue_id}")

    result = generate_ai_suggestion(row.rule, row.url, row.message, site_id=row.site_id)
    if result.value is None:
        raise HTTPException(status_code=422, detail=result.error or "Could not generate a suggestion for this issue")

    database.save_technical_issue_ai_suggestion(issue_id, result.value)
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
    """Module 58 — payload.run_date (default today) lets this backfill a
    specific past day's digest instead of always today's. payload.
    send_email/email_recipient reuse the same Gmail SMTP sender already
    live for DAR/alert/campaign email (automation/email/sender.py) —
    export/share was previously Slack + a Sheets tab only, no email."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    run_date = payload.run_date or date_cls.today()
    digest = generate_daily_digest(payload.site_id, site.name, run_date=run_date)
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

    database.save_daily_digest(payload.site_id, run_date, digest.narrative, stats_json, slack_delivered)

    if payload.send_email:
        from automation.email.sender import send_raw_email

        recipient = payload.email_recipient or settings.REPORT_RECIPIENT_EMAIL or settings.GMAIL_ADDRESS
        if recipient and send_raw_email(recipient, f"SEO Digest — {site.name} ({run_date.isoformat()})", digest.narrative):
            database.mark_daily_digest_emailed(payload.site_id, run_date)

    db.expire_all()
    return (
        db.query(SeoDailyDigest)
        .filter(SeoDailyDigest.site_id == payload.site_id, SeoDailyDigest.run_date == run_date)
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


@router.post("/digest/rollup/{period}", response_model=DigestRollupOut, status_code=201)
def generate_digest_rollup_route(period: str, payload: DigestRollupGenerateRequest, db: Session = Depends(get_db)):
    """Module 36 — the "every Monday, full week summary" / "monthly
    board report" the blueprint described but nothing ever generated.
    Same manual-trigger-plus-scheduled-cron pattern as /jobs/run-daily-
    cycle: api/main.py's scheduler calls this same function on its own
    schedule, and this lets it be run on demand too.

    Module 58 — period == "custom" takes an arbitrary payload.start_date/
    end_date range, not snapped to a week/month boundary; weekly/monthly
    accept an optional payload.reference_date to pull a specific past
    week's/month's report instead of only ever the current one. This
    used to be query-params-only (site_id/send_to_slack); now a body,
    since there are too many optional fields for that to stay readable."""
    if period not in ("weekly", "monthly", "custom"):
        raise HTTPException(status_code=400, detail="period must be 'weekly', 'monthly', or 'custom'")
    if period == "custom" and (payload.start_date is None or payload.end_date is None):
        raise HTTPException(status_code=400, detail="start_date and end_date are required when period is 'custom'")
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    report = generate_rollup_digest(
        payload.site_id, site.name, period,
        reference_date=payload.reference_date, custom_start=payload.start_date, custom_end=payload.end_date,
    )
    slack_delivered = False
    if payload.send_to_slack:
        slack_delivered = send_slack_message(f"*SEO {period.capitalize()} Roll-Up — {site.name}*\n{report.narrative}")

    period_start = date_cls.fromisoformat(report.period_start)
    period_end = date_cls.fromisoformat(report.period_end)
    database.save_digest_rollup(
        payload.site_id, period, period_start, period_end, report.narrative, report.stats_json, slack_delivered,
    )

    if payload.send_email:
        from automation.email.sender import send_raw_email

        recipient = payload.email_recipient or settings.REPORT_RECIPIENT_EMAIL or settings.GMAIL_ADDRESS
        subject = f"SEO {period.capitalize()} Roll-Up — {site.name} ({report.period_start} to {report.period_end})"
        if recipient and send_raw_email(recipient, subject, report.narrative):
            database.mark_digest_rollup_emailed(payload.site_id, period, period_start, period_end)

    db.expire_all()
    return (
        db.query(SeoDigestRollup)
        .filter(
            SeoDigestRollup.site_id == payload.site_id,
            SeoDigestRollup.period == period,
            SeoDigestRollup.period_start == period_start,
            SeoDigestRollup.period_end == period_end,
        )
        .first()
    )


@router.get("/digest/rollups", response_model=list[DigestRollupOut])
def list_digest_rollups_route(site_id: int, period: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(SeoDigestRollup).filter(SeoDigestRollup.site_id == site_id)
    if period is not None:
        query = query.filter(SeoDigestRollup.period == period)
    return query.order_by(SeoDigestRollup.period_start.desc()).limit(limit).all()


def _sheet_open_url(spreadsheet_id: str, kind: str = "main") -> str:
    """The bare spreadsheet edit URL opens whatever tab the browser last
    had active — for a first-time visitor that's index-0, a human's own
    pre-existing "Sheet1", not any of this app's own tabs. Deep-links
    straight into that kind's own default tab instead (see
    sheets_client.SPREADSHEET_DEFAULT_TAB — the tab most people click
    "Open spreadsheet" to actually check), falling back to the bare URL
    if the gid lookup itself fails for any reason."""
    from automation.seo.sheets_client import SPREADSHEET_DEFAULT_TAB, get_tab_url

    return get_tab_url(spreadsheet_id, SPREADSHEET_DEFAULT_TAB[kind]) or f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


@router.get("/sheets", response_model=SheetsStatusOut)
def get_sheets_status_route(kind: str = "main"):
    """Creates the given kind's spreadsheet on first call (idempotent
    after that — see sheets_client.get_or_create_spreadsheet), shared
    with settings.SEO_SHEETS_SHARE_EMAIL if set. kind is "main" (the
    automated pipeline's own log tabs), "gsc", or "ga4" — Module 56 split
    what used to be one shared spreadsheet into three. configured=False
    with an error message is the honest, expected result until the
    Sheets + Drive APIs are enabled for the Google Cloud project the
    service account belongs to (and in practice, for a brand new kind,
    until a human adopts a sheet they created themselves — see
    /sheets/adopt's docstring)."""
    from automation.seo.sheets_client import get_or_create_spreadsheet

    spreadsheet_id = get_or_create_spreadsheet(kind)
    if spreadsheet_id is None:
        return SheetsStatusOut(
            configured=False,
            error="Could not create the spreadsheet — enable the Google Sheets API and Google Drive API "
            "for this project in Google Cloud Console, then retry, or connect an existing sheet below. "
            "See server logs for the exact error.",
        )
    return SheetsStatusOut(
        configured=True,
        spreadsheet_id=spreadsheet_id,
        url=_sheet_open_url(spreadsheet_id, kind),
    )


@router.post("/sheets/share", response_model=SheetsStatusOut)
def share_sheets_route(payload: SheetsShareRequest):
    from automation.seo.sheets_client import get_or_create_spreadsheet, share_spreadsheet

    spreadsheet_id = get_or_create_spreadsheet(payload.kind)
    if spreadsheet_id is None:
        return SheetsStatusOut(configured=False, error="Spreadsheet doesn't exist yet and couldn't be created.")

    ok = share_spreadsheet(spreadsheet_id, payload.email)
    return SheetsStatusOut(
        configured=ok,
        spreadsheet_id=spreadsheet_id,
        url=_sheet_open_url(spreadsheet_id, payload.kind),
        error=None if ok else f"Could not share with {payload.email} — see server logs",
    )


@router.post("/sheets/adopt", response_model=SheetsStatusOut)
def adopt_sheets_route(payload: SheetsAdoptRequest):
    """Module 36 follow-up — service accounts created after April 2025
    have zero Drive storage quota, so spreadsheets.create (the /sheets
    GET route's fallback) is permanently rejected for accounts like this
    one, verified live. The real path: a human creates a normal Google
    Sheet in their own Drive and shares it with the service account as
    Editor, then gives the app that sheet's id/URL here — writing to an
    existing shared file needs no quota, only creating a new one does.
    Module 56 — payload.kind picks which of the three spreadsheets
    (main/gsc/ga4) this sheet becomes; adopting three separate sheets
    means calling this three times, once per kind."""
    import re

    from automation.seo.sheets_client import adopt_existing_spreadsheet

    match = re.search(r"/d/([a-zA-Z0-9_-]+)", payload.spreadsheet_id_or_url)
    spreadsheet_id = match.group(1) if match else payload.spreadsheet_id_or_url.strip()

    ok = adopt_existing_spreadsheet(spreadsheet_id, payload.kind)
    return SheetsStatusOut(
        configured=ok,
        spreadsheet_id=spreadsheet_id if ok else None,
        url=_sheet_open_url(spreadsheet_id, payload.kind) if ok else None,
        error=None if ok else "Could not read/write this spreadsheet — make sure it's shared with "
        "workpulse-seo-agent@workpulse-ai-506706.iam.gserviceaccount.com as Editor, and the id/URL is correct.",
    )


@router.post("/social/generate", response_model=list[SocialPostOut], status_code=201)
def generate_social_posts_route(payload: SocialGenerateRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    # Loaded once and grown as posts are created, rather than re-querying
    # per platform — see _check_and_store_social_quality's own comment.
    candidates = _load_quality_check_candidates(db, payload.site_id)
    created_ids = []
    for platform in payload.platforms:
        draft = generate_social_post(platform, payload.page_title, payload.content_excerpt, site_id=payload.site_id)
        if draft is None:
            continue  # one platform failing shouldn't fail the whole batch
        post_id = database.create_social_post(
            payload.site_id,
            platform,
            draft.content,
            payload.source_url,
            payload.image_url,
            facebook_account_id=payload.facebook_account_id if platform == "facebook" else None,
        )
        _check_and_store_social_quality(db, post_id, payload.site_id, draft.content, candidates=candidates)
        candidates.append(("social", post_id, f"{platform} post #{post_id}", draft.content))
        created_ids.append(post_id)

    if not created_ids:
        raise HTTPException(status_code=502, detail="Social content generation failed for every requested platform")

    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id.in_(created_ids)).all()


@router.post("/social/{post_id}/image/generate", response_model=SocialPostOut)
def generate_social_post_image_route(post_id: int, payload: ImageGenerateRequest, db: Session = Depends(get_db)):
    """Same image pipeline as the blog route above — Instagram in
    particular has no text-only post type, so this is what actually lets
    an Instagram draft become publishable."""
    row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")

    prompt = payload.prompt or derive_image_prompt(row.content, site_id=row.site_id) or row.content[:200]
    result = generate_and_publish_image(site, prompt, task=f"social_{row.platform}")
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)

    database.set_social_post_image(post_id, result.url)
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.post("/social/{post_id}/image/upload", response_model=SocialPostOut)
async def upload_social_post_image_route(post_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Module 38 — manual image upload counterpart to .../image/generate
    above, same reasoning."""
    row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = upload_image_bytes(site, image_bytes, file.filename or row.platform)
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)

    database.set_social_post_image(post_id, result.url)
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.get("/social", response_model=list[SocialPostOut])
def list_social_posts_route(site_id: int, status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(SeoSocialPost).filter(SeoSocialPost.site_id == site_id)
    if status is not None:
        query = query.filter(SeoSocialPost.status == status)
    return query.order_by(SeoSocialPost.created_at.desc()).limit(limit).all()


@router.patch("/social/{post_id}", response_model=SocialPostOut)
def update_social_post_route(post_id: int, payload: SocialPostUpdate, db: Session = Depends(get_db)):
    """Manual edit of an AI-generated draft — content is a starting point,
    not final; a human can revise wording before approving. Blocked once
    a post is already 'posted' (it's live, editing the record wouldn't
    change what's actually on the platform)."""
    row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    if row.status == "posted":
        raise HTTPException(status_code=409, detail="Can't edit a post that's already been published")

    database.update_social_post_content(post_id, payload.content)
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


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

    publish_one_social_post(post_id)

    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.post("/social/{post_id}/schedule", response_model=SocialPostOut)
def schedule_social_post_route(post_id: int, payload: SocialScheduleRequest, db: Session = Depends(get_db)):
    """Module 41 — sets/clears when this post should auto-publish. Scheduling
    and approval are independent on purpose: a draft can be scheduled ahead
    of time, but the scheduler job only ever picks up posts that are ALSO
    status='approved' — so a scheduled-but-still-draft post won't go out
    just because its time arrived, preserving the human-review gate."""
    row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No social post {post_id}")
    if row.status == "posted":
        raise HTTPException(status_code=409, detail="Can't schedule a post that's already been published")

    scheduled_for = payload.scheduled_for.strftime("%Y-%m-%d %H:%M:%S") if payload.scheduled_for else None
    database.set_social_post_schedule(post_id, scheduled_for)
    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()


@router.post("/social/bulk-approve", response_model=list[SocialBulkActionResultOut])
def bulk_approve_social_posts_route(payload: SocialBulkIdsRequest):
    results = []
    for post_id in payload.post_ids:
        ok = database.set_social_post_status(post_id, "approved")
        results.append(
            SocialBulkActionResultOut(
                post_id=post_id, ok=ok, detail="Approved" if ok else f"No social post {post_id}"
            )
        )
    return results


@router.post("/social/bulk-publish", response_model=list[SocialBulkActionResultOut])
def bulk_publish_social_posts_route(payload: SocialBulkIdsRequest, db: Session = Depends(get_db)):
    results = []
    for post_id in payload.post_ids:
        row = db.query(SeoSocialPost).filter(SeoSocialPost.id == post_id).first()
        if row is None:
            results.append(SocialBulkActionResultOut(post_id=post_id, ok=False, detail=f"No social post {post_id}"))
            continue
        if row.status not in ("approved", "failed"):
            results.append(
                SocialBulkActionResultOut(
                    post_id=post_id, ok=False, detail=f"Must be approved first (current status: {row.status})"
                )
            )
            continue
        result = publish_one_social_post(post_id)
        results.append(SocialBulkActionResultOut(post_id=post_id, ok=result.ok, detail=result.detail))
    return results


@router.post("/social/bulk-generate", response_model=list[SocialPostOut], status_code=201)
def bulk_generate_social_posts_route(payload: SocialBulkGenerateRequest, db: Session = Depends(get_db)):
    """Module 41 — the same generation call /social/generate makes, just
    looped over multiple pasted topics in one request instead of one
    page_title/content_excerpt pair. Each topic becomes its own
    page_title AND content_excerpt (there's no separate "excerpt" for a
    bare pasted topic) — one platform failing for one topic doesn't stop
    the rest, same graceful-degrade-per-item convention as the batch
    /social/generate endpoint already uses per platform."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    candidates = _load_quality_check_candidates(db, payload.site_id)
    created_ids = []
    for topic in payload.topics:
        topic = topic.strip()
        if not topic:
            continue
        for platform in payload.platforms:
            draft = generate_social_post(platform, topic, topic, site_id=payload.site_id)
            if draft is None:
                continue
            post_id = database.create_social_post(
                payload.site_id,
                platform,
                draft.content,
                None,
                payload.image_url,
                facebook_account_id=payload.facebook_account_id if platform == "facebook" else None,
            )
            # Bulk-generation's actual duplicate-content risk is here, not
            # the single-post route's: a topic list with near-duplicate
            # entries (or an AI drifting toward the same phrasing across a
            # long list) is exactly what this catches, checked against the
            # whole batch generated so far plus everything already on the
            # site.
            _check_and_store_social_quality(db, post_id, payload.site_id, draft.content, candidates=candidates)
            candidates.append(("social", post_id, f"{platform} post #{post_id}", draft.content))
            created_ids.append(post_id)

    if not created_ids:
        raise HTTPException(status_code=502, detail="Social content generation failed for every topic/platform combination")

    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id.in_(created_ids)).all()


@router.post("/social/generate-calendar", response_model=list[SocialPostOut], status_code=201)
def generate_social_calendar_route(payload: SocialCalendarGenerateRequest, db: Session = Depends(get_db)):
    """Module 41 — a real 30-day (or however many `days`) content
    calendar: cycles through the given topics (repeating if there are
    fewer topics than days) so every day in the range gets a real,
    LLM-generated post per selected platform, each pre-scheduled for
    that day at `post_time`. Lands as 'draft' like every other generated
    post — a human still has to review and bulk-approve before the
    scheduler will actually auto-publish any of them; a calendar of
    unreviewed AI content going out untouched isn't this feature's job."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    topics = [t.strip() for t in payload.topics if t.strip()]
    if not topics:
        raise HTTPException(status_code=400, detail="At least one topic is required")

    try:
        post_hour, post_minute = (int(part) for part in payload.post_time.split(":", 1))
    except ValueError:
        raise HTTPException(status_code=400, detail="post_time must be in HH:MM format")

    candidates = _load_quality_check_candidates(db, payload.site_id)
    created_ids = []
    for day_offset in range(payload.days):
        day = payload.start_date + timedelta(days=day_offset)
        topic = topics[day_offset % len(topics)]
        scheduled_for = datetime.combine(day, time(post_hour, post_minute)).strftime("%Y-%m-%d %H:%M:%S")

        for platform in payload.platforms:
            draft = generate_social_post(platform, topic, topic, site_id=payload.site_id)
            if draft is None:
                continue
            post_id = database.create_social_post(
                payload.site_id,
                platform,
                draft.content,
                None,
                payload.image_url,
                facebook_account_id=payload.facebook_account_id if platform == "facebook" else None,
            )
            database.set_social_post_schedule(post_id, scheduled_for)
            # A calendar cycles through few topics over many days — the
            # exact scenario most likely to produce near-duplicate posts,
            # so this matters here even more than in bulk-generate above.
            _check_and_store_social_quality(db, post_id, payload.site_id, draft.content, candidates=candidates)
            candidates.append(("social", post_id, f"{platform} post #{post_id}", draft.content))
            created_ids.append(post_id)

    if not created_ids:
        raise HTTPException(status_code=502, detail="Social content generation failed for every day/platform combination")

    db.expire_all()
    return db.query(SeoSocialPost).filter(SeoSocialPost.id.in_(created_ids)).all()


@router.post("/social/export-to-sheet", response_model=SocialExportResult)
def export_social_posts_to_sheet_route(payload: SocialExportRequest, db: Session = Depends(get_db)):
    """Module 41 — the Social tab's own "Export to Sheet" button: every
    generated post for this site (any status) goes into the combined
    "Social Posts" tab, AND into its own per-platform tab (Facebook/
    Instagram/LinkedIn/Twitter) — same shape as GSC Queries/Pages/
    Countries/Devices being separate tabs over the same underlying data,
    so a user can jump straight to e.g. "LinkedIn" instead of scanning a
    Platform column. All tabs overwritten on each export (see
    overwrite_rows), never appended — a re-export always reflects
    current post state (an approval, a publish, a reschedule since the
    last export), not a stale copy."""
    from automation.seo.sheets_client import TAB_HEADERS, format_tab_top_aligned, get_or_create_spreadsheet, overwrite_rows

    # Display names, not the raw lowercase platform enum values — the
    # whole point of this column is to identify which post is for which
    # platform at a glance. PLATFORM_TABS maps the same enum value to the
    # per-platform tab it belongs on (sheets_client.py's own tab names).
    platform_labels = {"linkedin": "LinkedIn", "facebook": "Facebook", "instagram": "Instagram", "twitter": "Twitter/X"}
    platform_tabs = {"linkedin": "LinkedIn", "facebook": "Facebook", "instagram": "Instagram", "twitter": "Twitter"}

    _site_or_404(payload.site_id, db)
    spreadsheet_id = get_or_create_spreadsheet("social")
    if not spreadsheet_id:
        return SocialExportResult(ok=False, detail="No Social Media sheet connected yet — connect one on the Social tab.")

    rows = (
        db.query(SeoSocialPost)
        .filter(SeoSocialPost.site_id == payload.site_id)
        .order_by(SeoSocialPost.created_at.desc())
        .all()
    )
    if not rows:
        return SocialExportResult(ok=False, detail="No social posts yet for this site — generate some first.")

    def _title_from_content(content: str) -> str:
        first_line = content.strip().split("\n", 1)[0]
        return f"{first_line[:97]}..." if len(first_line) > 100 else first_line

    def _shared_fields(row) -> list:
        return [
            _title_from_content(row.content),
            row.content,
            row.status,
            row.scheduled_for.isoformat() if row.scheduled_for else "",
            row.posted_at.isoformat() if row.posted_at else "",
            row.source_url or "",
            row.external_post_id or "",
            row.created_at.isoformat() if row.created_at else "",
        ]

    combined_rows = [
        [_title_from_content(row.content), platform_labels.get(row.platform, row.platform), *_shared_fields(row)[1:]]
        for row in rows
    ]

    if not overwrite_rows("Social Posts", TAB_HEADERS["Social Posts"], combined_rows):
        return SocialExportResult(ok=False, detail="Sheets write failed — see server logs.")
    format_tab_top_aligned("Social Posts")  # best-effort, never undoes the data write above

    for platform, tab_name in platform_tabs.items():
        platform_rows = [_shared_fields(row) for row in rows if row.platform == platform]
        if overwrite_rows(tab_name, TAB_HEADERS[tab_name], platform_rows):
            format_tab_top_aligned(tab_name)
        else:
            logger.warning("Social export: failed to write the %r tab — combined tab still exported fine", tab_name)

    return SocialExportResult(
        ok=True, detail=f"Exported {len(combined_rows)} post(s).", sheet_url=_sheet_open_url(spreadsheet_id, "social")
    )


@router.get("/facebook-accounts", response_model=list[FacebookAccountOut])
def list_facebook_accounts_route(db: Session = Depends(get_db)):
    return db.query(SeoFacebookAccount).order_by(SeoFacebookAccount.created_at.asc()).all()


@router.post("/facebook-accounts", response_model=FacebookAccountOut, status_code=201)
def create_facebook_account_route(payload: FacebookAccountCreate, db: Session = Depends(get_db)):
    account_id = database.create_facebook_account(payload.label, payload.page_id, payload.page_access_token)
    return db.query(SeoFacebookAccount).filter(SeoFacebookAccount.id == account_id).first()


@router.delete("/facebook-accounts/{account_id}", status_code=204)
def delete_facebook_account_route(account_id: int):
    ok = database.delete_facebook_account(account_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No Facebook account {account_id}")


@router.post("/backlinks/pull", response_model=list[BacklinkMentionOut], status_code=201)
def pull_backlinks_route(payload: BacklinkPullRequest, db: Session = Depends(get_db)):
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    provider = get_backlink_provider()
    mentions = provider.fetch_mentions()
    database.upsert_backlink_mentions(payload.site_id, mentions)
    for mention in mentions[:20]:
        _log_to_sheet_safe(
            "Link Monitor",
            [date_cls.today().isoformat(), site.name, mention.source_url, mention.anchor_text or "", "new"],
        )

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
    """Module 33's real automated pipeline (technical audit -> GSC query
    pull -> GSC page pull -> index check -> GA4 -> PageSpeed -> meta
    rewrite opportunities -> digest, per active site) normally fires on
    its own once a day via api/main.py's BackgroundScheduler. This lets it
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


# Module 39 — a process-local guard against double-triggering the bulk
# WebP job for the same site (e.g. an impatient double-click) while a
# real (non-dry-run) run is already in flight. Not a durable/distributed
# lock — this app runs as one process, which is all that's needed here.
_webp_convert_running: set = set()


@router.post("/webp-convert", response_model=BulkConvertReportOut)
def webp_convert_route(payload: WebpConvertRequest, db: Session = Depends(get_db)):
    """Module 39 — scans every published post/page for JPG/PNG <img>
    references, converts each to WebP, uploads it alongside the
    original (nothing is deleted), and rewrites the post to point at
    the new file — see automation/seo/webp_bulk_converter.py's module
    docstring for the full design (caching, backups, dry-run). dry_run
    defaults to True: call it once to see exactly what would happen,
    call it again with dry_run=False once you're satisfied."""
    from automation.seo.webp_bulk_converter import scan_site_images

    site = _site_or_404(payload.site_id, db)

    if not payload.dry_run:
        if payload.site_id in _webp_convert_running:
            raise HTTPException(status_code=409, detail="A conversion run is already in progress for this site")
        _webp_convert_running.add(payload.site_id)

    try:
        client = _cms_client_for(site)
        report = scan_site_images(site, client, dry_run=payload.dry_run)
    finally:
        _webp_convert_running.discard(payload.site_id)

    return report


@router.post("/webp-convert/url", response_model=BulkConvertReportOut)
def webp_convert_url_route(payload: WebpConvertUrlRequest, db: Session = Depends(get_db)):
    """Module 39 follow-up — converts images on one specific page
    (resolved by URL) instead of scanning the whole site. Same
    dry_run/backup/caching behaviour as /webp-convert, same double-
    trigger guard, just for a single CmsClient.find_post_by_url match."""
    from automation.seo.webp_bulk_converter import convert_url_images

    site = _site_or_404(payload.site_id, db)

    if not payload.dry_run:
        if payload.site_id in _webp_convert_running:
            raise HTTPException(status_code=409, detail="A conversion run is already in progress for this site")
        _webp_convert_running.add(payload.site_id)

    try:
        client = _cms_client_for(site)
        report = convert_url_images(site, client, payload.url, dry_run=payload.dry_run)
    finally:
        _webp_convert_running.discard(payload.site_id)

    return report


@router.get("/webp-convert/backups", response_model=list[ContentBackupSummaryOut])
def list_content_backups_route(site_id: int, cms_post_id: Optional[str] = None, limit: int = 50):
    return [dict(row) for row in database.list_content_backups(site_id, cms_post_id, limit)]


@router.get("/webp-convert/backups/{backup_id}", response_model=ContentBackupOut)
def get_content_backup_route(backup_id: int):
    row = database.get_content_backup(backup_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No content backup {backup_id}")
    return dict(row)


@router.post("/blog/generate", response_model=BlogPostOut, status_code=201)
def generate_blog_post_route(payload: BlogGenerateRequest, db: Session = Depends(get_db)):
    """Generates a full blog post draft, immediately runs it through
    module 27.5's own structure checker (analyze_structure) and module
    60's plagiarism/humanization check so a reviewer sees the H1/word-
    count/keyword findings AND originality/AI-pattern findings right
    alongside the draft rather than as a separate manual step, and stores
    it as 'draft' — no CMS call happens here. See /blog/{id}/publish for
    what approval leads to."""
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
    _check_and_store_blog_quality(db, post_id, payload.site_id, draft.content_html)
    _log_to_sheet_safe(
        "Content Pipeline",
        [date_cls.today().isoformat(), site.name, payload.topic, draft.title, "draft", structure.passed],
    )

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/{post_id}/image/generate", response_model=BlogPostOut)
def generate_blog_post_image_route(post_id: int, payload: ImageGenerateRequest, db: Session = Depends(get_db)):
    """Module 36 — generates a featured image (via ai/images/factory.py),
    converts it to WebP, and uploads it to the site's own server via
    Server Access, then attaches the resulting URL to the post. 404s if
    the post doesn't exist; a provider/upload failure comes back as a
    502 with the specific reason (unconfigured image provider, no
    server access, etc.) rather than silently doing nothing."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")

    prompt = payload.prompt or derive_image_prompt(row.content, title=row.title, site_id=row.site_id) or row.title
    result = generate_and_publish_image(site, prompt, task="blog_post")
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)

    database.set_blog_post_image(post_id, result.url)
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/{post_id}/image/upload", response_model=BlogPostOut)
async def upload_blog_post_image_route(post_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Module 38 — manual image upload: same WebP-conversion-then-
    upload-to-the-site pipeline as .../image/generate, just for a file a
    human picked themselves instead of one the AI generated. Same
    Server Access requirement, same failure-reason surfacing."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {row.site_id}")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = upload_image_bytes(site, image_bytes, file.filename or row.title)
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)

    database.set_blog_post_image(post_id, result.url)
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
    draft. Allowed while 'draft', 'approved', or 'failed' — once it's
    actually 'published'/'live' the content already exists in the CMS,
    so editing here wouldn't be reflected there and would just be
    misleading; 'approved'/'failed' still only exist locally."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    if row.status not in ("draft", "approved", "failed"):
        raise HTTPException(
            status_code=409, detail=f"Can't edit a post that's already in the CMS (current status: {row.status})"
        )

    structure = analyze_structure(payload.content, primary_keyword=row.primary_keyword)
    structure_issues_json = json.dumps(
        [{"rule": i.rule, "severity": i.severity, "message": i.message} for i in structure.issues]
    )
    database.update_blog_post(post_id, payload.title, payload.excerpt, payload.content, structure.passed, structure_issues_json)

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.patch("/blog/{post_id}/taxonomy", response_model=BlogPostOut)
def update_blog_post_taxonomy_route(post_id: int, payload: BlogTaxonomyUpdate, db: Session = Depends(get_db)):
    """Module 38 — slug/tags/categories, set before Publish so
    publish_blog_post_route (below) can pass them through to the CMS at
    create_post time. Same widened restriction as content editing above
    ('draft', 'approved', or 'failed') — these become the actual
    WordPress taxonomy/slug the moment the post is created there, so
    once it's actually 'published'/'live' this no longer applies."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    if row.status not in ("draft", "approved", "failed"):
        raise HTTPException(
            status_code=409, detail=f"Can't edit a post that's already in the CMS (current status: {row.status})"
        )

    database.set_blog_post_taxonomy(
        post_id,
        payload.slug,
        json.dumps(payload.tags) if payload.tags is not None else None,
        json.dumps(payload.categories) if payload.categories is not None else None,
    )

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


def _inject_interlinks(site_id: int, post_id: int, title: str, content_html: str) -> str:
    """Module 36 — closes the "no on-publish automation" gap for
    interlinking: queries the vector index (ai/seo/interlink_engine.py)
    for semantically related already-published pages and appends a real
    "Related Reading" section with live links, rather than leaving
    interlink_engine's /interlinks/suggest endpoint as something nobody
    ever calls. Never raises — logs and returns content_html unchanged
    on any failure, since a missing related-reading section is not a
    reason to block publishing."""
    try:
        related = find_related_pages(site_id, f"blog-draft:{post_id}", title, content_html, n_results=5)
    except Exception:
        logger.exception("Interlink lookup failed for blog post %s — publishing without it", post_id)
        return content_html
    if not related:
        return content_html
    items = "".join(f'<li><a href="{p.url}">{p.title}</a></li>' for p in related)
    return f"{content_html}\n<h2>Related Reading</h2>\n<ul>\n{items}\n</ul>"


def _run_post_publish_automation(site, post_id: int, title: str, excerpt: Optional[str], live_url: Optional[str]) -> None:
    """Module 36 — the "when a post is published, the agent also..."
    steps the blueprint described but nothing in this codebase actually
    triggered: OG tags, indexing this page for future interlink
    suggestions, and submitting the live URL to GSC for faster
    (re)crawl. Runs AFTER the CMS publish already succeeded, so a
    failure in any one of these three never affects whether the post
    itself got published — each is independently try/excepted and only
    logged on failure, same graceful-degrade convention as every other
    automated step in this codebase."""
    if not live_url:
        return

    try:
        tags = generate_og_tags(title, excerpt or title, site_id=site.id)
        if tags:
            database.upsert_og_tags(site.id, live_url, title, tags.og_title, tags.og_description)
    except Exception:
        logger.exception("Auto OG-tag generation failed for post %s — publish itself already succeeded", post_id)

    try:
        index_page(site.id, live_url, title, excerpt or title)
    except Exception:
        logger.exception("Interlink indexing failed for post %s — publish itself already succeeded", post_id)

    try:
        submit_url_for_indexing(live_url, "URL_UPDATED")
    except Exception:
        logger.exception("GSC indexing submission failed for post %s — publish itself already succeeded", post_id)


def _do_go_live_blog_post(post_id: int, db: Session) -> tuple[bool, str]:
    """The actual "flip the CMS post to publish/isDraft=false" step —
    shared by the manual /blog/{id}/go-live route and _do_publish_
    blog_post's go_live=True path (the scheduler), same "one code path"
    reasoning as _do_publish_blog_post's own docstring. Assumes the post
    already has a cms_post_id (the route validates this before calling
    in); returns (ok, detail), never raises for an ordinary CMS failure."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        return False, f"No blog post {post_id}"
    site = db.query(SeoSite).filter(SeoSite.id == row.site_id).first()
    if site is None:
        return False, f"No SEO site {row.site_id}"

    client = _cms_client_for(site)
    result = client.update_post(row.cms_post_id, status="publish")
    if result.ok:
        database.mark_blog_post_live(post_id)
        return True, "Live"
    else:
        database.mark_blog_post_go_live_failed(post_id, result.detail)
        return False, result.detail


def _do_publish_blog_post(post_id: int, db: Session, go_live: bool = False) -> tuple[bool, str]:
    """The actual "resolve the CMS client, attach an image, inject
    interlinks, create the CMS draft, run post-publish automation"
    orchestration — shared by the manual /blog/{id}/publish route,
    /blog/bulk-publish, and the recurring scheduler job (ai/seo/
    blog_scheduler.py), same "one code path, not copies that could
    drift" reasoning as automation/seo/social_poster.py's publish_one.
    Takes its own db Session so the scheduler (no FastAPI request in
    scope) can pass in a short-lived SessionLocal() instance — see
    blog_scheduler.py. Returns (ok, detail); never raises for an
    ordinary publish failure (CMS error, missing image provider, etc.),
    only HTTPException for a genuinely missing post/site, matching every
    other route in this file.

    go_live=True immediately follows a successful CMS-draft creation
    with the same "make it actually public" step /blog/{id}/go-live
    does, rather than leaving it sitting as a CMS draft awaiting a human
    to notice and click Go Live. The manual Publish button and bulk-
    publish deliberately keep go_live=False (create-draft-then-human-
    reviews, /blog/{id}/publish's own long-standing behavior); the
    scheduler passes go_live=True — a post someone scheduled for a
    specific time is expected to actually appear on the site at that
    time, not land in an admin queue nobody's watching."""
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

    image_url = row.image_url
    if not image_url:
        try:
            image_prompt = derive_image_prompt(row.content, title=row.title, site_id=row.site_id) or row.title
            image_result = generate_and_publish_image(site, image_prompt, task="blog_post")
            if image_result.ok:
                image_url = image_result.url
                database.set_blog_post_image(post_id, image_url)
        except Exception:
            logger.exception("Auto image generation failed for post %s — publishing without one", post_id)

    content = row.content
    if image_url:
        content = f'<img src="{image_url}" alt="{row.title}" />\n{content}'
    content = _inject_interlinks(row.site_id, post_id, row.title, content)

    client = _cms_client_for(site)
    result = client.create_post(
        title=row.title,
        content=content,
        excerpt=row.excerpt,
        slug=row.slug,
        tags=json.loads(row.tags) if row.tags else None,
        categories=json.loads(row.categories) if row.categories else None,
    )
    if result.ok:
        link = result.post.link if result.post else None
        database.mark_blog_post_published(post_id, result.post.id if result.post else None, link)
        _run_post_publish_automation(site, post_id, row.title, row.excerpt, link)
        if go_live:
            # mark_blog_post_published just wrote cms_post_id through
            # agent/database.py's own (raw sqlite) connection — this
            # SQLAlchemy Session already has `row` in its identity map
            # from the query above, so without expiring it here,
            # _do_go_live_blog_post's own query would hand back that
            # same stale in-memory object (cms_post_id still None)
            # instead of re-reading the row this call just wrote.
            # Verified live: this produced a real 404 to
            # .../posts/None before this fix.
            db.expire_all()
            live_ok, live_detail = _do_go_live_blog_post(post_id, db)
            return live_ok, ("Live" if live_ok else f"Published as a CMS draft, but going live failed: {live_detail}")
        return True, "Published"
    else:
        database.mark_blog_post_failed(post_id, result.detail)
        return False, result.detail


@router.post("/blog/{post_id}/publish", response_model=BlogPostOut)
def publish_blog_post_route(post_id: int, db: Session = Depends(get_db)):
    """'Publish' means "create it as a draft in the CMS" — see
    automation/seo/cms/base.py's create_post docstring for why this
    deliberately never puts a page live on its own; a human still has to
    hit Publish inside WordPress/Webflow itself.

    Module 36 — before pushing to the CMS, auto-attaches a featured
    image (if one hasn't already been generated/set) and injects a
    Related Reading section; after a successful publish, auto-generates
    OG tags, indexes the page for future interlinking, and submits the
    URL to GSC. All of this graceful-degrades — a site with no image
    provider or no server access configured still publishes normally,
    just without those extras."""
    _do_publish_blog_post(post_id, db)
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/{post_id}/schedule", response_model=BlogPostOut)
def schedule_blog_post_route(post_id: int, payload: BlogScheduleRequest, db: Session = Depends(get_db)):
    """Module 59 — sets/clears when this post should auto-publish.
    Scheduling and approval are independent on purpose, same as the
    social-post equivalent: a draft can be scheduled ahead of time, but
    the scheduler job only ever picks up posts that are ALSO
    status='approved' — so a scheduled-but-still-draft post won't go out
    just because its time arrived, preserving the human-review gate."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    if row.status == "live":
        raise HTTPException(status_code=409, detail="Can't schedule a post that's already live")

    scheduled_at = payload.scheduled_at.strftime("%Y-%m-%d %H:%M:%S") if payload.scheduled_at else None
    database.set_blog_post_schedule(post_id, scheduled_at)
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()


@router.post("/blog/bulk-approve", response_model=list[BlogBulkActionResultOut])
def bulk_approve_blog_posts_route(payload: BlogBulkIdsRequest):
    results = []
    for post_id in payload.post_ids:
        ok = database.set_blog_post_status(post_id, "approved")
        results.append(BlogBulkActionResultOut(post_id=post_id, ok=ok, detail="Approved" if ok else f"No blog post {post_id}"))
    return results


@router.post("/blog/bulk-publish", response_model=list[BlogBulkActionResultOut])
def bulk_publish_blog_posts_route(payload: BlogBulkIdsRequest, db: Session = Depends(get_db)):
    """One post's failure (CMS error, transient network issue) never
    stops the rest, same graceful-degrade-per-item convention as the
    social-post bulk-publish route."""
    results = []
    for post_id in payload.post_ids:
        try:
            ok, detail = _do_publish_blog_post(post_id, db)
            results.append(BlogBulkActionResultOut(post_id=post_id, ok=ok, detail=detail))
        except HTTPException as exc:
            results.append(BlogBulkActionResultOut(post_id=post_id, ok=False, detail=str(exc.detail)))
    return results


def _generate_and_save_blog_post(
    db: Session, site: SeoSite, topic: str, min_words: int, generate_image: bool, candidates=None
) -> Optional[int]:
    """Shared by bulk-generate and generate-calendar below: one full
    draft (text via generate_blog_post + structure check, matching
    /blog/generate exactly) plus, if requested, a real featured image via
    the same generate_and_publish_image pipeline /blog/{id}/publish uses.
    Returns the new post id, or None if text generation itself failed
    (an image failure alone doesn't discard an otherwise-good draft —
    same graceful-degrade convention as publish's own auto-image step).
    `candidates` — see _check_and_store_blog_quality's own comment; the
    caller passes one site-wide pool it loaded once, grown as each post
    is created, so a whole bulk/calendar run doesn't re-query per post."""
    draft = generate_blog_post(topic, None, site_id=site.id, min_words=min_words)
    if draft is None:
        return None

    structure = analyze_structure(draft.content_html, primary_keyword=None, min_words=min_words)
    structure_issues_json = json.dumps(
        [{"rule": i.rule, "severity": i.severity, "message": i.message} for i in structure.issues]
    )
    post_id = database.create_blog_post(
        site.id, topic, None, draft.title, draft.excerpt, draft.content_html, structure.passed, structure_issues_json
    )
    _check_and_store_blog_quality(db, post_id, site.id, draft.content_html, candidates=candidates)
    if candidates is not None:
        candidates.append(("blog", post_id, draft.title, draft.content_html))

    if generate_image:
        try:
            image_prompt = derive_image_prompt(draft.content_html, title=draft.title, site_id=site.id) or draft.title
            image_result = generate_and_publish_image(site, image_prompt, task="blog_post")
            if image_result.ok:
                database.set_blog_post_image(post_id, image_result.url)
        except Exception:
            logger.exception("Bulk-generate: image generation failed for post %s — draft still saved without one", post_id)

    return post_id


@router.post("/blog/bulk-generate", response_model=list[BlogPostOut], status_code=201)
def bulk_generate_blog_posts_route(payload: BlogBulkGenerateRequest, db: Session = Depends(get_db)):
    """Module 59 — the same generation call /blog/generate makes, just
    looped over multiple pasted topics in one request. Each topic takes
    roughly 1-3 minutes for the text alone (the slower, higher-quality
    model, same as a single /blog/generate call) plus another 30-90s for
    its image if generate_image is set — a batch of several topics can
    genuinely take many minutes; the frontend uses no request timeout for
    this route for that reason. One topic's failure doesn't stop the
    rest, same graceful-degrade-per-item convention as the social-post
    bulk-generate route."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    candidates = _load_quality_check_candidates(db, payload.site_id)
    created_ids = []
    for topic in payload.topics:
        topic = topic.strip()
        if not topic:
            continue
        post_id = _generate_and_save_blog_post(db, site, topic, payload.min_words, payload.generate_image, candidates=candidates)
        if post_id is not None:
            created_ids.append(post_id)

    if not created_ids:
        raise HTTPException(status_code=502, detail="Blog post generation failed for every topic given")

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id.in_(created_ids)).all()


@router.post("/blog/generate-calendar", response_model=list[BlogPostOut], status_code=201)
def generate_blog_calendar_route(payload: BlogCalendarGenerateRequest, db: Session = Depends(get_db)):
    """Module 59 — a real content calendar for the blog, same mechanism
    as /social/generate-calendar: cycles through the given topics
    (repeating if there are fewer topics than days) so every day in the
    range gets a real, LLM-generated post pre-scheduled for that day at
    post_time. Lands as 'draft' like every other generated post — a
    human still has to review and bulk-approve before the scheduler will
    actually auto-publish any of them."""
    site = db.query(SeoSite).filter(SeoSite.id == payload.site_id).first()
    if site is None:
        raise HTTPException(status_code=404, detail=f"No SEO site {payload.site_id}")

    topics = [t.strip() for t in payload.topics if t.strip()]
    if not topics:
        raise HTTPException(status_code=400, detail="At least one topic is required")

    try:
        post_hour, post_minute = (int(part) for part in payload.post_time.split(":", 1))
    except ValueError:
        raise HTTPException(status_code=400, detail="post_time must be in HH:MM format")

    candidates = _load_quality_check_candidates(db, payload.site_id)
    created_ids = []
    for day_offset in range(payload.days):
        day = payload.start_date + timedelta(days=day_offset)
        topic = topics[day_offset % len(topics)]
        scheduled_at = datetime.combine(day, time(post_hour, post_minute)).strftime("%Y-%m-%d %H:%M:%S")

        post_id = _generate_and_save_blog_post(db, site, topic, payload.min_words, payload.generate_image, candidates=candidates)
        if post_id is not None:
            database.set_blog_post_schedule(post_id, scheduled_at)
            created_ids.append(post_id)

    if not created_ids:
        raise HTTPException(status_code=502, detail="Blog post generation failed for every day given")

    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id.in_(created_ids)).all()


@router.post("/blog/export-to-sheet", response_model=BlogExportResult)
def export_blog_posts_to_sheet_route(payload: BlogExportRequest, db: Session = Depends(get_db)):
    """Module 59 — the Blog tab's own "Export to Sheet" button: every
    generated post for this site (any status) into a "Blog Posts" tab —
    title, status, category, tags, author, slug, primary keyword,
    scheduled time, and its CMS-draft/live link once published.
    Overwritten on each export (see overwrite_rows), never appended — a
    re-export always reflects current post state (an approval/publish/
    reschedule since the last export), same convention as
    /social/export-to-sheet. There's no separate "author" concept
    tracked per blog post — every post this app publishes goes out
    under the site's own configured CMS account, so that account's
    username is the real, truthful answer here."""
    from automation.seo.sheets_client import TAB_HEADERS, format_tab_top_aligned, get_or_create_spreadsheet, overwrite_rows

    site = _site_or_404(payload.site_id, db)
    author = site.cms_username or site.name
    spreadsheet_id = get_or_create_spreadsheet("blog")
    if not spreadsheet_id:
        return BlogExportResult(ok=False, detail="No Blog sheet connected yet — connect one on the Blog tab.")

    rows = (
        db.query(SeoBlogPost)
        .filter(SeoBlogPost.site_id == payload.site_id)
        .order_by(SeoBlogPost.created_at.desc())
        .all()
    )
    if not rows:
        return BlogExportResult(ok=False, detail="No blog posts yet for this site — generate some first.")

    def _joined(json_str: Optional[str]) -> str:
        if not json_str:
            return ""
        try:
            return ", ".join(json.loads(json_str))
        except (TypeError, ValueError):
            return ""

    sheet_rows = [
        [
            row.title,
            row.status,
            _joined(row.categories),
            _joined(row.tags),
            author,
            row.slug or "",
            row.primary_keyword or "",
            row.scheduled_at.isoformat() if row.scheduled_at else "",
            row.cms_post_link or "",
            row.created_at.isoformat() if row.created_at else "",
        ]
        for row in rows
    ]

    if not overwrite_rows("Blog Posts", TAB_HEADERS["Blog Posts"], sheet_rows):
        return BlogExportResult(ok=False, detail="Sheets write failed — see server logs.")
    format_tab_top_aligned("Blog Posts")  # best-effort, never undoes the data write above

    return BlogExportResult(
        ok=True, detail=f"Exported {len(sheet_rows)} post(s).", sheet_url=_sheet_open_url(spreadsheet_id, "blog")
    )


@router.post("/blog/{post_id}/go-live", response_model=BlogPostOut)
def go_live_blog_post_route(post_id: int, db: Session = Depends(get_db)):
    """Module 38 — the explicit, separate 'actually make it public'
    action /blog/{post_id}/publish's own docstring says has always
    needed a human: /publish only ever created a CMS draft. This is
    that human action, callable from the dashboard instead of requiring
    a trip into WordPress/Webflow's own admin — sets status='publish'
    (WordPress) / isDraft=false (Webflow) on the already-created post."""
    row = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No blog post {post_id}")
    if row.status != "published":
        raise HTTPException(
            status_code=409,
            detail=f"Post must be created in the CMS first via Publish (current status: {row.status})",
        )
    if not row.cms_post_id:
        raise HTTPException(status_code=409, detail="No CMS post id on record — publish it again first")

    _do_go_live_blog_post(post_id, db)
    db.expire_all()
    return db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
