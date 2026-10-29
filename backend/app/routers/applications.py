from datetime import date, datetime, timedelta, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require_roles
from ..models import Application, AuditLog, FacultyProfile, Milestone, Opportunity, OpportunityVersion, Project, ProjectMember, StudentProfile, User
from ..rules import check_application_eligibility
from ..schemas import ApplyIn, DecideIn

router = APIRouter(tags=["applications"])


def _serialize(application: Application) -> dict:
    return {"id": application.id, "student_id": application.student_id,
            "opportunity_id": application.opportunity_id, "motivation": application.motivation,
            "req_version": application.req_version, "status": application.status,
            "faculty_comment": application.faculty_comment,
            "submitted_at": application.submitted_at.isoformat(),
            "decided_at": application.decided_at.isoformat() if application.decided_at else None}


@router.post("/opportunities/{opportunity_id}/apply", status_code=status.HTTP_201_CREATED)
def apply(opportunity_id: int, body: ApplyIn, user: User = Depends(require_roles("Student")),
          db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    existing = db.query(Application).filter(Application.student_id == user.id,
        Application.opportunity_id == opportunity_id, Application.status != "Withdrawn").first()
    allowed, reason = check_application_eligibility(opportunity.status, opportunity.deadline, date.today(), existing is not None)
    if not allowed:
        raise HTTPException(status_code=409, detail=reason)
    profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
    snapshot = {"name": user.name,
                "skills": [item.skill_name for item in profile.skills] if profile else [],
                "interests": [item.interest for item in profile.interests] if profile else [],
                "research_experience": profile.research_experience if profile else ""}
    application = Application(student_id=user.id, opportunity_id=opportunity.id,
        motivation=body.motivation, profile_snapshot=json.dumps(snapshot),
        req_version=opportunity.requirements_version, status="Submitted")
    db.add(application)
    try:
        db.flush()
        db.add(AuditLog(actor_user_id=user.id, entity_type="application", entity_id=application.id,
                        action="submitted", detail={"opportunity_id": opportunity.id}))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An active application already exists") from None
    db.refresh(application)
    return _serialize(application)


@router.get("/applications/mine")
def my_applications(user: User = Depends(require_roles("Student")), db: Session = Depends(get_db)):
    rows = db.query(Application, Opportunity).join(Opportunity, Application.opportunity_id == Opportunity.id).filter(
        Application.student_id == user.id).order_by(Application.submitted_at.desc()).all()
    return [{**_serialize(application), "opportunity_title": opportunity.title,
             "domain": opportunity.domain} for application, opportunity in rows]


@router.post("/applications/{application_id}/withdraw")
def withdraw(application_id: int, user: User = Depends(require_roles("Student")), db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.student_id != user.id:
        raise HTTPException(status_code=403, detail="Only the applicant can withdraw")
    if application.status not in {"Submitted", "Shortlisted"}:
        raise HTTPException(status_code=409, detail="Application cannot be withdrawn in its current state")
    application.status = "Withdrawn"
    application.decided_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=user.id, entity_type="application", entity_id=application.id,
                    action="withdrawn", detail={}))
    db.commit()
    return _serialize(application)


@router.get("/opportunities/{opportunity_id}/applications")
def opportunity_applications(opportunity_id: int, user: User = Depends(require_roles("Faculty")),
                              db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opportunity.faculty_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owning faculty member can review applications")
    items = db.query(Application).filter_by(opportunity_id=opportunity_id).order_by(Application.submitted_at).all()
    return [_serialize(item) | {"profile_snapshot": json.loads(item.profile_snapshot or "{}")}
            for item in items]


@router.post("/applications/{application_id}/decide")
def decide(application_id: int, body: DecideIn, user: User = Depends(require_roles("Faculty")),
           db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    opportunity = db.query(Opportunity).filter(Opportunity.id == application.opportunity_id).with_for_update().first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opportunity.faculty_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owning faculty member can decide")
    if application.status not in {"Submitted", "Shortlisted"}:
        raise HTTPException(status_code=409, detail="Application has already been decided")
    if body.status == "Accepted":
        accepted = db.query(func.count(Application.id)).filter(
            Application.opportunity_id == opportunity.id, Application.status == "Accepted").scalar() or 0
        if accepted >= opportunity.capacity:
            raise HTTPException(status_code=409, detail="Opportunity capacity has been reached")

        # Automatically link or create Project and enroll members
        project = db.query(Project).filter(Project.opportunity_id == opportunity.id).first()
        if not project:
            project = Project(
                opportunity_id=opportunity.id,
                title=f"{opportunity.title} Lab",
                description=opportunity.description[:500] if opportunity.description else "",
                domain=opportunity.domain or "Research",
                status="Active",
            )
            db.add(project)
            db.flush()

        faculty_member = db.query(ProjectMember).filter(ProjectMember.project_id == project.id, ProjectMember.user_id == opportunity.faculty_id).first()
        if not faculty_member:
            db.add(ProjectMember(project_id=project.id, user_id=opportunity.faculty_id, role_in_project="Lead"))
            db.flush()

        student_member = db.query(ProjectMember).filter(ProjectMember.project_id == project.id, ProjectMember.user_id == application.student_id).first()
        if not student_member:
            db.add(ProjectMember(project_id=project.id, user_id=application.student_id, role_in_project="Member"))
            db.flush()

        has_milestone = db.query(Milestone).filter(Milestone.project_id == project.id).first()
        if not has_milestone:
            db.add(Milestone(
                project_id=project.id,
                description=f"Initial onboarding and literature review for {opportunity.title}",
                target_date=datetime.now(timezone.utc).date() + timedelta(days=14),
                status="In Progress",
            ))
            db.flush()

    application.status = body.status
    application.faculty_comment = body.faculty_comment
    application.decided_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=user.id, entity_type="application", entity_id=application.id,
                    action=body.status.casefold(), detail={"opportunity_id": opportunity.id}))
    db.commit()
    return _serialize(application)
