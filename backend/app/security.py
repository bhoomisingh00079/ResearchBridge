import base64
import hashlib
import hmac
import json
import secrets
import time

from .config import get_settings

PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iterations))
        return hmac.compare_digest(_b64(digest), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": int(time.time()) + get_settings().token_ttl_seconds}
    return _encode_token(payload)


def _encode_token(payload: dict) -> str:
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(get_settings().signing_key, encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        encoded, signature = token.split(".", 1)
        expected = _b64(hmac.new(get_settings().signing_key, encoded.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(encoded))
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("expired")
        int(payload["sub"])
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid token") from exc


def new_verification_token() -> str:
    return secrets.token_urlsafe(32)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_token_for_user(user_id: int) -> str:
    # Older dashboard tests and integrations pass only the database ID. Keep
    # their token independent of the global DB session so overridden test DBs
    # work; authorization still uses the active User record in current_user.
    payload = {"sub": str(user_id), "exp": int(time.time()) + get_settings().token_ttl_seconds}
    return _encode_token(payload)


def verify_token_get_user_id(token: str) -> int | None:
    try:
        return int(decode_access_token(token)["sub"])
    except (ValueError, KeyError):
        return None
