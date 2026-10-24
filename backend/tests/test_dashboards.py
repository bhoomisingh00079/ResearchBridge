"""Tests for Dashboards and Agent Endpoints (Task C5: FR-031 to FR-034)."""
from unittest.mock import patch
import pytest

from app.models import AgentRecommendation, Application, Opportunity, Project, ProjectMember
from .conftest import make_auth_header, make_user


class TestStudentDashboard:
    """FR-032: Student Dashboard API."""

    def test_student_dashboard_success(self, client, db):
        student = make_user(db, "stud1@ves.ac.in", "Student")
        headers = make_auth_header(student)

        # Create dummy application
        fac = make_user(db, "fac1@ves.ac.in", "Faculty")
        opp = Opportunity(
            faculty_id=fac.id,
            title="Quantum Research",
            description="Details",
            domain="Physics",
            capacity=2,
            status="Published",
        )
        db.add(opp)
        db.commit()

        app = Application(
            student_id=student.id,
            opportunity_id=opp.id,
            status="Submitted",
        )
        db.add(app)
        db.commit()

        res = client.get("/dashboard/student", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["applications"]) == 1
        assert data["applications"][0]["opportunity_title"] == "Quantum Research"
        assert data["applications"][0]["status"] == "Submitted"

    def test_faculty_forbidden_from_student_dashboard(self, client, db):
        fac = make_user(db, "fac_denied@ves.ac.in", "Faculty")
        headers = make_auth_header(fac)

        res = client.get("/dashboard/student", headers=headers)
        assert res.status_code == 403


class TestFacultyDashboard:
    """FR-033: Faculty Dashboard API."""

    def test_faculty_dashboard_success(self, client, db):
        fac = make_user(db, "fac2@ves.ac.in", "Faculty")
        headers = make_auth_header(fac)

        # Opportunity with pending applicant
        opp = Opportunity(
            faculty_id=fac.id,
            title="AI Vision Lab",
            description="Computer Vision",
            domain="AI",
            capacity=3,
            status="Published",
        )
        db.add(opp)
        db.commit()

        student = make_user(db, "stud2@ves.ac.in", "Student")
        app = Application(
            student_id=student.id,
            opportunity_id=opp.id,
            status="Submitted",
        )
        db.add(app)
        db.commit()

        res = client.get("/dashboard/faculty", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["pending_applicants_count"] == 1
        assert data["pending_applicants"][0]["student_name"] == "Test User"

    def test_student_forbidden_from_faculty_dashboard(self, client, db):
        student = make_user(db, "stud_denied@ves.ac.in", "Student")
        headers = make_auth_header(student)

        res = client.get("/dashboard/faculty", headers=headers)
        assert res.status_code == 403


class TestCoordinatorDashboard:
    """FR-034: Coordinator Dashboard API."""

    def test_coordinator_dashboard_aggregates(self, client, db):
        coord = make_user(db, "coord@ves.ac.in", "Coordinator")
        headers = make_auth_header(coord)

        res = client.get("/dashboard/coordinator", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "users_by_role" in data["metrics"]
        assert "opportunities_by_status" in data["metrics"]

    def test_regular_user_forbidden(self, client, db):
        student = make_user(db, "stud_no_coord@ves.ac.in", "Student")
        headers = make_auth_header(student)

        res = client.get("/dashboard/coordinator", headers=headers)
        assert res.status_code == 403


class TestDismissRecommendationEndpoint:
    """FR-031: Dismissal endpoint."""

    def test_dismiss_recommendation_endpoint(self, client, db):
        student = make_user(db, "stud_rec@ves.ac.in", "Student")
        headers = make_auth_header(student)

        rec = AgentRecommendation(
            user_id=student.id,
            type="opportunity",
            reference_entity="opportunity:101",
            reason_text="Recommended for Python skills",
            score=25,
            status="Active",
        )
        db.add(rec)
        db.commit()

        # Dismiss it
        res = client.post(f"/agent/recommendations/{rec.id}/dismiss", headers=headers)
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Check DB status is Dismissed
        updated = db.query(AgentRecommendation).filter(AgentRecommendation.id == rec.id).first()
        assert updated.status == "Dismissed"
