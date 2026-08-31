# WorkPulse AI

A full-stack, agentic AI work-intelligence platform: a Windows desktop agent tracks
work activity, a local AI stack turns it into focus scores and daily reports, and a
React dashboard gives employees and managers a real-time and historical view of it —
all with zero paid cloud AI APIs.

WorkPulse AI doesn't wait for button clicks. It watches, thinks, and acts: tracking
apps and websites, scoring focus, writing a daily activity report every evening, and
posting/emailing on your behalf, on a schedule, with no human intervention unless a
decision genuinely needs one.

## Features

**Work Intelligence**
- Active window / app & website tracking, idle detection, break classification
- Meeting-aware idle detection — a scheduled meeting (synced from a local `.ics`
  calendar export) excuses that time from counting as idle
- Live focus score, active hours, and context-switching analysis
- AI-written Daily Activity Reports (DAR) — narrative and structured task-log views,
  with CSV/DOCX/PDF export and CSV import
- Department-custom DAR templates with per-department custom fields

**Team Management (Admin/Manager)**
- Per-member profile: live overview + timeline, attendance calendar,
  and full DAR history — not just today's snapshot
- Admin-controlled per-employee feature toggles (activity tracking, DAR
  generation, alerts) that actually gate the employee's own desktop agent, not
  just the dashboard view
- Role-based access control: `employee` (own data only), `manager` (team oversight),
  `admin` (full account control)
- AI-powered weekly team analysis: high performers, struggling members, workload
  imbalance, burnout risk

**Business Automation**
- LinkedIn post writing + posting via real browser automation (Playwright)
- Personalised email campaigns via Gmail SMTP + local RAG
- Lead discovery and enrichment

**Auth**
- Email/password login with JWT + bcrypt
- Optional "Sign in with Google" SSO (off by default, invite-only — matches an
  existing account by email, never auto-creates one)

## Architecture

Three independent pieces sharing one SQLite database:

```
┌─────────────────────┐        ┌──────────────────────┐        ┌──────────────────┐
│   Desktop Agent      │        │   FastAPI Backend      │        │  React Dashboard   │
│  (agent/, packaged    │──────▶│  (api/, ai/,            │◀──────▶│  (frontend/)        │
│   as WorkPulseAgent   │  same │   automation/)          │  REST  │                    │
│   .exe per employee)  │ SQLite│                         │        │                    │
└─────────────────────┘  file  └──────────────────────┘        └──────────────────┘
                                          │
                                          ▼
                                  Local Ollama models
                                  (classification, DAR
                                   writing, team analysis)
```

- **`agent/`** — runs on each employee's machine. Tracks the active window,
  detects idle time, and writes straight to the local SQLite file. Packaged as
  a single-file `.exe` with a system-tray icon (`agent/tray_main.py`,
  `scripts/build_exe.bat`).
- **`api/`** — FastAPI backend serving the dashboard: auth, activity,
  attendance, reports, team management, SSO.
- **`ai/`** — the agentic layer: a LangGraph Master Agent, DAR generation,
  productivity scoring, pattern analysis, and team analysis, all via local Ollama.
- **`automation/`** — LinkedIn posting, email campaigns, and lead generation via
  Playwright + Gmail SMTP.
- **`frontend/`** — the React + Vite + TailwindCSS dashboard.

## Tech stack

| Layer | Technology |
|---|---|
| AI inference | Ollama (`qwen3:1.7b`, `phi3:mini`, `nomic-embed-text`) — fully local |
| Agent orchestration | LangGraph + LangChain |
| Vector store | ChromaDB (classification memory, RAG) |
| Desktop tracking | pywin32, psutil, Pillow, pystray |
| Browser automation | Playwright |
| Backend | FastAPI, SQLAlchemy, Pydantic, python-jose (JWT), bcrypt |
| Database | SQLite (local-first; PostgreSQL-compatible for cloud deploys) |
| Email | Gmail SMTP via `smtplib` |
| Frontend | React 19, Vite, TypeScript, TailwindCSS v4, TanStack Query, React Router |
| Packaging | PyInstaller (desktop agent → single `.exe`) |

## Zero-external-API architecture

The AI layer never calls a paid cloud API — no OpenAI, Anthropic, or Groq. All
inference (classification, DAR writing, team analysis) runs on local Ollama models,
so there's no per-token cost and no activity data ever leaves the machine it's
tracked on. A small number of free, optional, explicitly-documented integrations
exist alongside that rule — Gmail SMTP for report emails, Playwright for LinkedIn
posting, and optional Google SSO for login — none of which are paid, none of which
touch the tracking/AI pipeline, and all of which are off unless you configure them.

## Getting started

### Prerequisites

- Python 3.11+ (Windows, for the desktop agent — `pywin32` is Windows-only)
- Node.js 18+
- [Ollama](https://ollama.com), with the models this project uses pulled locally:
  ```
  ollama pull qwen3:1.7b
  ollama pull phi3:mini
  ollama pull nomic-embed-text
  ```

### 1. Configure environment

```
cp .env.example .env
```

Fill in whichever sections you need — everything is optional except `SECRET_KEY`
(change it from the default). See the comments in `.env.example` for Gmail,
LinkedIn, and Google SSO setup steps.

### 2. Backend + AI stack

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000
```

The first request creates `workpulse.db` (SQLite) automatically.

### 3. Desktop agent

```
python -m agent.main
```

Runs from source using `WORKPULSE_USER_ID` (or `local` by default). To build the
packaged, double-clickable `.exe` for distributing to employee machines, see
`scripts/build_exe.bat` and `workpulse-agent.spec`.

### 4. Dashboard

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The first account you create becomes the admin.

## Project layout

```
agent/          Desktop tracking agent (per-employee, packaged as .exe)
api/             FastAPI backend — routes, auth, database models
ai/              Agentic layer — Master Agent, DAR generation, scoring, analysis
automation/      LinkedIn, email, and lead-generation automation
frontend/        React + Vite + TailwindCSS dashboard
scripts/         Build and packaging utilities
docs/            API reference and deployment notes
DEVELOPMENT.md   Full internal build spec and module-by-module architecture notes
```

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for the complete module-by-module build
history and architectural reasoning behind each feature.
