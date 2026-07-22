import secrets
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters

from database import User, Heir

NAME, RELATION, BIRTHDATE = range(3)


async def addheir_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Heir ka *naam* kya hai?", parse_mode="Markdown")
    return NAME


async def addheir_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["heir_name"] = update.message.text.strip()
    await update.message.reply_text("Aapse unka rishta kya hai? (jaise: Beta, Beti, Dost, Partner)")
    return RELATION


async def addheir_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["heir_relation"] = update.message.text.strip()
    await update.message.reply_text(
        "Unki *date of birth* bhejo (YYYY-MM-DD format me). Agar 'age' based capsules "
        "nahi banane, toh /skip likho.",
        parse_mode="Markdown",
    )
    return BIRTHDATE


async def addheir_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    birth_date = None
    if text.lower() != "/skip":
        try:
            birth_date = datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Format galat hai. YYYY-MM-DD me bhejo, jaise 2015-08-20.")
            return BIRTHDATE

    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    if not owner:
        await update.message.reply_text("Pehle /start karo.")
        return ConversationHandler.END

    code = secrets.token_urlsafe(6)
    heir = Heir(
        owner_id=owner.id,
        name=context.user_data["heir_name"],
        relation=context.user_data.get("heir_relation"),
        birth_date=birth_date,
        verification_code=code,
        verified=False,
    )
    await heir.insert()

    await update.message.reply_text(
        f"✅ Heir *{heir.name}* register ho gaya.\n\n"
        f"Unhe ye verification code bhejo aur unse bolo iss bot ko yeh command bhejein — "
        f"tabhi bot unhe legacy deliver kar payega:\n\n"
        f"`/verify {code}`",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def verify_heir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /verify <code>")
        return
    code = context.args[0]
    heir = await Heir.find_one(Heir.verification_code == code)
    if not heir:
        await update.message.reply_text("❌ Invalid code.")
        return
    heir.telegram_id = update.effective_user.id
    heir.verified = True
    await heir.save()

    owner = await User.get(heir.owner_id)
    owner_name = owner.display_name if owner else "unke"
    await update.message.reply_text(
        f"✅ Verified! Ab aap *{owner_name}* ke digital legacy ke heir ke roop me link ho chuke ho.",
        parse_mode="Markdown",
    )


addheir_conv = ConversationHandler(
    entry_points=[CommandHandler("addheir", addheir_start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addheir_name)],
        RELATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, addheir_relation)],
        BIRTHDATE: [MessageHandler(filters.TEXT, addheir_birthdate)],
    },
    fallbacks=[],
)
