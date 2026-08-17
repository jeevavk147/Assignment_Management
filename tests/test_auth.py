import unittest

import database
from auth import hash_password, login, verify_password
from tests.base import IsolatedDBTestCase


class HashPasswordTests(unittest.TestCase):
    def test_hash_contains_salt_and_digest(self):
        hashed = hash_password("secret123")
        salt_hex, digest_hex = hashed.split("$")
        self.assertTrue(salt_hex)
        self.assertTrue(digest_hex)

    def test_same_password_hashes_differently_each_time(self):
        # Random salt per call — two hashes of the same password must never match
        # verbatim, even though both verify correctly.
        first = hash_password("secret123")
        second = hash_password("secret123")
        self.assertNotEqual(first, second)

    def test_verify_password_correct(self):
        hashed = hash_password("secret123")
        self.assertTrue(verify_password("secret123", hashed))

    def test_verify_password_incorrect(self):
        hashed = hash_password("secret123")
        self.assertFalse(verify_password("wrong-password", hashed))


class LoginTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        database.create_user("Test User", "test@example.com", hash_password("secret123"), "student")

    def test_login_success_returns_user_row(self):
        user = login("test@example.com", "secret123")
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "test@example.com")
        self.assertEqual(user["role"], "student")

    def test_login_wrong_password_returns_none(self):
        self.assertIsNone(login("test@example.com", "wrong-password"))

    def test_login_unknown_email_returns_none(self):
        self.assertIsNone(login("nobody@example.com", "secret123"))


if __name__ == "__main__":
    unittest.main()
