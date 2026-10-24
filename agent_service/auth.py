"""
Service-token authentication for the Agent Service internal API.

All requests must include header ``X-Service-Token`` matching the
server's configured token (environment variable AGENT_SERVICE_TOKEN).
The backend is the only caller (SRS 3.3, Section 1 architecture).
"""
import os

from fastapi import Header, HTTPException, status


def _get_expected_token() -> str:
    """Read the expected service token from the environment."""
    token = os.environ.get("AGENT_SERVICE_TOKEN", "")
    if not token:
        raise RuntimeError(
            "AGENT_SERVICE_TOKEN environment variable is not set. "
            "The agent service cannot start without a configured service token."
        )
    return token


def verify_service_token(
    x_service_token: str = Header(...),
) -> str:
    """FastAPI dependency: reject requests without a valid service token.

    FastAPI automatically maps the ``x_service_token`` parameter name
    to the ``X-Service-Token`` HTTP header.
    """
    expected = _get_expected_token()
    if x_service_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )
    return x_service_token

