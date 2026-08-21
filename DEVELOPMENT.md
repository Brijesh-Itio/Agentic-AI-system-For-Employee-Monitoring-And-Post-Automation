# WorkPulse AI — Development Guide

> **Read this file completely before writing any code.**
> This is the single source of truth for architecture, module structure, build order, and conventions.
> Every feature is built module by module, sub-module by sub-module, one at a time.

---

## 1. Product Vision

WorkPulse AI is a full-stack, production-ready, Agentic AI business operating system. It combines:

- **Work Intelligence** — automatic activity tracking, screenshots, productivity scoring, DAR generation
- **Business Automation** — LinkedIn posting, email campaigns, lead generation, all autonomous
- **Agentic AI Brain** — LangGraph Master Agent that plans, delegates, monitors and reports every day

**Core philosophy:** The system does not wait for button clicks. It watches, thinks, decides and acts. Every feature must be designed to run autonomously with zero human intervention unless a human decision is explicitly required.

**Zero external API rule:** The entire system runs on local Ollama, free Python libraries, Gmail SMTP, and Playwright browser automation. No paid APIs. No per-token cloud costs. No IP whitelisting. No third-party SaaS dependencies except where absolutely unavoidable and explicitly documented.

---

## 2. Project Structure

```
workpulse-ai/
│
├── DEVELOPMENT.md              ← this file — read before touching anything
│
├── agent/                      ← Desktop tracking agent (runs on employee PC)
│   ├── main.py                 ← Entry point, starts all trackers
│   ├── app_tracker.py          ← Active window tracking via pywin32
│   ├── screenshot.py           ← Screenshot capture via Pillow
│   ├── idle_detector.py        ← Keyboard and mouse idle detection
│   ├── browser_tracker.py      ← Window title reading for browser sites
│   ├── time_intelligence.py    ← Focus score, break tracking, work day detection
│   ├── sync.py                 ← Syncs local SQLite to cloud PostgreSQL
│   ├── database.py             ← SQLite schema and queries
│   └── config.py               ← All agent settings
│
├── api/                        ← FastAPI backend (runs on server or local PC)
│   ├── main.py                 ← FastAPI app entry point
│   ├── database.py             ← SQLAlchemy models and DB connection
│   ├── config.py               ← All API settings and credentials
│   ├── routes/
│   │   ├── activity.py         ← App tracking endpoints
│   │   ├── screenshots.py      ← Screenshot endpoints
│   │   ├── websites.py         ← Browser tracking endpoints
│   │   ├── reports.py          ← DAR and weekly report endpoints
│   │   ├── productivity.py     ← Score and pattern endpoints
│   │   ├── linkedin.py         ← LinkedIn automation endpoints
│   │   ├── email.py            ← Email campaign endpoints
│   │   ├── leads.py            ← Lead management endpoints
│   │   ├── command.py          ← Command Mode endpoints
│   │   ├── team.py             ← Team intelligence endpoints
│   │   └── status.py           ← System health endpoints
│   └── middleware/
│       ├── auth.py             ← JWT authentication
│       └── logging.py          ← Request logging
│
├── ai/                         ← All AI and agent logic
│   ├── master_agent.py         ← LangGraph Master Agent
│   ├── sub_agents/
│   │   ├── tracker_agent.py    ← Monitors activity and sends alerts
│   │   ├── linkedin_agent.py   ← LinkedIn content and posting
│   │   ├── email_agent.py      ← Email outreach and follow-up
│   │   ├── research_agent.py   ← Web scraping and lead research
│   │   └── reporting_agent.py  ← DAR and weekly report generation
│   ├── tools/
│   │   ├── activity_tools.py   ← Tools for reading activity data
│   │   ├── email_tools.py      ← Tools for sending emails
│   │   ├── linkedin_tools.py   ← Tools for LinkedIn browser automation
│   │   ├── search_tools.py     ← Tools for web search and scraping
│   │   └── report_tools.py     ← Tools for generating reports
│   ├── dar_generator.py        ← Daily Activity Report generation
│   ├── productivity_scorer.py  ← App and website classification and scoring
│   ├── pattern_analyser.py     ← Peak hours, context switching, break analysis
│   ├── rag.py                  ← ChromaDB RAG for lead personalisation
│   └── memory.py               ← Agent persistent memory via ChromaDB
│
├── automation/                 ← Business automation modules
│   ├── linkedin/
│   │   ├── poster.py           ← Playwright LinkedIn browser automation
│   │   ├── content_writer.py   ← AI post writing with Ollama
│   │   └── image_finder.py     ← Playwright image search and download
│   ├── email/
│   │   ├── sender.py           ← Gmail SMTP via smtplib
│   │   ├── writer.py           ← RAG-powered personalised email writing
│   │   ├── campaign.py         ← Campaign scheduling and execution
│   │   └── logger.py           ← Campaign logging and duplicate prevention
│   └── leads/
│       ├── finder.py           ← Playwright web scraping for lead discovery
│       ├── enricher.py         ← Lead profile enrichment via web scraping
│       └── store.py            ← Lead storage in SQLite and ChromaDB
│
├── dashboard/                  ← React frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Timeline.jsx
│   │   │   ├── Screenshots.jsx
│   │   │   ├── Reports.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── CommandMode.jsx
│   │   │   ├── LinkedIn.jsx
│   │   │   ├── Email.jsx
│   │   │   ├── Team.jsx
│   │   │   └── Settings.jsx
│   │   ├── components/
│   │   │   ├── Timeline/
│   │   │   ├── Charts/
│   │   │   ├── Screenshots/
│   │   │   ├── DAR/
│   │   │   ├── Alerts/
│   │   │   └── shared/
│   │   └── api/
│   │       └── index.js        ← All Axios API calls
│   └── public/
│
├── extension/                  ← Chrome extension for URL tracking
│   ├── manifest.json
│   ├── content.js
│   └── background.js
│
├── scripts/                    ← Utility scripts
│   ├── setup.py                ← One-command project setup
│   ├── start_all.py            ← Starts all services
│   └── test_all.py             ← Runs full system test
│
└── docs/
    ├── DEVELOPMENT.md          ← this file
    ├── API.md                  ← all API endpoint documentation
    └── DEPLOYMENT.md           ← deployment instructions
```

---

## 3. Technology Stack

### Confirmed and Non-Negotiable

| Layer | Technology | Reason |
|---|---|---|
| AI Inference | Ollama + qwen3:1.7b | Fully local, zero cost, zero API |
| Fast AI tasks | Ollama + phi3:mini | Faster CPU inference for classifications |
| Embeddings | nomic-embed-text via Ollama | Local embeddings, no API |
| Agent Framework | LangChain | Tool management, memory, prompts |
| Multi-Agent | LangGraph | Master Agent + sub-agent orchestration |
| Vector Store | ChromaDB | Local RAG, lead personalisation, agent memory |
| Desktop Tracking | pywin32 + psutil + Pillow | Windows native, zero API |
| Browser Automation | Playwright | LinkedIn/Instagram/Facebook posting, image finding, lead scraping |
| Backend API | FastAPI + uvicorn | High performance, auto docs, async support |
| Local Database | SQLite via SQLAlchemy | Zero config, built into Python |
| Cloud Database | Self-hosted PostgreSQL on Oracle Cloud Free | Always free, no subscription |
| Screenshot Storage | Local disk Phase 1, MinIO Phase 2 | Self-hosted, zero cost |
| Email Sending | Python smtplib + Gmail SMTP | 500/day free, any IP, no whitelisting |
| Dashboard | React + Vite | Fast, modern, component-based |
| Charts | Recharts | Timeline, bar, line, pie charts |
| Styling | TailwindCSS | Utility-first, consistent design |
| Navigation | React Router DOM | Multi-page SPA routing |
| API Calls | Axios | HTTP client for React |
| Desktop Notifications | plyer | Windows toast notifications, zero API |
| Packaging | PyInstaller | .exe for employee PC distribution |
| Dashboard Hosting | Vercel free tier | Auto deploy from GitHub |
| API Hosting | Railway free tier | FastAPI cloud hosting |

