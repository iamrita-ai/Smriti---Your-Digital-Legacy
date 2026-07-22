"""
Dead Man's Switch: every HEARTBEAT_INTERVAL_DAYS, the scheduler (jobs.py)
sends a secret phrase like "Green Apple". The user must reply with the
exact phrase within HEARTBEAT_GRACE_DAYS days, or via /heartbeat command.
"""

import random
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from database import User, UserStatus

CODE_WORDS = [
    "Green Apple", "Blue Ocean", "Silver Moon", "Orange Sky", "Golden Leaf",
    "Purple Rain", "Crimson Sun", "Amber Wave", "Violet Storm", "Ivory Cloud",
]


def generate_code() -> str:
    return random.choice(CODE_WORDS)


async def heartbeat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual check-in via /heartbeat, in case the user wants to confirm early."""
    user = await User.find_one(User.telegram_id == update.effective_user.id)
    if not user:
        await update.message.reply_text("Pehle /start karo.")
        return
    user.status = UserStatus.ACTIVE
    user.last_reply_at = datetime.now(timezone.utc)
    user.heartbeat_code = None
    await user.save()
    await update.message.reply_text("✅ Confirmed — aap active ho. Agla heartbeat check niyam se aayega.")


async def heartbeat_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Catches plain-text replies matching the sent code word.
    Returns True if it handled the message (so the caller can stop routing further)."""
    user = await User.find_one(User.telegram_id == update.effective_user.id)
    if not user or user.status != UserStatus.AWAITING_REPLY:
        return False
    text = (update.message.text or "").strip().lower()
    if user.heartbeat_code and text == user.heartbeat_code.lower():
        user.status = UserStatus.ACTIVE
        user.last_reply_at = datetime.now(timezone.utc)
        user.heartbeat_code = None
        await user.save()
        await update.message.reply_text("✅ Shukriya! Aapka status *active* confirm ho gaya.", parse_mode="Markdown")
        return True
    return False
