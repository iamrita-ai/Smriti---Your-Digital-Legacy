"""
/addcapsule conversation:
1. Send the content itself (text / voice / photo / document / video)
2. Choose a trigger: on_death, on_date, on_age, manual
3. Choose the heir it belongs to
4. Optionally set an "emotional password" question+answer
"""

from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler, CommandHandler,
    CallbackQueryHandler, filters,
)

from database import User, Heir, Capsule, CapsuleType, TriggerType
import encryption

CONTENT, TRIGGER, DATE_INPUT, AGE_HEIR, AGE_VALUE, HEIR_PICK, EMOTIONAL_Q, EMOTIONAL_A = range(8)


async def addcapsule_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["capsule"] = {}
    await update.message.reply_text(
        "Capsule ka content bhejo — text likho, ya voice note / photo / document / video bhejo."
    )
    return CONTENT


async def addcapsule_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    data = context.user_data["capsule"]

    if msg.voice:
        data["type"] = CapsuleType.VOICE
        data["file_id"] = msg.voice.file_id
        data["text"] = msg.caption or ""
    elif msg.photo:
        data["type"] = CapsuleType.PHOTO
        data["file_id"] = msg.photo[-1].file_id
        data["text"] = msg.caption or ""
    elif msg.document:
        data["type"] = CapsuleType.DOCUMENT
        data["file_id"] = msg.document.file_id
        data["text"] = msg.caption or ""
    elif msg.video:
        data["type"] = CapsuleType.VIDEO
        data["file_id"] = msg.video.file_id
        data["text"] = msg.caption or ""
    else:
        data["type"] = CapsuleType.TEXT
        data["file_id"] = None
        data["text"] = msg.text or ""

    keyboard = [
        [InlineKeyboardButton("💀 Dead Man's Switch", callback_data="trigger:on_death")],
        [InlineKeyboardButton("📅 Specific Date", callback_data="trigger:on_date")],
        [InlineKeyboardButton("🎂 Heir's Age", callback_data="trigger:on_age")],
        [InlineKeyboardButton("✋ Manual only", callback_data="trigger:manual")],
    ]
    await update.message.reply_text(
        "Ye capsule kab unlock/deliver ho? Trigger chuno:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return TRIGGER


async def addcapsule_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trigger = query.data.split(":")[1]
    context.user_data["capsule"]["trigger_type"] = TriggerType(trigger)

    if trigger == "on_date":
        await query.edit_message_text("Date bhejo (YYYY-MM-DD):")
        return DATE_INPUT
    elif trigger == "on_age":
        owner = await User.find_one(User.telegram_id == update.effective_user.id)
        heirs = await Heir.find(Heir.owner_id == owner.id).to_list()
        if not heirs:
            await query.edit_message_text("Pehle /addheir se ek heir register karo.")
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton(h.name, callback_data=f"ageheir:{h.id}")] for h in heirs]
        await query.edit_message_text(
            "Kis heir ki age track karni hai?", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AGE_HEIR
    else:
        return await _ask_heir_pick(update, context, via_callback=True)


async def addcapsule_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        trigger_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Format galat hai, YYYY-MM-DD me bhejo (jaise 2030-01-01).")
        return DATE_INPUT
    context.user_data["capsule"]["trigger_date"] = trigger_date
    return await _ask_heir_pick(update, context, via_callback=False)


async def addcapsule_age_heir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    heir_id = query.data.split(":")[1]
    context.user_data["capsule"]["heir_id"] = heir_id
    await query.edit_message_text("Kis age pe deliver karna hai? (sirf number bhejo, jaise 18)")
    return AGE_VALUE


async def addcapsule_age_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Sirf number bhejo, jaise 18.")
        return AGE_VALUE
    context.user_data["capsule"]["trigger_age"] = age
    return await _ask_emotional(update, context, via_callback=False)


async def _ask_heir_pick(update: Update, context: ContextTypes.DEFAULT_TYPE, via_callback: bool):
    tg_id = update.effective_user.id
    owner = await User.find_one(User.telegram_id == tg_id)
    heirs = await Heir.find(Heir.owner_id == owner.id).to_list()
    text = "Ye capsule kis heir ke liye hai?"
    if not heirs:
        reply_text = "Pehle /addheir se ek heir register karo."
        if via_callback:
            await update.callback_query.edit_message_text(reply_text)
        else:
            await update.message.reply_text(reply_text)
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(h.name, callback_data=f"heirpick:{h.id}")] for h in heirs]
    if via_callback:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return HEIR_PICK


