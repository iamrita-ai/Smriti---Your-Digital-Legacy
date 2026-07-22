"""
/talk — chat with the AI avatar built from the user's own stored text
memories (capsules marked is_memory=True). Useful for the owner to test
how their avatar will "sound", and this same code path is used when a
verified heir messages the bot after the owner is marked deceased.
"""

from telegram import Update
from telegram.ext import ContextTypes

from database import User, Capsule
import encryption
import groq_client


async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = await User.find_one(User.telegram_id == update.effective_user.id)
    if not owner:
        await update.message.reply_text("Pehle /start karo.")
        return
    memories = await _load_memories(owner.id)
    user_message = " ".join(context.args) if context.args else "Hi"
    system_prompt = groq_client.build_avatar_system_prompt(owner.display_name or "you", memories)
    reply = await groq_client.chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
    )
    await update.message.reply_text(reply)


async def _load_memories(owner_id) -> list[str]:
    capsules = await Capsule.find(Capsule.owner_id == owner_id, Capsule.is_memory == True).to_list()  # noqa: E712
    out = []
    for c in capsules:
        if c.encrypted_text:
            try:
                out.append(encryption.decrypt(c.encrypted_text))
            except ValueError:
                continue
    return out


async def talk_as_heir(update: Update, context: ContextTypes.DEFAULT_TYPE, owner: User):
    """Called from main.py's generic message handler when a verified heir
    talks to a DECEASED user's avatar."""
    memories = await _load_memories(owner.id)
    system_prompt = groq_client.build_avatar_system_prompt(owner.display_name or "them", memories)
    reply = await groq_client.chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": update.message.text}]
    )
    await update.message.reply_text(reply)
