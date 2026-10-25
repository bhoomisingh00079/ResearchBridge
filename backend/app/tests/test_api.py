from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password, create_access_token, decode_access_token


@pytest.fixture
def client(tmp_path):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    def override_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    test_client = TestClient(app)
    test_client.test_session_factory = TestSession
    yield test_client
    app.dependency_overrides.clear()
    test_engine.dispose()


def register(client, email="student@ves.ac.in", role="Student", password="Password123"):
    response = client.post("/auth/register", json={
        "email": email, "password": password, "name": "Taylor Researcher", "role": role,
    })
    assert response.status_code == 201, response.text
    return response.json()


def login(client, user):
    client.post(f"/auth/verify/{user['dev_verify_token']}")
    response = client.post("/auth/login", json={"email": user["email"], "password": "Password123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def faculty_opportunity(client, headers, capacity=1, deadline=None):
    return client.post("/opportunities", headers=headers, json={
        "title": "Research in AI", "description": "Study models", "domain": "AI",
        "duration": "10 weeks", "capacity": capacity,
        "deadline": deadline.isoformat() if deadline else None,
        "required_skills": ["Python", "Statistics"],
    })


def test_health_and_openapi_contract_survive(client):
    assert client.get("/").json() == {"message": "ResearchBridge API is running"}
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/openapi.json").status_code == 200


def test_registration_verification_login_and_generic_duplicate_error(client):
    user = register(client)
    assert "password_hash" not in user and "verify_token" not in user
    duplicate = client.post("/auth/register", json={
        "email": "student@ves.ac.in", "password": "Password123", "name": "Other", "role": "Student",
    })
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Registration failed"
    invalid_login = client.post("/auth/login", json={"email": user["email"], "password": "wrongpass"})
    assert invalid_login.status_code == 401
    headers = login(client, user)
    me = client.get("/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == user["email"]
    assert client.get("/me").status_code == 401
    token = client.post("/auth/login", json={"email": user["email"], "password": "Password123"}).json()["token"]
    with pytest.raises(ValueError):
        decode_access_token(token + "tampered")


@pytest.mark.parametrize("email,role,password,status", [
    ("person@gmail.com", "Student", "Password123", 400),
    ("malformed", "Student", "Password123", 400),
    ("person@ves.ac.in", "Administrator", "Password123", 400),
    ("person@ves.ac.in", "Student", "short", 422),
])
def test_registration_validation_partitions(client, email, role, password, status):
    response = client.post("/auth/register", json={
        "email": email, "password": password, "name": "Test User", "role": role,
    })
    assert response.status_code == status


def test_profiles_are_role_gated_and_sanitized(client):
    student = register(client)
    student_headers = login(client, student)
    response = client.put("/profile/student", headers=student_headers, json={
        "research_experience": "<script>alert(1)</script>Research assistant",
        "skills": ["python", "<b>python</b>", "statistics"], "interests": ["AI"],
    })
    assert response.status_code == 200
    assert response.json()["research_experience"] == "Research assistant"
    assert response.json()["skills"] == ["python", "statistics"]
    assert client.get("/profile/student", headers=student_headers).json()["interests"] == ["AI"]
    assert client.put("/profile/faculty", headers=student_headers, json={"bio": "No", "expertise": []}).status_code == 403
    faculty = register(client, "faculty@ves.ac.in", "Faculty")
    faculty_headers = login(client, faculty)
    assert client.put("/profile/faculty", headers=faculty_headers,
                      json={"bio": "AI research", "expertise": ["ML"]}).status_code == 200


def test_opportunity_lifecycle_search_pagination_and_requirement_versions(client):
    faculty = register(client, "faculty@ves.ac.in", "Faculty")
    headers = login(client, faculty)
    response = faculty_opportunity(client, headers, capacity=2, deadline=date.today() + timedelta(days=7))
    assert response.status_code == 201
    opp = response.json()
    assert opp["capacity"] == 2 and opp["requirements_version"] == 1
    mine = client.get("/opportunities/mine", headers=headers)
    assert mine.status_code == 200 and mine.json()["items"][0]["id"] == opp["id"]
    assert client.get("/opportunities/mine").status_code == 401
    assert client.get("/opportunities").json()["items"] == []
    published = client.post(f"/opportunities/{opp['id']}/state/publish", headers=headers)
    assert published.status_code == 200 and published.json()["status"] == "Published"
    assert client.post(f"/opportunities/{opp['id']}/state/publish", headers=headers).status_code == 409
    search = client.get("/opportunities", params={"q": "Research", "skill": "python", "available": True})
    assert search.status_code == 200 and len(search.json()["items"]) == 1
    assert client.get(f"/opportunities/{opp['id']}").status_code == 200
    updated = client.put(f"/opportunities/{opp['id']}", headers=headers, json={
        "title": "Updated AI opportunity", "description": "New scope", "domain": "AI",
        "duration": "12 weeks", "capacity": 3, "deadline": None, "required_skills": ["Python", "ML"],
    })
    assert updated.status_code == 200 and updated.json()["requirements_version"] == 2
    from app.models import OpportunityVersion
    with client.test_session_factory() as session:
        history = session.query(OpportunityVersion).filter_by(opportunity_id=opp["id"]).order_by(
            OpportunityVersion.version).all()
        assert [item.version for item in history] == [1, 2]
        assert history[0].snapshot["required_skills"] == ["Python", "Statistics"]
    # The public representation reflects the current edited version.
    assert client.get(f"/opportunities/{opp['id']}").json()["required_skills"] == ["Python", "ML"]
    closed = client.post(f"/opportunities/{opp['id']}/state/close", headers=headers)
    assert closed.status_code == 200 and closed.json()["status"] == "Closed"
    archived = client.post(f"/opportunities/{opp['id']}/state/archive", headers=headers)
    assert archived.status_code == 200 and archived.json()["status"] == "Archived"
    assert client.get("/opportunities").json()["items"] == []
    assert client.get(f"/opportunities/{opp['id']}").status_code == 404


def test_capacity_ownership_and_html_validation(client):
    faculty = register(client, "faculty@ves.ac.in", "Faculty")
    headers = login(client, faculty)
    assert faculty_opportunity(client, headers, capacity=0).status_code == 422
    own = faculty_opportunity(client, headers, capacity=1).json()
    other = register(client, "other@ves.ac.in", "Faculty")
    other_headers = login(client, other)
    assert client.put(f"/opportunities/{own['id']}", headers=other_headers, json={
        "title": "Intrusion", "description": "x", "domain": "x", "capacity": 1,
        "required_skills": [],
    }).status_code == 403
    created = faculty_opportunity(client, headers, capacity=1)
    assert "<script>" not in created.text


def test_application_duplicate_withdraw_decide_capacity_and_project_members(client):
    faculty = register(client, "faculty@ves.ac.in", "Faculty")
    faculty_headers = login(client, faculty)
    student = register(client, "student@ves.ac.in")
    student_headers = login(client, student)
    opportunity = faculty_opportunity(client, faculty_headers, capacity=1,
                                      deadline=date.today() + timedelta(days=2)).json()
    client.post(f"/opportunities/{opportunity['id']}/state/publish", headers=faculty_headers)
    first = client.post(f"/opportunities/{opportunity['id']}/apply", headers=student_headers,
                        json={"motivation": "<b>Interested</b>"})
    assert first.status_code == 201 and first.json()["motivation"] == "Interested"
    assert first.json()["req_version"] == 1
    my_apps = client.get("/applications/mine", headers=student_headers)
    assert my_apps.status_code == 200
    assert my_apps.json()[0]["opportunity_title"] == opportunity["title"]
    duplicate = client.post(f"/opportunities/{opportunity['id']}/apply", headers=student_headers,
                            json={"motivation": "Again"})
    assert duplicate.status_code == 409
    withdrawn = client.post(f"/applications/{first.json()['id']}/withdraw", headers=student_headers)
    assert withdrawn.status_code == 200 and withdrawn.json()["status"] == "Withdrawn"
    second = client.post(f"/opportunities/{opportunity['id']}/apply", headers=student_headers,
                         json={"motivation": "Reapplied"})
    assert second.status_code == 201
    decided = client.post(f"/applications/{second.json()['id']}/decide", headers=faculty_headers,
                          json={"status": "Accepted", "faculty_comment": "Welcome"})
    assert decided.status_code == 200 and decided.json()["status"] == "Accepted"
    project = client.post("/projects", headers=faculty_headers,
                          json={"title": "New team", "application_ids": [second.json()["id"]]})
    assert project.status_code == 201
    assert client.get(f"/projects/{project.json()['project_id']}", headers=student_headers).status_code == 200
    another_student = register(client, "second@ves.ac.in")
    another_headers = login(client, another_student)
    assert client.get(f"/projects/{project.json()['project_id']}", headers=another_headers).status_code == 403
    # Accepted student occupies the only seat; a new application is not accepted above capacity.
    candidate = register(client, "third@ves.ac.in")
    candidate_headers = login(client, candidate)
    third = client.post(f"/opportunities/{opportunity['id']}/apply", headers=candidate_headers,
                        json={"motivation": "Apply"})
    assert third.status_code == 201
    rejected_for_capacity = client.post(f"/applications/{third.json()['id']}/decide", headers=faculty_headers,
                                        json={"status": "Accepted"})
    assert rejected_for_capacity.status_code == 409


def test_closed_and_expired_opportunities_reject_student_applications(client):
    faculty = register(client, "faculty@ves.ac.in", "Faculty")
    faculty_headers = login(client, faculty)
    student = register(client)
    student_headers = login(client, student)
    expired = faculty_opportunity(client, faculty_headers, deadline=date.today() - timedelta(days=1)).json()
    client.post(f"/opportunities/{expired['id']}/state/publish", headers=faculty_headers)
    response = client.post(f"/opportunities/{expired['id']}/apply", headers=student_headers,
                           json={"motivation": "I want to learn"})
    assert response.status_code == 409 and response.json()["detail"] == "Deadline passed"
    open_opp = faculty_opportunity(client, faculty_headers, deadline=date.today()).json()
    client.post(f"/opportunities/{open_opp['id']}/state/publish", headers=faculty_headers)
    client.post(f"/opportunities/{open_opp['id']}/state/close", headers=faculty_headers)
    closed_response = client.post(f"/opportunities/{open_opp['id']}/apply", headers=student_headers,
                                  json={"motivation": "I want to learn"})
    assert closed_response.status_code == 409 and closed_response.json()["detail"] == "Opportunity is not open"


def test_admin_permissions_audit_and_sensitive_fields_are_not_returned(client):
    student = register(client)
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    admin = User(email="admin@ves.ac.in", password_hash=hash_password("Password123"), name="Admin",
                 role="Administrator", status="Active")
    db.add(admin)
    db.commit()
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin.id, admin.role)}"}
    listing = client.get("/admin/users", headers=admin_headers)
    assert listing.status_code == 200
    assert all("password_hash" not in item and "verify_token" not in item for item in listing.json())
    assert client.get("/admin/users").status_code == 401
    student_id = next(item["id"] for item in listing.json() if item["email"] == student["email"])
    updated = client.patch(f"/admin/users/{student_id}", headers=admin_headers, json={"status": "Disabled"})
    assert updated.status_code == 200 and updated.json()["status"] == "Disabled"
    assert client.get("/admin/audit", headers=admin_headers).json()
    db.close()
    db_generator.close()