### What is NOT Allowed

- No Brevo, SendGrid or any email API — use Gmail SMTP only
- No Unipile, LinkedIn API or any LinkedIn developer account — use Playwright only
- No Unsplash API or any image API — use Playwright to find and download images
- No Supabase — use self-hosted PostgreSQL on Oracle Cloud free tier
- No Groq, OpenAI, Anthropic or any cloud AI API — use local Ollama only
- No Firebase, MongoDB Atlas or any paid database — self-host everything
- No paid Chrome extension or browser API — build the extension yourself

---

## 4. Module Build Order

Build strictly in this order. Do not start a module until the previous module passes its test. Do not add features to a later module while an earlier module is incomplete.

```
MODULE 1  — Desktop App Tracker
MODULE 2  — Time Intelligence Engine
MODULE 3  — Screenshot System
MODULE 4  — Browser and Website Tracker
MODULE 5  — FastAPI Backend
MODULE 6  — Productivity Scorer and Pattern Analyser
MODULE 7  — AI DAR Generator
MODULE 8  — Gmail Email Delivery
MODULE 9  — React Dashboard Core
MODULE 10 — Timeline View
MODULE 11 — App Usage Charts and Analytics
MODULE 12 — Screenshot Gallery
MODULE 13 — DAR Viewer and Reports Page
MODULE 14 — Smart Alerts System
MODULE 15 — LangGraph Master Agent
MODULE 16 — Sub-Agent Implementation
MODULE 17 — Command Mode
MODULE 18 — LinkedIn Automation via Playwright
MODULE 19 — Email Campaign Automation
MODULE 20 — Lead Research and Generation Agent
MODULE 21 — Team Intelligence Dashboard
MODULE 22 — Chrome Extension for URL Tracking
MODULE 23 — PyInstaller .exe Packaging
MODULE 24 — Cloud Deployment
```

---

## 5. Module Specifications

---

### MODULE 1 — Desktop App Tracker

**File:** `agent/app_tracker.py`

**Purpose:** Read the active Windows application and window title every second and log every app session to SQLite with exact timestamps.

**Sub-modules to build in order:**

**1.1 — Active window reader**
Use `win32gui.GetForegroundWindow()` and `win32gui.GetWindowText()` to get the current active window handle and title. Use `psutil.Process()` to get the process name from the window handle. Run this in a loop every 1 second.

**1.2 — Session detector**
Compare current app name to previous app name. When they differ, a new session has started. Close the previous session by recording its end time and duration. Open a new session with current timestamp as start time.

