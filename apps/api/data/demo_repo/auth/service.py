"""Authentication service managing user registration and verification."""

import sqlite3
from typing import Optional

from auth.models import User
from utils.crypto import hash_password, verify_password
from utils.validators import validate_email, validate_username


class AuthService:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def register_user(self, username: str, email: str, password: str) -> User:
        """Registers a new user after validation and hashing."""
        if not validate_username(username):
            raise ValueError(f"Invalid username: {username}")
        if not validate_email(email):
            raise ValueError(f"Invalid email: {email}")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")

        hashed = hash_password(password)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username.strip(), email.strip(), hashed),
        )
        self.conn.commit()
        user_id = cursor.lastrowid
        return User(id=user_id, username=username, email=email, password_hash=hashed)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticates user credentials against the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, created_at FROM users WHERE username = ?",
            (username.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None

        if not verify_password(password, row["password_hash"]):
            return None

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
        )
