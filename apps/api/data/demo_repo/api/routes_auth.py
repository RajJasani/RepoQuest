"""Authentication API endpoint handlers."""

from typing import Tuple
from auth.service import AuthService
from utils.validators import validate_email, validate_username


class AuthHandler:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def handle_register(self, payload: dict) -> Tuple[int, dict]:
        """Handles user registration request."""
        username = payload.get("username", "")
        email = payload.get("email", "")
        password = payload.get("password", "")

        if not validate_username(username):
            return 400, {"error": "Invalid username"}
        if not validate_email(email):
            return 400, {"error": "Invalid email format"}

        try:
            user = self.auth_service.register_user(username, email, password)
            return 201, {"user": user.to_dict()}
        except Exception as exc:
            return 400, {"error": str(exc)}

    def handle_login(self, payload: dict) -> Tuple[int, dict]:
        """Handles user authentication request."""
        username = payload.get("username", "")
        password = payload.get("password", "")
        user = self.auth_service.authenticate_user(username, password)
        if not user:
            return 401, {"error": "Invalid credentials"}
        return 200, {"token": f"demo-session-{user.id}", "user": user.to_dict()}

