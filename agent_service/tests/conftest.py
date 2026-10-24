"""
Shared test fixtures for the Agent Service test suite.
Sets AGENT_SERVICE_TOKEN before any test module imports the app.
"""
import os

os.environ.setdefault("AGENT_SERVICE_TOKEN", "test-secret-token")

import pytest
from fastapi.testclient import TestClient

from agent_service.app import app

TEST_TOKEN = os.environ["AGENT_SERVICE_TOKEN"]
AUTH_HEADER = {"X-Service-Token": TEST_TOKEN}


@pytest.fixture
def client():
    """FastAPI test client for the agent service."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid authentication headers for internal API calls."""
    return AUTH_HEADER.copy()

