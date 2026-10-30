"""Tests for user authentication."""

import unittest
from auth.service import AuthService
from tests.conftest import BaseTestCase


class TestAuth(BaseTestCase):
    def test_register_and_authenticate(self):
        service = AuthService(self.conn)
        user = service.register_user("charlie", "charlie@example.com", "password123")
        self.assertEqual(user.username, "charlie")
        self.assertEqual(user.email, "charlie@example.com")

        auth_user = service.authenticate_user("charlie", "password123")
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user.id, user.id)

    def test_invalid_login(self):
        service = AuthService(self.conn)
        service.register_user("bob", "bob@example.com", "securepwd")
        auth_user = service.authenticate_user("bob", "wrongpassword")
        self.assertIsNone(auth_user)


if __name__ == "__main__":
    unittest.main()
