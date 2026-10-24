"""Dependencies for FastAPI routes: database, auth, and role checks (NFR-006, NFR-007)."""
from typing import List, Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import verify_token_get_user_id


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer token and retrieve active user (NFR-006)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization[len("Bearer ") :].strip()
    user_id = verify_token_get_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
        )
    return user


def require_role(*allowed_roles: str):
    """Enforce server-side role check (NFR-007, FR-003)."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: required role in {allowed_roles}, your role is {current_user.role}",
            )
        return current_user

    return role_checker