**1.3 — SQLite writer**
Write every completed session to the `activity_logs` table. Schema:
```sql
CREATE TABLE activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'local',
    app_name TEXT NOT NULL,
    window_title TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    category TEXT DEFAULT 'uncategorised',
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**1.4 — App switch counter**
Maintain a daily counter of app switches. Increment every time the active window changes. Store in a separate `daily_stats` table. Reset at midnight.

**1.5 — Context switching detector**
Count app switches per 5-minute window. If switches exceed 10 in any 5-minute window flag that window as high-context-switching and store the flag in SQLite.

**Module 1 test:** Run agent for 10 minutes, open 5 different apps, query SQLite and verify every app session is logged with accurate start time, end time and duration. Zero tolerance for missed sessions or wrong timestamps.

---

### MODULE 2 — Time Intelligence Engine

**File:** `agent/time_intelligence.py`

**Purpose:** Extract meaningful time metrics from raw activity data — idle detection, break classification, focus score, productive hours, work day boundaries, weekly trends.

**Sub-modules to build in order:**

**2.1 — Idle detector**
Monitor keyboard and mouse input using the `keyboard` library and `win32api.GetLastInputInfo()`. If no input is detected for 300 consecutive seconds (5 minutes) mark the current period as idle. When input resumes close the idle period and resume the active session timer.

**2.2 — Work day detector**
Record the timestamp of the first keyboard or mouse input of the day as `work_start`. Record the timestamp of the last input before a 15-minute or longer idle as `work_end`. Store both in the `daily_stats` table.

**2.3 — Break classifier**
Classify idle periods by duration:
- Under 5 minutes: micro-break, do not count as break
- 5 to 15 minutes: short break
- Over 15 minutes: long break
Store break type, start time and duration in a `breaks` table.

**2.4 — Focus score calculator**
At end of each hour calculate: `focus_score = (productive_seconds / total_active_seconds) * 100`. Store hourly scores in `hourly_scores` table. Calculate daily focus score from sum of hourly productive seconds divided by sum of hourly active seconds.

**2.5 — Productive hours counter**
Sum all seconds spent in apps classified as `productive` category. Convert to hours and minutes. Store as `productive_hours_today` in `daily_stats`.

**2.6 — Longest focus session detector**
Scan activity logs for the longest consecutive block of productive app sessions without any idle period or distraction app. Store start time, end time and duration.

**2.7 — Weekly trends calculator**
Every day at 6pm query the past 7 days of `daily_stats` and calculate: average focus score, total hours per day, productive hours per day, trend direction (improving or declining). Store results in `weekly_trends` table.

**Module 2 test:** Run agent for 30 minutes including deliberate idle periods. Verify idle is detected correctly at exactly 5 minutes. Verify focus score matches manually calculated value. Verify work start time is accurate.

---

### MODULE 3 — Screenshot System

**File:** `agent/screenshot.py`

**Purpose:** Capture screenshots every 5 minutes with timestamp overlay, save locally, support blur option, support manual capture via API call.

**Sub-modules to build in order:**

**3.1 — Screen capture**
Use `PIL.ImageGrab.grab()` to capture the full screen. Save as JPEG with 85% quality to reduce file size. File naming convention: `screenshots/YYYY-MM-DD/HH-MM-SS.jpg`.

**3.2 — Timestamp overlay**
Use `PIL.ImageDraw` and `PIL.ImageFont` to draw the date and time string in the bottom-right corner of every screenshot. Background: semi-transparent black rectangle. Text: white, readable font size.

**3.3 — Blur option**
When `blur_screenshots = True` in config, apply `PIL.ImageFilter.GaussianBlur(radius=8)` to the saved image. Store both the blurred version for manager view and the original for audit purposes. Original is encrypted at rest in Phase 2.

**3.4 — Scheduler**
Use the `schedule` library to trigger capture every 5 minutes. This runs in its own thread alongside the app tracker so both operate simultaneously without blocking each other.

**3.5 — Screenshot metadata logger**
After every capture write a record to the `screenshots` table:
```sql
CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'local',
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    timestamp DATETIME NOT NULL,
    date DATE NOT NULL,
    is_blurred INTEGER DEFAULT 0,
    cloud_url TEXT
);
```

**3.6 — Thumbnail generator**
Generate a 320x180 pixel thumbnail of each screenshot for dashboard gallery display. Save alongside original with `_thumb` suffix.

**3.7 — Manual capture endpoint**
Expose a function `capture_now()` that the FastAPI backend can call to trigger an immediate screenshot on demand from the dashboard.

**Module 3 test:** Run for 15 minutes, verify 3 screenshots captured, verify timestamps are correct, verify files exist in correct folder structure, verify thumbnails generated.

---

### MODULE 4 — Browser and Website Tracker

**File:** `agent/browser_tracker.py` and `extension/`

**Purpose:** Track which websites are visited and for how long, without any browser API or external service.

**Sub-modules to build in order:**

**4.1 — Window title reader**
Every second when the active app is Chrome or Edge, extract the website name from the window title. Chrome format: `Page Title - Google Chrome`. Parse out the page title and infer the domain where possible.

**4.2 — Chrome extension**
Build a minimal Chrome extension that runs alongside the tracker for full URL accuracy:

`extension/manifest.json`:
```json
{
  "manifest_version": 3,
  "name": "WorkPulse Tracker",
  "version": "1.0",
  "permissions": ["tabs", "activeTab"],
  "background": { "service_worker": "background.js" },
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["content.js"]
  }]
}
```

`extension/content.js` — reads current URL and page title, sends to localhost:8001 every 5 seconds via fetch.

`extension/background.js` — handles tab change events and sends URL immediately on tab switch.

**4.3 — URL receiver endpoint**
In `agent/browser_tracker.py` run a simple HTTP server on port 8001 that receives URL data from the extension. Close the previous URL session and open a new one on every URL change.

**4.4 — Website session logger**
Write every website session to the `websites` table:
```sql
CREATE TABLE websites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'local',
    url TEXT,
    domain TEXT,
    page_title TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    category TEXT DEFAULT 'uncategorised',
    date DATE NOT NULL
);
```

**4.5 — Top sites calculator**
Query the `websites` table to produce a ranked list of domains by total time spent per day. Store in `daily_stats.top_sites_json` as a JSON array.

**Module 4 test:** Browse 5 different websites for 2 minutes each, verify all sessions logged with correct domains, correct durations and correct page titles.

---

### MODULE 5 — FastAPI Backend

**File:** `api/main.py` and all route files

**Purpose:** Expose all data and operations as REST API endpoints that the React dashboard and agent can call.

**Sub-modules to build in order:**

**5.1 — Project setup**
Create FastAPI app with CORS enabled for localhost:5173. Configure SQLAlchemy with SQLite. Create Pydantic models for all data types. Set up lifespan event to create all database tables on startup.

**5.2 — Activity routes** (`api/routes/activity.py`)
- `GET /api/activity/today` — all app sessions for today
- `GET /api/activity/date/{date}` — all sessions for a specific date
- `GET /api/activity/apps/summary` — total time per app for today
- `GET /api/activity/apps/top` — top 10 apps by time today
- `GET /api/activity/context-switching` — hourly context switching score

**5.3 — Screenshots routes** (`api/routes/screenshots.py`)
- `GET /api/screenshots/today` — all screenshots for today with metadata
- `GET /api/screenshots/date/{date}` — screenshots for a specific date
- `GET /api/screenshots/{id}` — single screenshot metadata
- `POST /api/screenshots/capture` — trigger manual screenshot
- `GET /api/screenshots/file/{filename}` — serve screenshot image file

**5.4 — Website routes** (`api/routes/websites.py`)
- `GET /api/websites/today` — all website sessions for today
- `GET /api/websites/top` — top sites today ranked by time
- `GET /api/websites/date/{date}` — website sessions for a specific date

**5.5 — Productivity routes** (`api/routes/productivity.py`)
- `GET /api/productivity/score/today` — today's focus score
- `GET /api/productivity/score/date/{date}` — score for any date
- `GET /api/productivity/weekly` — 7-day trend data
- `GET /api/productivity/patterns` — peak hours and context switching analysis

**5.6 — Reports routes** (`api/routes/reports.py`)
- `GET /api/reports/dar/today` — today's DAR if generated
- `GET /api/reports/dar/date/{date}` — DAR for any date
- `GET /api/reports/dar/all` — list of all generated DARs
- `POST /api/reports/dar/generate` — trigger immediate DAR generation
- `GET /api/reports/weekly/latest` — latest weekly report
- `POST /api/reports/weekly/generate` — trigger weekly report generation

**5.7 — Status routes** (`api/routes/status.py`)
- `GET /api/status` — system health: Ollama running, agent running, DB connected, Gmail connected, Playwright ready

**Module 5 test:** Use curl to hit every endpoint and verify correct HTTP status codes and response shapes. All endpoints must return valid JSON with no 500 errors.

---

### MODULE 6 — Productivity Scorer and Pattern Analyser

**File:** `ai/productivity_scorer.py` and `ai/pattern_analyser.py`

**Purpose:** AI classifies every app and website, calculates scores, detects patterns, uses ChromaDB memory so classifications are consistent and learned over time.

**Sub-modules to build in order:**

**6.1 — App classifier**
Send app name and window title to local Ollama with a structured prompt. The prompt instructs the model to return exactly one of three words: `productive`, `neutral`, `distraction`. Store each classification result in ChromaDB so next time the same app is seen the classification is retrieved from memory instead of calling Ollama again. This makes classification instant after the first time.

**6.2 — Website classifier**
Same approach as app classifier but using domain name and page title. Social media domains are always distraction. News sites are neutral unless the user is a journalist. Development documentation sites are always productive.

**6.3 — Score calculator**
Hourly: query all activity logs for the past hour, sum productive seconds, sum total active seconds, calculate percentage. Daily: same calculation across the full day. Store both in SQLite.

**6.4 — Peak focus hours detector**
Query hourly scores for the past 14 days. Group by hour of day and average the score for each hour. The top 3 hours by average score are the user's peak focus hours. Update weekly and store in `user_patterns` table.

**6.5 — Context switching analyser**
For each hour of the day calculate the average app switch count across the past 14 days. Identify hours with consistently high switching as fragmented hours and hours with consistently low switching as deep work hours.

**6.6 — Break habit analyser**
Correlate break frequency and duration with the productivity score of the following hour. Identify the optimal break duration for this specific user. Store insight in `user_patterns`.

**Module 6 test:** Run classifier on a list of 20 common apps, verify all classifications are sensible. Run scorer on a simulated day of data, verify score matches manual calculation. Verify ChromaDB stores and retrieves classifications correctly.

---

### MODULE 7 — AI DAR Generator

**File:** `ai/dar_generator.py`

**Purpose:** Read the full day's activity data and generate a professional, accurate Daily Activity Report using local Ollama. Save to SQLite and make available via API.

**Sub-modules to build in order:**

**7.1 — Day log builder**
Query SQLite for all activity logs, website logs, idle periods, break records, focus score, productive hours, top apps, and screenshot count for the requested date. Format this raw data into a clean structured text that can be passed to Ollama as context.

Format:
```
DATE: 2026-08-19
WORK START: 09:02 AM
WORK END: 06:45 PM
TOTAL ACTIVE: 7h 23m
PRODUCTIVE: 5h 12m (70%)
IDLE: 1h 20m
BREAKS: 3 short, 1 long

TOP APPS:
- VS Code (2h 45m) — productive
- Chrome (1h 30m) — mixed
- Slack (45m) — neutral

TOP WEBSITES:
- github.com (45m) — productive
- stackoverflow.com (30m) — productive
- youtube.com (20m) — distraction

