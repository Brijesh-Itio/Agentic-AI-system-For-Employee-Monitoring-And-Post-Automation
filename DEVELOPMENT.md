# WorkPulse AI — Development Guide

The engineering reference for WorkPulse AI: how the system is put together, how to run and configure it,
the conventions the code follows, and how each subsystem — especially the SEO suite — works internally.

| Looking for | Go to |
|---|---|
| What the product does, quick start | [`README.md`](README.md) |
| How to *use* the dashboard | [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) |
| Deploying to Railway / Vercel, packaging the agent | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| The original per-module build spec and test log | [`docs/MODULE_SPECIFICATIONS.md`](docs/MODULE_SPECIFICATIONS.md) (archive) |
| API endpoint index | [`docs/API.md`](docs/API.md); the live contract is `http://localhost:8000/docs` (Swagger UI) |

## Contents

1. [Product and principles](#1-product-and-principles)
2. [System architecture](#2-system-architecture)
3. [Repository layout](#3-repository-layout)
4. [Technology stack](#4-technology-stack)
5. [Local development setup](#5-local-development-setup)
6. [Configuration reference](#6-configuration-reference)
7. [Backend](#7-backend)
8. [Frontend](#8-frontend)
9. [SEO suite](#9-seo-suite)
10. [Desktop agent](#10-desktop-agent)
11. [Data and storage](#11-data-and-storage)
12. [Testing and verification](#12-testing-and-verification)
13. [Operations and troubleshooting](#13-operations-and-troubleshooting)
14. [Coding conventions](#14-coding-conventions)
15. [Build, release and deployment](#15-build-release-and-deployment)
16. [Module index](#16-module-index)
17. [Known limitations](#17-known-limitations)

---

## 1. Product and principles

WorkPulse AI combines three things in one system:

- **Work intelligence** — a desktop agent tracks activity; the backend scores focus, builds timelines and
  attendance, writes AI Daily Activity Reports (DAR), and raises alerts.
- **SEO operations** — technical audits, Google Search Console / Analytics / PageSpeed, an AI blog and social
  pipeline, sitemap generation, redirects, all run per registered website and partly on a daily schedule.
- **Business automation** — LinkedIn posting, email campaigns, lead research and a natural-language Command Mode.

Principles that shape the code:

| Principle | Consequence |
|---|---|
| **Local-first AI** | All inference goes through Ollama by default. No paid cloud AI is required. Claude / OpenAI exist behind the same provider interface for the SEO layer but are off unless configured. |
| **Autonomous, with a human gate where it matters** | Scheduled jobs run without clicks (daily SEO cycle, scheduled posts). Anything that publishes or changes a live site goes through an explicit approve / publish step. |
| **Degrade, don't crash** | Integration clients never raise past their caller: they return `None` / a result object with `ok=False` and a reason. A missing credential or an unreachable service disables one feature, not the app. |
| **Honest failure reporting** | A failure is stored and shown with its real reason (e.g. Google's permission message), never swallowed or replaced with a generic error. |
| **Additive schema changes** | Existing installs must keep working. Columns are added with `ALTER TABLE … ADD COLUMN`, never by dropping data. |
| **Least surprise for existing features** | New work must not change the behaviour of features it doesn't concern. Model choices, timeouts and defaults are set per feature, not globally. |

---

## 2. System architecture

```
                         ┌──────────────────────────────────────────────┐
                         │                 FastAPI process                │
┌────────────────┐       │  routes (api/routes/*)                         │       ┌───────────────┐
│ Desktop agent  │       │  auth + RBAC (api/auth.py)                     │ REST  │  React SPA    │
│ agent/         │──────▶│  BackgroundScheduler (APScheduler, main.py)    │◀─────▶│  frontend/    │
│ tray .exe      │ SQLite│  LangGraph Master Agent + SEO Master Agent     │       │  (Vite)       │
└────────────────┘  file │  LLM / image / CMS provider factories          │       └───────────────┘
                         └───────┬───────────────┬──────────────┬─────────┘
                                 │               │              │
                          workpulse.db       Ollama          External services
                          (SQLite, WAL)    (local models)    Google APIs · CMS · SFTP/FTP
                          chromadb/                          Gmail · social platforms
                          sitemaps/
```

**Process model.** One API process hosts the REST routes *and* the APScheduler `BackgroundScheduler`. Long
operations (sitemap generation, blog publish, LLM calls) run on worker threads or inside a request with a
generous timeout; the UI polls where a job outlives a request (see [sitemap generation](#94-sitemap-generator)).
The desktop agent is a separate process (one per employee) that writes to the same SQLite file.

**Two database layers, one file.**

| Layer | File | Used for |
|---|---|---|
| Raw `sqlite3` (schema owner) | `agent/database.py` | `SCHEMA`, migrations, the agent's writes, and most data-access helpers used by the AI/SEO code |
| SQLAlchemy models | `api/database.py` | Typed reads and writes from FastAPI routes |

`agent/database.py` creates every table (`CREATE TABLE IF NOT EXISTS`) and applies additive columns through
`_ensure_extra_columns`. When you add a column, add it to **both** the migration dictionary there and the
SQLAlchemy model in `api/database.py`.

**Request flow (typical SEO action).** Browser → `axios` (`frontend/src/api/index.ts`) → `/api/seo/...` route →
per-site credentials loaded from `seo_sites` → integration client in `automation/seo/` → result stored in a
`seo_*` table → JSON back. The client never receives stored secrets (only `*_set` booleans).

---

## 3. Repository layout

```
workpulse-ai/
├── README.md                     Product overview and quick start
├── DEVELOPMENT.md                This file
├── requirements.txt              Python dependencies (pinned)
├── requirements-build.txt        Extra dependencies for building the agent .exe
├── .env.example                  Every supported environment variable, documented
├── start.bat / setup.bat         One-command install + run (wrappers for scripts/setup.py)
├── start-servers.bat             One-click launcher: API + dashboard in two windows, opens the browser
├── stop-servers.bat              Stops whatever is listening on ports 8000 and 5173
├── Procfile, railway.json        Railway API deployment
├── workpulse-agent.spec          PyInstaller spec for the desktop agent
│
├── agent/                        Desktop tracking agent (Windows)
│   ├── main.py                   Entry point (source run); tray_main.py is the packaged entry point
│   ├── app_tracker.py            Active window / process tracking
│   ├── browser_tracker.py        Website detection from window titles
│   ├── idle_detector.py          Idle + break detection
│   ├── time_intelligence.py      Work windows, meeting-aware idle subtraction
│   ├── calendar_tracker.py       Reads a local .ics export
│   ├── file_watcher.py           Optional shared-folder activity (off until configured)
│   ├── attendance.py             Check-in / check-out and late-mark logic
│   ├── sync.py                   Optional push of local data to the API
│   ├── database.py               SQLite schema, migrations and data-access helpers  ← schema owner
│   ├── config.py / runtime_config.py   Constants and workpulse-config.json handling
│   └── data/                     Runtime logs and data (git-ignored)
│
├── api/                          FastAPI backend
│   ├── main.py                   App factory, routers, CORS, scheduler jobs, lifespan
│   ├── config.py                 pydantic Settings (reads .env)
│   ├── auth.py                   JWT, bcrypt, get_current_user, require_role
│   ├── database.py               SQLAlchemy models + session
│   ├── schemas.py                Pydantic request/response models
│   ├── middleware/               Request logging, auth helpers
│   └── routes/                   One module per area (see §7.2)
│
├── ai/                           AI layer
│   ├── ollama_client.py          Thin Ollama wrapper (timeouts, token caps)
│   ├── llm/                      Provider interface: ollama (default), claude, openai; retry; usage logging
│   ├── images/                   Image provider interface: image_worker, fastsd, pexels, puter, stability
│   ├── master_agent.py           LangGraph Master Agent (Command Mode, daily planning)
│   ├── sub_agents/               linkedin, email, research, reporting, tracker, facebook agents
│   ├── dar_generator.py          Daily Activity Report generation
│   ├── productivity_scorer.py    Classification + focus score
│   ├── pattern_analyser.py       Behaviour patterns
│   ├── team_analysis.py          Weekly team analysis
│   ├── rag.py / memory.py        ChromaDB-backed retrieval and agent memory
│   ├── seo_master_agent.py       LangGraph daily SEO pipeline
│   └── seo/                      SEO content: blog, social, digests, quality, grammar, interlinking, meta rewrites
│
├── automation/                   Integrations (mostly network clients)
│   ├── linkedin/ facebook/ instagram/ twitter/   Social posting
│   ├── email/                    Gmail SMTP sender, campaign, templates
│   ├── leads/                    Lead finder, enricher, store
│   └── seo/                      Google (GSC, GA4, Sheets, PageSpeed, indexing, sitemaps), CMS adapters,
│                                 crawler, technical audit, sitemap generator, server access (SFTP/FTP), backlinks
│
├── frontend/                     React SPA
│   └── src/
│       ├── App.tsx               Routes and guards
│       ├── api/index.ts          All HTTP calls, typed
│       ├── context/              Auth, theme, sidebar, toast, page-active
│       ├── layout/               App shell, sidebar, header, KeepAliveOutlet
│       ├── pages/                One folder per page (Seo/SeoPage.tsx is the largest)
│       └── components/           Shared UI (shadcn-style primitives, charts, editors)
│
├── scripts/                      setup.py, start_all.py, build_exe.bat, generate_icon.py
├── docs/                         USER_GUIDE, DEPLOYMENT, MODULE_SPECIFICATIONS
├── sitemaps/                     Generated sitemap files per site (runtime, created on demand)
└── chromadb/, data/, *.db        Runtime state (git-ignored)
```

---

## 4. Technology stack

| Layer | Technology | Notes |
|---|---|---|
| Language / runtime | Python 3.11+, Node 18+ | Agent is Windows-only (`pywin32`) |
| API | FastAPI 0.115, Uvicorn, Pydantic 2, SQLAlchemy 2 | |
| Scheduling | APScheduler `BackgroundScheduler` | Started in the FastAPI lifespan |
| Database | SQLite, WAL, `foreign_keys=ON` | Postgres is deliberately deferred — see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) |
| Auth | python-jose (JWT, 24 h default), bcrypt | |
| AI | Ollama (`qwen3:1.7b` main, `phi3:mini` fast, `nomic-embed-text` embeddings) | Models configurable |
| Orchestration | LangGraph, langchain-core | Master Agent and SEO daily cycle are real `StateGraph`s |
| Vector store | ChromaDB | Classification cache, RAG, interlinking |
| Crawling | requests + BeautifulSoup | No lxml dependency, on purpose |
| Browser automation | Playwright | LinkedIn / social posting |
| Server access | paramiko (SFTP), ftplib (FTP/FTPS) | For site files, redirects, sitemaps, image upload |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query v5, React Router, TipTap, CodeMirror | |
| Packaging | PyInstaller | Agent → single `.exe` |

**Not allowed without an explicit, documented decision:** paid per-token AI APIs in the core pipeline, browser
extensions for tracking, and any dependency that needs a C toolchain to install.

---

## 5. Local development setup

### 5.1 One command

```bash
start.bat                          # Windows
python3 scripts/setup.py --start   # macOS / Linux
```

`scripts/setup.py` is idempotent and uses only the standard library. It checks Python and Node, creates
`.venv`, installs `requirements.txt`, downloads the Playwright browser, creates `.env` with a generated
`SECRET_KEY`, installs the frontend packages, creates the database, smoke-tests the backend import, pulls the
Ollama models and writes `workpulse-config.json`. Flags: `--start`, `--agent`, `--check`, `--skip-models`,
`--skip-playwright`, `--skip-frontend`, `--build-agent`, `--api-port`, `--host`.

### 5.2 Manual, four processes

```bash
ollama serve                                    # 1. models
python -m uvicorn api.main:app --port 8000      # 2. API   (no --reload — see below)
cd frontend && npm run dev                      # 3. dashboard on :5173
python -m agent.main                            # 4. desktop agent (optional, Windows)
```

| Service | Default URL |
|---|---|
| API | `http://localhost:8000` (Swagger at `/docs`) |
| Dashboard | `http://localhost:5173` |
| Ollama | `http://localhost:11434` |
| Optional local image generator (FastSD CPU) | `http://localhost:8100` — run it with `--port 8100` |

> **Do not use `uvicorn --reload`.** In this project the reloader has been observed to detect a change, log
> "Reloading…", and then never finish restarting the worker — silently serving stale code. Restart the process
> after backend changes. The Vite dev server does hot-reload the frontend.

### 5.3 First run

Open the dashboard. On an empty database the login page offers **Create the Admin Account**; that first user is
the admin. Sign in, open **SEO**, and register a site.

---

## 6. Configuration reference

### 6.1 Backend — `.env` → `api/config.py`

Values are loaded by pydantic `Settings` from `.env` at the project root. `.env.example` is the canonical,
commented list; this table groups them.

| Group | Variables | Default / note |
|---|---|---|
| Core | `SECRET_KEY` | **Must be changed.** Signs JWTs. |
| | `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 |
| | `CORS_ORIGINS` | JSON list; default `["http://localhost:5173"]` |
| | `DATABASE_URL` | SQLite file in the project root |
| Local AI | `OLLAMA_BASE_URL` | `http://localhost:11434` |
| | `OLLAMA_MODEL` | `qwen3:1.7b` — long-form writing |
| | `OLLAMA_FAST_MODEL` | `phi3:mini` — classification and short outputs |
| | `OLLAMA_TIMEOUT_SECONDS` | 120 — fast-model calls |
| | `OLLAMA_GENERATE_TIMEOUT_SECONDS` | 600 — main-model calls |
| SEO LLM | `SEO_LLM_PROVIDER_DEFAULT` | `ollama`; `claude` / `openai` need `CLAUDE_API_KEY` / `OPENAI_API_KEY` |
| Email | `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `REPORT_RECIPIENT_EMAIL` | Gmail App Password, not the account password |
| SSO | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `API_PUBLIC_URL`, `FRONTEND_URL` | Blank = SSO off |
| Google (SEO) | `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` | Path to the service-account key file |
| | `GSC_SITE_URL` | Fallback GSC property when exactly one site exists; per-site value wins |
| | `GA4_PROPERTY_ID`, `PAGESPEED_API_KEY` | |
| CMS | `WORDPRESS_URL/USERNAME/APP_PASSWORD`, `WEBFLOW_*` | Fallbacks; per-site values are stored in `seo_sites` |
| SEO automation | `SEO_AUTOMATION_ENABLED` (True), `SEO_AUTOMATION_HOUR` (6) | Daily cycle + startup catch-up |
| Images | `IMAGE_PROVIDER_DEFAULT` (`image_worker`), `IMAGE_WORKER_URL/API_KEY`, `PEXELS_API_KEY`, `STABILITY_API_KEY`, `PUTER_AUTH_TOKEN`, `FASTSD_API_URL` | |
| Social | `LINKEDIN_EMAIL/PASSWORD`, `FACEBOOK_*`, `INSTAGRAM_*` | LinkedIn stores a session cookie file after first login |
| Notifications | `SLACK_WEBHOOK_URL` | Digest delivery |
| Research | `BACKLINK_PROVIDER_DEFAULT` (`google_alerts`), `GOOGLE_ALERTS_RSS_URL`, `SEMRUSH_API_KEY`, `SEMRUSH_DATABASE`, `RAPIDAPI_*`, `AHREFS_API_KEY` | Ahrefs is a documented extension point, not wired |
| Sheets | `SEO_SHEETS_SHARE_EMAIL` | |

### 6.2 Per-site configuration (stored in the database)

Entered in **SEO → Overview**, stored in `seo_sites` (and `app_settings` for spreadsheet links). Secrets are
write-only over the API — responses expose booleans such as `cms_app_password_set`.

| Setting | Columns |
|---|---|
| Google property / GA4 property | `gsc_site_url`, `ga4_property_id` |
| CMS login | `cms_type`, `cms_base_url`, `cms_username`, `cms_app_password`, `cms_api_token`, `cms_collection_id` |
| Server access | `ssh_host`, `ssh_port`, `ssh_username`, `ssh_password`, `ssh_protocol` (`sftp` / `ftp` / `ftps`) |

The connection cards use a **Saved / Change** pattern: once saved, fields lock and show *Saved*; **Change**
unlocks them, **Save** is disabled until something differs, and **Cancel** restores the stored values.

### 6.3 Desktop agent

| Source | Purpose |
|---|---|
| `agent/config.py` | Constants: idle threshold (5 min), work hours (09:00–19:00), attendance windows, sync interval, log path |
| Environment | `WORKPULSE_API_URL`, `WORKPULSE_USER_ID`, `WORKPULSE_LOG_LEVEL`, `WORKPULSE_FILE_WATCH_ROOTS`, calendar path |
| `workpulse-config.json` | Written by the packaged `.exe` on first run (API URL, user id, name). Git-ignored. Deliberately contains **no** email credentials. |

---

## 7. Backend

### 7.1 Authentication and access control

- `POST /api/auth/login` returns a JWT (`sub` = user id, `role` claim). Passwords are bcrypt-hashed.
- `get_current_user` is the FastAPI dependency for any authenticated route; `require_role(...)` builds
  `require_oversight` (manager + admin) and `require_admin`.
- `GET /api/auth/bootstrap-status` (public) tells the frontend to show the *create first admin* form.
- **Data scoping is enforced server-side.** Personal-data routes (activity, websites, productivity, reports,
  alerts, DAR entries, command, status) resolve the user from the token; an employee asking for someone else's
  data gets 403.
- Optional Google SSO (`/api/auth/sso/*`) only signs in **existing** accounts matched by email.
- SEO routes are open to all authenticated roles (by product decision); Team routes require manager/admin.

### 7.2 Routers

All mounted in `api/main.py`. Counts are endpoints per module.

| Prefix | Module | Endpoints | Purpose |
|---|---|---|---|
| `/api/auth`, `/api/auth/sso` | `auth.py`, `sso.py` | 5 + 3 | Login, setup, password change, Google SSO |
| `/api/activity`, `/api/websites`, `/api/productivity` | | 6 / 3 / 8 | Tracked activity, sites visited, scores |
| `/api/attendance`, `/api/holidays` | | 2 / 3 | Attendance, company holidays |
| `/api/reports`, `/api/reports/dar` | `reports.py`, `dar_entries.py` | 8 / 7 | DAR reports, weekly reports, structured entries, import/export |
| `/api/departments`, `/api/email-templates` | | 7 / 5 | DAR templates per department, mail templates |
| `/api/alerts`, `/api/status` | | 5 / 1 | Smart alerts, agent status |
| `/api/team` | `team.py` | 11 | Overview, member views, admin controls, AI analysis |
| `/api/command` | `command.py` | 4 | Command Mode jobs (submit, status, cancel, history) |
| `/api/linkedin`, `/api/email`, `/api/leads` | | 3 / 5 / 6 | Automation |
| `/api/notes` | `notes.py` | 3 | Notepad |
| `/api/redirects` | `redirects.py` | 6 | URL redirects and `.htaccess` sync |
| **`/api/seo`** | **`seo.py`** | **~165** | The SEO suite — see [§9](#9-seo-suite) |

### 7.3 Scheduler

Defined in the `lifespan` of `api/main.py` on one `BackgroundScheduler`.

| Job id | Schedule | What it does |
|---|---|---|
| `seo_daily_cycle` | Daily at `SEO_AUTOMATION_HOUR` (06:00), if `SEO_AUTOMATION_ENABLED` | Runs the SEO pipeline for every active site |
| `seo_daily_cycle_catchup` | Once, 15 s after startup | Same run; idempotent per (site, job, day), so a no-op if the cron already ran. Exists because the app is often started by hand and a fixed cron time gets missed. |
| `scheduled_blog_posts` | Every 1 min | Publishes approved posts whose `scheduled_at` has passed |
| `scheduled_social_posts` | Every 5 min | Publishes approved social posts whose `scheduled_for` has passed |
| `sitemap_auto_update` | Every 3 h (first run 2 min after start) | Regenerates and republishes sitemaps older than ~23 h for sites with auto-update on |
| `seo_weekly_rollup` | Mondays 07:30 | Weekly AI summary per site |
| `seo_monthly_rollup` | 1st of month 07:45 | Monthly AI summary per site |
| `server_file_backup_cleanup` | Daily 03:30 | Purges server-file backups older than 15 days |

Housekeeping jobs (backups, scheduled posts, roll-ups, sitemaps) are **not** gated by
`SEO_AUTOMATION_ENABLED`; they only act on things a human already approved or opted into.

### 7.4 LLM layer (`ai/llm`)

`get_provider(task, site_id)` returns an `LLMProvider` (`generate(prompt, fast=False, max_tokens=None)` →
`LLMResult(ok, text, error)`), wrapped in a logger that writes every call to `llm_usage_log`. Providers are
`ollama` (default), `claude`, `openai`. Rules for callers:

- Always check `result.ok`; never assume text. Provide a deterministic fallback.
- **Choose the model per feature.** `fast=True` selects `phi3:mini` (120 s limit); the default is `qwen3:1.7b`
  (600 s limit). On CPU, generation speed is roughly a few words per second, so *time = reply length*.
  Cap replies with `max_tokens` (mapped to Ollama `num_predict`) and split long inputs into chunks
  (see `ai/seo/grammar_checker.py` for the pattern: chunking, capped replies, tolerant JSON parsing,
  a time budget, partial results).
- Small models emit imperfect JSON. Parse tolerantly (salvage complete objects, repair missing quotes) and retry
  once before giving up (`ai/seo/content_structure.py::_parse_faq_pairs`).
- The frontend timeout for an endpoint must exceed its server-side worst case (see §8.4).

### 7.5 Logging

`agent/logging_config.setup_logging()` is called at API start. Use `logging`, never `print`. Log the exception
with `logger.exception(...)` where it is handled, and store a user-readable reason on the record.

---

## 8. Frontend

### 8.1 Structure and routing

| Route | Page | Guard |
|---|---|---|
| `/login`, `/sso-callback` | Auth | public |
| `/`, `/timeline`, `/attendance`, `/reports`, `/analytics`, `/command`, `/linkedin`, `/email`, `/seo`, `/notepad`, `/settings` | Pages | authenticated |
| `/team`, `/team/:userId` | Team | authenticated **and** manager/admin (`OversightRoute`) |

`layout/KeepAliveOutlet.tsx` keeps visited pages mounted (hidden) so switching pages does not lose state or
cancel work in progress; a `PageActiveContext` tells pages when they are the visible one.

### 8.2 Data fetching

- **TanStack Query v5** for reads (`useQuery`) and writes (`useMutation`). Query keys are namespaced
  (`["seo", "issues", siteId]`); a mutation invalidates the keys it changes.
- All HTTP lives in `src/api/index.ts` as small typed functions. Never call axios from a component.
- Server errors are turned into text by `utils/serverError.ts::serverErrorDetail(err, fallback)`; surface the
  server's `detail` so users see the real reason.
- Notifications use `ToastContext` (`useToast()`); toasts render above the header (`z-[100000]`) and errors stay
  longer than successes.

### 8.3 SEO page architecture (`pages/Seo/SeoPage.tsx`)

- A site selector at the top scopes everything below it; the selection persists in `localStorage`
  (`workpulse-seo-selected-site-id`).
- Ten tabs render from one `TABS` array: **Overview, Technical Audit, Performance, Search Console, Analytics,
  Indexing, Social, Blog, Backlinks, Redirection.**
- **Keep-alive tabs.** A tab mounts on first visit and then stays mounted (hidden) so a running audit, digest or
  bulk job keeps its progress when you switch tabs. `openedTabs` (a ref) records which have been visited.
- **Deep links.** The active tab is in the URL (`/seo?tab=blog`). Tab buttons are real links: a plain click
  switches in place; Ctrl/Cmd/Shift-click and middle-click open the tab in a new browser tab.
- Each tab is a component composed of self-contained cards; a card owns its queries and mutations.
- **Feature flags for hidden UI.** Some cards are kept in the code but not rendered until their prerequisites
  exist. Flip the constant to bring them back:

  | Constant | Hides | Enable when |
  |---|---|---|
  | `SHOW_SEMRUSH_PANELS` | Semrush Domain Overview, Backlinks & Referring Domains, Backlink Gap (Backlinks tab) | `SEMRUSH_API_KEY` is set |
  | `SHOW_RECRAWL_PANEL` | "Request re-crawl" (Indexing tab) | The Google Indexing API is enabled for the project |

  The Site Verification card was removed from the Search Console tab (its backend route remains).

### 8.4 Timeouts

The axios default is 15 s. Any endpoint that runs an AI model or crawls must set an explicit timeout above its
server-side worst case, otherwise the browser reports a failure while the server is still working (this caused
false "publish failed" messages). Current values: blog publish 10 min, grammar check 10 min, FAQ generation
5 min, roll-up 12 min, go-live 2 min, daily digest 2 min.

### 8.5 Rich text editor

`components/Reports/RichTextEditor.tsx` (TipTap) is shared by DAR comments and the blog editor. Options are
opt-in props: `headings` (H1–H3, tables), `imageBlocks` (block inserter + image upload / library), and
`copyButton` (toolbar button that copies the content as rich HTML + plain text). Only the blog post editor turns
on `copyButton`.

### 8.6 Build

```bash
cd frontend
npm run build      # tsc -b && vite build — type errors fail the build
npm run lint
```

`npm run build` is the required check before considering frontend work done.

---

## 9. SEO suite

Everything under `/api/seo`, `automation/seo/`, `ai/seo/`, `ai/seo_master_agent.py` and the SEO page.
A **site** (`seo_sites`) is the unit everything hangs off; `base_url` is validated as a public address at
creation and again at crawl time (`automation/seo/url_safety.py`, SSRF protection).

### 9.1 Daily pipeline (`ai/seo_master_agent.py`)

A LangGraph `StateGraph`, run per active site:

```
planning → technical_audit → gsc_pull → gsc_pages_pull → index_check → ga4_pull
        → pagespeed_check → meta_opportunity → daily_digest → completion_compiler
```

Each node goes through `_run_job`, which records a `seo_job_runs` row keyed by **(site, job type, date)**. A
second trigger the same day is skipped, and a failure marks that node failed without stopping the rest. History
shows in **Overview → Automation Job History**.

### 9.2 Feature map

| Feature | Backend | AI / logic | Tab |
|---|---|---|---|
| Technical audit | `automation/seo/crawler.py`, `technical_audit.py` (10 detectors) | — | Technical Audit |
| Issue fixes | `issue_applier.py`, `server_access.py`, `cms/` | `ai/seo/issue_remediation.py` | Technical Audit |
| Single-page tag audit | `page_tag_audit.py` | — | Technical Audit |
| PageSpeed | `pagespeed_client.py` | — | Performance |
| Search Console | `gsc_client.py` | `ai/seo/rank_alerts.py`, `meta_rewrite_generator.py` | Search Console, Overview |
| Analytics (GA4) | `ga4_client.py` | — | Analytics |
| Index coverage | `indexing_client.py` | — | Indexing |
| Sitemaps | `sitemap_generator.py`, `sitemap_service.py`, `sitemap_client.py` | — | Search Console |
| Blog | `cms/wordpress_client.py`, `cms/webflow_client.py` | `ai/seo/blog_content.py`, `content_structure.py`, `grammar_checker.py`, `content_quality.py`, `interlink_engine.py`, `blog_scheduler.py` | Blog |
| Social | `social_poster.py`, `automation/linkedin/…` | `ai/seo/social_content.py`, `social_scheduler.py` | Social |
| Images | `ai/images/*`, `ai/seo/image_pipeline.py`, `webp_converter.py`, `webp_bulk_converter.py` | `image_prompt.py` | Blog, Social, Overview |
| Digests / roll-ups | `slack_notifier.py` | `daily_digest.py`, `rollup_digest.py`, `report_metrics.py` | Overview |
| Backlinks / research | `backlinks/`, `semrush_client.py`, `rapidapi_*` | `outreach_drafter.py` | Backlinks |
| Redirects | `htaccess_redirects.py` | — | Redirection |
| Sheets export | `sheets_client.py` | — | Overview, Social, Blog |

### 9.3 Google integration

Authentication is a from-scratch service-account OAuth2 flow (`automation/seo/google_auth.py`, JWT signed with
the existing `python-jose`), no Google SDK. Facts that matter operationally:

- The service account is a **user on each Search Console property**. *Restricted* is enough for reporting;
  **URL Inspection and sitemap submit/delete need *Full* or *Owner*.** A missing permission surfaces as a real
  Google 403, which the UI shows (the Inspect failure message names the account email and the fix).
- Each Google API must be **enabled separately** in Cloud Console (Search Console, Analytics Data, Sheets,
  Indexing, PageSpeed). "API has not been used in project…" means exactly that.
- The property URL must match Search Console exactly, including the trailing slash and any subdirectory
  (`https://example.com/demo/`).
- Google's Sitemaps API needs the sitemap's **full URL**; the backend expands a bare `sitemap.xml` against the
  site's base URL.
- Site Verification, and the Indexing API used for "request re-crawl", need extra setup (Workspace delegation /
  API enablement) and are hidden or removed in the UI for that reason.

### 9.4 Sitemap generator

Files: `automation/seo/sitemap_generator.py` (pure discovery + XML), `sitemap_service.py` (state, publishing,
scheduling); routes `/api/seo/sitemap/*`; UI: **Search Console → Sitemap Generator**.

**Discovery** merges four sources, then de-duplicates by normalised URL:

1. WordPress REST API (pages, posts, categories, tags — paginated, real modified dates, embedded images/videos).
2. Blog posts published through the app (`seo_blog_posts` with status `live`).
3. Any sitemap the site already serves (index files followed; used only as crawl seeds).
4. A threaded same-origin crawl (8 workers, default cap 5,000 pages) that **verifies** each URL: HTTP 200, HTML,
   not `noindex`, no redirect, canonical points to itself. It also extracts images (`img`, `og:image`) and videos
   (YouTube / Vimeo embeds, `<video>`).

**Output** is a single `sitemap.xml` with `<image:image>` and `<video:video>` extensions, ordered
**home → other pages → blog listing → posts (newest first) → categories → tags**. Only a site exceeding
Google's limits (50,000 URLs or ~40 MB) is split into `sitemap-pages/posts/categories/tags*.xml` under a
`sitemapindex`. Images and videos are attached to the page that shows them (the sitemap format has no
standalone image entries).

**`<lastmod>`** is only ever a date the site actually reported (WordPress `modified_gmt`, `article:modified_time`,
`Last-Modified`, or the site's previous sitemap). When a crawled page's **content hash** differs from the last
run, its `lastmod` becomes "now". A first sighting with no known date has no `lastmod` — stamping every URL
"today" makes Google distrust the field.

**State and storage.** Files and the entry list (`entries.json`) are in `sitemaps/<site_id>/`; run state is JSON
in `app_settings` under `seo_sitemap_state_<site_id>`. Generation runs on a background thread with a per-site
lock; the UI polls `/sitemap/status` every 2 s while `status == "running"`.

**Publishing** (`sitemap_service.publish`): finds the document root over SFTP/FTP (checks `""`, `/public_html`,
`/www`, `/htdocs`, `/public`, `/httpdocs` for WordPress/index markers), backs up the previous `sitemap.xml`
into `seo_server_file_backups`, uploads, deletes files from a previous split layout, then **fetches the public
URL to verify it is live** before recording success and submitting to Search Console. Without server access,
files can be downloaded (`/sitemap/file`, `/sitemap/download`).

**Automatic updates.** (a) `sitemap_auto_update` regenerates sites already generated once, when ~a day old.
(b) When a blog post goes live, `schedule_touch` adds the URL to the stored list (20 s debounce) and republishes
without a crawl. The technical audit's orphan-page check follows sitemap index files, so it works with either
layout.

### 9.5 Technical audit

`crawl_site` (BFS, polite delay) feeds `run_all_detectors` (broken links, missing/duplicate titles and meta,
missing canonical, schema, orphan pages, redirect chains, crawl depth, hreflang, robots conflicts). Findings are
upserted into `seo_technical_issues`; the upsert never changes the status of an issue a human already reviewed.
The **Technical Audit** tab lists them (pending / approved / rejected / resolved), and for approved issues can
generate a ready-to-use fix (for example replacement title or meta text), apply it to the CMS or via server
access, or open the target file in **Overview → Server Files**.

### 9.6 Blog pipeline

`draft → approved → published (CMS draft) → live`, plus `failed` (retryable) and `rejected`.

1. **Generate** (`ai/seo/blog_content.py`): the article only, targeting **700–800 words** with at most one retry (and
   only if the draft is under 85 % of the minimum). The draft is saved and returned immediately. The extras — originality
   check, meta title/description and keyword density, five FAQs (`content_structure.generate_faq`, tolerant parser +
   one retry), internal links and the grammar check, plus the image for bulk runs — are then prepared by one background
   worker (`_start_blog_followups` in `api/routes/seo.py`). `GET /api/seo/blog/followups` reports the current step per
   post, and the Blog tab polls it and shows "preparing the extras" on each card. Bulk and calendar generation create
   all drafts first, then queue their extras. Measured on the local CPU: article ≈ 3 min, extras ≈ 5 min more.
2. **Checks:** structure/word count, plagiarism + AI-detection score (`content_quality.py`), and grammar
   (`grammar_checker.py`: ≈150-word chunks, ≤8 chunks, capped replies, 7-minute budget, partial results).
3. **Approve** (human) → **Publish** creates a **draft in the CMS** — it never makes a page public on its own.
   Publish attaches a featured image (generated if missing), injects interlinks, and creates the draft, then runs
   best-effort post-publish steps (OG tags, interlink index, an indexing-submission attempt) that never affect the result.
   The featured image is inserted **centered, right after the first paragraph** (`_insert_featured_image` in
   `api/routes/seo.py`), not above the headline.
4. **Go Live** flips the CMS post to published and schedules the sitemap update.
5. `blog_scheduler` can auto-publish + go live approved posts at their `scheduled_at`.

An unexpected exception during publish is stored on the post as its failure reason so it can be retried, rather
than surfacing as a bare 500.

### 9.7 Social pipeline

Posts (`seo_social_posts`) for LinkedIn, X/Twitter, Instagram, Facebook. **Create** by AI (single, bulk, or a
30-day content calendar) or by hand (**Posts → Add post**); **edit** text, platform, source URL and image URL;
**delete** anything not yet posted; **images** by AI (**Generate image**) or upload; per-platform character
limits are enforced in the UI; **schedule**, **approve**, **publish**. Instagram cannot publish without an
image. Only LinkedIn is auto-posted through Playwright; the other platforms use the human review queue unless
their API credentials are set. Facebook supports multiple Pages (`seo_facebook_accounts`).

### 9.8 Digests and roll-ups

`daily_digest.py` (fast model) summarises the day's numbers and can post to Slack; `rollup_digest.py` (main
model, notes capped and truncated in the prompt, deterministic fallback narrative that says *AI summary
unavailable — press Generate to retry*) produces weekly, monthly or custom-period reports. Both honour the
metric picker (`report_metrics.py`).

### 9.9 Server access

`automation/seo/server_access.py` wraps SFTP (paramiko) and FTP/FTPS behind one interface
(`list_dir`, `read_file`, `write_file`, `mkdir_p`, `rename_file`, `delete_file`, binary variants). It backs
**Overview → Server Files** (a browser/editor with a 15-day backup-and-restore history), image upload, redirect
sync to `.htaccess`, WebP conversion, and sitemap publishing. Web-root detection is by marker files, since the FTP
root is often not the document root.

### 9.10 Adding a new SEO feature — checklist

1. Client in `automation/seo/` that never raises: return `None` or `Result(ok, detail)`; log with context.
2. Route in `api/routes/seo.py` using `_site_or_404`; load credentials from the site row; validate URLs.
3. Persist through `agent/database.py` (add table/columns to the schema and migrations) and the SQLAlchemy model.
4. Typed function in `frontend/src/api/index.ts` with an explicit timeout.
5. A self-contained card in the right tab: loading, empty, error (with the server's reason) and success states.
6. If it takes more than a few seconds: background thread + status polling, or a raised timeout — never a 15 s default.
7. `npm run build`; then exercise it in a real browser.

---

## 10. Desktop agent

`agent/main.py::start_components()` initialises the database and starts these components, each on its own
thread, all writing to the local SQLite file:

| Component | Behaviour |
|---|---|
| `AppTracker` | Polls the foreground window every second → `activity_logs`, `daily_stats`; writes the liveness heartbeat (`agent_heartbeat`) that drives the dashboard's active / idle / offline status |
| `CalendarTracker` | Re-reads a local `.ics` export every 5 minutes into `calendar_events`, so meetings are not counted as idle |
| `FileActivityWatcher` | Native filesystem events for configured shared folders; inert until `WORKPULSE_FILE_WATCH_ROOTS` is set |
| `TimeIntelligenceEngine` | Work windows, idle / break classification (5-minute idle threshold), context-switch flags, and the daily weekly-trend calculation at 18:00 |
| `BrowserTracker` | Website detection from window titles (no browser extension, by decision) → `websites` |
| `AlertMonitor` | Focus checks every minute and wellbeing checks every 15 minutes → `alerts` |
| `MasterAgentScheduler` | Runs the 18:00 completion cycle: the day's report and the scheduled automation (LinkedIn, campaigns) |
| `LiveScoringScheduler` | Recomputes live productivity scores every 60 seconds |

`agent/sync.py` contains the optional push of local data to the API; it is not part of the default component set.

Screenshot capture was **removed** by product decision; existing rows are untouched but nothing produces new ones.
An employee's dashboard is empty until an agent runs with `WORKPULSE_USER_ID` equal to that login's user id.
`agent/tray_main.py` is the packaged entry point (windowed, tray icon, HKCU autostart, first-run setup dialog).
Build with `scripts/build_exe.bat` / `pyinstaller workpulse-agent.spec`.

---

## 11. Data and storage

### 11.1 Database tables

| Area | Tables |
|---|---|
| Tracking | `activity_logs`, `daily_stats`, `context_switch_flags`, `idle_periods`, `breaks`, `hourly_scores`, `weekly_trends`, `user_patterns`, `websites`, `file_activity_logs`, `calendar_events`, `agent_heartbeat` |
| Reports | `dar_reports`, `weekly_reports`, `dar_templates`, `dar_entries`, `tasks`, `departments`, `company_holidays` |
| People / access | `users`, `feature_flags`, `alerts`, `alert_preferences` |
| Automation | `jobs`, `post_log`, `campaign_log`, `leads`, `email_templates`, `notes`, `url_redirects` |
| Platform | `app_settings` (key/value), `llm_usage_log` |
| SEO core | `seo_sites`, `seo_job_runs`, `seo_technical_issues`, `seo_daily_digests`, `seo_digest_rollups` |
| SEO data | `seo_gsc_queries`, `seo_gsc_pages`, `seo_ga4_pages`, `seo_pagespeed_results`, `seo_semrush_metrics`, `seo_index_status`, `seo_indexing_submissions`, `seo_meta_rewrite_queue`, `seo_og_tags` |
| SEO content | `seo_blog_posts`, `seo_social_posts`, `seo_facebook_accounts`, `seo_backlink_mentions`, `seo_webp_conversions`, `seo_content_backups`, `seo_server_file_backups` |

Schema changes: edit `SCHEMA` / the `_…_EXTRA_COLUMNS` dictionaries in `agent/database.py` (additive only), mirror
in `api/database.py`, and never run destructive migrations on existing data.

### 11.2 Files on disk (all git-ignored)

| Path | Contents |
|---|---|
| `workpulse.db` (+ `-wal`, `-shm`) | The database. Back up all three, or use SQLite's online backup. |
| `sitemaps/<site_id>/` | Generated `sitemap*.xml` and `entries.json` |
| `chromadb/` | Vector store |
| `agent/data/` | Agent logs and runtime data |
| `.env`, `workpulse-config.json`, `linkedin_cookies.json` | Secrets and local config — never commit or share |

---

## 12. Testing and verification

The project relies on **real end-to-end verification** rather than mock-heavy suites. The expected bar for a
change:

| Change | Verify by |
|---|---|
| Backend logic | Import check (`python -c "import api.main"`), then call the real route against the running API with a token |
| Integration client | A real call against a real service or a controlled local one; assert the failure path (bad credentials, timeout) shows an honest reason |
| Frontend | `npm run build` (type check), then drive the real page in a headless browser (Playwright) and assert visible behaviour, not just that it renders |
| AI feature | Run with the real local model; measure the time; check the fallback when the model is slow or returns invalid JSON |
| Scheduled / long jobs | Confirm idempotency (run twice), progress reporting, and behaviour when the browser tab is switched |

Guidelines learned the hard way:

- Tests must not publish, post or email for real. Use a scratch site / temporary records and **clean up** after.
- Never point a test at a live customer site with write access. Read-only crawls are fine.
- Restart the API after backend edits; the frontend hot-reloads.
- `scripts/test_all.py` is an intentionally empty placeholder — there is no aggregated automated suite yet.

---

## 13. Operations and troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "GSC fetch failed" for one site | Service account not added to that property / API not enabled / wrong property URL (trailing slash, subdirectory) | Add the account as a user (Full for inspection and sitemap submit); enable the API; fix the property URL |
| URL Inspection 403 | Account lacks Full/Owner, or the property was re-verified and access dropped | Re-add the account with Full |
| Sitemap submit says permission denied | Restricted user | Full/Owner |
| Blog publish "failed" but post exists | Browser timed out while the server finished | Refresh; publish timeout is now 10 min |
| CMS 401 | Wrong WordPress user / used the login password | Create an **Application Password** and save it in *CMS Publishing* |
| CMS/site returns 406 or 403 | Host firewall (mod_security) rejecting the app's requests | Whitelist the server, allow `/wp-json` |
| CMS 500 on `/wp-json` | Broken permalinks/plugin on that site | Fix on the WordPress side; test `…/wp-json/` in a browser |
| AI step times out | CPU inference; large prompt; qwen3 "thinking" on long outputs | Reduce input, cap reply tokens, chunk, use the fast model, or add a GPU |
| Sitemap "Live" check fails | Files uploaded to the wrong directory, or the web root wasn't detected | Check *Publishing* message; upload manually from Download |
| Two servers after a restart | A stray process still on port 8000 | End all `uvicorn api.main` processes, start one |
| Stale backend behaviour | Edited code, didn't restart | Restart the API |
| Scheduled job "didn't run today" | App wasn't running at the cron time | The startup catch-up handles the daily cycle; sitemap job checks every 3 h |

**Logs.** API and agent log to `agent/data/logs/agent.log`; every LLM call is recorded in `llm_usage_log`;
job outcomes in `seo_job_runs`; publish / crawl failures are stored on the record (`error` columns).

---

## 14. Coding conventions

**General**
- One thing at a time; verify it works before starting the next. Don't change behaviour of features you weren't
  asked to touch (models, timeouts and defaults are per-feature).
- Configuration over hardcoding: settings in `api/config.py` / `agent/config.py`; per-site values in the database.
- No `print` — use `logging`. No secrets in code, logs, error messages or responses.
- Wrap every call to Ollama, the network, the database or Playwright in error handling; log it; return a default or
  a result object with a reason.
- Every outbound HTTP call has a timeout. Every Ollama call has a timeout.

**Backend**
- Routes stay thin: validate, load, call a client/service, persist, return. Business logic lives in `ai/` or
  `automation/`.
- Validate any user-supplied URL with `assert_public_url` before fetching it server-side.
- Long work → background thread + status endpoint (see the sitemap route), not an open request.
- Additive schema only. Read stored secrets server-side; return only `*_set` flags.
- Playwright uses a persistent session (cookies file) so login happens once.
- ChromaDB collections are named by function (`leads`, `app_classifications`, `agent_memory`, …); never mix data types.

**Frontend**
- Components in `.tsx` with explicit prop types; no `any` unless unavoidable.
- Reads through `useQuery`, writes through `useMutation` with `onError` → `toast.error(serverErrorDetail(...))`.
- Every card handles loading, empty, error and success.
- Destructive actions use a confirm modal, not `window.confirm`.
- Keep a card self-contained; share only through query keys and props.
- Use the design tokens/classes already in the codebase (Tailwind theme, `Card`, `Button`, `Badge`, `Input`).

**Git and secrets**
- Never commit `.env`, `workpulse-config.json`, `linkedin_cookies.json`, databases or logs (all in `.gitignore`).
- Commit only when asked; **never push without an explicit instruction for that push.**

---

## 15. Build, release and deployment

| Artifact | How |
|---|---|
| Dashboard (static) | `cd frontend && npm run build` → `frontend/dist` (Vercel: root `frontend`, `VITE_API_URL` = API URL) |
| API | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` (`Procfile`, `railway.json`) |
| Desktop agent | `scripts/build_exe.bat` → `dist/WorkPulseAgent.exe` (needs `requirements-build.txt`) |

Deployment specifics — Railway volumes for the SQLite file, Playwright on the server, CORS — are in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Pre-release checklist: `npm run build` passes; API imports and
starts; a fresh database can be created and the first-admin flow works; `.env.example` lists every new variable;
this guide and the user guide describe any user-visible change.

---

## 16. Module index

The system was built in numbered modules. Modules 1–32 are specified in
[`docs/MODULE_SPECIFICATIONS.md`](docs/MODULE_SPECIFICATIONS.md); later SEO modules are described by tagged
comments (`Module N —`) next to the code they introduced.

| Modules | Area | Status |
|---|---|---|
| 1–2 | Desktop app tracker, time intelligence | Done |
| 3, 12 | Screenshot system and gallery | **Removed** (product decision) |
| 4 | Browser / website tracker (window titles) | Done |
| 5–6 | FastAPI backend, productivity scorer, patterns | Done |
| 7 | AI DAR generator + custom templates, export/import | Done |
| 8 | Gmail delivery | Done (needs Gmail credentials) |
| 9–11, 13 | Dashboard core, timeline, analytics, DAR viewer | Done |
| 14 | Smart alerts | Done |
| 15–17 | Master Agent, sub-agents, Command Mode | Done |
| 18–20 | LinkedIn, email campaigns, lead research | Done (LinkedIn scraping-based lead search is limited by anti-bot systems) |
| 21 | Team intelligence | Done |
| 22 | Chrome extension | **Removed** (product decision) |
| 23 | `.exe` packaging | Done |
| 24 | Cloud deployment | **Partial by decision** — Postgres and multi-agent sync deferred |
| Login / RBAC | JWT login, three roles, per-user scoping | Done |
| 25–32 | SEO foundation, CMS + Google data, content, technical audit, digest, social, backlinks, gap closure | Done |
| 33–61 | SEO scheduling, fix generation, roll-ups, RapidAPI/Semrush, blog and social scheduling, GSC/GA4 depth, quality checks, sitemap tooling | Done — see code tags |
| Post-61 | Technical Audit tab; Sitemap Generator (single file, ordered, auto-update); Social CRUD; blog image placement; Saved/Change connection cards; toast and timeout fixes; tab deep links | Done |

---

## 17. Known limitations

- **Single SQLite file.** One agent + one API. Multi-employee central sync and Postgres are deferred; see
  [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
- **CPU inference is slow.** AI features are chunked and time-boxed, but a long article can take minutes.
  Other features still on the fast model (classification, meta, image prompts, social) may be slow on weak hardware.
- **Grammar check adds time** to blog generation; moving it to the background is a possible improvement.
- **Sitemap crawl** is capped (default 5,000 pages) and single-host; URLs beyond the cap are kept unverified.
- **Search Console** access is per property and manual; some Google APIs (Site Verification, Indexing) need
  Workspace-level setup and are hidden in the UI.
- **Social:** only LinkedIn is auto-posted by default; Instagram cannot publish without an image.
- **Lead discovery** through Google/LinkedIn scraping is limited by anti-bot protection.
- **No aggregated automated test suite**; verification is real end-to-end runs (see §12).
- `docs/API.md` is generated from the OpenAPI schema (endpoint index only); the live Swagger UI at `/docs` is the
  authoritative contract for request and response bodies.

---

*Last updated: September 25, 2026.*
