"""
Financial & Crypto Inheritance Map.
IMPORTANT: we deliberately never store actual private keys/passwords —
only an encrypted *hint* pointing to where the real secret lives
(a safe, a diary, a hardware wallet, etc).
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters

from database import User, Heir, FinancialMap
import encryption

LABEL, HINT, HEIR_PICK = range(3)


async def financialmap_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Yaad rahe: kabhi bhi actual password/private key yahan mat likho.\n\n"
        "Pehle batao ye kis cheez ka hint hai? (jaise: 'MetaMask wallet')"
    )
    return LABEL


async def financialmap_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fm_label"] = update.message.text.strip()
    await update.message.reply_text(
        "Ab location HINT likho (asli key nahi!). Jaise: 'Almirah ke 3rd drawer ke peeche red diary me'."
    )
    return HINT


async def financialmap_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fm_hint"] = update.message.text.strip()
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    heirs = await Heir.find(Heir.owner_id == owner.id).to_list()
    if not heirs:
        await update.message.reply_text("Pehle /addheir se kisi ko register karo.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(h.name, callback_data=f"fmheir:{h.id}")] for h in heirs]
    await update.message.reply_text(
        "Ye kis verified heir ko milega (sirf unke death-verification ke baad)?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return HEIR_PICK


async def financialmap_heir_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    heir_id = query.data.split(":")[1]
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    fm = FinancialMap(
        owner_id=owner.id,
        label=context.user_data["fm_label"],
        encrypted_hint=encryption.encrypt(context.user_data["fm_hint"]),
        heir_id=heir_id,
    )
    await fm.insert()
    await query.edit_message_text("✅ Financial/crypto hint encrypted state me save ho gaya.")
    context.user_data.pop("fm_label", None)
    context.user_data.pop("fm_hint", None)
    return ConversationHandler.END


financialmap_conv = ConversationHandler(
    entry_points=[CommandHandler("financialmap", financialmap_start)],
    states={
        LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, financialmap_label)],
        HINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, financialmap_hint)],
        HEIR_PICK: [CallbackQueryHandler(financialmap_heir_pick, pattern=r"^fmheir:")],
    },
    fallbacks=[],
)