CONTEXT SWITCHING: 47 switches (moderate)
LONGEST FOCUS: 1h 15m (10:30am - 11:45am)
SCREENSHOTS: 18 captured
```

**7.2 — DAR prompt**
Instruct Ollama to read the structured log and write a professional DAR with these exact sections: Executive Summary (2-3 sentences), Work Accomplished (bullet points of what was actually done based on app usage), Time Analysis (honest breakdown of productive vs lost time), Focus Insights (peak performance moments and distractions), Tomorrow's Recommendations (3 specific actionable suggestions). The prompt must explicitly instruct the model to write in first person as if the employee is reporting their own day.

**7.3 — DAR saver**
Save the generated DAR text to the `dar_reports` table:
```sql
CREATE TABLE dar_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'local',
    date DATE NOT NULL UNIQUE,
    content TEXT NOT NULL,
    productivity_score REAL,
    total_active_seconds INTEGER,
    productive_seconds INTEGER,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    emailed_at DATETIME
);
```

**7.4 — Scheduler**
Use `schedule.every().day.at("18:00").do(generate_and_save_dar)` to trigger DAR generation automatically at 6pm every evening.

**Module 7 test:** Generate a DAR from today's real tracked data. Verify the output reads professionally, covers all sections, and is factually accurate based on the raw log data.

---

#### Module 7 extension — Department-Custom DAR Templates, Structured Entries & Export/Import

Not in the original module list above — added afterward because different
departments genuinely need different structured fields on their DAR (an HR
DAR tracking candidates is not shaped like a Sales DAR tracking deal value,
which is not shaped like an IT DAR tracking ticket IDs), on top of the
narrative report 7.1-7.4 already produce. This extension is purely
additive: it does not change `generate_and_save_dar()`'s existing
behaviour, prompt, or output in any way — every sub-module below is new
tables and new routes layered next to it.

**7.5 — Departments & custom field templates**
A `departments` table (id, name) holds the org's departments (e.g. HR,
Sales, IT), fully admin-creatable — nothing is hardcoded. Each department
has at most one `dar_templates` row defining its **custom** fields as a
JSON array of `{key, label, type, required, options?}` (type is one of
`text`, `textarea`, `number`, `date`, `select`, `url`). A NULL-department
template is the default/base template applied when a department has none
of its own.

**7.6 — Structured DAR entries (task log)**
A `dar_entries` table holds the actual task-level rows for a given user's
day, independent of and alongside the narrative DAR. Every entry always
carries the same **base** fields regardless of department — `task`,
`task_description`, `start_time`, `end_time`, `comment`, `remarks`,
`link` — plus a `custom_fields_json` blob holding values for whatever
extra fields that entry's department template defines. Entries are
created/edited manually via the API (the realistic path — remarks and
links are inherently human input) or drafted by 7.7.

**7.7 — AI-assisted entry drafting**
An optional endpoint that reuses 7.1's existing day log and asks Ollama to
draft `dar_entries` rows matching the day's department template, returned
as JSON and parsed defensively (a malformed/unparseable response fails
the request with a clear error — it never fabricates entries or silently
returns nothing). Drafted rows are tagged `source='ai_draft'` and are
edited or deleted exactly like manual entries; nothing about 7.1-7.4's
narrative generation path is touched by this.

**7.8 — DAR export (CSV / DOCX / PDF)**
Given a date, export the narrative DAR content plus that day's
`dar_entries` (including each department's custom fields) as CSV, a
formatted DOCX, or a formatted PDF — the same three formats, one
document per date.

**7.9 — DAR import (CSV)**
Bulk-create `dar_entries` for a date from an uploaded CSV. Columns
matching a base field or the department template's field keys map
directly; unrecognised columns are preserved in `custom_fields_json`
rather than silently dropped, so importing never loses data even if the
CSV's shape doesn't perfectly match the current template.

**Module 7 extension test:** Create a department with two custom fields,
add three `dar_entries` for today (mixing manual and AI-drafted), export
today's DAR as CSV/DOCX/PDF and confirm all three open correctly and
contain every entry and custom field value, then re-import the exported
CSV into a fresh date and confirm the entries recreate exactly.

---

### MODULE 8 — Gmail Email Delivery

**File:** `automation/email/sender.py`

**Purpose:** Send emails via Gmail SMTP using Python smtplib. No Brevo, no SendGrid, no IP whitelisting required. Works from any network.

**Sub-modules to build in order:**

**8.1 — Gmail SMTP connector**
Configure smtplib with Gmail SMTP server `smtp.gmail.com` port 587 with STARTTLS. Authenticate using Gmail address and Gmail App Password (not account password — user must generate App Password in Google Account security settings).

**8.2 — DAR email sender**
Format the DAR as a clean plain text email with proper subject line including the date and productivity score. Send to the configured recipient email address. Update `dar_reports.emailed_at` timestamp in SQLite after successful send.

**8.3 — Alert email sender**
Send alert emails for all four alert types — focus, distraction, wellbeing, manager. Each alert email includes the alert type, trigger reason, current time, and a link to the dashboard.

**8.4 — Campaign email sender**
For bulk lead outreach — iterate through leads, write personalised email using Ollama and RAG, send via Gmail SMTP with 3-second delay between sends, log every send result to `campaign_log` table.

**8.5 — Connection tester**
`test_gmail_connection()` function that verifies credentials work and returns True or False. Called by the FastAPI status endpoint.

**Module 8 test:** Send a test email to yourself, verify it arrives in Gmail inbox (not spam), verify it sends from any network without IP errors.

---

### MODULE 9 — React Dashboard Core

**File:** `dashboard/src/App.jsx` and layout components

**Purpose:** Build the dashboard shell — navigation, routing, status cards, overall layout — connected to real FastAPI data.

**Sub-modules to build in order:**

**9.1 — Vite project setup**
Create Vite React project. Install: `recharts react-router-dom axios lucide-react date-fns @tanstack/react-query`. Configure TailwindCSS. Set up environment variable for API base URL defaulting to `http://localhost:8000`.

**9.2 — App router**
Configure React Router DOM with routes for all pages: `/`, `/timeline`, `/screenshots`, `/reports`, `/analytics`, `/command`, `/linkedin`, `/email`, `/team`, `/settings`.

**9.3 — Sidebar navigation**
Fixed left sidebar with logo, navigation links with icons, active state highlighting, collapse option. Navigation items: Dashboard, Timeline, Screenshots, Reports, Analytics, Command Mode, LinkedIn, Email, Team, Settings.

**9.4 — Top navigation bar**
Top bar with current date, system status indicator (green dot if all systems running), notification bell with unread count, user avatar.

**9.5 — Dashboard home page**
Status cards row showing: Ollama AI (running/offline), Desktop Agent (running/offline), Gmail (connected/offline), Today's Focus Score, Active Hours Today, Total Apps Tracked. Each card fetches from `/api/status` and `/api/productivity/score/today`. Auto-refresh every 30 seconds.

**9.6 — Quick actions**
Below status cards: Generate DAR Now, Post to LinkedIn, Run Email Campaign, View Today's Timeline. Each button calls the corresponding FastAPI endpoint.

**Module 9 test:** Dashboard loads at localhost:5173 with no console errors. All status cards show real data from FastAPI. Navigation routes to correct pages.

---

### MODULE 10 — Timeline View

**File:** `dashboard/src/pages/Timeline.jsx` and `dashboard/src/components/Timeline/`

**Purpose:** Visual minute-by-minute timeline of the full work day showing every app session as a colour-coded bar.

**Sub-modules to build in order:**

**10.1 — Timeline data fetcher**
Fetch all activity logs for selected date from `/api/activity/date/{date}`. Transform into timeline segments with calculated pixel positions based on the day's time range.

**10.2 — Timeline renderer**
Render each app session as a horizontal bar. Width proportional to duration. Colour coded: green for productive, blue for neutral, red for distraction, grey for idle. Show app name as label inside bar if bar is wide enough.

