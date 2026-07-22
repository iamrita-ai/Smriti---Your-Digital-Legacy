from telegram import Update
from telegram.ext import ContextTypes

import config
from database import User, UserStatus, get_or_create_user

HELP_TEXT = f"""👋 Main hoon *{config.BOT_DISPLAY_NAME}* — aapki digital legacy ka rakshak.

*Kya kar sakti hoon:*
/addcapsule — Ek naya memory/message/photo/voice "time-capsule" me daalo
/addheir — Kisi heir (beta/beti/dost) ko register karo
/heartbeat — Apna zinda-hone-ka status abhi confirm karo
/pause — Bot ko temporarily pause karo (jaise trip pe ho)
/resume — Wapas active karo
/financialmap — Crypto/financial "location hint" store karo (asli password kabhi nahi)
/regret — Ek message daalo jo 24 ghante me delete na kiya toh delivered ho jayega
/talk — Apni AI-avatar se abhi test-chat karo
/mycapsules — Apni saari saved capsules dekho
/help — Ye message dobara dikhao

⚠️ Har mahine main ek secret "heartbeat" code bhejungi. Agar {config.HEARTBEAT_GRACE_DAYS + config.HEARTBEAT_INTERVAL_DAYS} din tak reply nahi aaya, toh aapki legacy activate ho jayegi.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user, created = await get_or_create_user(tg_user.id, tg_user.username, tg_user.full_name)
    if created:
        await update.message.reply_text(
            f"Namaste {tg_user.first_name}! Aapka account bana diya gaya hai.\n\n" + HELP_TEXT,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"Wapas swagat hai, {tg_user.first_name}.\n\n" + HELP_TEXT,
            parse_mode="Markdown",
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await User.find_one(User.telegram_id == update.effective_user.id)
    if not user:
        await update.message.reply_text("Pehle /start karo.")
        return
    user.status = UserStatus.PAUSED
    await user.save()
    await update.message.reply_text(
        "⏸️ Dead man's switch *paused* kar diya gaya hai. Jab wapas ready ho, /resume karo.",
        parse_mode="Markdown",
    )


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await User.find_one(User.telegram_id == update.effective_user.id)
    if not user:
        await update.message.reply_text("Pehle /start karo.")
        return
    user.status = UserStatus.ACTIVE
    user.last_reply_at = None
    user.heartbeat_sent_at = None
    user.heartbeat_code = None
    await user.save()
    await update.message.reply_text("▶️ Active mode me wapas aa gaye ho. Heartbeat monitoring dobara chalu.")
