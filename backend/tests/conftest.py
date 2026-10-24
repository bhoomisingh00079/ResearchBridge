"""Shared test fixtures for the backend test suite."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./test_backend.db"
os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["AGENT_SERVICE_TOKEN"] = "dev-secret-token"

from app.db import Base, get_db
from app.models import User, StudentProfile, StudentSkill, StudentInterest, Opportunity, OpportunitySkill, Application, Project, ProjectMember, Milestone
from app.security import hash_password, create_token_for_user
from main import app

# Test database engine
engine = create_engine("sqlite:///./test_backend.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_backend.db"):
        try:
            os.remove("./test_backend.db")
        except OSError:
            pass


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: session

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def make_user(db, email, role, name="Test User", status="Active"):
    u = User(
        email=email,
        password_hash=hash_password("Password123"),
        name=name,
        role=role,
        status=status,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_auth_header(user):
    token = create_token_for_user(user.id)
    return {"Authorization": f"Bearer {token}"}
