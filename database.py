"""
MongoDB data layer using Beanie (async ODM on top of Motor).

Beanie gives us Pydantic-model documents with async query methods, which
keeps handler code close to a normal ORM style while being fully async
(important since PTB v20 handlers are async and we must never block the
event loop with sync DB calls).
"""

import enum
from datetime import datetime, timezone
from typing import Optional

import certifi
from beanie import Document, PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import Field

import config


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    AWAITING_REPLY = "awaiting_reply"
    DECEASED = "deceased"


class TriggerType(str, enum.Enum):
    ON_DEATH = "on_death"
    ON_DATE = "on_date"
    ON_AGE = "on_age"
    MANUAL = "manual"


class CapsuleType(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"
    PHOTO = "photo"
    DOCUMENT = "document"
    VIDEO = "video"


class User(Document):
    telegram_id: int
    username: Optional[str] = None
    display_name: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE

    heartbeat_code: Optional[str] = None
    heartbeat_sent_at: Optional[datetime] = None
    last_reply_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "users"


class Heir(Document):
    owner_id: PydanticObjectId
    name: str
    relation: Optional[str] = None
    birth_date: Optional[datetime] = None
    telegram_id: Optional[int] = None
    verification_code: str
    verified: bool = False

    class Settings:
        name = "heirs"


class Capsule(Document):
    owner_id: PydanticObjectId
    heir_id: Optional[PydanticObjectId] = None

    capsule_type: CapsuleType
    file_id: Optional[str] = None  # fallback if LOG_CHANNEL_ID isn't configured
    log_channel_message_id: Optional[int] = None  # preferred: message_id in the log channel
    encrypted_text: Optional[str] = None

    trigger_type: TriggerType
    trigger_date: Optional[datetime] = None
    trigger_age: Optional[int] = None

    emotional_question: Optional[str] = None
    emotional_answer_hash: Optional[str] = None

    is_memory: bool = False
    delivered: bool = False
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "capsules"


class RegretMessage(Document):
    owner_id: PydanticObjectId
    heir_id: PydanticObjectId
    encrypted_text: str
    created_at: datetime = Field(default_factory=_utcnow)
    deadline: datetime
    cancelled: bool = False
    delivered: bool = False

    class Settings:
        name = "regret_messages"


class FinancialMap(Document):
    owner_id: PydanticObjectId
    label: str
    encrypted_hint: str
    heir_id: Optional[PydanticObjectId] = None
    delivered: bool = False
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "financial_maps"


_client: Optional[AsyncIOMotorClient] = None


async def init_db() -> None:
    """Call once at startup (from main.py's post_init) before any queries run."""
    global _client
    # tlsCAFile=certifi.where() avoids TLS handshake failures against MongoDB
    # Atlas that can happen in minimal Docker images with an incomplete/old
    # system CA bundle (a common issue on Render/Railway/Heroku-style hosts).
    _client = AsyncIOMotorClient(config.MONGODB_URI, tlsCAFile=certifi.where())
    db = _client[config.MONGODB_DB_NAME]
    await init_beanie(
        database=db,
        document_models=[User, Heir, Capsule, RegretMessage, FinancialMap],
    )


async def get_or_create_user(telegram_id: int, username: str, display_name: str) -> tuple[User, bool]:
    user = await User.find_one(User.telegram_id == telegram_id)
    if user:
        return user, False
    user = User(telegram_id=telegram_id, username=username, display_name=display_name)
    await user.insert()
    return user, True
