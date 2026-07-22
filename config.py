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


def _get_int(name: str, default: int = 0) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


# ---- Telegram ----------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_DISPLAY_NAME: str = os.getenv("BOT_DISPLAY_NAME", "Smriti (स्मृति)")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "my_smriti_bot")
ADMIN_TELEGRAM_ID: int = _get_int("ADMIN_TELEGRAM_ID", 0)

# ---- Groq AI -------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_BASE: str = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")

# ---- MongoDB ---------------------------------------------------------------------
MONGODB_URI: str = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "smriti")

# ---- Security ----------------------------------------------------------------------
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# This CANNOT be left blank - it encrypts every capsule/financial hint at rest.
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# ---- Dead Man's Switch --------------------------------------------------------------
HEARTBEAT_INTERVAL_DAYS: int = _get_int("HEARTBEAT_INTERVAL_DAYS", 30)
HEARTBEAT_GRACE_DAYS: int = _get_int("HEARTBEAT_GRACE_DAYS", 5)
JOB_CHECK_INTERVAL_HOURS: int = _get_int("JOB_CHECK_INTERVAL_HOURS", 6)

# ---- Log / Storage Channel ------------------------------------------------------------
# Optional but strongly recommended: create a PRIVATE Telegram channel, add
# this bot as an admin, then set LOG_CHANNEL_ID to that channel's numeric id
# (looks like -1001234567890). All photo/video/voice/document capsules get
# copied there at save-time, and delivered later via copy_message - this
# keeps the media alive independently of the original chat, which matters a
# lot for a bot that may need to deliver something 10-20 years from now.
# Leave blank to fall back to storing the raw Telegram file_id directly
# (works fine for quick testing, less durable for very long time horizons).
LOG_CHANNEL_ID: int = _get_int("LOG_CHANNEL_ID", 0)

# ---- GIFs / Stickers (optional, cosmetic) ----------------------------------------------
# Direct .gif links from Giphy (or any hosted gif/sticker url). Leave blank
# to skip - the bot works fine without them.
START_GIF: str = os.getenv("START_GIF", "")
PROCESSING_GIF: str = os.getenv("PROCESSING_GIF", "")

# ---- Render Web Service / Webhook ------------------------------------------------------
# Render injects PORT automatically for every Web Service.
PORT: int = _get_int("PORT", 8080)
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
