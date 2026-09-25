# WorkPulse AI

**A local-first, agentic AI platform for work intelligence and SEO operations.**

A desktop agent tracks work activity, a local AI stack turns it into focus scores and daily reports,
and a web dashboard gives employees, managers and SEO teams a live and historical view of it — plus a
full SEO operations suite (technical audits, Search Console / Analytics, blog and social publishing,
sitemaps). All AI inference runs on your own machine through [Ollama](https://ollama.com): no
per-token cost, and activity data never leaves the machine it is tracked on.

---

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Roles and access](#roles-and-access)
- [Project layout](#project-layout)
- [Documentation](#documentation)
- [Production checklist](#production-checklist)
- [Troubleshooting](#troubleshooting)

---

## Features

### Work intelligence
- Active window, app and website tracking; idle detection; break classification.
- Meeting-aware idle time — meetings from a local `.ics` calendar export are not counted as idle.
- Live focus score, active hours and context-switching analysis.
- Attendance tracking (check-in / check-out, late marks, weekly consistency).
- **AI-written Daily Activity Reports (DAR)** — narrative and structured task-log views, department-specific
  templates, CSV / DOCX / PDF export and CSV import, and email delivery.
- Smart alerts: focus, distraction, wellbeing / burnout, and manager alerts, with per-type preferences.

### Team management (managers and admins)
- Per-member overview, timeline, attendance calendar and full DAR history.
- Admin-controlled per-employee feature toggles that gate the employee's own desktop agent.
- AI-powered weekly team analysis: high performers, struggling members, workload imbalance, burnout risk.
- Role-based access control: `employee`, `manager`, `admin`.

### SEO suite
| Area | What it does |
|---|---|
| **Overview** | Site health, latest AI daily digest, weekly / monthly roll-ups, automation job history, connection setup (Google, CMS, server access, Google Sheets) |
| **Technical Audit** | Crawls the site, lists issues (missing tags, broken links, duplicates, redirects, hreflang, robots…), approve / reject / AI-generate and apply fixes, single-page tag audit |
| **Performance** | PageSpeed Insights (Core Web Vitals, resource audit, prioritised fixes) |
| **Search Console** | Clicks, impressions, CTR and position with drill-down and search; **Sitemap Generator**; sitemap submission |
| **Analytics** | GA4 realtime, performance and events |
| **Indexing** | Index coverage and URL inspection |
| **Social** | AI-generated or hand-written posts for LinkedIn, X / Twitter, Instagram and Facebook — edit, delete, attach or generate images, schedule, publish |
| **Blog** | AI blog generation with structure, grammar, plagiarism and FAQ checks; draft → approve → publish to WordPress / Webflow; content calendar |
| **Backlinks** | Brand-mention monitoring, keyword and domain research |
| **Redirection** | Manage URL redirects and sync them to the site's `.htaccess` |

### Business automation
- LinkedIn post writing and posting through real browser automation (Playwright).
- Personalised email campaigns (Gmail SMTP + local RAG) and lead discovery / enrichment.
- **Command Mode** — type an instruction in plain language and the Master Agent runs it.

### Authentication
- Email / password login (JWT + bcrypt). The **first account created becomes the admin.**
- Optional "Sign in with Google" (off by default, invite-only — it only matches existing accounts).

---

## Architecture

Three cooperating pieces share one SQLite database:

```
┌────────────────────┐      ┌──────────────────────────┐      ┌────────────────────┐
│   Desktop Agent    │      │     FastAPI backend      │      │  React dashboard   │
│   agent/           │─────▶│  api/  ai/  automation/  │◀────▶│  frontend/         │
│ (one per employee, │ same │  + background scheduler  │ REST │  (Vite + React 19) │
│  packaged as .exe) │SQLite└────────────┬─────────────┘      └────────────────────┘
└────────────────────┘ file              │
                                         ▼
                           Local Ollama models (classification, reports,
                           SEO content)  ·  optional external integrations
                           (Google APIs, CMS, Gmail, social platforms)
```

| Folder | Role |
|---|---|
| `agent/` | Tracks the active window, idle time, calendar and file activity; writes to local SQLite; system-tray app |
| `api/` | FastAPI backend: authentication, REST routes, database models, background scheduler |
| `ai/` | AI layer: LangGraph Master Agent, DAR generation, scoring, team analysis, SEO content and digests |
| `automation/` | Integrations: LinkedIn, email, leads, Google Search Console / Analytics / Sheets, CMS, sitemaps, crawler |
| `frontend/` | React + TypeScript dashboard |

---

## Technology stack

| Layer | Technology |
|---|---|
| AI inference | Ollama — `qwen3:1.7b`, `phi3:mini`, `nomic-embed-text` (all local) |
| Orchestration | LangGraph + LangChain |
| Vector store | ChromaDB |
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2, APScheduler, python-jose (JWT), bcrypt |
| Database | SQLite (WAL mode) |
| Desktop agent | pywin32, psutil, Pillow, pystray, watchdog — packaged with PyInstaller |
| Browser automation | Playwright |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Router |
| Crawling / parsing | requests, BeautifulSoup |
| Exports | python-docx, reportlab, openpyxl |

**Local-first policy.** The AI layer does not require any paid cloud API. The SEO module's LLM factory can
optionally be pointed at Claude or OpenAI (`SEO_LLM_PROVIDER_DEFAULT`), but it defaults to Ollama and is off
unless you configure a key. Google APIs, Gmail, CMS and social integrations are all opt-in.

---

## Quick start

### Requirements

| | Version |
|---|---|
| Python | 3.11 or newer (Windows for the desktop agent — `pywin32` is Windows-only) |
| Node.js | 18 or newer |
| [Ollama](https://ollama.com) | Running locally, with the three models above pulled (~4 GB) |

### One command

```bash
start.bat                          # Windows
python3 scripts/setup.py --start   # macOS / Linux
```

The first run creates the virtual environment, installs Python and Node dependencies and the Playwright
browser, creates `.env` (with a random `SECRET_KEY`) and the database, and pulls the Ollama models. Later runs
skip straight to starting the **API on `:8000`** and the **dashboard on `:5173`**.

Options: `--agent` (also run the desktop agent), `--skip-models`, `--api-port N`. `setup.bat` installs
without starting; `setup.bat --check` reports what is missing.

Open <http://localhost:5173> and create the first (admin) account.

**Day-to-day:** once installed, double-click **`start-servers.bat`** to start the API and the dashboard in two
windows and open the browser. **`stop-servers.bat`** stops both (handy before restarting after a backend change).

### Manual start

```bash
# 1. Environment
cp .env.example .env            # then edit — see Configuration

# 2. Backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --port 8000

# 3. Dashboard (new terminal)
cd frontend
npm install
npm run dev

# 4. Desktop agent (optional, Windows, new terminal)
python -m agent.main
```

> Run the API **without** `--reload`. It has been unreliable in this project (the worker can fail to restart
> and silently keep serving old code). Restart the process manually after backend changes.

---

## Configuration

All backend settings live in `.env` (copy `.env.example`). Only `SECRET_KEY` needs changing to get started;
everything else is optional and enables a specific integration.

| Group | Variables | Enables |
|---|---|---|
| Core | `SECRET_KEY`, `CORS_ORIGINS`, `DATABASE_URL` | Security, browser access, database location |
| Local AI | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL` | Which Ollama models are used |
| Email | `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `REPORT_RECIPIENT_EMAIL` | Report and alert emails, campaigns |
| Google sign-in | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `API_PUBLIC_URL`, `FRONTEND_URL` | "Sign in with Google" |
| Google APIs (SEO) | `GOOGLE_SERVICE_ACCOUNT_JSON_PATH`, `GSC_SITE_URL`, `PAGESPEED_API_KEY` | Search Console, Analytics, Sheets, PageSpeed |
| CMS (SEO) | `WORDPRESS_*`, `WEBFLOW_*` (or set per site in the dashboard) | Publishing blog posts |
| SEO automation | `SEO_AUTOMATION_ENABLED`, `SEO_AUTOMATION_HOUR` | The daily SEO pipeline (default on, 06:00) |
| Images | `IMAGE_PROVIDER_DEFAULT`, `PEXELS_API_KEY`, `IMAGE_WORKER_*`, `STABILITY_API_KEY` | Blog / social image generation |
| Social | `LINKEDIN_*`, `FACEBOOK_*`, `INSTAGRAM_*` | Social publishing |
| Notifications | `SLACK_WEBHOOK_URL` | Digest delivery to Slack |
| Research | `SEMRUSH_API_KEY`, `RAPIDAPI_*` keys, `GOOGLE_ALERTS_RSS_URL` | Keyword, backlink and brand-mention data |

Per-site SEO credentials (Google property, CMS login, server access, Google Sheets) are entered in the
dashboard's SEO → Overview tab and stored in the database, not in `.env`.

The desktop agent reads `workpulse-config.json` (API URL and user id), created on first run.
See [`DEVELOPMENT.md`](DEVELOPMENT.md#6-configuration-reference) for the full reference.

---

## Roles and access

| Role | Can do |
|---|---|
| `employee` | See their own tracked data, reports and alerts; use the SEO, Command, LinkedIn, Email and Notepad pages |
| `manager` | Everything an employee can, plus read-only oversight of every employee and the AI team analysis |
| `admin` | Everything a manager can, plus create / delete users, change roles and reset passwords |

The first account created on a fresh install is the admin. Personal-data routes are scoped to the logged-in
user on the server, not just hidden in the UI.

---

## Project layout

```
agent/          Desktop tracking agent (per employee, packaged as .exe)
api/            FastAPI backend — routes, auth, models, scheduler
ai/             AI layer — Master Agent, DAR, scoring, team analysis, SEO content
  llm/          Provider layer (Ollama default; Claude / OpenAI optional)
  images/       Image provider layer
  seo/          SEO content, digests, quality and grammar checks
automation/     Integrations — LinkedIn, email, leads, Google, CMS, sitemaps, crawler
  seo/          Search Console, GA4, Sheets, PageSpeed, CMS adapters, sitemap generator
frontend/       React + Vite + Tailwind dashboard
scripts/        setup.py, start_all.py, build_exe.bat, icon generation
docs/           Guides and archived specifications
sitemaps/       Generated sitemap files (per site) — created at runtime
```

---

## Documentation

| Document | Audience | Contents |
|---|---|---|
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | Everyone who uses the dashboard | Page-by-page guide, common tasks, FAQ |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Developers | Architecture, setup, configuration, conventions, the SEO suite internals, testing, operations |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Operators | Deploying the API and dashboard, packaging the agent |
| [`docs/MODULE_SPECIFICATIONS.md`](docs/MODULE_SPECIFICATIONS.md) | Maintainers | Archived original build specification and status log |
| [`docs/API.md`](docs/API.md) | Developers | Index of every API endpoint, grouped by area |
| `http://localhost:8000/docs` | Developers | Live, interactive API reference (Swagger UI, generated from the code) |

---

## Production checklist

- [ ] Set a strong, unique `SECRET_KEY` — never keep the default.
- [ ] Set `CORS_ORIGINS` to your real dashboard origin(s) only.
- [ ] Serve the API and dashboard over HTTPS.
- [ ] Put `workpulse.db` on a persistent volume and back it up (copy the `-wal` and `-shm` files with it, or
      use SQLite's online backup).
- [ ] Never commit `.env`, `workpulse-config.json`, `linkedin_cookies.json` or any credential file
      (all are in `.gitignore`).
- [ ] Give Google service accounts only the access they need (Search Console *Full* is required for URL
      inspection and sitemap submission).
- [ ] Run the API without `--reload`, under a process supervisor that restarts it on failure.
- [ ] Size the Ollama host for the models you use — CPU-only inference is slow (a few words per second);
      long AI tasks are chunked and run with generous timeouts for that reason.

---

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Dashboard shows "GSC fetch failed" | The Google service account is not added to that Search Console property, or the API is not enabled in Google Cloud. Add it as a user (Full for inspection / sitemaps) and enable *Search Console API*. |
| Blog publish says it failed but the post appears | The publish request is long-running (image generation + upload + CMS call). Wait for it to finish and refresh; the app now waits up to 10 minutes. |
| AI features are slow or time out | Ollama is running on CPU or the model is still loading. Check `ollama ps`; use the smaller model, or a machine with a GPU. |
| CMS publish returns 401 | The WordPress user or Application Password is wrong. Use an **Application Password** (Users → Profile), not the login password. |
| A host returns HTTP 406 / 403 to the app | The host's firewall is blocking the request. Whitelist the server's IP or relax the rule for `/wp-json`. |
| Dashboard empty for an employee | No desktop agent is running with that employee's `WORKPULSE_USER_ID`. |

More operational notes are in [`DEVELOPMENT.md`](DEVELOPMENT.md#13-operations-and-troubleshooting).

---

*Internal project. See `DEVELOPMENT.md` for contribution conventions.*
