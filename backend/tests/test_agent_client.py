"""Tests for Agent Client (Task C4: FR-030, FR-031, NFR-002, NFR-009)."""
from unittest.mock import patch
import httpx
import pytest

from app.models import AgentRecommendation
from app.services.agent_client import AgentClient, persist_recommendations
from .conftest import make_user


class TestAgentClientTimeoutAndDegradation:
    """Verifies 10s timeout and graceful degradation (NFR-002, SRS 5.4)."""

    def test_default_timeout_is_10s(self):
        client = AgentClient()
        assert client.timeout == 10.0

    @patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out"))
    def test_timeout_handled_gracefully(self, mock_post):
        client = AgentClient()
        res = client.match_opportunities(["python"], ["ai"], [{"id": 1, "domain": "AI"}])
        assert res["available"] is False
        assert res["items"] == []

    @patch("httpx.Client.post", side_effect=Exception("Connection refused"))
    def test_network_failure_handled_gracefully(self, mock_post):
        client = AgentClient()
        res = client.progress_milestones([{"id": 1, "target_date": "2026-10-25", "status": "In Progress"}])
        assert res["available"] is False
        assert res["alerts"] == []


class TestDataMinimisation:
    """Verifies that only structured fields are sent to agent (NFR-009)."""

    @patch("httpx.Client.post")
    def test_data_minimisation_payload(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"items": []}

        client = AgentClient()
        client.match_opportunities(
            student_skills=["python", "ml"],
            student_interests=["ai"],
            opportunities=[{"id": 10, "domain": "AI", "required_skills": ["python"]}],
        )

        args, kwargs = mock_post.call_args
        sent_body = kwargs["json"]

        # Student payload must contain only skills and interests
        assert set(sent_body["student"].keys()) == {"skills", "interests"}
        # Opp payload must contain only id, domain, required_skills
        assert set(sent_body["opportunities"][0].keys()) == {"id", "domain", "required_skills"}


class TestRecommendationPersistenceAndDismissal:
    """Verifies recommendation persistence and FR-031 dismissal non-recreation."""

    def test_new_recommendation_persisted(self, db):
        student = make_user(db, "s1@ves.ac.in", "Student")
        items = [{"opportunity_id": 99, "score": 25, "reason": "Match reason"}]

        recs = persist_recommendations(db, student.id, "opportunity", items, "opportunity_id")
        assert len(recs) == 1
        assert recs[0].status == "Active"
        assert recs[0].score == 25

    def test_dismissed_recommendation_not_recreated(self, db):
        """FR-031: Dismissed recommendations are never re-created or re-shown."""
        student = make_user(db, "s2@ves.ac.in", "Student")
        items = [{"opportunity_id": 55, "score": 20, "reason": "Initial reason"}]

        # 1. First persist
        recs = persist_recommendations(db, student.id, "opportunity", items, "opportunity_id")
        rec_id = recs[0].id

        # 2. User dismisses it
        saved_rec = db.query(AgentRecommendation).filter(AgentRecommendation.id == rec_id).first()
        saved_rec.status = "Dismissed"
        db.commit()

        # 3. Next agent scan runs with same opportunity
        updated_items = [{"opportunity_id": 55, "score": 30, "reason": "Updated reason"}]
        new_recs = persist_recommendations(db, student.id, "opportunity", updated_items, "opportunity_id")

        # Must not be in returned active recs
        assert len(new_recs) == 0

        # In DB, status remains Dismissed, not overwritten to Active
        rec_in_db = db.query(AgentRecommendation).filter(AgentRecommendation.id == rec_id).first()
        assert rec_in_db.status == "Dismissed"
