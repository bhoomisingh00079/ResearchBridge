"""Milestones Router (FR-019)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Milestone, User

router = APIRouter(prefix="/milestones", tags=["milestones"])

VALID_STATUSES = {"Not Started", "In Progress", "Completed", "Blocked"}


class UpdateMilestoneRequest(BaseModel):
    status: str


@router.patch("/{id}")
def update_milestone_status(
    id: int,
    req: UpdateMilestoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid milestone status. Must be one of {VALID_STATUSES}",
        )

    milestone = db.query(Milestone).filter(Milestone.id == id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone.status = req.status
    db.commit()
    db.refresh(milestone)
    return {"id": milestone.id, "status": milestone.status}

