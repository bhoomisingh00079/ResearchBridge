"""Projects Router (FR-013, FR-014, FR-018, FR-020)."""
import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Application, Milestone, Project, ProjectMember, User

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    domain: Optional[str] = "AI"
    application_ids: List[int] = []


class CreateMilestoneRequest(BaseModel):
    description: str
    target_date: dt.date


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    req: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = Project(
        title=req.title,
        description=req.description,
        domain=req.domain,
        status="Active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Add creator as Lead
    creator_member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role_in_project="Lead",
    )
    db.add(creator_member)

    # Add accepted applicant students as Members
    for app_id in req.application_ids:
        app = db.query(Application).filter(Application.id == app_id).first()
        if app:
            m = ProjectMember(
                project_id=project.id,
                user_id=app.student_id,
                role_in_project="Member",
            )
            db.add(m)

    db.commit()
    return {"project_id": project.id, "title": project.title, "status": project.status}


@router.get("")
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = db.query(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()
    project_ids = [m.project_id for m in memberships]
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    return [{"id": p.id, "title": p.title, "domain": p.domain, "status": p.status} for p in projects]


@router.get("/{id}")
def get_project(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not is_member and current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Member access required")

    members = db.query(ProjectMember).filter(ProjectMember.project_id == id).all()
    return {
        "id": project.id,
        "title": project.title,
        "domain": project.domain,
        "status": project.status,
        "members": [{"user_id": m.user_id, "role": m.role_in_project} for m in members],
    }


@router.post("/{id}/milestones", status_code=status.HTTP_201_CREATED)
def create_milestone(
    id: int,
    req: CreateMilestoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    milestone = Milestone(
        project_id=id,
        description=req.description,
        target_date=req.target_date,
        status="Not Started",
        last_activity_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return {"id": milestone.id, "description": milestone.description, "target_date": str(milestone.target_date)}


@router.get("/{id}/milestones/overdue")
def get_overdue_milestones(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = dt.date.today()
    overdue = (
        db.query(Milestone)
        .filter(
            Milestone.project_id == id,
            Milestone.status != "Completed",
            Milestone.target_date < today,
        )
        .all()
    )
    return [
        {
            "id": m.id,
            "description": m.description,
            "target_date": str(m.target_date),
            "status": m.status,
        }
        for m in overdue
    ]

