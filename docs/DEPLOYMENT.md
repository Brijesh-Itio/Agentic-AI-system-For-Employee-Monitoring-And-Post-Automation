# WorkPulse AI — Deployment Guide (Module 24)

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
   once you have it — step 2 below).
5. Railway's filesystem is ephemeral on redeploy — `workpulse.db` and
   `agent/data/screenshots/` will reset when the service restarts unless
   you attach a Railway **Volume** to the project and point
   `DATABASE_URL`/`SCREENSHOTS_DIR` at it (or use MinIO for screenshots,
   see step 3).
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

## 3. Optional: MinIO screenshot storage (module 24.4)

Off by default — screenshots stay on local disk exactly as before. To turn
it on: run a MinIO server (self-hosted, or any S3-compatible provider),
create a bucket, and set in `.env` (or Railway's Variables, if the agent
is running somewhere with access to those same vars):

```
MINIO_ENDPOINT=your-minio-host:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=workpulse-screenshots
MINIO_SECURE=true
```

Once set, every new screenshot uploads to MinIO in addition to its local
copy (local file is never deleted), and `cloud_url` gets populated on the
`screenshots` row. Nothing currently reads `cloud_url` in the dashboard —
the gallery still serves from local disk via the API's
`/api/screenshots/file/{filename}` route — so this is infrastructure for a
future remote-dashboard-without-local-disk-access setup, not required for
the Vercel+Railway deployment above (Railway's disk is reachable by the
API that's serving the dashboard, so local-disk screenshots work fine
there too, modulo the ephemeral-filesystem caveat in step 1.5).

## 4. Desktop agent pointed at the cloud API (module 24.5, partial)

Build the packaged agent (module 23 — see the root `DEVELOPMENT.md` for
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

*Last updated: August 21, 2026*
