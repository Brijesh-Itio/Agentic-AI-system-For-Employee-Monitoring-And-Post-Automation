# WorkPulse AI — API Reference

Generated from the running backend's OpenAPI schema. For request/response bodies, try-it-out and the
authoritative, always-current contract, open the interactive docs at **`http://localhost:8000/docs`**
(Swagger UI) or **`/redoc`**; the raw schema is at `/openapi.json`.

## Conventions

| | |
|---|---|
| Base URL | `http://localhost:8000` (or your deployed API URL) |
| Format | JSON over HTTP; timestamps are ISO 8601 |
| Auth | `Authorization: Bearer <token>` from `POST /api/auth/login`. Public: login, `GET /api/auth/bootstrap-status`, SSO endpoints, `GET /` |
| Roles | `employee`, `manager`, `admin`. Team routes need manager/admin; user administration needs admin |
| Errors | `4xx/5xx` with `{"detail": "…"}` (validation errors return a list under `detail`). The message is safe to show to users |
| Long operations | Some SEO calls run for minutes (blog publish, grammar check, roll-ups). Use client timeouts of several minutes, or the status-polling endpoints (e.g. `/api/seo/sitemap/status`) |
| Secrets | Stored credentials are never returned; responses expose flags such as `cms_app_password_set` |

## Contents (265 endpoints)

