"""Opportunities router (FR-006, FR-007, FR-008, FR-009, BR-001, BR-002)."""
import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Application, Opportunity, OpportunitySkill, User
from app.rules import check_application_eligibility

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class CreateOpportunityRequest(BaseModel):
    title: str
    description: str
    domain: str
    duration: Optional[str] = "3 months"
    capacity: int = Field(ge=1, description="Capacity must be an integer >= 1 (BVA decision 0.4-1)")
    deadline: Optional[dt.date] = None
    required_skills: List[str] = []


class ApplyRequest(BaseModel):
    motivation: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_opportunity(
    req: CreateOpportunityRequest,
    current_user: User = Depends(require_role("Faculty")),
    db: Session = Depends(get_db),
):
    opp = Opportunity(
        faculty_id=current_user.id,
        title=req.title,
        description=req.description,
        domain=req.domain,
        duration=req.duration,
        capacity=req.capacity,
        deadline=req.deadline,
        status="Draft",
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)

    for skill in req.required_skills:
        os_rec = OpportunitySkill(opportunity_id=opp.id, skill_name=skill)
        db.add(os_rec)
    db.commit()

    return {"id": opp.id, "title": opp.title, "status": opp.status, "capacity": opp.capacity}


@router.post("/{id}/state/{action}")
def change_opportunity_state(
    id: int,
    action: str,
    current_user: User = Depends(require_role("Faculty")),
    db: Session = Depends(get_db),
):
    opp = db.query(Opportunity).filter(Opportunity.id == id, Opportunity.faculty_id == current_user.id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    state_map = {"publish": "Published", "close": "Closed", "archive": "Archived"}
    if action not in state_map:
        raise HTTPException(status_code=400, detail="Invalid action")

    opp.status = state_map[action]
    if action == "publish":
        opp.published_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return {"id": opp.id, "status": opp.status}


@router.get("")
def list_opportunities(
    domain: Optional[str] = None,
    available: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Opportunity).filter(Opportunity.status == "Published")
    if domain:
        query = query.filter(Opportunity.domain.ilike(f"%{domain}%"))
    opps = query.all()
    return [
        {
            "id": o.id,
            "title": o.title,
            "domain": o.domain,
            "capacity": o.capacity,
            "status": o.status,
            "deadline": str(o.deadline) if o.deadline else None,
        }
        for o in opps
    ]


@router.get("/{id}")
def get_opportunity(id: int, db: Session = Depends(get_db)):
    opp = db.query(Opportunity).filter(Opportunity.id == id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {
        "id": opp.id,
        "title": opp.title,
        "description": opp.description,
        "domain": opp.domain,
        "capacity": opp.capacity,
        "status": opp.status,
        "deadline": str(opp.deadline) if opp.deadline else None,
        "required_skills": [s.skill_name for s in opp.required_skills],
    }


@router.post("/{id}/apply", status_code=status.HTTP_201_CREATED)
def apply_opportunity(
    id: int,
    req: ApplyRequest,
    current_user: User = Depends(require_role("Student")),
    db: Session = Depends(get_db),
):
    opp = db.query(Opportunity).filter(Opportunity.id == id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Check if already applied (withdrawn apps ignored per FR-009/BR-002)
    active_app = (
        db.query(Application)
        .filter(
            Application.opportunity_id == id,
            Application.student_id == current_user.id,
            Application.status != "Withdrawn",
        )
        .first()
    )

    today = dt.date.today()
    allowed, reason = check_application_eligibility(
        opp_status=opp.status,
        deadline=opp.deadline,
        today=today,
        already_applied=active_app is not None,
    )

    if not allowed:
        raise HTTPException(status_code=400, detail=reason)

    application = Application(
        student_id=current_user.id,
        opportunity_id=opp.id,
        motivation=req.motivation,
        status="Submitted",
        req_version=opp.requirements_version,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return {"id": application.id, "status": application.status, "message": "Application submitted"}

