import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# CI runs pytest with backend/ as its working directory, while local runs may
# start at the repository root. Add the backend package root for both layouts.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from advisory.agent_client import AgentClient
from advisory.dashboard import create_dashboard_router
from advisory.recommendations import InMemoryRecommendationStore, Recommendation


def test_agent_client_allowlists_fields_and_returns_unavailable_on_error():
    async def scenario():
        seen = {}

        async def handler(request):
            seen.update(json.loads(request.content))
            return httpx.Response(500)

        client = AgentClient("http://agent", "token", transport=httpx.MockTransport(handler))
        result = await client.recommendations_or_unavailable(
            ["python"], ["AI"], [{"id": 2, "domain": "AI", "required_skills": ["python"], "student_name": "private"}],
        )
        assert result["available"] is False
        assert "student_name" not in str(seen)

    asyncio.run(scenario())


def test_agent_timeout_limit_is_at_most_ten_seconds():
    with pytest.raises(ValueError):
        AgentClient("http://agent", "token", timeout_seconds=10.01)


def test_recommendation_store_does_not_recreate_dismissed_items():
    store = InMemoryRecommendationStore()
    item = Recommendation(user_id=4, kind="opportunity", reference_id=8, reason="skill match", score=10)
    assert store.upsert_unseen(item)
    assert not store.upsert_unseen(item)
    assert store.dismiss(4, 8)
    assert not store.upsert_unseen(item)


def test_dashboard_role_gate_and_provider_are_server_side():
    class User:
        def __init__(self, role, user_id=5):
            self.role, self.id = role, user_id

    app = FastAPI()
    def current_user():
        return User("Student")

    router = create_dashboard_router(current_user, lambda role, user_id: {"role": role, "user_id": user_id})
    app.include_router(router)
    response = TestClient(app).get("/dashboard/student")
    assert response.status_code == 200
    assert response.json() == {"role": "student", "user_id": 5}
    assert TestClient(app).get("/dashboard/faculty").status_code == 403
