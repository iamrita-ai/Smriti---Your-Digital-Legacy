"""
Background jobs, run periodically via PTB's JobQueue (built on APScheduler).
Registered from main.py with app.job_queue.run_repeating(...).
"""

from datetime import datetime, timedelta, timezone

from telegram.ext import ContextTypes

import config
from database import User, UserStatus, Capsule, TriggerType, Heir, RegretMessage, FinancialMap
import encryption
from handlers.heartbeat import generate_code


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def check_heartbeats(context: ContextTypes.DEFAULT_TYPE):
    """Sends a new heartbeat code to active users whose interval elapsed,
    and marks overdue AWAITING_REPLY users as DECEASED after the grace period."""
    now = datetime.now(timezone.utc)

    active_users = await User.find(User.status == UserStatus.ACTIVE).to_list()
    for user in active_users:
        last = _aware(user.last_reply_at or user.created_at)
        if now - last >= timedelta(days=config.HEARTBEAT_INTERVAL_DAYS):
            code = generate_code()
            user.heartbeat_code = code
            user.heartbeat_sent_at = now
            user.status = UserStatus.AWAITING_REPLY
            await user.save()
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    f"🔔 *Heartbeat Check*\nSecret code reply karo taaki pata chale aap "
                    f"theek ho:\n\n`{code}`\n\n{config.HEARTBEAT_GRACE_DAYS} din ke andar reply karo."
                ),
                parse_mode="Markdown",
            )

    awaiting_users = await User.find(User.status == UserStatus.AWAITING_REPLY).to_list()
    for user in awaiting_users:
        if not user.heartbeat_sent_at:
            continue
        sent = _aware(user.heartbeat_sent_at)
        if now - sent >= timedelta(days=config.HEARTBEAT_GRACE_DAYS):
            user.status = UserStatus.DECEASED
            await user.save()
            await _release_death_capsules(context, user)


async def _release_death_capsules(context, user: User):
    capsules = await Capsule.find(
        Capsule.owner_id == user.id,
        Capsule.trigger_type == TriggerType.ON_DEATH,
        Capsule.delivered == False,  # noqa: E712
    ).to_list()
    for c in capsules:
        await deliver_capsule(context, c)

    maps = await FinancialMap.find(
        FinancialMap.owner_id == user.id, FinancialMap.delivered == False  # noqa: E712
    ).to_list()
    for m in maps:
        heir = await Heir.get(m.heir_id) if m.heir_id else None
        if heir and heir.verified and heir.telegram_id:
            await context.bot.send_message(
                chat_id=heir.telegram_id,
                text=f"🔐 Financial/Crypto hint — *{m.label}*:\n\n{encryption.decrypt(m.encrypted_hint)}",
                parse_mode="Markdown",
            )
            m.delivered = True
            await m.save()

    if config.ADMIN_TELEGRAM_ID and user.telegram_id != config.ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=config.ADMIN_TELEGRAM_ID,
            text=f"⚠️ User {user.display_name} ({user.telegram_id}) ko DECEASED mark kiya gaya. Legacy released.",
        )


async def check_scheduled_triggers(context: ContextTypes.DEFAULT_TYPE):
    """Handles ON_DATE and ON_AGE capsules, independent of the dead man's switch."""
    now = datetime.now(timezone.utc)

    date_capsules = await Capsule.find(
        Capsule.trigger_type == TriggerType.ON_DATE, Capsule.delivered == False  # noqa: E712
    ).to_list()
    for c in date_capsules:
        if c.trigger_date and now >= _aware(c.trigger_date):
            await deliver_capsule(context, c)

    age_capsules = await Capsule.find(
        Capsule.trigger_type == TriggerType.ON_AGE, Capsule.delivered == False  # noqa: E712
    ).to_list()
    for c in age_capsules:
        heir = await Heir.get(c.heir_id) if c.heir_id else None
        if heir and heir.birth_date and c.trigger_age is not None:
            age_years = (now.date() - heir.birth_date.date()).days // 365
            if age_years >= c.trigger_age:
                await deliver_capsule(context, c)


async def check_regret_messages(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc)
    pending = await RegretMessage.find(
        RegretMessage.delivered == False, RegretMessage.cancelled == False  # noqa: E712
    ).to_list()
    for rm in pending:
        if now >= _aware(rm.deadline):
            heir = await Heir.get(rm.heir_id)
            if heir and heir.verified and heir.telegram_id:
                await context.bot.send_message(
                    chat_id=heir.telegram_id,
                    text=f"💌 Ek time-capsule message aaya hai:\n\n{encryption.decrypt(rm.encrypted_text)}",
                )
            rm.delivered = True
            await rm.save()


async def deliver_capsule(context, capsule: Capsule):
    heir = await Heir.get(capsule.heir_id) if capsule.heir_id else None
    if not heir or not heir.verified or not heir.telegram_id:
        return  # will retry next cycle once heir verifies

    if capsule.emotional_question:
        await context.bot.send_message(
            chat_id=heir.telegram_id,
            text=(
                f"🔒 Ek capsule (id: `{capsule.id}`) aapke liye ready hai lekin ek sawaal ka "
                f"sahi jawab dena hoga:\n\n{capsule.emotional_question}\n\n"
                f"Reply karo: /unlock {capsule.id} <aapka jawab>"
            ),
            parse_mode="Markdown",
        )
        return

    caption = encryption.decrypt(capsule.encrypted_text) if capsule.encrypted_text else None
    ctype = capsule.capsule_type.value
    if ctype == "text":
        await context.bot.send_message(chat_id=heir.telegram_id, text=caption or "(empty memory)")
    elif ctype == "voice":
        await context.bot.send_voice(chat_id=heir.telegram_id, voice=capsule.file_id, caption=caption)
    elif ctype == "photo":
        await context.bot.send_photo(chat_id=heir.telegram_id, photo=capsule.file_id, caption=caption)
    elif ctype == "video":
        await context.bot.send_video(chat_id=heir.telegram_id, video=capsule.file_id, caption=caption)
    elif ctype == "document":
        await context.bot.send_document(chat_id=heir.telegram_id, document=capsule.file_id, caption=caption)

    capsule.delivered = True
    await capsule.save()
