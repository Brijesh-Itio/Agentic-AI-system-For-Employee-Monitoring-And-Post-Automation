"""
API configuration — all FastAPI backend settings and credentials live here.
Never hardcode credentials in route or business-logic files.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = API_ROOT.parent

# Same physical SQLite file the desktop agent writes to (agent/config.py).
DATABASE_PATH = PROJECT_ROOT / "workpulse.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    # ── Database ──
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"

    # ── Security ──
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── SSO (Google OAuth) ──
    # Leave both blank to keep SSO off — /api/auth/sso/status reports it as
    # disabled and the frontend hides the "Sign in with Google" button.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # This backend's own publicly reachable base URL — must exactly match
    # the "Authorized redirect URI" registered in the Google Cloud OAuth
    # client (this value + /api/auth/sso/google/callback), or Google
    # rejects the token exchange.
    API_PUBLIC_URL: str = "http://localhost:8000"
    # Where the browser lands after SSO completes (success or failure).
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Gmail (module 8) ──
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""
    # Where DAR/alert emails go. Defaults to GMAIL_ADDRESS (send-to-self),
    # matching module 8's own test ("send a test email to yourself").
    REPORT_RECIPIENT_EMAIL: str = ""

    # ── LinkedIn (module 18) ──
    # Only used for the *first* login, which saves a session cookie file
    # (LINKEDIN_COOKIES_PATH in automation/config.py) — every run after
    # that reuses the saved session instead of logging in again.
    LINKEDIN_EMAIL: str = ""
    LINKEDIN_PASSWORD: str = ""

    # ── Pexels image search (module 18.3, fallback only) ──
    # Free API key, not Playwright scraping: Pexels/Pixabay both sit behind
    # Cloudflare bot-detection that blocks headless browsers outright (a
    # "Verify you are human" wall, not a missing selector) — verified
    # empirically, not assumed. Kept as a stock-photo fallback for when
    # FastSD CPU (below) is unavailable or produces nothing usable.
    PEXELS_API_KEY: str = ""

    # ── FastSD CPU local image generation (module 18.3, primary) ──
    # A second local-inference server, same pattern as Ollama: runs on this
    # machine, not a paid/third-party API, matching the zero-API-cost goal.
    # Not part of the Railway/cloud deployment (that stays lightweight) —
    # like Ollama, it only ever needs to run wherever automation actually
    # executes. Default port 8100 (not 8000) to avoid colliding with this
    # backend's own uvicorn server.
    FASTSD_API_URL: str = "http://127.0.0.1:8100"
    FASTSD_TIMEOUT_SECONDS: int = 600

    # ── Ollama / AI stack (module 6+) ──
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:1.7b"
    OLLAMA_FAST_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT_SECONDS: int = 120  # classification calls (fast=True)
    # Full narrative generation (DAR, etc.) genuinely takes longer than
    # classification — observed ~167s for a full DAR on CPU inference, but
    # AI-drafted task-log entries measured at ~275s under real load. A real
    # AI-draft attempt still hit the 420s budget and timed out outright
    # under heavy system load (many Chrome/VS Code windows open) — raised
    # again for real margin on this CPU-only hardware under load.
    OLLAMA_GENERATE_TIMEOUT_SECONDS: int = 600

    # ── ChromaDB (module 6+) ──
    CHROMADB_PATH: str = str(PROJECT_ROOT / "chromadb")

    # ── SEO Agentic AI: generic LLM provider layer (module 25) ──
    # Which provider runs SEO tasks by default. "ollama" (the default)
    # keeps every SEO pipeline on the zero-cost local stack with no
    # config changes. Per-task overrides read directly from the
    # environment as SEO_LLM_PROVIDER_<TASK> (e.g. SEO_LLM_PROVIDER_CONTENT)
    # rather than being predeclared fields here, so a new task name never
    # requires touching this file — see ai/llm/factory.py.
    SEO_LLM_PROVIDER_DEFAULT: str = "ollama"
    # Both blank = that provider stays off (ai/llm/factory.py's adapters
    # fail closed with a clear error rather than silently falling back).
    # Only needed at all once something sets SEO_LLM_PROVIDER_DEFAULT or a
    # SEO_LLM_PROVIDER_<TASK> override to "claude"/"openai".
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = ""
    OPENAI_EMBED_MODEL: str = ""

    # ── SEO Agentic AI: CMS integration (module 26) ──
    # v1 credentials are one global default-site credential set, matched
    # against whichever seo_sites row is passed in — same simplicity as
    # every other credential in this file (Gmail, LinkedIn). Per-site
    # DB-stored credentials are a documented extension point for if/when
    # a second real site is actually connected, not built ahead of need.
    WORDPRESS_URL: str = ""
    WORDPRESS_USERNAME: str = ""
    WORDPRESS_APP_PASSWORD: str = ""

    WEBFLOW_API_TOKEN: str = ""
    WEBFLOW_SITE_ID: str = ""
    WEBFLOW_COLLECTION_ID: str = ""
    # Webflow CMS collections have no fixed field names (unlike WordPress's
    # title/excerpt/content) — these three map CmsClient's generic fields
    # onto this collection's actual field slugs. Defaults match Webflow's
    # own default Blog template; override for a custom collection schema.
    WEBFLOW_FIELD_TITLE: str = "name"
    WEBFLOW_FIELD_EXCERPT: str = "post-summary"
    WEBFLOW_FIELD_CONTENT: str = "post-body"

    # ── SEO Agentic AI: free Google data pulls (module 26) ──
    # PageSpeed Insights works unauthenticated too, just at a much lower
    # quota — blank means "use the free anonymous quota" rather than off.
    PAGESPEED_API_KEY: str = ""

    # GSC and GA4 both authenticate as one Google Cloud service account
    # (Search Console property + Analytics property both shared with that
    # account's email in each respective Google product's UI). Path to the
    # downloaded JSON key file, not the JSON inline — a private key with
    # embedded newlines is awkward and error-prone in a flat .env value.
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = ""
    # Search Console verified property, exactly as shown in GSC's property
    # switcher — either a URL-prefix property ("https://workpulse.ai/") or
    # a domain property ("sc-domain:workpulse.ai").
    GSC_SITE_URL: str = ""
    # GA4 property, formatted "properties/123456789" (the numeric GA4
    # property ID, from Admin -> Property Settings).
    GA4_PROPERTY_ID: str = ""

    # ── SEO Agentic AI: reporting/alerts (module 29) ──
    # Blank = digests still generate and store, just aren't also pushed
    # to Slack — same "off by default" convention as every other
    # optional integration here.
    SLACK_WEBHOOK_URL: str = ""

    # ── SEO Agentic AI: backlink/mention monitoring (module 31) ──
    # "google_alerts" is the only built provider — free, no key, just a
    # feed URL from an alert's "Deliver to: RSS feed" setting. Blank =
    # off, same as every other optional integration here.
    BACKLINK_PROVIDER_DEFAULT: str = "google_alerts"
    GOOGLE_ALERTS_RSS_URL: str = ""
    AHREFS_API_KEY: str = ""  # accepted for future use — see backlinks/factory.py

    # ── SEO Agentic AI: generic image provider layer (module 27) ──
    # "fastsd" (the default) keeps every SEO image task on the zero-cost
    # local stack (module 18.3's FastSD CPU server) with no config
    # changes. Per-task overrides read IMAGE_PROVIDER_<TASK> from the
    # environment directly, same as SEO_LLM_PROVIDER_<TASK> — see
    # ai/images/factory.py.
    IMAGE_PROVIDER_DEFAULT: str = "fastsd"
    # Blank = stays off; ai/images/providers/stability_provider.py fails
    # closed with a clear error rather than silently falling back.
    STABILITY_API_KEY: str = ""

    # ── SEO Agentic AI: autonomous daily scheduling (module 33) ──
    # Runs the full per-site pipeline (technical audit, GSC/GA4 pulls,
    # PageSpeed check, digest + Slack) once a day for every active site
    # with no manual trigger needed — see ai/seo_master_agent.py. Only
    # the parts that publish externally (social posts, outreach emails)
    # stay manual/draft-only; this covers everything else. False keeps
    # every one of those a manual button click, same as before this
    # module — the manual endpoints keep working either way.
    SEO_AUTOMATION_ENABLED: bool = True
    # 24h local time the daily cycle fires. Early morning by default so
    # it runs against overnight-settled analytics data before anyone's
    # working day starts, and well clear of any manual testing.
    SEO_AUTOMATION_HOUR: int = 6

    # ── Server ──
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ── Identity ──
    DEFAULT_USER_ID: str = "local"

    # Heuristic window for the /api/status "agent running" check: the agent
    # closes at least one activity session roughly every few seconds while
    # tracking, so no fresh row within this window means it's likely down.
    AGENT_HEARTBEAT_WINDOW_SECONDS: int = 30


settings = Settings()
