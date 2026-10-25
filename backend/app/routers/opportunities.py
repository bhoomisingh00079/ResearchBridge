from datetime import datetime, timezone
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import optional_user, require_roles
from ..models import Application, Opportunity, OpportunitySkill, OpportunityVersion, User
from ..schemas import OpportunityIn

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def accepted_count(db: Session, opportunity_id: int) -> int:
    return db.query(func.count(Application.id)).filter(
        Application.opportunity_id == opportunity_id, Application.status == "Accepted").scalar() or 0


def serialize(opportunity: Opportunity, db: Session) -> dict:
    return {
        "id": opportunity.id, "faculty_id": opportunity.faculty_id, "title": opportunity.title,
        "description": opportunity.description, "domain": opportunity.domain,
        "duration": opportunity.duration, "capacity": opportunity.capacity,
        "status": opportunity.status, "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
        "published_at": opportunity.published_at.isoformat() if opportunity.published_at else None,
        "requirements_version": opportunity.requirements_version,
        "required_skills": [item.skill_name for item in opportunity.required_skills],
        "available_places": max(0, opportunity.capacity - accepted_count(db, opportunity.id)),
    }


def version_snapshot(opportunity: Opportunity) -> dict:
    return {"title": opportunity.title, "description": opportunity.description,
            "domain": opportunity.domain, "duration": opportunity.duration,
            "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
            "required_skills": [item.skill_name for item in opportunity.required_skills]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_opportunity(body: OpportunityIn, user: User = Depends(require_roles("Faculty")),
                       db: Session = Depends(get_db)):
    values = body.model_dump()
    skills = values.pop("required_skills")
    opportunity = Opportunity(faculty_id=user.id, **values)
    db.add(opportunity)
    db.flush()
    opportunity.required_skills.extend(OpportunitySkill(skill_name=name) for name in skills)
    db.add(OpportunityVersion(opportunity_id=opportunity.id, version=1,
                              snapshot=version_snapshot(opportunity)))
    db.commit()
    db.refresh(opportunity)
    return serialize(opportunity, db)


@router.put("/{opportunity_id}")
def update_opportunity(opportunity_id: int, body: OpportunityIn,
                       user: User = Depends(require_roles("Faculty")), db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opportunity.faculty_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owning faculty member can edit this opportunity")
    values = body.model_dump()
    skills = values.pop("required_skills")
    for key, value in values.items():
        setattr(opportunity, key, value)
    opportunity.required_skills.clear()
    opportunity.required_skills.extend(OpportunitySkill(skill_name=name) for name in skills)
    opportunity.requirements_version += 1
    db.add(OpportunityVersion(opportunity_id=opportunity.id, version=opportunity.requirements_version,
                              snapshot=version_snapshot(opportunity)))
    db.commit()
    db.refresh(opportunity)
    return serialize(opportunity, db)


@router.post("/{opportunity_id}/state/{action}")
def change_opportunity_state(opportunity_id: int, action: Literal["publish", "close", "archive"],
                             user: User = Depends(require_roles("Faculty")), db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opportunity.faculty_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owning faculty member can change this opportunity")
    transitions = {"publish": ("Draft", "Published"), "close": ("Published", "Closed"),
                   "archive": (("Draft", "Published", "Closed"), "Archived")}
    allowed_from, target = transitions[action]
    if opportunity.status not in ((allowed_from,) if isinstance(allowed_from, str) else allowed_from):
        raise HTTPException(status_code=409, detail=f"Cannot {action} an opportunity in state {opportunity.status}")
    opportunity.status = target
    if target == "Published":
        opportunity.published_at = datetime.now(timezone.utc)
    db.commit()
    return serialize(opportunity, db)


@router.get("")
def search_opportunities(domain: str | None = None, skill: str | None = None,
                         duration: str | None = None, available: bool | None = None,
                         q: str | None = None, offset: int = Query(0, ge=0),
                         limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Opportunity).filter(Opportunity.status == "Published")
    if domain:
        query = query.filter(func.lower(Opportunity.domain) == domain.strip().casefold())
    if duration:
        query = query.filter(func.lower(Opportunity.duration).contains(duration.strip().casefold()))
    if q:
        text = f"%{q.strip()[:120]}%"
        query = query.filter((Opportunity.title.ilike(text)) | (Opportunity.description.ilike(text)))
    if skill:
        term = skill.strip().casefold()
        query = query.filter(Opportunity.required_skills.any(OpportunitySkill.skill_name.ilike(f"%{term}%")))
    accepted = select(func.count(Application.id)).where(
        Application.opportunity_id == Opportunity.id, Application.status == "Accepted").scalar_subquery()
    if available is True:
        query = query.filter(accepted < Opportunity.capacity)
    elif available is False:
        query = query.filter(accepted >= Opportunity.capacity)
    items = query.order_by(Opportunity.published_at.desc(), Opportunity.id.desc()).offset(offset).limit(limit).all()
    results = [serialize(item, db) for item in items]
    return {"items": results, "offset": offset, "limit": limit}


@router.get("/mine")
def my_opportunities(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                    user: User = Depends(require_roles("Faculty")), db: Session = Depends(get_db)):
    items = db.query(Opportunity).filter(Opportunity.faculty_id == user.id).order_by(
        Opportunity.created_at.desc(), Opportunity.id.desc()).offset(offset).limit(limit).all()
    return {"items": [serialize(item, db) for item in items], "offset": offset, "limit": limit}


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: int, user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.status == "Archived":
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opportunity.status != "Published" and not (user and user.id == opportunity.faculty_id):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return serialize(opportunity, db)