async def addcapsule_heir_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    heir_id = query.data.split(":")[1]
    context.user_data["capsule"]["heir_id"] = heir_id
    return await _ask_emotional(update, context, via_callback=True)


async def _ask_emotional(update: Update, context: ContextTypes.DEFAULT_TYPE, via_callback: bool):
    keyboard = [
        [InlineKeyboardButton("Haan 🔒", callback_data="emo:yes"),
         InlineKeyboardButton("Nahi", callback_data="emo:no")],
    ]
    text = "Kya iss capsule ko 'emotional password' se lock karna hai (koi personal sawaal)?"
    if via_callback:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return EMOTIONAL_Q


async def addcapsule_emotional_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "emo:yes":
        await query.edit_message_text(
            "Sawaal likho (jaise: 'Humari last Goa trip pe humne khana kahan khaya tha?')"
        )
        context.user_data["_awaiting_emo"] = "question"
        return EMOTIONAL_A
    else:
        return await _save_capsule(update, context, via_callback=True)


async def addcapsule_emotional_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stage = context.user_data.get("_awaiting_emo")
    if stage == "question":
        context.user_data["capsule"]["emotional_question"] = update.message.text.strip()
        context.user_data["_awaiting_emo"] = "answer"
        await update.message.reply_text(
            "Ab sahi jawab likho (ye sirf verify karne ke liye hash ho jayega, plain-text me kahi store nahi hoga):"
        )
        return EMOTIONAL_A
    else:
        answer = update.message.text.strip()
        context.user_data["capsule"]["emotional_answer_hash"] = encryption.hash_answer(answer)
        return await _save_capsule(update, context, via_callback=False)


async def _save_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE, via_callback: bool):
    data = context.user_data["capsule"]
    owner = await User.find_one(User.telegram_id == update.effective_user.id)

    capsule = Capsule(
        owner_id=owner.id,
        heir_id=data.get("heir_id"),
        capsule_type=data["type"],
        file_id=data.get("file_id"),
        encrypted_text=encryption.encrypt(data.get("text", "")) if data.get("text") else None,
        trigger_type=data["trigger_type"],
        trigger_date=data.get("trigger_date"),
        trigger_age=data.get("trigger_age"),
        emotional_question=data.get("emotional_question"),
        emotional_answer_hash=data.get("emotional_answer_hash"),
        is_memory=(data["type"] == CapsuleType.TEXT),
    )
    await capsule.insert()

    text = "✅ Capsule safely save ho gaya, encrypted state me."
    if via_callback:
        await update.callback_query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

    context.user_data.pop("capsule", None)
    context.user_data.pop("_awaiting_emo", None)
    return ConversationHandler.END


async def mycapsules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    if not owner:
        await update.message.reply_text("Pehle /start karo.")
        return
    capsules = await Capsule.find(Capsule.owner_id == owner.id).to_list()
    if not capsules:
        await update.message.reply_text("Abhi tak koi capsule save nahi hui.")
        return
    lines = []
    for c in capsules:
        status = "✅ delivered" if c.delivered else "⏳ pending"
        lines.append(f"#{c.id} [{c.capsule_type.value}] trigger={c.trigger_type.value} — {status}")
    await update.message.reply_text("\n".join(lines))


addcapsule_conv = ConversationHandler(
    entry_points=[CommandHandler("addcapsule", addcapsule_start)],
    states={
        CONTENT: [MessageHandler(filters.ALL & ~filters.COMMAND, addcapsule_content)],
        TRIGGER: [CallbackQueryHandler(addcapsule_trigger, pattern=r"^trigger:")],
        DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcapsule_date)],
        AGE_HEIR: [CallbackQueryHandler(addcapsule_age_heir, pattern=r"^ageheir:")],
        AGE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcapsule_age_value)],
        HEIR_PICK: [CallbackQueryHandler(addcapsule_heir_pick, pattern=r"^heirpick:")],
        EMOTIONAL_Q: [CallbackQueryHandler(addcapsule_emotional_choice, pattern=r"^emo:")],
        EMOTIONAL_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcapsule_emotional_text)],
    },
    fallbacks=[],
)
