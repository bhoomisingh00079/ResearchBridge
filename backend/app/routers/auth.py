"""Authentication Router (FR-001, FR-002, FR-003, NFR-005, NFR-006)."""
import os
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.security import hash_password, verify_password, create_token_for_user

router = APIRouter(prefix="/auth", tags=["auth"])

ALLOWED_DOMAINS = [
    d.strip().lower()
    for d in os.environ.get("ALLOWED_DOMAINS", "ves.ac.in").split(",")
]


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = "User"
    role: str = "Student"


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()

    # FR-001: Email format and institutional domain validation
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Registration failed: invalid email")

    domain = email.split("@")[-1]
    # Check institutional domain (and reject look-alikes like ves.ac.in.evil.com)
    if domain not in ALLOWED_DOMAINS:
        raise HTTPException(status_code=400, detail="Registration failed: institutional email required")

    # FR-003: Self-registration limited to Student and Faculty
    if req.role not in ("Student", "Faculty"):
        raise HTTPException(status_code=400, detail="Registration failed: role not permitted for self-registration")

    # FR-002: Duplicate registration returns generic failure (no account enumeration)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Registration failed")

    dev_token = secrets.token_hex(16)
    user = User(
        email=email,
        password_hash=hash_password(req.password),
        name=req.name,
        role=req.role,
        status="Pending Verification",
        verify_token=dev_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Registration successful. Please verify institutional email.",
        "dev_verify_token": dev_token,
    }


@router.post("/verify/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verify_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user.status = "Active"
    user.verify_token = None
    db.commit()
    return {"message": "Account verified successfully"}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status != "Active":
        raise HTTPException(status_code=401, detail="Account not active")

    token = create_token_for_user(user.id)
    return {
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
    }

