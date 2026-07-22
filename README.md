# Smriti (स्मृति) — Digital Legacy & Time-Capsule Bot

A Telegram bot (python-telegram-bot / PTB v21, async, webhook mode) that
securely stores memories, messages, and inheritance hints in **MongoDB**,
and releases them via configurable triggers: a monthly "dead man's
switch" heartbeat, a specific date, an heir's age, or manual release.
Uses **Groq**'s LLM API to power a conversational "avatar" built strictly
from the owner's own recorded memories (Groq's model knowledge cutoff is
~2021-2023, so the avatar never relies on the model's built-in world
knowledge about the person — only what they actually recorded).

## Features
- `/addcapsule` — save text/voice/photo/video/document with a trigger
- `/addheir` + `/verify <code>` — register & verify heirs
- `/heartbeat`, `/pause`, `/resume` — dead man's switch controls
- `/regret` + `/cancelregret <id>` — 24-hour "regret eraser" messages
- `/financialmap` — encrypted *location hints* for crypto/financial assets
  (never stores actual private keys or passwords)
- `/talk` — chat with your own AI avatar (also used by verified heirs
  once you're marked deceased)
- `/unlock <capsule_id> <answer>` — emotional-password protected capsules

## Tech stack
- **python-telegram-bot v21** (async, webhook mode)
- **MongoDB** via **Beanie** (async ODM on top of **Motor**)
- **Groq API** (OpenAI-compatible `/chat/completions`)
- **cryptography (Fernet)** for encryption at rest
- **Docker** for deployment on **Render (Web Service)**

## Security notes
- All sensitive text is encrypted at rest with Fernet (`ENCRYPTION_KEY`).
- Emotional-password answers are stored only as a SHA-256 hash — never
  in plaintext.
- The financial/crypto feature intentionally stores *hints*, not secrets
  — e.g. "private key diary is in the 3rd drawer", never the key itself.
- Media (voice/photo/video/doc) is referenced by Telegram `file_id`. For
  a production system with a long time horizon (this bot may need to
  deliver content years or decades later), download and store these
  encrypted in object storage (S3/R2) instead — Telegram `file_id`s can
  become invalid if you regenerate the bot token or after long inactivity.
- The webhook path includes a random `WEBHOOK_SECRET` so the endpoint
  can't be guessed and spammed with fake updates.

## Local setup

1. Copy `.env.example` to `.env` and fill in values.
2. Generate an encryption key:
   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. Generate a webhook secret:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(24))"
   ```
4. Get a free MongoDB database at https://www.mongodb.com/cloud/atlas
   and put its connection string in `MONGODB_URI`.
5. Install deps: `pip install -r requirements.txt`
6. Run: `python main.py`
   - If `WEBHOOK_URL` is not set, it automatically falls back to polling
     mode, which is the easiest way to test locally without a public URL.

## Deploy on Render (Web Service)

1. Push this repo to GitHub.
2. Render dashboard -> **New -> Web Service** -> connect the repo ->
   Runtime: **Docker**.
3. Add all environment variables from `.env.example` in the Environment
   tab (BOT_TOKEN, GROQ_API_KEY, MONGODB_URI, ENCRYPTION_KEY,
   WEBHOOK_SECRET, etc). **Do not set `WEBHOOK_URL` manually** — Render
   automatically injects `RENDER_EXTERNAL_URL` for every Web Service,
   and `config.py` picks it up automatically. Also don't set `PORT` —
   Render injects that too.
4. Deploy. On startup the bot registers its Telegram webhook at
   `https://<your-render-app>.onrender.com/<WEBHOOK_SECRET>`.
5. Render's free tier spins the service down after inactivity, which
   will delay webhook delivery until the next request wakes it up. If
   you need the heartbeat/scheduler jobs to run reliably on a schedule
   even with no incoming Telegram traffic, upgrade to a paid Render
   instance type that doesn't sleep, since `run_repeating` jobs only
   fire while the process is alive.

## MongoDB collections
- `users` — one doc per bot user, tracks heartbeat/status
- `heirs` — registered heirs, linked to owner by `owner_id`
- `capsules` — the actual time-capsule content + trigger config
- `regret_messages` — 24-hour fuse messages
- `financial_maps` — encrypted crypto/financial location hints

## Known limitations / TODO
- No admin dashboard yet — `/mycapsules` is the only introspection tool.
- Consider adding a legal-disclaimer flow: this bot is not a substitute
  for an actual notarized will for legally binding inheritance.
- For true multi-decade durability, move media off Telegram `file_id`
  references and into permanent encrypted object storage.
