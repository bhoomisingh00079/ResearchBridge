"""Security utilities: password hashing and bearer token generation (NFR-005, NFR-006)."""
import hashlib
import hmac
import os
import secrets
from typing import Optional

SECRET_KEY = os.environ.get("SECRET_KEY", "rb-insecure-dev-secret-key-change-in-prod")
SALT_LENGTH = 16
ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Hash password using salted PBKDF2-HMAC-SHA256 (NFR-005)."""
    salt = secrets.token_hex(SALT_LENGTH)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS,
    )
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        salt, key_hex = hashed_password.split("$", 1)
        expected_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            ITERATIONS,
        )
        return hmac.compare_digest(expected_key.hex(), key_hex)
    except Exception:
        return False


def create_token_for_user(user_id: int) -> str:
    """Generate a simple signed token: <user_id>.<random_hex>.<signature>."""
    random_part = secrets.token_hex(16)
    payload = f"{user_id}:{random_part}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token_get_user_id(token: str) -> Optional[int]:
    """Verify signature and extract user_id."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id_str, random_part, sig = parts
        payload = f"{user_id_str}:{random_part}"
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig):
            return None
        return int(user_id_str)
    except Exception:
        return None
