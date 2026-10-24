"""
BLACK-BOX TESTING - Equivalence Partitioning (EP) + Boundary Value Analysis (BVA)
Target: the platform REST API (no knowledge of the code, only the SRS rules).
Run:  pytest -v test_blackbox_ep_bva.py
"""
import os, sys, datetime as dt

os.environ["DATABASE_URL"] = "sqlite:///./bb_test.db"
if os.path.exists("bb_test.db"):
    try:
        os.remove("bb_test.db")
    except OSError:
        pass

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from fastapi.testclient import TestClient
import main
from app.db import SessionLocal, init_db
from app.models import User

init_db()
c = TestClient(main.app)
_n = {"i": 0}


def reg(email=None, password="Password123", role="Student", name="T"):
    _n["i"] += 1
    return c.post(
        "/auth/register",
        json={
            "email": email if email is not None else f"u{_n['i']}@ves.ac.in",
            "password": password,
            "name": name,
            "role": role,
        },
    )


def login_hdr(role):
    r = reg(role=role)
    c.post(f"/auth/verify/{r.json()['dev_verify_token']}")
    email = SessionLocal().query(User).order_by(User.id.desc()).first().email
    return {
        "Authorization": "Bearer "
        + c.post("/auth/login", json={"email": email, "password": "Password123"}).json()["token"]
    }


# ---- 1. Password length (FR-001, min 8).  Partitions: <8 invalid | >=8 valid.  BVA: 0,7,8,9
@pytest.mark.parametrize(
    "pw,code",
    [("", 422), ("a" * 7, 422), ("a" * 8, 201), ("a" * 9, 201), ("a" * 64, 201)],
    ids=[
        "len0-invalid",
        "len7-below-boundary",
        "len8-boundary",
        "len9-above-boundary",
        "len64-valid-large",
    ],
)
def test_password_length(pw, code):
    assert reg(password=pw).status_code == code


# ---- 2. Email (FR-001 institutional domain).  Partitions: valid domain | other domain | malformed | empty
@pytest.mark.parametrize(
    "email,code",
    [
        ("ok1@ves.ac.in", 201),
        ("OK2@VES.AC.IN", 201),
        ("x@gmail.com", 400),
        ("no-at-sign", 400),
        ("", 400),
        ("a@ves.ac.in.evil.com", 400),
    ],
    ids=[
        "valid",
        "valid-uppercase",
        "other-domain",
        "malformed",
        "empty",
        "lookalike-domain",
    ],
)
def test_email_partitions(email, code):
    assert reg(email=email).status_code == code


def test_duplicate_registration_is_generic_error():  # FR-002 / no account enumeration
    reg(email="dup@ves.ac.in")
    r = reg(email="dup@ves.ac.in")
    assert r.status_code == 400 and r.json()["detail"] == "Registration failed"


# ---- 3. Role at registration.  Partitions: Student/Faculty valid | Admin/Coordinator/garbage invalid (cannot self-assign)
@pytest.mark.parametrize(
    "role,code",
    [
        ("Student", 201),
        ("Faculty", 201),
        ("Administrator", 400),
        ("Coordinator", 400),
        ("root", 400),
    ],
)
def test_role_partitions(role, code):
    assert reg(role=role).status_code == code


# ---- 4. Opportunity capacity (FR-006, positive integer).  BVA: -1,0,1,2
FAC = None


def _fac():
    global FAC
    FAC = FAC or login_hdr("Faculty")
    return FAC


@pytest.mark.parametrize(
    "cap,code",
    [(-1, 422), (0, 422), (1, 201), (2, 201), (100, 201)],
    ids=["-1", "0-below-boundary", "1-boundary", "2", "100"],
)
def test_capacity_bva(cap, code):
    r = c.post(
        "/opportunities",
        json={"title": "t", "description": "d", "domain": "AI", "capacity": cap},
        headers=_fac(),
    )
    assert r.status_code == code


# ---- 5. Milestone overdue boundary (FR-020).  target = today-1 (overdue) | today | today+1  (not overdue)
@pytest.mark.parametrize(
    "delta,overdue",
    [(-1, True), (0, False), (1, False)],
    ids=["yesterday", "today", "tomorrow"],
)
def test_overdue_boundary(delta, overdue):
    f, s = _fac(), login_hdr("Student")
    o = c.post(
        "/opportunities",
        json={"title": "t", "description": "d", "domain": "AI", "capacity": 2},
        headers=f,
    ).json()
    c.post(f"/opportunities/{o['id']}/state/publish", headers=f)
    a = c.post(
        f"/opportunities/{o['id']}/apply", json={"motivation": "m"}, headers=s
    ).json()
    c.post(f"/applications/{a['id']}/decide", json={"status": "Accepted"}, headers=f)
    pid = c.post(
        "/projects", json={"title": "p", "application_ids": [a["id"]]}, headers=f
    ).json()["project_id"]
    c.post(
        f"/projects/{pid}/milestones",
        json={
            "description": "m",
            "target_date": str(dt.date.today() + dt.timedelta(days=delta)),
        },
        headers=f,
    )
    assert (len(c.get(f"/projects/{pid}/milestones/overdue", headers=s).json()) == 1) is overdue


# ---- 6. Milestone status (FR-019).  Partitions: 4 valid values | anything else invalid
@pytest.mark.parametrize(
    "status,code",
    [
        ("Not Started", 200),
        ("In Progress", 200),
        ("Completed", 200),
        ("Blocked", 200),
        ("Done", 400),
        ("", 400),
    ],
)
def test_milestone_status_partitions(status, code):
    f, s = _fac(), login_hdr("Student")
    o = c.post(
        "/opportunities",
        json={"title": "t", "description": "d", "domain": "AI", "capacity": 1},
        headers=f,
    ).json()
    c.post(f"/opportunities/{o['id']}/state/publish", headers=f)
    a = c.post(
        f"/opportunities/{o['id']}/apply", json={"motivation": "m"}, headers=s
    ).json()
    c.post(f"/applications/{a['id']}/decide", json={"status": "Accepted"}, headers=f)
    pid = c.post(
        "/projects", json={"title": "p", "application_ids": [a["id"]]}, headers=f
    ).json()["project_id"]
    m = c.post(
        f"/projects/{pid}/milestones",
        json={"description": "m", "target_date": "2030-01-01"},
        headers=f,
    ).json()
    assert (
        c.patch(f"/milestones/{m['id']}", json={"status": status}, headers=s).status_code
        == code
    )

