"""
Entry point — wires up handlers + background jobs and starts the bot in
WEBHOOK mode (needed for Render "Web Service", which requires the app to
bind to $PORT and doesn't work well with long-polling).

Locally, run with: python main.py
It will still work locally as long as WEBHOOK_URL (or RENDER_EXTERNAL_URL)
points to a public HTTPS URL that reaches this machine (e.g. via ngrok).
For pure local testing without a public URL, see the LOCAL_POLLING note
at the bottom of this file.
"""

import logging
from datetime import timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import config
from database import init_db, User, Heir, UserStatus, Capsule
import encryption

from handlers.start import start, help_cmd, pause, resume
from handlers.heir import addheir_conv, verify_heir
from handlers.capsule import addcapsule_conv, mycapsules
from handlers.heartbeat import heartbeat_cmd, heartbeat_reply_handler
from handlers.regret_eraser import regret_conv, cancel_regret
from handlers.financial_map import financialmap_conv
from handlers.avatar import talk, talk_as_heir
import jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if config.DEBUG else logging.INFO,
)
logger = logging.getLogger(__name__)


async def unlock_capsule(update: Update, context):
    """`/unlock <capsule_id> <answer>` — emotional-password protected delivery."""
    if len(context.args) < 2:
        await update.message.reply_text("Use: /unlock <capsule_id> <aapka jawab>")
        return
    capsule_id = context.args[0]
    answer = " ".join(context.args[1:])

    try:
        capsule = await Capsule.get(capsule_id)
    except Exception:
        capsule = None
    if not capsule:
        await update.message.reply_text("Ye capsule nahi mila.")
        return
    if not capsule.emotional_answer_hash:
        await update.message.reply_text("Iss capsule pe koi password lock nahi hai.")
        return
    if not encryption.verify_answer(answer, capsule.emotional_answer_hash):
        await update.message.reply_text("❌ Galat jawab. Try again.")
        return

    capsule.emotional_question = None
    capsule.emotional_answer_hash = None
    await capsule.save()
    await jobs.deliver_capsule(context, capsule)
    await update.message.reply_text("✅ Sahi jawab! Capsule deliver ho raha hai.")


async def generic_message_router(update: Update, context):
    """
    Routes plain-text messages that aren't part of an active conversation:
    1. Heartbeat code replies from the owner.
    2. Chat messages from a VERIFIED heir whose owner is DECEASED -> avatar chat.
    """
    handled = await heartbeat_reply_handler(update, context)
    if handled:
        return

    heir = await Heir.find_one(Heir.telegram_id == update.effective_user.id, Heir.verified == True)  # noqa: E712
    if heir:
        owner = await User.get(heir.owner_id)
        if owner and owner.status == UserStatus.DECEASED:
            await talk_as_heir(update, context, owner)


async def post_init(app: Application) -> None:
    await init_db()
    logger.info("Connected to MongoDB (%s)", config.MONGODB_DB_NAME)


def build_app() -> Application:
    config.validate()
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    # Core
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("heartbeat", heartbeat_cmd))
    app.add_handler(CommandHandler("verify", verify_heir))
    app.add_handler(CommandHandler("mycapsules", mycapsules))
    app.add_handler(CommandHandler("cancelregret", cancel_regret))
    app.add_handler(CommandHandler("talk", talk))
    app.add_handler(CommandHandler("unlock", unlock_capsule))

    # Conversations
    app.add_handler(addheir_conv)
    app.add_handler(addcapsule_conv)
    app.add_handler(regret_conv)
    app.add_handler(financialmap_conv)

    # Generic fallback (heartbeat replies + heir-avatar chat)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generic_message_router))

    # Background jobs
    jq = app.job_queue
    interval = timedelta(hours=config.JOB_CHECK_INTERVAL_HOURS)
    jq.run_repeating(jobs.check_heartbeats, interval=interval, first=10)
    jq.run_repeating(jobs.check_scheduled_triggers, interval=interval, first=20)
    jq.run_repeating(jobs.check_regret_messages, interval=timedelta(minutes=30), first=30)

    return app


def main():
    app = build_app()

    if config.WEBHOOK_URL:
        url_path = config.WEBHOOK_SECRET
        webhook_full_url = f"{config.WEBHOOK_URL.rstrip('/')}/{url_path}"
        logger.info("Starting in WEBHOOK mode on port %s -> %s", config.PORT, webhook_full_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=url_path,
            webhook_url=webhook_full_url,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        # LOCAL_POLLING fallback: no public WEBHOOK_URL configured (e.g. plain
        # local dev without ngrok) - use polling instead so you can still test.
        logger.warning("WEBHOOK_URL not set - falling back to polling (fine for local dev only).")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
