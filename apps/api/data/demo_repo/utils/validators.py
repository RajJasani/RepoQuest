"""Validation helpers for user input and requests."""

import re

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")


def validate_email(email: str) -> bool:
    """Checks whether an email string adheres to basic RFC standards."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def validate_username(username: str) -> bool:
    """Checks whether a username contains only allowed alphanumeric characters."""
    if not username or not isinstance(username, str):
        return False
    return bool(USERNAME_REGEX.match(username.strip()))
