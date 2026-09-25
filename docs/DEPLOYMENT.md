# WorkPulse AI — Deployment Guide

Deploying the API (Railway), the dashboard (Vercel) and pointing the desktop agent at the cloud API.
For local setup see [`../README.md`](../README.md); for how the system works see [`../DEVELOPMENT.md`](../DEVELOPMENT.md).

**Contents:** [Scope](#whats-actually-deployed-here-and-what-isnt) · [1. API on Railway](#1-api-on-railway-module-242) ·
[2. Dashboard on Vercel](#2-dashboard-on-vercel-module-243) · [3. Desktop agent](#3-desktop-agent-pointed-at-the-cloud-api-module-245-partial) ·
[4. What must persist](#4-what-must-persist) · [5. Security and go-live checklist](#5-security-and-go-live-checklist) ·
[6. Ollama in the cloud](#6-local-ai-ollama-in-a-cloud-deployment)

## What's actually deployed here, and what isn't

This covers **dashboard on Vercel + API on Railway**, with the desktop
agent (module 23's packaged .exe) running on your own PC and pointing at
the Railway URL. That's a real, working deployment: one person (or a
handful sharing one agent's data) gets a dashboard reachable from anywhere,
backed by a server that's always on.

What this deliberately does **not** include, and why:

- **Postgres migration (originally 24.1).** `agent/database.py` — the
  schema owner every module reads and writes through, including the AI
  modules — is hand-written SQLite (`AUTOINCREMENT`, `?` placeholders, a
  raw `sqlite3` connection), not an ORM abstraction over a swappable
  database. Moving to Postgres means rewriting that whole persistence layer 
  across every file that touches it, which is a large, invasive change I
  can't safely verify without a live Postgres instance to test the rewrite
  against. Deferred by explicit decision — see the conversation this was
  decided in — not attempted partially.
- **Multi-agent cloud sync (originally 24.5).** Right now the agent and API
  share one local SQLite file on disk. A real multi-employee deployment
  (each agent on a separate PC, syncing to one central server) needs either
  the Postgres migration above or a new HTTP ingestion API the agent pushes
  to — neither exists yet. What's deployed here is **one agent, one API,
  one SQLite file** — the API just happens to run on Railway instead of
  your own machine, and the agent (or several, if everyone points at the
  same API and shares the `local` user_id) reaches it over the network.

If you outgrow this — multiple employees, each wanting their own tracked
identity synced centrally — that's the point to revisit the Postgres +
ingestion-API work, not before.

---

## 1. API on Railway (module 24.2)

1. Push this repo to GitHub (if it isn't already).
2. At [railway.app](https://railway.app), **New Project → Deploy from GitHub repo**, pick this repo.
3. Railway reads `railway.json` / `Procfile` automatically — build command
   `pip install -r requirements.txt`, start command
   `uvicorn api.main:app --host 0.0.0.0 --port $PORT`.
4. In the Railway project's **Variables** tab, set whatever you'd normally
   put in `.env`: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`,
   `REPORT_RECIPIENT_EMAIL`, `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`,
   `PEXELS_API_KEY`, `SECRET_KEY`, and `CORS_ORIGINS` (add your Vercel URL
   once you have it — step 2 below). For the SEO suite also set
   `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` (see §4 — the key file must exist on the server),
   `PAGESPEED_API_KEY`, `OLLAMA_BASE_URL` (see §6) and any CMS / social keys you use.
   The full list is in `.env.example`.
5. Railway's filesystem is ephemeral on redeploy — `workpulse.db` will
   reset when the service restarts unless you attach a Railway **Volume**
   to the project and point `DATABASE_URL` at it.
6. **Playwright-dependent endpoints** (LinkedIn posting, lead research)
   need Chromium installed on the server, which Railway's default Nixpacks
   build does not do automatically. Either add a
   `playwright install --with-deps chromium` build step, or accept that
   those specific endpoints won't work from the Railway deployment and only
   run them locally — everything else (tracking data, DAR, dashboard,
   Team, Command Mode's non-Playwright actions) works fine either way.
7. Note your Railway URL (e.g. `https://your-app.up.railway.app`) — you'll need it for steps 2 and 4.

## 2. Dashboard on Vercel (module 24.3)

1. At [vercel.com](https://vercel.com), **New Project**, import the same
   GitHub repo, set **Root Directory** to `frontend`.
2. Vercel reads `frontend/vercel.json` automatically (`npm run build`,
   output `dist`, with a rewrite so client-side routes like `/team` don't
   404 on direct navigation).
3. Set the environment variable `VITE_API_URL` to your Railway URL from
   step 1.6.
4. Deploy. Go back to Railway and add this Vercel URL to `CORS_ORIGINS`
   (see step 1.4) so the browser is actually allowed to call the API.

## 3. Desktop agent pointed at the cloud API (module 24.5, partial)

Build the packaged agent (module 23 — see [`../DEVELOPMENT.md`](../DEVELOPMENT.md) for
`scripts/build_exe.bat`), run it once, and when the first-run setup dialog
asks for the API server URL, give it your Railway URL instead of
`http://localhost:8000`. That's the entire "point at cloud" step for a
single agent — `workpulse-config.json` next to the .exe stores it, and
every future launch reuses it without asking again.

This works for one agent (or several agents that don't mind sharing the
same `local` user_id / tracking identity). It is **not** the multi-employee
"each person has their own synced identity" setup — see the note at the
top of this document for what that actually requires.

---   

## 4. What must persist

Everything the API writes at runtime lives on the server's disk. On Railway (ephemeral filesystem) attach a
**Volume** and keep these on it, or they reset on every redeploy:

| Path | Contents | If lost |
|---|---|---|
| `workpulse.db` (+ `-wal`, `-shm`) | All data, per-site credentials, settings | Everything is lost — back it up |
| `sitemaps/` | Generated sitemap files and their URL lists | Regenerate from **SEO → Search Console → Sitemap Generator** |
| `chromadb/` | Vector store (classification cache, interlinking index) | Rebuilt over time; interlink suggestions reset |
| Google service-account key file | Path in `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` | Search Console / Analytics / Sheets stop working |
| `linkedin_cookies.json` | Saved LinkedIn session | Sign in again once |

Point `DATABASE_URL` at the volume. Treat the service-account key and `.env` values as secrets: set them as platform
variables or mounted secret files, never commit them.

## 5. Security and go-live checklist

- [ ] `SECRET_KEY` is a long random value, unique to this deployment.
- [ ] `CORS_ORIGINS` lists only the real dashboard origin(s) — no wildcard.
- [ ] Everything is served over HTTPS (Railway and Vercel do this by default).
- [ ] The first admin account is created immediately after the first deploy (the first account registered becomes
      the admin, so do not leave a fresh deployment publicly reachable and unclaimed).
- [ ] `.env`, `workpulse-config.json`, `linkedin_cookies.json` and key files are not in the repository.
- [ ] The API is started without `--reload` under a supervisor (Railway's restart policy in `railway.json`).
- [ ] The database volume is backed up on a schedule (copy `-wal` and `-shm` with it, or use SQLite's online backup).
- [ ] Google service-account access is limited to the properties it needs.
- [ ] `GET /` returns the API's status message and `/docs` loads — a quick post-deploy health check.

## 6. Local AI (Ollama) in a cloud deployment

The AI features call an Ollama server at `OLLAMA_BASE_URL` (default `http://localhost:11434`). A Railway container
has no Ollama and usually no GPU, so on a cloud API either point `OLLAMA_BASE_URL` at a machine you run Ollama on
(reachable and secured), or accept that AI-dependent features (reports, blog and social generation, digests) will
report the AI as unavailable while everything else works. Inference on CPU is slow (a few words per second); the
SEO features chunk and time-box long AI tasks for that reason, and the dashboard waits several minutes for them.

---

*Last updated: September 25, 2026*
