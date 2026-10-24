"""
Integration tests for the Agent Service API — C1.

Tests the full HTTP request/response cycle including:
  - Service-token authentication (SRS 3.3)
  - Request schema validation
  - All five internal API endpoints
  - Health check (no auth)
"""
import os
import pytest

os.environ.setdefault("AGENT_SERVICE_TOKEN", "test-secret-token")

from fastapi.testclient import TestClient

from agent_service.app import app

TOKEN = os.environ["AGENT_SERVICE_TOKEN"]
AUTH = {"X-Service-Token": TOKEN}

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════
# Authentication (SRS 3.3)
# ═══════════════════════════════════════════════════════════════════════


class TestAuthentication:
    """Service-token authentication on all protected endpoints."""

    def test_missing_token_rejected(self):
        """Requests without X-Service-Token get 422 (missing header)."""
        r = client.post(
            "/internal/v1/match/opportunities",
            json={
                "student": {"skills": [], "interests": []},
                "opportunities": [],
            },
        )
        assert r.status_code == 422

    def test_invalid_token_rejected(self):
        """Requests with wrong token get 401."""
        r = client.post(
            "/internal/v1/match/opportunities",
            headers={"X-Service-Token": "wrong-token"},
            json={
                "student": {"skills": [], "interests": []},
                "opportunities": [],
            },
        )
        assert r.status_code == 401

    def test_valid_token_accepted(self):
        """Requests with correct token succeed."""
        r = client.post(
            "/internal/v1/match/opportunities",
            headers=AUTH,
            json={
                "student": {"skills": [], "interests": []},
                "opportunities": [],
            },
        )
        assert r.status_code == 200

    def test_all_protected_endpoints_require_token(self):
        """Every /internal/ endpoint rejects requests without a token."""
        endpoints = [
            ("/internal/v1/match/opportunities", {
                "student": {"skills": [], "interests": []},
                "opportunities": [],
            }),
            ("/internal/v1/match/collaborators", {
                "project": {"id": 1, "domain": "AI", "required_skills": []},
                "current_team_skills": [],
                "candidates": [],
            }),
            ("/internal/v1/match/resources", {
                "project": {"id": 1, "domain": "AI", "required_skills": []},
                "resources": [],
            }),
            ("/internal/v1/progress/milestones", {"milestones": []}),
            ("/internal/v1/progress/opportunities", {"opportunities": []}),
        ]
        for path, body in endpoints:
            r = client.post(path, json=body)
            assert r.status_code == 422, f"{path} should reject missing token"


# ═══════════════════════════════════════════════════════════════════════
# Health endpoint (no auth)
# ═══════════════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    """Health check requires no authentication."""

    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
        assert r.json()["service"] == "agent"


# ═══════════════════════════════════════════════════════════════════════
# Match Opportunities API (FR-025 / FR-026)
# ═══════════════════════════════════════════════════════════════════════


class TestMatchOpportunitiesAPI:
    """POST /internal/v1/match/opportunities end-to-end."""

    def test_plan_example(self):
        """Exact example from development plan Section 5."""
        r = client.post(
            "/internal/v1/match/opportunities",
            headers=AUTH,
            json={
                "student": {"skills": ["python", "ml"], "interests": ["ai"]},
                "opportunities": [
                    {
                        "id": 7,
                        "domain": "AI",
                        "required_skills": ["python", "ml", "statistics"],
                    },
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["opportunity_id"] == 7
        assert data["items"][0]["score"] == 25

    def test_invalid_request_body(self):
        """Malformed request body gets 422."""
        r = client.post(
            "/internal/v1/match/opportunities",
            headers=AUTH,
            json={"invalid": "data"},
        )
        assert r.status_code == 422

    def test_empty_input_returns_empty(self):
        """Empty opportunities list returns empty items."""
        r = client.post(
            "/internal/v1/match/opportunities",
            headers=AUTH,
            json={
                "student": {"skills": ["python"], "interests": ["ai"]},
                "opportunities": [],
            },
        )
        assert r.status_code == 200
        assert r.json()["items"] == []


# ═══════════════════════════════════════════════════════════════════════
# Match Collaborators API (FR-027)
# ═══════════════════════════════════════════════════════════════════════


class TestMatchCollaboratorsAPI:
    """POST /internal/v1/match/collaborators end-to-end."""

    def test_finds_gap_filler(self):
        r = client.post(
            "/internal/v1/match/collaborators",
            headers=AUTH,
            json={
                "project": {
                    "id": 1,
                    "domain": "AI",
                    "required_skills": ["python", "ml", "statistics"],
                },
                "current_team_skills": ["python", "ml"],
                "candidates": [
                    {"id": 5, "skills": ["statistics", "r"], "interests": ["ai"]},
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["user_id"] == 5
        assert "statistics" in data["items"][0]["reason"]


# ═══════════════════════════════════════════════════════════════════════
# Match Resources API (FR-028)
# ═══════════════════════════════════════════════════════════════════════


class TestMatchResourcesAPI:
    """POST /internal/v1/match/resources end-to-end."""

    def test_matches_keywords(self):
        r = client.post(
            "/internal/v1/match/resources",
            headers=AUTH,
            json={
                "project": {
                    "id": 1,
                    "domain": "AI",
                    "required_skills": ["python", "ml"],
                },
                "resources": [
                    {
                        "id": 10,
                        "title": "ML Tutorial",
                        "type": "Paper",
                        "keywords": ["ml", "python"],
                    },
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["resource_id"] == 10
        assert data["items"][0]["score"] == 20


# ═══════════════════════════════════════════════════════════════════════
# Progress Milestones API (FR-029)
# ═══════════════════════════════════════════════════════════════════════


class TestProgressMilestonesAPI:
    """POST /internal/v1/progress/milestones end-to-end."""

    def test_detects_overdue(self):
        r = client.post(
            "/internal/v1/progress/milestones",
            headers=AUTH,
            json={
                "milestones": [
                    {
                        "id": 1,
                        "target_date": "2020-01-01",
                        "status": "In Progress",
                        "last_activity_at": "2020-01-01T00:00:00Z",
                    },
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["alerts"]) >= 1
        assert any(a["type"] == "overdue" for a in data["alerts"])

    def test_empty_input(self):
        r = client.post(
            "/internal/v1/progress/milestones",
            headers=AUTH,
            json={"milestones": []},
        )
        assert r.status_code == 200
        assert r.json()["alerts"] == []


# ═══════════════════════════════════════════════════════════════════════
# Progress Opportunities API (FR-035)
# ═══════════════════════════════════════════════════════════════════════


class TestProgressOpportunitiesAPI:
    """POST /internal/v1/progress/opportunities end-to-end."""

    def test_detects_past_deadline(self):
        r = client.post(
            "/internal/v1/progress/opportunities",
            headers=AUTH,
            json={
                "opportunities": [
                    {
                        "id": 7,
                        "deadline": "2020-01-01",
                        "application_count": 0,
                        "capacity": 5,
                    },
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["type"] == "past_deadline"
        assert data["alerts"][0]["recommended_action"] == "extend deadline"

    def test_empty_input(self):
        r = client.post(
            "/internal/v1/progress/opportunities",
            headers=AUTH,
            json={"opportunities": []},
        )
        assert r.status_code == 200
        assert r.json()["alerts"] == []