- [Google sign-in (SSO)](#google-sign-in-sso) — 3
- [Authentication](#authentication) — 5
- [Activity](#activity) — 6
- [Websites](#websites) — 3
- [Productivity](#productivity) — 8
- [Attendance](#attendance) — 2
- [Company holidays](#company-holidays) — 3
- [DAR entries and templates](#dar-entries-and-templates) — 13
- [Reports](#reports) — 2
- [Departments](#departments) — 7
- [Email templates](#email-templates) — 5
- [Alerts](#alerts) — 5
- [Agent status](#agent-status) — 1
- [Team](#team) — 11
- [Command Mode](#command-mode) — 4
- [LinkedIn](#linkedin) — 3
- [Email campaigns](#email-campaigns) — 5
- [Leads](#leads) — 6
- [Notepad](#notepad) — 3
- [URL redirects](#url-redirects) — 6
- [SEO](#seo) — 163
- [Other](#other) — 1

## Google sign-in (SSO)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/auth/sso/google/callback` | Google Callback |
| `GET` | `/api/auth/sso/google/login` | Google Login |
| `GET` | `/api/auth/sso/status` | Public — lets the frontend show/hide the 'Sign in with Google' button depending on whether an admin has configured credentials. |

## Authentication

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/auth/bootstrap-status` | Public — lets the frontend show 'create the first admin account' instead of a login form when no accounts exist yet at all. |
| `POST` | `/api/auth/change-password` | Change Password |
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/logout` | Stateless JWT — there's no server-side session to invalidate. |
| `GET` | `/api/auth/me` | Me |

## Activity

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/activity/apps/summary` | Get Apps Summary |
| `GET` | `/api/activity/apps/top` | Get Top Apps |
| `GET` | `/api/activity/context-switching` | Hourly context switching score for a date (defaults to today), from module 2's rolled-up hourly_scores (each rollover captures the switch count for its hour). |
| `GET` | `/api/activity/date/{target_date}` | Get Activity By Date |
| `GET` | `/api/activity/idle/date/{target_date}` | Not in module 5's original route list — added for module 10's idle period markers, which need the raw idle_periods rows module 2 already tracks. |
| `GET` | `/api/activity/today` | Get Today Activity |

## Websites

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/websites/date/{target_date}` | Get Websites By Date |
| `GET` | `/api/websites/today` | Get Today Websites |
| `GET` | `/api/websites/top` | Get Top Sites |

## Productivity

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/productivity/daily-scores` | 11.4 — day-by-day focus scores (not week-aggregated) for a line chart. |
| `GET` | `/api/productivity/focus-sessions/today` | 11.5 — every focus run today (reusing module 2.6/11's shared compute_focus_runs), plus the aggregate stats the summary cards need. |
| `GET` | `/api/productivity/heatmap` | 11.6 — hour x day focus-score grid for the past N days. |
| `GET` | `/api/productivity/patterns` | Best-effort patterns computed live from hourly_scores/context_switch_flags. |
| `GET` | `/api/productivity/score/date/{target_date}` | Get Score By Date |
| `GET` | `/api/productivity/score/today` | Get Today Score |
| `GET` | `/api/productivity/summary` | Analytics page's 'Last N Days Average' stat row — same DailyStats rows daily-scores already reads, aggregated instead of listed day by day. |
| `GET` | `/api/productivity/weekly` | Get Weekly Trend |

## Attendance

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/attendance/me` | My Attendance |
| `GET` | `/api/attendance/{user_id}` | Manager/admin view of someone else's attendance — same oversight rule as team.py's per-member activity endpoint. |

## Company holidays

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/holidays` | List Holidays |
| `POST` | `/api/holidays` | Create Holiday |
| `DELETE` | `/api/holidays/{holiday_id}` | Delete Holiday |

## DAR entries and templates

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/reports/dar/all` | Get All Dars |
| `GET` | `/api/reports/dar/date/{target_date}` | Get Dar By Date |
| `GET` | `/api/reports/dar/date/{target_date}/entries` | List Entries |
| `GET` | `/api/reports/dar/date/{target_date}/export` | Export Dar |
| `POST` | `/api/reports/dar/date/{target_date}/import` | Import Dar Csv |
| `POST` | `/api/reports/dar/date/{target_date}/send` | 13.4 — email-resend button. |
| `POST` | `/api/reports/dar/entries` | Create Entry |
| `POST` | `/api/reports/dar/entries/draft` | Asks Ollama to draft dar_entries rows matching the department's template, from the same day log 7.1 already builds. |
| `DELETE` | `/api/reports/dar/entries/{entry_id}` | Delete Entry |
| `PATCH` | `/api/reports/dar/entries/{entry_id}` | Update Entry |
| `POST` | `/api/reports/dar/generate` | Generate Dar Now |
| `GET` | `/api/reports/dar/member/{user_id}/all` | Module 21 extension — same oversight rule as team.py's per-member activity endpoint: anyone can see their own reports, viewing someone else's requires manager/admin. |
| `GET` | `/api/reports/dar/today` | Get Today Dar |

## Reports

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/reports/weekly/generate` | Generate Weekly Report Now |
| `GET` | `/api/reports/weekly/latest` | Get Latest Weekly Report |

## Departments

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/departments` | List Departments |
| `POST` | `/api/departments` | Create Department |
| `GET` | `/api/departments/default/template` | Get Default Template |
| `PUT` | `/api/departments/default/template` | Set Default Template |
| `DELETE` | `/api/departments/{department_id}` | Delete Department |
| `GET` | `/api/departments/{department_id}/template` | Falls back to the default (NULL-department) template when this department has never defined its own, so callers always get something usable instead of a 404. |
| `PUT` | `/api/departments/{department_id}/template` | Set Department Template |

## Email templates

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/email-templates` | List Templates |
| `PUT` | `/api/email-templates/{template_key}` | Update Template |
| `POST` | `/api/email-templates/{template_key}/preview` | Renders the *unsaved* subject/body currently in the editor against sample data, so HR sees the real result before committing it. |
| `POST` | `/api/email-templates/{template_key}/reset` | Reset Template |
| `POST` | `/api/email-templates/{template_key}/send-test` | Send Test |

## Alerts

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/alerts` | Get Alerts |
| `GET` | `/api/alerts/preferences` | Get Preferences |
| `PUT` | `/api/alerts/preferences/{alert_type}` | Update Preference |
| `GET` | `/api/alerts/unread-count` | Get Unread Count |
| `POST` | `/api/alerts/{alert_id}/dismiss` | Dismiss Alert |

## Agent status

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/status` | Get System Status |

## Team

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/team/analysis` | 21.4 — weekly Ollama-powered team analysis, computed on demand. |
| `GET` | `/api/team/member/{user_id}/activity` | 21.3 — individual member view. |
| `GET` | `/api/team/member/{user_id}/features` | Module 21 extension — which automatic monitoring features an admin has enabled for this employee. |
| `PUT` | `/api/team/member/{user_id}/features/{feature}` | Admin-only, same as role changes and password resets — a manager gets oversight of what's already tracked, not control over whether tracking happens at all. |
| `GET` | `/api/team/overview` | Team Overview |
| `GET` | `/api/team/users` | List Users |
| `POST` | `/api/team/users` | Create User |
| `DELETE` | `/api/team/users/{user_id}` | Delete User |
| `POST` | `/api/team/users/{user_id}/password` | Admin sets or resets any account's login password — e.g. |
| `PATCH` | `/api/team/users/{user_id}/profile` | Admin-only edit of name/email — e.g. |
| `PATCH` | `/api/team/users/{user_id}/role` | Update User Role |

## Command Mode

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/command` | Run Command |
| `POST` | `/api/command/cancel/{job_id}` | Cancel Job |
| `GET` | `/api/command/history` | Job History |
| `GET` | `/api/command/status/{job_id}` | Get Job Status |

## LinkedIn

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/linkedin/post` | Post Now |
| `GET` | `/api/linkedin/posts` | List Posts |
| `GET` | `/api/linkedin/status` | Linkedin Status |

## Email campaigns

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/email/campaign/run` | Synchronous, like /api/reports/dar/generate — a real Ollama call per lead plus real SMTP sends, so this can take a while for a large batch. |
| `GET` | `/api/email/campaigns` | List Campaign Log |
| `GET` | `/api/email/campaigns/stats` | Campaign Stats |
| `POST` | `/api/email/follow-ups/run` | Trigger Follow Ups |
| `POST` | `/api/email/test-connection` | Test Connection |

## Leads

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/leads` | List Leads |
| `POST` | `/api/leads` | 20.4's dedup rule: same name+company is an update, not a duplicate. |
| `POST` | `/api/leads/research` | Synchronous, like /api/reports/dar/generate — real Playwright browser sessions against Google/LinkedIn, so this can take a while. |
| `DELETE` | `/api/leads/{lead_id}` | Delete Lead |
| `GET` | `/api/leads/{lead_id}` | Get Lead |
| `PATCH` | `/api/leads/{lead_id}` | Update Lead |

## Notepad

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/notes` | List Notes |
| `DELETE` | `/api/notes/{note_id}` | Delete Note |
| `PUT` | `/api/notes/{note_id}` | Upsert Note |

## URL redirects

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/redirects` | List Redirects |
| `POST` | `/api/redirects` | Create Redirect |
| `DELETE` | `/api/redirects/{redirect_id}` | Delete Redirect |
| `PUT` | `/api/redirects/{redirect_id}` | Update Redirect |
| `POST` | `/api/redirects/{redirect_id}/apply` | (Re-)writes this rule into its site's .htaccess and verifies it live. |
| `POST` | `/api/redirects/{redirect_id}/test` | Requests the rule's live source URL for real (without following the redirect) and checks the status code and Location it answers with. |

## SEO

### Sites, CMS, server access

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/cms/posts` | Cms Posts |
| `GET` | `/api/seo/cms/status` | Cms Status |
| `GET` | `/api/seo/sites` | List Sites |
| `POST` | `/api/seo/sites` | Create Site |
| `DELETE` | `/api/seo/sites/{site_id}` | Delete Site |
| `PATCH` | `/api/seo/sites/{site_id}/cms-config` | Update Site Cms Config |
| `PATCH` | `/api/seo/sites/{site_id}/google-config` | Update Site Google Config |
| `GET` | `/api/seo/sites/{site_id}/images` | Media Library for the blog editor: every image already published for this site through the app (blog featured images and social post images), newest first. |
| `POST` | `/api/seo/sites/{site_id}/images/upload` | Upload Site Image Route |
| `PATCH` | `/api/seo/sites/{site_id}/ssh-config` | Direct server access (SFTP, FTP, or FTPS), for the files a CMS REST API can't reach (wp-content/mu-plugins/*.php, .htaccess). |
| `GET` | `/api/seo/sites/{site_id}/ssh-status` | Ssh Status |

### Technical audit and issues

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/edit-target` | Get Url Edit Target Route |
| `POST` | `/api/seo/technical/audit` | Run Technical Audit Route |
| `POST` | `/api/seo/technical/audit/page` | Run Page Tag Audit Route |
| `GET` | `/api/seo/technical/issues` | List Technical Issues Route |
| `POST` | `/api/seo/technical/issues/{issue_id}/ai-suggestion` | An Ollama-generated, page-specific explanation of how to fix this issue, available for EVERY rule (not gated by REMEDIABLE_RULES like /generate-fix is). |
| `POST` | `/api/seo/technical/issues/{issue_id}/apply-fix` | Writes the generated fix_value to the real CMS post — the one action in this whole feature that touches the live site. |
| `POST` | `/api/seo/technical/issues/{issue_id}/approve` | Approve Technical Issue Route |
| `GET` | `/api/seo/technical/issues/{issue_id}/edit-target` | So "Mark as fixed manually" isn't a dead end — see _resolve_edit_target's docstring for how this resolves. |
| `POST` | `/api/seo/technical/issues/{issue_id}/generate-fix` | Produces a real, ready-to-use replacement value (not just advice text) for the small set of rules where one is knowable at all. |
| `POST` | `/api/seo/technical/issues/{issue_id}/reject` | Reject Technical Issue Route |
| `POST` | `/api/seo/technical/issues/{issue_id}/resolve` | Closes out an issue the human fixed themselves, outside this app (most technical-audit rules have no safe automatic CMS write at all — see issue_applier.py's docstring). |

### Blog

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/blog` | List Blog Posts Route |
| `POST` | `/api/seo/blog/bulk-approve` | Bulk Approve Blog Posts Route |
| `POST` | `/api/seo/blog/bulk-generate` | The same generation call /blog/generate makes, just looped over multiple pasted topics in one request. |
| `POST` | `/api/seo/blog/bulk-publish` | One post's failure (CMS error, transient network issue) never stops the rest, same graceful-degrade-per-item convention as the social-post bulk-publish route. |
| `POST` | `/api/seo/blog/export-to-sheet` | Export Blog Posts To Sheet Route |
| `POST` | `/api/seo/blog/generate` | Generate Blog Post Route |
| `POST` | `/api/seo/blog/generate-calendar` | Generate Blog Calendar Route |
| `PATCH` | `/api/seo/blog/{post_id}` | Lets a reviewer fix a draft directly — tighten wording, clear a word-count minimum, adjust a heading — instead of only Approve/Reject on whatever the LLM produced. |
| `POST` | `/api/seo/blog/{post_id}/approve` | Approve Blog Post Route |
| `POST` | `/api/seo/blog/{post_id}/faqs/generate` | Generate Blog Post Faqs Route |
| `POST` | `/api/seo/blog/{post_id}/go-live` | The explicit, separate 'actually make it public' action /blog/{post_id}/publish's own docstring says has always needed a human: /publish only ever created a CMS draft. |
| `POST` | `/api/seo/blog/{post_id}/grammar-check` | Manual re-check — e.g. |
| `POST` | `/api/seo/blog/{post_id}/image/generate` | Generate Blog Post Image Route |
| `POST` | `/api/seo/blog/{post_id}/image/upload` | Upload Blog Post Image Route |
| `POST` | `/api/seo/blog/{post_id}/interlinks/generate` | Generate Blog Post Interlinks Route |
| `PATCH` | `/api/seo/blog/{post_id}/meta` | Update Blog Post Meta Route |
| `POST` | `/api/seo/blog/{post_id}/meta/generate` | Manual regenerate — e.g. |
| `POST` | `/api/seo/blog/{post_id}/publish` | Publish Blog Post Route |
| `POST` | `/api/seo/blog/{post_id}/quality-check` | Manual re-check — e.g. |
| `POST` | `/api/seo/blog/{post_id}/reject` | Reject Blog Post Route |
| `POST` | `/api/seo/blog/{post_id}/schedule` | Sets/clears when this post should auto-publish. |
| `PATCH` | `/api/seo/blog/{post_id}/taxonomy` | Slug/tags/categories, set before Publish so publish_blog_post_route (below) can pass them through to the CMS at create_post time. |
| `POST` | `/api/seo/interlinks/index` | Index Page Route |
| `POST` | `/api/seo/interlinks/suggest` | Suggest Interlinks Route |

### Content tools

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/seo/content/analyze` | Analyze Content Route |
| `POST` | `/api/seo/content/faq` | Generate Faq Route |
| `POST` | `/api/seo/content/quality-check` | General-purpose version of the same check the generation routes run automatically — lets any piece of content (e.g. |
| `GET` | `/api/seo/og-tags` | List Og Tags Route |
| `POST` | `/api/seo/og-tags/generate` | Generate Og Tags Route |

### Jobs and automation

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/jobs` | List Jobs |
| `POST` | `/api/seo/jobs/run-daily-cycle` | Run Daily Cycle Now |
| `POST` | `/api/seo/jobs/trigger` | Trigger Job |
| `GET` | `/api/seo/llm-usage` | List Llm Usage |

### Backlinks and brand mentions

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/backlinks` | List Backlinks Route |
| `POST` | `/api/seo/backlinks/competitor-analysis` | Competitor Analysis Route |
| `POST` | `/api/seo/backlinks/domain-authority` | Domain/Page Authority, spam score, Domain Rating, and estimated organic traffic for one domain (semrush-seo3's /dapa.php), verified live this session. |
| `POST` | `/api/seo/backlinks/domain-authority/bulk` | Bulk Domain Authority Route |
| `POST` | `/api/seo/backlinks/pull` | Pull Backlinks Route |
| `POST` | `/api/seo/backlinks/top` | Top Backlinks Route |
| `POST` | `/api/seo/backlinks/website-traffic` | Website Traffic Route |
| `POST` | `/api/seo/backlinks/{mention_id}/draft-outreach` | Draft Outreach Route |
| `POST` | `/api/seo/keywords/difficulty` | A THIRD distinct RapidAPI product/host (semrush-seo10.p.rapidapi.com), same key/application as the Magic Tool endpoint above. |
| `POST` | `/api/seo/keywords/insights` | Keyword Insights Route |
| `POST` | `/api/seo/keywords/rapidapi-check` | A third-party RapidAPI keyword wrapper (NOT Semrush's own official API, see automation/seo/rapidapi_keyword_client.py's module docstring). |
| `POST` | `/api/seo/keywords/research` | Keyword Research Route |
| `GET` | `/api/seo/semrush` | List Semrush Metrics |
| `POST` | `/api/seo/semrush/backlink-gap` | Semrush Backlink Gap |
| `GET` | `/api/seo/semrush/backlinks` | Semrush Backlinks |
| `POST` | `/api/seo/semrush/check` | Check Semrush Metrics |
| `GET` | `/api/seo/semrush/referring-domains` | Semrush Referring Domains |

### Images and WebP

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/seo/webp-convert` | Webp Convert Route |
| `GET` | `/api/seo/webp-convert/backups` | List Content Backups Route |
| `GET` | `/api/seo/webp-convert/backups/{backup_id}` | Get Content Backup Route |
| `POST` | `/api/seo/webp-convert/url` | Converts images on one specific page (resolved by URL) instead of scanning the whole site. |

### Search Console sitemaps

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/site-verification` | List Verified Sites Route |
| `POST` | `/api/seo/sitemaps` | Real Search Console Sitemaps list for this property. |
| `POST` | `/api/seo/sitemaps/delete` | Same permission requirement as /sitemaps/submit above. |
| `POST` | `/api/seo/sitemaps/submit` | Registers a sitemap with Search Console. |

### Digests and roll-ups

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/digest` | List Digests Route |
| `POST` | `/api/seo/digest/generate` | Payload.run_date (default today) lets this backfill a specific past day's digest instead of always today's. |
| `GET` | `/api/seo/digest/metrics` | The metrics a report can be limited to — feeds the frontend's picker so its list can't drift from what generate_daily_digest/ generate_rollup_digest actually accept. |
| `POST` | `/api/seo/digest/rollup/{period}` | The "every Monday, full week summary" / "monthly board report" the blueprint described but nothing ever generated. |
| `GET` | `/api/seo/digest/rollups` | List Digest Rollups Route |
| `POST` | `/api/seo/overview/export-to-sheet` | Overview Export To Sheet Route |

### Server files (SFTP/FTP)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/server/backups` | List Server File Backups Route |
| `POST` | `/api/seo/server/backups` | Create Server File Backup Route |
| `GET` | `/api/seo/server/backups/{backup_id}` | Get Server File Backup Route |
| `POST` | `/api/seo/server/backups/{backup_id}/restore` | Writes a backup's content back to its original path. |
| `DELETE` | `/api/seo/server/file` | Server Delete File |
| `GET` | `/api/seo/server/file` | Server Read File |
| `PUT` | `/api/seo/server/file` | Server Write File |
| `GET` | `/api/seo/server/list` | Server List Dir |
| `POST` | `/api/seo/server/rename` | Server Rename File |

### PageSpeed

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/pagespeed` | List Pagespeed |
| `POST` | `/api/seo/pagespeed/check` | Check Pagespeed |
| `GET` | `/api/seo/pagespeed/{result_id}/opportunities` | Pagespeed Opportunities |

### Search Console

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/gsc` | List Gsc |
| `POST` | `/api/seo/gsc/country` | Country-dimension breakdown, live (stateless, no local table — this data is cheap to re-fetch and isn't fed into any existing pipeline the way query/page dimensions are). |
| `POST` | `/api/seo/gsc/device` | Device-dimension breakdown (DESKTOP/MOBILE/TABLET). |
| `POST` | `/api/seo/gsc/export-all-to-sheet` | Gsc Export All To Sheet Route |
| `POST` | `/api/seo/gsc/export-to-sheet` | Gsc Export To Sheet Route |
| `GET` | `/api/seo/gsc/pages` | List Gsc Pages |
| `POST` | `/api/seo/gsc/pages/live` | Page-dimension breakdown, live — see /gsc/queries/live above for why this is separate from the persisted /gsc/pages/pull. |
| `POST` | `/api/seo/gsc/pages/pull` | Page-dimension GSC pull ("CTR by page") — see /gsc/pull above for the query-dimension equivalent this mirrors. |
| `POST` | `/api/seo/gsc/pull` | Pull Gsc |
| `POST` | `/api/seo/gsc/queries/live` | Gsc Queries Live Route |
| `GET` | `/api/seo/gsc/rank-alerts` | Diffs today's query positions against the last pull before it — see ai/seo/rank_alerts.py. |
| `POST` | `/api/seo/gsc/search-appearance` | Search-appearance-dimension breakdown (which SERP feature type impressions came from). |
| `POST` | `/api/seo/gsc/timeseries` | Gsc Timeseries Route |

### Google Analytics (GA4)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/ga4` | List Ga4 |
| `POST` | `/api/seo/ga4/countries/live` | Ga4 Countries Live Route |
| `POST` | `/api/seo/ga4/devices/live` | Ga4 Devices Live Route |
| `POST` | `/api/seo/ga4/events` | GA4's own "Events: Event name" report. |
| `POST` | `/api/seo/ga4/export-all-to-sheet` | Ga4 Export All To Sheet Route |
| `POST` | `/api/seo/ga4/pages/live` | Ga4 Pages Live Route |
| `POST` | `/api/seo/ga4/pull` | Pull Ga4 |
| `GET` | `/api/seo/ga4/realtime` | Active users right now, broken down by country, matching the real GA4 UI's own Home/Realtime report. |
| `GET` | `/api/seo/ga4/realtime/by-audience` | GA4's own "Active users by Audience" realtime tile — empty when the property has no GA4 Audiences configured, same honest empty state the real GA4 UI shows. |
| `GET` | `/api/seo/ga4/realtime/by-device` | Ga4 Realtime By Device Route |
| `GET` | `/api/seo/ga4/realtime/by-minute` | The "Active users per minute" bar chart on GA4's own Realtime overview report. |
| `GET` | `/api/seo/ga4/realtime/by-page` | GA4's own "Views by Page title and screen name" realtime tile. |
| `POST` | `/api/seo/ga4/sources/live` | Ga4 Sources Live Route |
| `POST` | `/api/seo/ga4/timeseries` | Per-day sessions/bounce rate/conversions, the trend- chart data behind the Analytics Performance panel's chart, matching /gsc/timeseries above. |

### Indexing and URL inspection

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/seo/indexing/inspect` | Inspect Url Route |
| `GET` | `/api/seo/indexing/status` | List Index Status Route |
| `GET` | `/api/seo/indexing/submissions` | List Indexing Submissions Route |
| `POST` | `/api/seo/indexing/submit` | Submit For Indexing Route |

### Sitemap generator

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/sitemap/download` | Sitemap Download |
| `GET` | `/api/seo/sitemap/file` | Sitemap File |
| `POST` | `/api/seo/sitemap/generate` | Starts a full generation in the background (a big site takes minutes); the panel polls /sitemap/status for progress. |
| `POST` | `/api/seo/sitemap/publish` | Uploads the last generated files to the server again and (re)submits to Google — e.g. |
| `PUT` | `/api/seo/sitemap/settings` | Sitemap Settings |
| `GET` | `/api/seo/sitemap/status` | Sitemap Status |

### Social

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/social` | List Social Posts Route |
| `POST` | `/api/seo/social` | Create a post by hand (the Create part of Social's CRUD) — the AI generator above is the other way in. |
| `POST` | `/api/seo/social/bulk-approve` | Bulk Approve Social Posts Route |
| `POST` | `/api/seo/social/bulk-delete` | Bulk Delete Social Posts Route |
| `POST` | `/api/seo/social/bulk-generate` | The same generation call /social/generate makes, just looped over multiple pasted topics in one request instead of one page_title/content_excerpt pair. |
| `POST` | `/api/seo/social/bulk-publish` | Bulk Publish Social Posts Route |
| `POST` | `/api/seo/social/export-to-sheet` | Export Social Posts To Sheet Route |
| `POST` | `/api/seo/social/generate` | Generate Social Posts Route |
| `POST` | `/api/seo/social/generate-calendar` | Generate Social Calendar Route |
| `DELETE` | `/api/seo/social/{post_id}` | Real deletion — a draft/rejected/failed post a human doesn't want cluttering the list actually goes away, not just gets hidden. |
| `PATCH` | `/api/seo/social/{post_id}` | Manual edit of an AI-generated draft — content is a starting point, not final; a human can revise wording before approving. |
| `POST` | `/api/seo/social/{post_id}/approve` | Approve Social Post Route |
| `POST` | `/api/seo/social/{post_id}/image/generate` | Same image pipeline as the blog route above — Instagram in particular has no text-only post type, so this is what actually lets an Instagram draft become publishable. |
| `POST` | `/api/seo/social/{post_id}/image/upload` | Manual image upload counterpart to .../image/generate above, same reasoning. |
| `POST` | `/api/seo/social/{post_id}/publish` | Publish Social Post Route |
| `POST` | `/api/seo/social/{post_id}/quality-check` | Manual re-check counterpart — see check_blog_post_quality_route. |
| `POST` | `/api/seo/social/{post_id}/reject` | Reject Social Post Route |
| `POST` | `/api/seo/social/{post_id}/schedule` | Sets/clears when this post should auto-publish. |

### Social — Facebook Pages

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/facebook-accounts` | List Facebook Accounts Route |
| `POST` | `/api/seo/facebook-accounts` | Create Facebook Account Route |
| `DELETE` | `/api/seo/facebook-accounts/{account_id}` | Delete Facebook Account Route |

### Meta rewrite queue

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/meta-rewrites` | List Meta Rewrites |
| `PATCH` | `/api/seo/meta-rewrites/{item_id}` | Lets a reviewer edit the AI-drafted title/description before approving it — the draft is a starting point, not the final copy. |
| `POST` | `/api/seo/meta-rewrites/{item_id}/approve` | Marks a rewrite reviewed and approved. |
| `POST` | `/api/seo/meta-rewrites/{item_id}/reject` | Reject Meta Rewrite Route |

### Google Sheets

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/seo/sheets` | Get Sheets Status Route |
| `POST` | `/api/seo/sheets/adopt` | Adopt Sheets Route |
| `POST` | `/api/seo/sheets/share` | Share Sheets Route |

## Other

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root |

