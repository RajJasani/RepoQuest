from cryptography.fernet import Fernet
import pytest

from app.core.security import (
    decrypt_token,
    encrypt_token,
    reset_fernet,
    validate_secret_key,
)


def test_encrypt_and_decrypt():
    test_key = Fernet.generate_key().decode()
    validate_secret_key(test_key)

    plaintext = "ghp_1234567890abcdef1234567890abcdef"
    ciphertext = encrypt_token(plaintext)

    assert ciphertext != plaintext
    assert plaintext not in ciphertext

    decrypted = decrypt_token(ciphertext)
    assert decrypted == plaintext


def test_missing_or_empty_key_raises_runtime_error():
    reset_fernet()
    with pytest.raises(RuntimeError) as exc_empty:
        validate_secret_key("")
    assert "APP_SECRET_KEY is missing or empty" in str(exc_empty.value)

    with pytest.raises(RuntimeError) as exc_none:
        validate_secret_key("   ")
    assert "APP_SECRET_KEY is missing or empty" in str(exc_none.value)


def test_invalid_key_raises_runtime_error():
    reset_fernet()
    with pytest.raises(RuntimeError) as exc:
        validate_secret_key("not-a-valid-fernet-key")
    assert "APP_SECRET_KEY is invalid" in str(exc.value)


def test_invalid_ciphertext_raises_value_error():
    test_key = Fernet.generate_key().decode()
    validate_secret_key(test_key)

    with pytest.raises(ValueError) as exc:
        decrypt_token("invalid-ciphertext")
    assert "Failed to decrypt token" in str(exc.value)


def test_empty_token_raises_value_error():
    test_key = Fernet.generate_key().decode()
    validate_secret_key(test_key)

    with pytest.raises(ValueError):
        encrypt_token("")
    with pytest.raises(ValueError):
        decrypt_token("")