**10.3 — Tooltip on hover**
On hover over any bar show: app name, window title, start time, end time, duration, category badge.

**10.4 — Date selector**
Date picker above timeline to switch between days. Default to today. Navigate to any past date.

**10.5 — Screenshot markers**
Small camera icon markers on the timeline at each screenshot timestamp. Clicking opens the screenshot in a modal.

**10.6 — Idle period markers**
Grey hatched sections on the timeline showing all idle periods with duration label.

**10.7 — Context switching indicator**
Colour-coded hour blocks below the timeline showing red for high context switching hours, yellow for moderate, green for focused hours.

**10.8 — Session detail panel**
Clicking any session bar opens a right-side detail panel showing full window title history during that session, screenshot if one was taken nearby, and category with confidence.

**Module 10 test:** View today's real tracked data in the timeline. Verify every app session appears in the correct position with correct colour. Verify idle periods visible. Verify clicking opens correct details.

---

### MODULE 11 — App Usage Charts and Analytics

**File:** `dashboard/src/pages/Analytics.jsx`

**Purpose:** Data visualisation of productivity metrics — app usage breakdown, weekly trends, focus score, productive hours.

**Sub-modules to build in order:**

**11.1 — Top apps bar chart**
Horizontal bar chart showing top 10 apps by total time today. Sorted by duration descending. Colour coded by category. Duration label on each bar.

**11.2 — Category split pie chart**
Pie chart with three segments: productive (green), neutral (blue), distraction (red). Show percentage and hours for each segment. Legend below chart.

**11.3 — Productivity score gauge**
Circular progress gauge showing today's focus score 0 to 100. Colour transitions red to yellow to green based on value. Score number displayed in centre. Comparison to yesterday below gauge.

**11.4 — Weekly trend line chart**
Line chart showing daily focus scores for the past 7 days. X-axis: days of week. Y-axis: score 0 to 100. Trend line with data point markers. Reference line at user's average.

**11.5 — Focus sessions summary**
Cards showing: number of focus sessions today, average session length, longest session, sessions interrupted by distraction. All calculated from activity log data.

**11.6 — Peak hours heatmap**
7-day heat map showing productivity score per hour. Rows are hours of the day (8am to 8pm), columns are days of the week. Cell colour intensity represents productivity score. Helps user identify their consistent peak performance windows.

**11.7 — Context switching chart**
Hourly bar chart showing number of app switches per hour for today. Threshold line at 10 switches showing the alert boundary.

**Module 11 test:** View analytics for a full day of real tracked data. Verify all numbers match raw database values. Verify charts render without errors or NaN values.

---

### MODULE 12 — Screenshot Gallery

**File:** `dashboard/src/pages/Screenshots.jsx`

**Purpose:** Browse all screenshots in a searchable, filterable gallery with full-size modal view.

**Sub-modules to build in order:**

**12.1 — Screenshot grid**
Responsive grid of thumbnail images fetched from `/api/screenshots/today`. Each thumbnail shows the image, timestamp below, and the app that was active at that time.

**12.2 — Date selector**
View screenshots from any past date. Default to today.

**12.3 — Full-size modal**
Clicking any thumbnail opens a modal with the full-size screenshot. Navigation arrows to move to previous or next screenshot in the current day.

**12.4 — Blur toggle**
Toggle button per screenshot to switch between blurred and original view. Blurred is default for privacy.

**12.5 — Timeline correlation**
Clicking a screenshot in the gallery highlights the corresponding moment on a mini timeline strip below the gallery.

**12.6 — Manual capture button**
Button that calls `/api/screenshots/capture` to take an immediate screenshot. Shows a loading state then refreshes the gallery.

**Module 12 test:** Verify all screenshots from today load correctly. Verify modal opens and closes. Verify blur toggle works. Verify manual capture takes and displays new screenshot.

---

### MODULE 13 — DAR Viewer and Reports Page

**File:** `dashboard/src/pages/Reports.jsx`

**Purpose:** View all generated Daily Activity Reports and Weekly Reports in a clean readable format.

**Sub-modules to build in order:**

**13.1 — Reports list**
Sidebar list of all DARs sorted by date descending. Each entry shows date, productivity score badge, and sent status. Clicking loads that report in the main area.

**13.2 — DAR display**
Render the DAR text in a clean typographic format. Section headers styled distinctly. Bullet points formatted. Productivity score shown prominently at top.

**13.3 — Generate now button**
Button that calls `/api/reports/dar/generate`. Shows loading state with estimated wait time. Refreshes view when complete.

**13.4 — Email resend button**
Button that re-sends the current DAR via Gmail SMTP. Shows confirmation on success.

**13.5 — Weekly report section**
Separate tab for weekly reports. Shows the latest weekly report and a list of all past weekly reports. Same display format as DAR.

**13.6 — Export option**
Download any DAR as a plain text file with the date as filename.

**Module 13 test:** View a real generated DAR. Verify all sections display correctly. Verify Generate Now produces a new report. Verify email send works.

---

### MODULE 14 — Smart Alerts System

**File:** `ai/tools/activity_tools.py` alert section and `dashboard/src/components/Alerts/`

**Purpose:** AI monitors activity patterns and sends proactive alerts when something needs attention.

**Sub-modules to build in order:**

**14.1 — Focus alert**
Monitor idle time in real time. If idle period exceeds 30 consecutive minutes during configured work hours (9am to 7pm) trigger a focus alert. Send Windows desktop notification via plyer. Optionally send email alert. Log alert to `alerts` table.

**14.2 — Distraction alert**
Every hour calculate percentage of time spent on distraction category apps or websites. If distraction time exceeds 30% of the hour trigger a distraction alert with the specific apps or sites that triggered it.

**14.3 — Wellbeing alert**
If total active time for the day exceeds 10 hours trigger an overwork alert. If this happens 5 consecutive days trigger a burnout risk alert. Both sent as desktop notification and email.

**14.4 — Manager alert (Team Module)**
When a team member shows no activity for over 2 hours during work hours, send a manager notification. Only applies when team mode is enabled.

**14.5 — Alert dashboard display**
Notification bell in dashboard top bar shows unread alert count. Clicking opens a dropdown list of recent alerts with type, message, timestamp, and dismiss button.

**14.6 — Alert preferences**
Settings page allows enabling or disabling each alert type and configuring thresholds.

**Module 14 test:** Simulate each alert condition and verify desktop notification appears, email arrives, and alert appears in dashboard notification centre.

---

### MODULE 15 — LangGraph Master Agent

**File:** `ai/master_agent.py`

**Purpose:** The central autonomous agent that orchestrates all sub-agents, plans the day, delegates tasks, handles failures, and compiles the evening report. Built on LangGraph for stateful multi-agent coordination.

**Sub-modules to build in order:**

**15.1 — State definition**
Define the `AgentState` TypedDict for LangGraph:
```python
class AgentState(TypedDict):
    date: str
    yesterday_dar: str
    lead_pipeline: list
    linkedin_analytics: dict
    email_log: list
    daily_plan: list
    completed_tasks: list
    failed_tasks: list
    current_task: str
    messages: list
    final_report: str
```

**15.2 — Planning node**
Morning planning function that reads yesterday's DAR from SQLite, checks lead pipeline, reviews LinkedIn post log, identifies unresponded email leads, checks any calendar file, and generates a structured daily task plan. Returns updated state with `daily_plan` populated.

**15.3 — Task router**
Conditional edge function that reads `current_task` from state and routes to the correct sub-agent node — LinkedIn, Email, Research, Tracking, Reporting.

