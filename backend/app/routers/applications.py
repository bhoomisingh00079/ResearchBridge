"""Applications Router (FR-010, FR-011, FR-012, BR-003)."""
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Application, Opportunity, User

router = APIRouter(prefix="/applications", tags=["applications"])


class DecideRequest(BaseModel):
    status: str
    comment: Optional[str] = None


@router.get("/mine")
def get_my_applications(
    current_user: User = Depends(require_role("Student")),
    db: Session = Depends(get_db),
):
    apps = db.query(Application).filter(Application.student_id == current_user.id).all()
    return [
        {
            "id": a.id,
            "opportunity_id": a.opportunity_id,
            "opportunity_title": a.opportunity.title if a.opportunity else "Unknown",
            "status": a.status,
            "submitted_at": str(a.submitted_at),
            "faculty_comment": a.faculty_comment,
        }
        for a in apps
    ]


@router.post("/{id}/withdraw")
def withdraw_application(
    id: int,
    current_user: User = Depends(require_role("Student")),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == id, Application.student_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status in ("Accepted", "Rejected", "Withdrawn"):
        raise HTTPException(status_code=400, detail="Cannot withdraw finalized application")

    app.status = "Withdrawn"
    db.commit()
    return {"id": app.id, "status": "Withdrawn"}


@router.post("/{id}/decide")
def decide_application(
    id: int,
    req: DecideRequest,
    current_user: User = Depends(require_role("Faculty")),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if req.status not in ("Shortlisted", "Accepted", "Rejected"):
        raise HTTPException(status_code=400, detail="Invalid decision status")

    app.status = req.status
    app.faculty_comment = req.comment
    app.decided_at = dt.datetime.now(dt.timezone.utc)
    db.commit()

    return {"id": app.id, "status": app.status}

