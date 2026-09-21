# Database snapshot (credentials removed)

`workpulse.clean.db` is a copy of the WorkPulse AI SQLite database taken on 2026-09-21.
It keeps all data (activity logs, SEO data, DAR reports, ...) but has these removed:

- every user's `password_hash` (so no existing account can log in until a password is set)
- `seo_sites`: `cms_app_password`, `cms_api_token`, `ssh_password`
- `seo_facebook_accounts.page_access_token`

## Restore on another machine

1. Stop the API, then copy the file over the live database from the project root:

       copy db_snapshot\workpulse.clean.db workpulse.db        (Windows)
       cp db_snapshot/workpulse.clean.db workpulse.db          (macOS / Linux)

2. Set a new password for your admin account (run from the project root; use the venv's Python):

       .venv\Scripts\python.exe -c "import sqlite3; from api.auth import hash_password; c=sqlite3.connect('workpulse.db'); c.execute('update users set password_hash=? where email=?', (hash_password('NEW-PASSWORD'), 'you@example.com')); c.commit()"

3. Re-enter the CMS / SSH passwords for each site in the SEO settings of the dashboard.

Start the app afterwards with `start.bat`.
