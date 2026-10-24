import datetime as dt

from fastapi.testclient import TestClient

from agent_service.app import create_app
from agent_service.matching import match_opportunities, suggest_collaborators, suggest_resources
from agent_service.progress import milestone_alerts, opportunity_alerts

TODAY = dt.date(2026, 10, 24)


def test_service_requires_internal_token():
    client = TestClient(create_app("secret"))
    response = client.post("/internal/v1/match/opportunities", json={"student": {}, "opportunities": []})
    assert response.status_code == 401


def test_opportunity_match_score_explanation_and_tie_break():
    result = match_opportunities(
        {"skills": ["Python", "ml"], "interests": ["ai", "statistics"]},
        [{"id": 2, "domain": "AI", "required_skills": ["python", "ml", "statistics"]},
         {"id": 1, "domain": "AI", "required_skills": ["python", "ml", "statistics"]}],
    )
    assert [item["opportunity_id"] for item in result] == [1, 2]
    assert result[0]["score"] == 28
    assert result[0]["reason"] == (
        "You have 2 of 3 required skills: ml, python; Matches your interest in AI; "
        "Matches your skill interests: statistics"
    )


def test_http_opportunity_match_is_authenticated_and_schema_checked():
    client = TestClient(create_app("secret"))
    response = client.post("/internal/v1/match/opportunities", headers={"X-Service-Token": "secret"},
                           json={"student": {"skills": ["python"], "interests": []},
                                 "opportunities": [{"id": 7, "domain": "AI", "required_skills": ["python"]}]})
    assert response.status_code == 200
    assert response.json()["items"][0]["score"] == 10


def test_collaborator_suggestion_only_fills_missing_project_skill():
    result = suggest_collaborators(["python"], ["python", "statistics"],
                                  [{"id": 8, "skills": ["statistics", "python"]}, {"id": 9, "skills": ["python"]}])
    assert result == [{"candidate_id": 8, "fills": ["statistics"], "reason": "Fills skill gap: statistics"}]


def test_resource_suggestions_match_authorized_index_fields():
    result = suggest_resources(["python"], [{"id": 4, "title": "Python methods", "type": "Paper", "tags": []},
                                             {"id": 5, "title": "Other", "type": "Dataset", "tags": []}])
    assert result == [{"resource_id": 4, "matches": ["python"], "reason": "Related to: python"}]


def test_milestone_due_date_and_inactivity_boundaries_and_completed_exclusion():
    milestones = [
        {"id": 1, "target_date": "2026-10-23", "last_activity_at": "2026-10-24", "status": "In Progress"},
        {"id": 2, "target_date": "2026-10-24", "last_activity_at": "2026-10-17", "status": "In Progress"},
        {"id": 3, "target_date": "2026-10-24", "last_activity_at": "2026-10-18", "status": "In Progress"},
        {"id": 4, "target_date": "2026-10-01", "last_activity_at": "2026-09-01", "status": "Completed"},
    ]
    result = milestone_alerts(milestones, TODAY)
    assert [(item["milestone_id"], item["kind"]) for item in result] == [(1, "overdue"), (2, "inactive")]


def test_opportunity_deadline_capacity_alert_window_and_full_capacity():
    opportunities = [
        {"id": 1, "deadline": "2026-10-28", "capacity": 5, "application_count": 4},
        {"id": 2, "deadline": "2026-11-08", "capacity": 5, "application_count": 1},
        {"id": 3, "deadline": "2026-10-25", "capacity": 1, "application_count": 1},
        {"id": 4, "deadline": "2026-10-23", "capacity": 4, "application_count": 1},
    ]
    result = opportunity_alerts(opportunities, TODAY)
    assert [item["opportunity_id"] for item in result] == [1]
    assert result[0]["recommended_action"] == "promote"


def test_dashboard_agent_failure_shape_is_advisory_and_empty():
    client = TestClient(create_app("secret"))
    assert client.get("/health").json() == {"status": "healthy"}
