"""Authentication package for TaskBoard."""

from auth.models import User
from auth.service import AuthService

__all__ = ["User", "AuthService"]
