"""
Thin async wrapper around the Groq chat-completions API (OpenAI-compatible).

Groq's model knowledge cutoff is roughly 2021-2023, so we always build a
system prompt from the user's OWN stored memories/capsules rather than
relying on the model's built-in world knowledge for anything about the
person's life.
"""

import httpx
import config

AVATAR_SYSTEM_TEMPLATE = """You are a conversational digital-legacy avatar of {name}.
You must speak ONLY based on the memories, values, and philosophies listed
below, which {name} recorded during their life. Never invent facts about
{name}'s life that are not present in these memories. If asked something
you don't have a memory of, say so honestly and warmly, the way {name}
might have. Stay warm, personal, and true to their voice.

--- MEMORIES ---
{memories}
--- END MEMORIES ---
"""


async def chat_completion(messages: list[dict], temperature: float = 0.7) -> str:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not configured")

    url = f"{config.GROQ_API_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 700,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def build_avatar_system_prompt(name: str, memories: list[str]) -> str:
    joined = "\n\n".join(f"- {m}" for m in memories) or "(no memories recorded yet)"
    return AVATAR_SYSTEM_TEMPLATE.format(name=name, memories=joined)
