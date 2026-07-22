"""
Central configuration for the Smriti (स्मृति) Digital Legacy Bot.
Everything is read from environment variables so the same code runs
locally (.env file) and on Render (dashboard -> Environment tab).
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


# ---- Telegram ----------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_DISPLAY_NAME: str = os.getenv("BOT_DISPLAY_NAME", "Smriti (स्मृति)")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "my_smriti_bot")
ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0") or 0)

# ---- Groq AI -------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_BASE: str = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")

# ---- MongoDB ---------------------------------------------------------------------
MONGODB_URI: str = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "smriti")

# ---- Security ----------------------------------------------------------------------
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# ---- Dead Man's Switch --------------------------------------------------------------
HEARTBEAT_INTERVAL_DAYS: int = int(os.getenv("HEARTBEAT_INTERVAL_DAYS", "30"))
HEARTBEAT_GRACE_DAYS: int = int(os.getenv("HEARTBEAT_GRACE_DAYS", "5"))
JOB_CHECK_INTERVAL_HOURS: int = int(os.getenv("JOB_CHECK_INTERVAL_HOURS", "6"))

# ---- Render Web Service / Webhook ------------------------------------------------------
# Render injects PORT automatically for every Web Service.
PORT: int = int(os.getenv("PORT", "8080"))
# Render also auto-injects RENDER_EXTERNAL_URL for web services - prefer it,
# fall back to a manually-set WEBHOOK_URL for non-Render hosts.
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL", "")
# Random unguessable path segment appended to the webhook URL.
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "smriti-webhook")

# ---- Misc -----------------------------------------------------------------------------
TIMEZONE: str = os.getenv("TIMEZONE", "UTC")
DEBUG: bool = _get_bool("DEBUG", False)


def validate() -> None:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not ENCRYPTION_KEY:
        missing.append("ENCRYPTION_KEY")
    if not MONGODB_URI:
        missing.append("MONGODB_URI")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
