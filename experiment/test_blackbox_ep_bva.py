"""Black-box API EP/BVA suite for the Member A contract.

This integration suite becomes active when the auth, opportunity, application and
milestone endpoints are mounted. The current health-only scaffold is detected and
the module is skipped with an explicit reason instead of generating false failures.
"""

import datetime as dt
import os
import sys

import pytest

BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND)
os.environ.setdefault("DATABASE_URL", "sqlite:///./bb_test.db")

import main  # noqa: E402

REQUIRED_PATHS = {
    "/auth/register", "/auth/verify/{token}", "/auth/login", "/opportunities",
    "/opportunities/{opportunity_id}/apply", "/applications/{application_id}/decide",
    "/projects", "/projects/{project_id}/milestones", "/milestones/{milestone_id}",
    "/projects/{project_id}/milestones/overdue",
}
available_paths = {route.path for route in main.app.routes}
if not REQUIRED_PATHS.issubset(available_paths):
    pytest.skip("Member A auth/opportunity/application/milestone API contract is not mounted yet",
                allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(main.app)
_counter = 0


def register(email=None, password="Password123", role="Student", name="Researcher"):
    global _counter
    _counter += 1
    return client.post("/auth/register", json={
        "email": email or f"memberc{_counter}@ves.ac.in", "password": password,
        "name": name, "role": role,
    })


def login_headers(role):
    response = register(role=role)
    token = response.json().get("dev_verify_token")
    if token:
        client.post(f"/auth/verify/{token}")
    email = response.json().get("email")
    if not email:
        email = f"memberc{_counter}@ves.ac.in"
    login = client.post("/auth/login", json={"email": email, "password": "Password123"})
    return {"Authorization": f"Bearer {login.json()['token']}"}


def create_project_for_student(faculty, student):
    opportunity = client.post("/opportunities", headers=faculty, json={
        "title": "Boundary study", "description": "Experiment", "domain": "AI", "capacity": 2,
    })
    assert opportunity.status_code == 201
    opportunity_id = opportunity.json()["id"]
    client.post(f"/opportunities/{opportunity_id}/state/publish", headers=faculty)
    application = client.post(f"/opportunities/{opportunity_id}/apply", headers=student,
                              json={"motivation": "Study the boundary"})
    assert application.status_code == 201
    client.post(f"/applications/{application.json()['id']}/decide", headers=faculty,
                json={"status": "Accepted"})
    project = client.post("/projects", headers=faculty, json={
        "title": "Boundary project", "application_ids": [application.json()["id"]],
    })
    assert project.status_code == 201
    return project.json()["project_id"]


@pytest.mark.parametrize("password,status", [("", 422), ("a" * 7, 422), ("a" * 8, 201),
                                              ("a" * 9, 201), ("a" * 64, 201)],
                         ids=["password-empty", "password-7-below", "password-8-boundary",
                              "password-9-above", "password-64-valid"])
def test_password_length_bva(password, status):
    assert register(password=password).status_code == status


@pytest.mark.parametrize("email,status", [("ok@ves.ac.in", 201), ("OK@VES.AC.IN", 201),
                                           ("x@gmail.com", 400), ("no-at-sign", 400),
                                           ("", 400), ("a@ves.ac.in.evil.com", 400)],
                         ids=["institutional", "institutional-case", "external-domain",
                              "malformed", "empty", "lookalike-domain"])
def test_email_partitions(email, status):
    assert register(email=email).status_code == status


def test_duplicate_registration_is_generic():
    register(email="duplicate@ves.ac.in")
    response = register(email="duplicate@ves.ac.in")
    assert response.status_code == 400
    assert response.json()["detail"] == "Registration failed"


@pytest.mark.parametrize("role,status", [("Student", 201), ("Faculty", 201),
                                          ("Administrator", 400), ("Coordinator", 400), ("root", 400)])
def test_self_registration_role_partitions(role, status):
    assert register(role=role).status_code == status


@pytest.mark.parametrize("capacity,status", [(-1, 422), (0, 422), (1, 201), (2, 201), (100, 201)],
                         ids=["negative", "zero", "minimum", "above-minimum", "large"])
def test_capacity_bva(capacity, status):
    response = client.post("/opportunities", headers=login_headers("Faculty"), json={
        "title": "Capacity boundary", "description": "Test", "domain": "AI", "capacity": capacity,
    })
    assert response.status_code == status


@pytest.mark.parametrize("delta,overdue", [(-1, True), (0, False), (1, False)],
                         ids=["yesterday", "today", "tomorrow"])
def test_milestone_overdue_date_boundary(delta, overdue):
    faculty, student = login_headers("Faculty"), login_headers("Student")
    project_id = create_project_for_student(faculty, student)
    response = client.post(f"/projects/{project_id}/milestones", headers=faculty, json={
        "description": "Date boundary", "target_date": str(dt.date.today() + dt.timedelta(days=delta)),
    })
    assert response.status_code == 201
    overdue_items = client.get(f"/projects/{project_id}/milestones/overdue", headers=student).json()
    assert (len(overdue_items) == 1) is overdue


@pytest.mark.parametrize("status,expected", [("Not Started", 200), ("In Progress", 200),
                                              ("Completed", 200), ("Blocked", 200),
                                              ("Done", 400), ("", 400)])
def test_milestone_status_partitions(status, expected):
    faculty, student = login_headers("Faculty"), login_headers("Student")
    project_id = create_project_for_student(faculty, student)
    response = client.post(f"/projects/{project_id}/milestones", headers=faculty, json={
        "description": "Status boundary", "target_date": "2030-01-01",
    })
    assert response.status_code == 201
    assert client.patch(f"/milestones/{response.json()['id']}", headers=student,
                        json={"status": status}).status_code == expected
