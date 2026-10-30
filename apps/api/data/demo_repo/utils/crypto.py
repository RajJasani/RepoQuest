"""Cryptographic and password hashing helpers."""

import hashlib
import hmac
from config import SECRET_KEY


def hash_password(password: str) -> str:
    """Generates a secure SHA-256 HMAC hash for a password."""
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verifies that a password matches its hashed representation."""
    expected = hash_password(password)
    return hmac.compare_digest(expected, hashed)