**15.4 — Failure handler**
If a sub-agent returns a failure status, the failure handler node logs the failure, increments a retry counter, and re-routes to the same sub-agent with modified instructions. After 3 failures marks the task as permanently failed and moves on.

**15.5 — Completion compiler**
End-of-day node that reads all `completed_tasks` and `failed_tasks` from state, combines with the tracking data DAR, and writes a comprehensive Master Report covering both work activity and automation results.

**15.6 — LangGraph graph assembly**
Assemble all nodes into a LangGraph `StateGraph`. Add edges between nodes. Compile the graph. The graph entry point is the planning node and the terminal node is the completion compiler.

**15.7 — Daily scheduler**
Schedule the Master Agent to run its morning planning cycle at 9am and its completion cycle at 6pm every day via the `schedule` library.

**Module 15 test:** Run the Master Agent through a complete simulated day cycle. Verify it reads yesterday's DAR, generates a plan, routes correctly to each sub-agent, handles a simulated failure with retry, and produces a final report.

---

### MODULE 16 — Sub-Agent Implementation

**Files:** `ai/sub_agents/`

**Purpose:** Build each sub-agent as a LangGraph-compatible node that receives state, executes its specific task, and returns updated state.

**Sub-modules to build in order:**

**16.1 — Tracker Sub-Agent** (`ai/sub_agents/tracker_agent.py`)
Reads real-time activity data from SQLite every hour. Checks alert thresholds. Triggers alerts when thresholds exceeded. Updates `daily_stats` with current metrics. Returns status to Master Agent.

**16.2 — Reporting Sub-Agent** (`ai/sub_agents/reporting_agent.py`)
Calls `dar_generator.py` to generate the DAR. Calls weekly report generator on Mondays. Calls Gmail sender to email reports. Updates Master Agent state with report content for inclusion in Master Report.

**16.3 — LinkedIn Sub-Agent** (`ai/sub_agents/linkedin_agent.py`)
Receives topic from Master Agent plan. Calls `automation/linkedin/content_writer.py` to write post using Ollama. Calls `automation/linkedin/image_finder.py` to find relevant image via Playwright. Calls `automation/linkedin/poster.py` to publish via Playwright browser automation. Returns success or failure with post ID.

**16.4 — Email Sub-Agent** (`ai/sub_agents/email_agent.py`)
Receives list of leads requiring follow-up from Master Agent plan. For each lead calls `automation/email/writer.py` to write personalised email using RAG. Calls `automation/email/sender.py` to send via Gmail SMTP. Updates campaign log. Returns send results.

**16.5 — Research Sub-Agent** (`ai/sub_agents/research_agent.py`)
Receives target profile from Master Agent plan. Uses Playwright to search Google and LinkedIn public pages for matching profiles. Extracts name, company, role, and any available contact information. Stores results in ChromaDB and SQLite leads table. Returns number of new leads found.

**Module 16 test:** Test each sub-agent individually with mock state input. Verify it completes its task and returns correct state updates. Then test with Master Agent orchestrating all sub-agents in sequence.

---

### MODULE 17 — Command Mode

**Files:** `api/routes/command.py` and `dashboard/src/pages/CommandMode.jsx`

**Purpose:** Natural language command interface where the user types any instruction and the Master Agent executes it across any module.

**Sub-modules to build in order:**

**17.1 — Command parser**
Rule-based regex parser (never AI parser for reliability) that extracts: action type (post/email/find/report/status), topic or target, count, time interval, and any other parameters from the natural language input.

**17.2 — Command router**
Routes parsed command to the correct sub-agent or tool based on action type. Post commands go to LinkedIn sub-agent. Email commands go to Email sub-agent. Find commands go to Research sub-agent. Report commands go to Reporting sub-agent.

**17.3 — Background job runner**
Each command runs in a background thread so the API returns immediately with a job ID. The job executes asynchronously and updates a `jobs` dictionary with live status, logs, and results.

**17.4 — Job status endpoint**
`GET /api/command/status/{job_id}` returns current job status, percentage complete, live logs array, and results.

**17.5 — Job cancel endpoint**
`POST /api/command/cancel/{job_id}` sets a cancel flag on the job. The background thread checks this flag and exits gracefully.

**17.6 — Command Mode UI**
Large text input with example commands shown below. Run button. Live log output with auto-scroll. Progress bar. Job history showing all previous commands with results. Cancel button visible while job is running.

**Module 17 test:** Run five different command types. Verify each routes to the correct module. Verify live logs appear in real time. Verify cancel stops the job cleanly.

---

### MODULE 18 — LinkedIn Automation via Playwright

**Files:** `automation/linkedin/`

**Purpose:** Post to LinkedIn entirely through browser automation. No LinkedIn API, no developer account, no IP restrictions.

**Sub-modules to build in order:**

**18.1 — Content writer** (`automation/linkedin/content_writer.py`)
Write LinkedIn post using Ollama with structured prompt. Format with proper line breaks between paragraphs. Hashtags on last line. Maximum 1300 characters enforced. Return both content and topic used.

**18.2 — Topic rotation** (`automation/linkedin/content_writer.py`)
Maintain `last_topic.txt` to track which topic was last used. Rotate through `POST_TOPICS` list in `config.py` so no topic repeats until all have been used.

**18.3 — Image finder** (`automation/linkedin/image_finder.py`)
Use Playwright to open `pexels.com`, search for images matching the post topic keywords, click the first high-quality result, download the full resolution image to a temp file. Return the temp file path.

**18.4 — LinkedIn browser poster** (`automation/linkedin/poster.py`)
Use Playwright with a persistent browser context that saves LinkedIn session cookies so login is only required once. Navigate to LinkedIn, click the post creation area, type the content using `page.fill()`, attach the image if provided, click the Post button. Extract the post ID from the URL after posting.

**18.5 — Session management**
Save browser cookies to a JSON file after first login. Load cookies on subsequent runs to avoid re-login. Handle session expiry by detecting the login page and re-authenticating.

**18.6 — Rate limiting**
Enforce a minimum 30-minute gap between posts to avoid LinkedIn anti-automation detection. Log all posts to `post_log` table with timestamps. Refuse to post if last post was less than 30 minutes ago.

**Module 18 test:** Post a test message to LinkedIn. Verify it appears on the profile. Verify image attaches. Verify session persists across multiple runs without re-login.

---

### MODULE 19 — Email Campaign Automation

**Files:** `automation/email/`

**Purpose:** Find leads, write personalised emails using RAG, send via Gmail SMTP, track results, handle follow-ups automatically.

**Sub-modules to build in order:**

**19.1 — Lead loader** (`automation/leads/store.py`)
Load leads from SQLite leads table. Filter out leads already contacted in the current campaign period by checking `campaign_log`. Return only new uncontacted leads up to the daily limit.

**19.2 — RAG email writer** (`automation/email/writer.py`)
For each lead query ChromaDB for all stored information about that lead. Build a rich context string from retrieved chunks. Pass context plus lead basic info to Ollama with a personalisation prompt. Parse subject line and body from the response. Validate that the email actually references the lead's specific information.

**19.3 — Gmail sender** (`automation/email/sender.py`)
Build MIME email with From header showing sender name and Gmail address. Set proper subject. Body as plain text. Send via smtplib with STARTTLS. Handle send errors gracefully and log failure reason.

**19.4 — Campaign logger** (`automation/email/logger.py`)
Log every send attempt to `campaign_log` table whether it succeeded or failed. Fields: date, time, lead name, email, company, subject, status, error message. Prevent duplicate sends by checking this log before each send.

**19.5 — Follow-up scheduler**
Check campaign log daily for leads who received an email 3 days ago with no reply detected. Generate a follow-up email referencing the previous email and send. Mark as follow-up in the log.

