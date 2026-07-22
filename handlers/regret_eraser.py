"""
'Regret Eraser': store a message with a 24-hour fuse. If the owner doesn't
cancel it in time, it's auto-delivered to the chosen heir/friend.
"""

from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters

from database import User, Heir, RegretMessage
import encryption

TEXT, HEIR_PICK = range(2)


async def regret_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Woh message likho jo aap bhejna chahte ho (24 ghante ke andar cancel kar sakte ho):"
    )
    return TEXT


async def regret_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["regret_text"] = update.message.text
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    heirs = await Heir.find(Heir.owner_id == owner.id).to_list()
    if not heirs:
        await update.message.reply_text("Pehle /addheir se kisi ko register karo.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(h.name, callback_data=f"regretheir:{h.id}")] for h in heirs]
    await update.message.reply_text(
        "Kise bhejna hai (agar 24 ghante me cancel na kiya toh)?", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return HEIR_PICK


async def regret_heir_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    heir_id = query.data.split(":")[1]
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    rm = RegretMessage(
        owner_id=owner.id,
        heir_id=heir_id,
        encrypted_text=encryption.encrypt(context.user_data["regret_text"]),
        deadline=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    await rm.insert()
    await query.edit_message_text(
        f"⏳ Message capsule me daal diya (id: `{rm.id}`). Agar 24 ghante me delete "
        f"nahi kiya (`/cancelregret {rm.id}`), toh delivered ho jayega.",
        parse_mode="Markdown",
    )
    context.user_data.pop("regret_text", None)
    return ConversationHandler.END


async def cancel_regret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /cancelregret <id>")
        return
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    try:
        rm = await RegretMessage.get(context.args[0])
    except Exception:
        rm = None
    if not rm or rm.owner_id != owner.id:
        await update.message.reply_text("Ye message nahi mila.")
        return
    if rm.delivered:
        await update.message.reply_text("Ye pehle hi deliver ho chuka hai.")
        return
    rm.cancelled = True
    await rm.save()
    await update.message.reply_text("✅ Cancel ho gaya — thank god! 😂")


regret_conv = ConversationHandler(
    entry_points=[CommandHandler("regret", regret_start)],
    states={
        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, regret_text)],
        HEIR_PICK: [CallbackQueryHandler(regret_heir_pick, pattern=r"^regretheir:")],
    },
    fallbacks=[],
)
