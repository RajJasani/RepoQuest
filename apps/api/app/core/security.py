import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger("app.core.security")

_fernet_instance: Optional[Fernet] = None


def validate_secret_key(key: Optional[str] = None) -> Fernet:
    """Validates that APP_SECRET_KEY is present and a valid Fernet key."""
    if key is None:
        key = get_settings().APP_SECRET_KEY

    if not key or not isinstance(key, str) or not key.strip():
        raise RuntimeError(
            "APP_SECRET_KEY is missing or empty. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    try:
        key_bytes = key.strip().encode("utf-8")
        return Fernet(key_bytes)
    except Exception as exc:
        raise RuntimeError(
            "APP_SECRET_KEY is invalid. "
            "Generate a valid Fernet key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        ) from exc


def get_fernet() -> Fernet:
    """Returns the cached Fernet instance, validating APP_SECRET_KEY on first use."""
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = validate_secret_key()
    return _fernet_instance


def reset_fernet() -> None:
    """Resets the cached Fernet instance (useful for testing key changes)."""
    global _fernet_instance
    _fernet_instance = None


def encrypt_token(token: str) -> str:
    """Encrypts a sensitive token string at rest. The token is never logged."""
    if not token:
        raise ValueError("Cannot encrypt an empty token")
    fernet = get_fernet()
    encrypted_bytes = fernet.encrypt(token.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_token(token_enc: str) -> str:
    """Decrypts an encrypted token string. The token is never logged."""
    if not token_enc:
        raise ValueError("Cannot decrypt an empty token")
    fernet = get_fernet()
    try:
        decrypted_bytes = fernet.decrypt(token_enc.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt token: invalid ciphertext or wrong APP_SECRET_KEY") from exc