**19.6 — Campaign runner** (`automation/email/campaign.py`)
Orchestrates the full campaign: load leads, write emails, send with 3-second delay between sends, log results, print summary. Respects daily limit of 500 emails. Runs on schedule via Master Agent or on demand via Command Mode.

**Module 19 test:** Run a campaign to 3 test email addresses you control. Verify all 3 receive personalised emails referencing their specific lead data. Verify campaign log records all sends correctly. Verify no duplicate sends on second run.

---

### MODULE 20 — Lead Research and Generation Agent

**Files:** `automation/leads/` and `ai/sub_agents/research_agent.py`

**Purpose:** Automatically find new leads matching the target profile using Playwright web scraping. No paid lead database. No API.

**Sub-modules to build in order:**

**20.1 — Google search scraper** (`automation/leads/finder.py`)
Use Playwright to search Google for queries like `"AI automation" site:linkedin.com OR "Agentic AI" founder email`. Parse the search result page for names, company names, and any visible email addresses. Handle Google's anti-scraping measures with random delays between 2 and 5 seconds between page loads.

**20.2 — LinkedIn public profile reader**
For LinkedIn public profiles (not logged in) use Playwright to visit the profile page and extract name, headline, location, and company from the publicly visible information. Do not scrape when logged in to avoid account risk.

**20.3 — Lead enricher** (`automation/leads/enricher.py`)
For each found lead search for their company website, find the contact page or about page, extract any email patterns, and build a complete profile. Store all gathered information as ChromaDB documents for RAG use.

**20.4 — Lead deduplicator**
Before storing any new lead check SQLite leads table for existing entry with same name and company. If duplicate found update the existing record with any new information rather than creating a duplicate.

**20.5 — Lead store** (`automation/leads/store.py`)
Store leads in both SQLite `leads` table and ChromaDB as vector embeddings. SQLite for structured queries. ChromaDB for semantic search and RAG personalisation.

**Module 20 test:** Run the research agent with a target profile. Verify it finds at least 5 new leads. Verify all are stored correctly in SQLite and ChromaDB. Verify no duplicates created.

---

### MODULE 21 — Team Intelligence Dashboard

**Files:** `api/routes/team.py` and `dashboard/src/pages/Team.jsx`

**Purpose:** Manager view showing all team members' activity, productivity, and AI-generated team insights.

**Sub-modules to build in order:**

**21.1 — Multi-user data model**
Update all SQLite tables to include `user_id` column (already in schema above). Add `users` table:
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    role TEXT DEFAULT 'employee',
    organisation_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**21.2 — Team overview page**
Grid of team member cards. Each card shows: name, avatar placeholder, current status (active/idle/offline), today's focus score, hours worked today, current active app. Auto-refresh every 60 seconds.

**21.3 — Individual member view**
Clicking a team member opens their full timeline, app usage breakdown and screenshots for the selected date. Same components as personal view but filtered to that user's data.

**21.4 — AI team analysis**
Weekly Ollama-powered analysis that reads all team members' weekly data and produces: high performer identification, struggling member flags, workload imbalance detection, bottleneck identification, rebalancing suggestions, burnout risk scoring.

**21.5 — Team comparison chart**
Bar chart comparing all team members by focus score, productive hours, and context switching for the selected week. Anonymise names option for sensitive team environments.

**Module 21 test:** Simulate two users' data in SQLite. Verify manager dashboard shows both users. Verify clicking each shows their individual data. Verify AI team analysis produces sensible output.

---

### MODULE 22 — Chrome Extension for URL Tracking

**File:** `extension/`

**Purpose:** Accurately track which websites are visited by sending real URL data from the browser to the local Python tracker.

**Sub-modules to build in order:**

**22.1 — Manifest and permissions**
Write `manifest.json` with manifest version 3, tab permissions, activeTab permission, background service worker.

**22.2 — Content script**
`content.js` runs on every page. Sends current `document.URL` and `document.title` to `http://localhost:8001/url` via fetch every 5 seconds.

**22.3 — Background service worker**
`background.js` listens for tab change events via `chrome.tabs.onActivated` and `chrome.tabs.onUpdated`. On every tab change immediately sends the new URL to the local tracker without waiting for the 5-second interval.

**22.4 — Local URL receiver**
`agent/browser_tracker.py` runs an HTTP server on port 8001. Every received URL closes the previous website session and opens a new one with current timestamp.

**22.5 — Install instructions**
Document how to load the extension in Chrome developer mode: open `chrome://extensions`, enable Developer Mode, click Load Unpacked, select the `extension/` folder.

**Module 22 test:** Install extension, browse 5 websites for 2 minutes each, verify all exact URLs and page titles are logged in SQLite websites table with correct durations.

---

### MODULE 23 — PyInstaller .exe Packaging

**File:** `scripts/` and project root

**Purpose:** Package the desktop agent into a single .exe file that employees can install on their Windows PC with one double-click. No Python required on the employee machine.

**Sub-modules to build in order:**

**23.1 — Spec file**
Write `workpulse-agent.spec` for PyInstaller with all hidden imports for pywin32, Pillow, keyboard, schedule, requests, and SQLite.

**23.2 — Build script**
`scripts/build_exe.bat` that runs `pyinstaller workpulse-agent.spec --onefile --windowed --icon=icon.ico`. The `--windowed` flag prevents a CMD window from appearing. The `--onefile` flag packages everything into a single .exe.

**23.3 — Auto-start on Windows**
Add a registry key to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` so the agent starts automatically when Windows starts. This is done programmatically by the agent on first run.

**23.4 — Config file**
The .exe reads `workpulse-config.json` from the same directory as the .exe. This config contains the API server URL, user ID, Gmail credentials for email, and agent settings. No hardcoded credentials in the .exe.

**23.5 — First-run setup**
On first run the agent shows a simple setup prompt in the system tray asking for the API server URL and the user's name. After setup it saves config and starts tracking automatically.

**Module 23 test:** Build the .exe, install on a clean Windows machine with no Python, verify agent starts and tracks apps correctly, verify auto-start on Windows restart.

---

### MODULE 24 — Cloud Deployment

**Files:** `docs/DEPLOYMENT.md` and deployment configs

**Purpose:** Deploy the full system to cloud so managers can access the dashboard from anywhere and team agents sync to the central server.

**Sub-modules to build in order:**

**24.1 — Oracle Cloud PostgreSQL**
Set up a free Oracle Cloud Always Free VPS (1 OCPU, 1GB RAM, 50GB storage). Install PostgreSQL. Migrate SQLite schema to PostgreSQL. Configure remote access with SSL.

**24.2 — Railway FastAPI deployment**
Connect GitHub repository to Railway. Configure build command `pip install -r requirements.txt` and start command `uvicorn api.main:app --host 0.0.0.0 --port 8000`. Set environment variables for PostgreSQL connection string and all credentials.

**24.3 — Vercel React deployment**
Connect GitHub repository to Vercel. Configure build command `npm run build` and output directory `dist`. Set environment variable `VITE_API_URL` to the Railway deployment URL.

**24.4 — MinIO screenshot storage**
Install MinIO on the Oracle Cloud VPS. Configure as S3-compatible object storage for screenshots. Update agent sync to upload screenshots to MinIO instead of local disk. Update dashboard to serve screenshots from MinIO URLs.

**24.5 — Agent cloud config**
Update `workpulse-config.json` to point to the Railway API URL instead of localhost. All agents on all employee PCs sync to the central cloud server.

**Module 24 test:** Deploy everything. Verify dashboard loads from Vercel URL. Verify agent data syncs to cloud PostgreSQL. Verify screenshots accessible from MinIO. Verify team dashboard shows data from multiple agents.

---

## 6. Database Schema Reference

```sql
-- Core tracking tables
CREATE TABLE activity_logs (id, user_id, app_name, window_title, start_time, end_time, duration_seconds, category, date, created_at);
CREATE TABLE websites (id, user_id, url, domain, page_title, start_time, end_time, duration_seconds, category, date);
CREATE TABLE screenshots (id, user_id, file_path, thumbnail_path, timestamp, date, is_blurred, cloud_url);
CREATE TABLE breaks (id, user_id, start_time, end_time, duration_seconds, break_type, date);
CREATE TABLE idle_periods (id, user_id, start_time, end_time, duration_seconds, date);

