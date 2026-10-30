"""Authentication utility functions."""

from typing import Optional
from auth.models import User
from utils.validators import validate_username


def sanitize_user_input(username: str) -> Optional[str]:
    """Cleans and verifies username strings before querying."""
    if not validate_username(username):
        return None
    return username.strip().lower()


def format_user_badge(user: User) -> str:
    """Returns a visual string badge for user profile."""
    return f"@{user.username} (#{user.id})"

