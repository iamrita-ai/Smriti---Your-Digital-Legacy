"""
Symmetric encryption helper (Fernet/AES) for anything sensitive:
capsule content, financial/crypto inheritance hints, etc.

We NEVER store raw private keys or passwords by design (see financial_map.py) -
only encrypted *hints* pointing to where the real secret physically/digitally lives.
"""

import hashlib
from cryptography.fernet import Fernet, InvalidToken

import config

_fernet = Fernet(config.ENCRYPTION_KEY.encode()) if config.ENCRYPTION_KEY else None


def encrypt(plaintext: str) -> str:
    if not _fernet:
        raise RuntimeError("ENCRYPTION_KEY not configured")
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    if not _fernet:
        raise RuntimeError("ENCRYPTION_KEY not configured")
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Could not decrypt — data corrupted or wrong key")


def hash_answer(answer: str) -> str:
    """One-way hash for 'emotional password' answers — we only ever compare,
    never need to recover the original answer."""
    normalized = answer.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def verify_answer(answer: str, stored_hash: str) -> bool:
    return hash_answer(answer) == stored_hash