-- Metrics tables
CREATE TABLE daily_stats (id, user_id, date, work_start, work_end, total_active_seconds, productive_seconds, idle_seconds, focus_score, app_switch_count, top_apps_json, top_sites_json);
CREATE TABLE hourly_scores (id, user_id, date, hour, focus_score, productive_seconds, total_seconds, switch_count);
CREATE TABLE user_patterns (id, user_id, peak_focus_hours_json, optimal_break_duration, fragmented_hours_json, updated_at);
CREATE TABLE weekly_trends (id, user_id, week_start, avg_focus_score, total_hours, productive_hours, trend_direction);

-- Report tables
CREATE TABLE dar_reports (id, user_id, date, content, productivity_score, total_active_seconds, productive_seconds, generated_at, emailed_at);
CREATE TABLE weekly_reports (id, user_id, week_start, content, generated_at, emailed_at);
CREATE TABLE alerts (id, user_id, alert_type, message, triggered_at, dismissed_at, emailed);

-- Module 7 extension: department-custom DAR templates & structured entries
CREATE TABLE departments (id, name, created_at);
CREATE TABLE dar_templates (id, department_id, fields_json, updated_at);
CREATE TABLE dar_entries (id, user_id, date, department_id, task, task_description, start_time, end_time, comment, remarks, link, custom_fields_json, source, created_at, updated_at);

-- User and team tables
CREATE TABLE users (id, name, email, role, organisation_id, created_at);
CREATE TABLE organisations (id, name, plan, created_at);

-- Automation tables
CREATE TABLE leads (id, name, company, role, interest, email, notes, last_contact, source, created_at);
CREATE TABLE campaign_log (id, date, time, name, email, company, subject, status, error, follow_up_sent);
CREATE TABLE post_log (id, date, time, topic, content, post_id, platform, status, likes, comments, error);
CREATE TABLE jobs (id, command, status, progress, logs_json, result, created_at, completed_at);
```

---

## 7. Configuration Reference

All settings live in `config.py` files. Never hardcode credentials in any other file.

```python
# agent/config.py
API_URL = "http://localhost:8000"
USER_ID = "local"
SCREENSHOT_INTERVAL_MINUTES = 5
IDLE_THRESHOLD_SECONDS = 300
WORK_HOURS_START = "09:00"
WORK_HOURS_END = "19:00"
BLUR_SCREENSHOTS = False
DAR_GENERATION_TIME = "18:00"

# api/config.py
DATABASE_URL = "sqlite:///./workpulse.db"
SECRET_KEY = "change-this-in-production"
GMAIL_ADDRESS = ""
GMAIL_APP_PASSWORD = ""
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:1.7b"
OLLAMA_FAST_MODEL = "phi3:mini"
CHROMADB_PATH = "./chromadb"

# automation/config.py
LINKEDIN_EMAIL = ""
LINKEDIN_PASSWORD = ""
LINKEDIN_COOKIES_PATH = "./linkedin_cookies.json"
POST_TOPICS = []
DAILY_POST_LIMIT = 3
MIN_POST_INTERVAL_MINUTES = 30
DAILY_EMAIL_LIMIT = 500
```

---

## 8. Development Conventions

**One sub-module at a time.** Complete and test each sub-module before starting the next. Never write two sub-modules simultaneously.

**Test before moving on.** Every module has a defined test at the bottom of its specification. Run that test and verify it passes completely before marking the module done.

**Error handling everywhere.** Every function that calls Ollama, hits a database, or uses Playwright must be wrapped in try-except. Failures must be logged to SQLite, not silently swallowed.

**No print statements in production code.** Use Python `logging` module. Log levels: DEBUG for detailed tracing, INFO for normal operation, WARNING for recoverable issues, ERROR for failures.

**Configuration over hardcoding.** Every setting, credential, threshold, or path lives in `config.py`. Never hardcode in business logic files.

**Backward compatible schema changes.** When adding a column to SQLite use `ALTER TABLE ADD COLUMN` with a DEFAULT value so existing data is not broken.

**Playwright always uses persistent context.** Always initialise Playwright with `browser.new_context(storage_state="cookies.json")` so sessions persist between runs without re-login.

**Ollama calls always include timeout.** Every request to Ollama must include `timeout=120` minimum. If Ollama times out log the failure and return a default value rather than crashing.

**ChromaDB collections are named by function.** `leads` for lead data. `app_classifications` for cached app category decisions. `agent_memory` for Master Agent persistent memory. Never mix data types in one collection.

---

## 9. Running the System Locally

Open 4 CMD windows and run one command in each:

```bash
# Window 1 — Ollama
ollama serve

# Window 2 — Desktop Agent
cd C:\workpulse-ai\agent
python main.py

# Window 3 — FastAPI Backend
cd C:\workpulse-ai\api
uvicorn main:app --reload --port 8000

# Window 4 — React Dashboard
cd C:\workpulse-ai\dashboard
npm run dev
```

Open browser at `http://localhost:5173`

---

## 10. Current Build Status

Update this section as each module is completed.

| Module | Status | Notes |
|---|---|---|
| MODULE 1 — App Tracker | ⬜ Not started | |
| MODULE 2 — Time Intelligence | ⬜ Not started | |
| MODULE 3 — Screenshot System | ⬜ Not started | |
| MODULE 4 — Browser Tracker | ⬜ Not started | |
| MODULE 5 — FastAPI Backend | ⬜ Not started | |
| MODULE 6 — Productivity Scorer | ⬜ Not started | |
| MODULE 7 — DAR Generator | ⬜ Not started | |
| MODULE 8 — Gmail Email | ⬜ Not started | |
| MODULE 9 — Dashboard Core | ⬜ Not started | |
| MODULE 10 — Timeline View | ⬜ Not started | |
| MODULE 11 — Analytics Charts | ⬜ Not started | |
| MODULE 12 — Screenshot Gallery | ⬜ Not started | |
| MODULE 13 — DAR Viewer | ⬜ Not started | |
| MODULE 14 — Smart Alerts | ⬜ Not started | |
| MODULE 15 — Master Agent | ⬜ Not started | |
| MODULE 16 — Sub-Agents | ⬜ Not started | |
| MODULE 17 — Command Mode | ⬜ Not started | |
| MODULE 18 — LinkedIn Playwright | ⬜ Not started | |
| MODULE 19 — Email Campaigns | ⬜ Not started | |
| MODULE 20 — Lead Research | ⬜ Not started | |
| MODULE 21 — Team Intelligence | ⬜ Not started | |
| MODULE 22 — Chrome Extension | ⬜ Not started | |
| MODULE 23 — .exe Packaging | ⬜ Not started | |
| MODULE 24 — Cloud Deployment | ⬜ Not started | |

---

*Last updated: August 19, 2026*
*Version: 1.0.0*