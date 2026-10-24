"""Router for Agent endpoints (PLAN Section 4.7: FR-025 to FR-031, FR-035)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import (
    AgentRecommendation,
    Opportunity,
    Project,
    ProjectMember,
    Resource,
    StudentInterest,
    StudentProfile,
    StudentSkill,
    User,
)
from app.services.agent_client import agent_client, persist_recommendations
from app.jobs.agent_scan import run_agent_scans

router = APIRouter(prefix="/agent", tags=["agent"])


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    reference_entity: str
    reason_text: str
    score: int
    status: str


class DismissResponse(BaseModel):
    success: bool
    message: str


# ─── GET /agent/recommendations ──────────────────────────────────────


@router.get("/recommendations", response_model=List[RecommendationOut])
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve active recommendations for current user (FR-025, FR-026, FR-031).

    If student has no recommendations cached, runs live match on published opportunities.
    Gracefully handles agent downtime (NFR-002).
    Dismissed recommendations are excluded (FR-031).
    """
    if current_user.role == "Student":
        # Get active cached recommendations
        recs = (
            db.query(AgentRecommendation)
            .filter(
                AgentRecommendation.user_id == current_user.id,
                AgentRecommendation.status == "Active",
            )
            .order_by(AgentRecommendation.score.desc())
            .all()
        )
        if recs:
            return recs

        # Fetch live if none cached
        profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == current_user.id)
            .first()
        )
        skills = [s.skill_name for s in profile.skills] if profile and profile.skills else []
        interests = [i.interest for i in profile.interests] if profile and profile.interests else []

        opportunities = (
            db.query(Opportunity)
            .filter(Opportunity.status == "Published")
            .all()
        )
        opp_slices = [
            {
                "id": o.id,
                "domain": o.domain,
                "required_skills": [s.skill_name for s in o.required_skills],
            }
            for o in opportunities
        ]

        res = agent_client.match_opportunities(skills, interests, opp_slices)
        if res.get("available") and res.get("items"):
            recs = persist_recommendations(
                db, current_user.id, "opportunity", res["items"], "opportunity_id"
            )
            return recs

        return []

    # Non-student roles (Faculty, etc.)
    return (
        db.query(AgentRecommendation)
        .filter(
            AgentRecommendation.user_id == current_user.id,
            AgentRecommendation.status == "Active",
        )
        .order_by(AgentRecommendation.score.desc())
        .all()
    )


# ─── POST /agent/recommendations/{id}/dismiss ────────────────────────


@router.post("/recommendations/{id}/dismiss", response_model=DismissResponse)
def dismiss_recommendation(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss a recommendation so it is never re-created or re-shown (FR-031)."""
    rec = (
        db.query(AgentRecommendation)
        .filter(
            AgentRecommendation.id == id,
            AgentRecommendation.user_id == current_user.id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )

    rec.status = "Dismissed"
    db.commit()
    return DismissResponse(success=True, message="Recommendation dismissed")


# ─── GET /agent/projects/{id}/collaborators ─────────────────────────


@router.get("/projects/{id}/collaborators")
def get_project_collaborators(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find collaborator candidates for a project (FR-027).

    Caller must be project lead or faculty (Section 4.7).
    """
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )
    if current_user.role != "Faculty" and (not is_member or is_member.role_in_project != "Lead"):
        raise HTTPException(status_code=403, detail="Only project leads and faculty can request collaborator suggestions")

    # Team skills
    members = db.query(ProjectMember).filter(ProjectMember.project_id == id).all()
    team_user_ids = {m.user_id for m in members}
    current_team_skills = set()
    for uid in team_user_ids:
        sp = db.query(StudentProfile).filter(StudentProfile.user_id == uid).first()
        if sp and sp.skills:
            current_team_skills.update([s.skill_name for s in sp.skills])

    # Candidate students (not already in team)
    candidates = []
    student_users = db.query(User).filter(User.role == "Student", User.status == "Active").all()
    for su in student_users:
        if su.id not in team_user_ids:
            sp = db.query(StudentProfile).filter(StudentProfile.user_id == su.id).first()
            if sp:
                candidates.append({
                    "id": su.id,
                    "skills": [s.skill_name for s in sp.skills],
                    "interests": [i.interest for i in sp.interests],
                })

    # Required skills from project or linked opportunity
    required_skills = []
    if project.opportunity_id:
        opp = db.query(Opportunity).filter(Opportunity.id == project.opportunity_id).first()
        if opp and opp.required_skills:
            required_skills = [s.skill_name for s in opp.required_skills]

    res = agent_client.match_collaborators(
        project_id=project.id,
        project_domain=project.domain,
        project_required_skills=required_skills,
        current_team_skills=list(current_team_skills),
        candidates=candidates,
    )

    if res.get("available") and res.get("items"):
        recs = persist_recommendations(
            db, current_user.id, "collaborator", res["items"], "user_id"
        )
        return {"available": True, "items": res["items"]}

    return {"available": res.get("available", False), "items": []}


# ─── GET /agent/projects/{id}/resources ──────────────────────────────


@router.get("/projects/{id}/resources")
def get_project_resources(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suggest platform-indexed resources for a project (FR-028)."""
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Member check
    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )
    if not is_member and current_user.role != "Faculty":
        raise HTTPException(status_code=403, detail="Member access required")

    required_skills = []
    if project.opportunity_id:
        opp = db.query(Opportunity).filter(Opportunity.id == project.opportunity_id).first()
        if opp and opp.required_skills:
            required_skills = [s.skill_name for s in opp.required_skills]

    resources = db.query(Resource).all()
    res_slices = [
        {
            "id": r.id,
            "title": r.title,
            "type": r.type,
            "keywords": [r.title.lower(), project.domain.lower()],
        }
        for r in resources
    ]

    res = agent_client.match_resources(
        project_id=project.id,
        project_domain=project.domain,
        project_required_skills=required_skills,
        resources=res_slices,
    )

    if res.get("available") and res.get("items"):
        persist_recommendations(
            db, current_user.id, "resource", res["items"], "resource_id"
        )
        return {"available": True, "items": res["items"]}

    return {"available": res.get("available", False), "items": []}


# ─── GET /agent/alerts ───────────────────────────────────────────────


@router.get("/alerts")
def get_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve active alerts for current user (FR-029, FR-035)."""
    alerts = (
        db.query(AgentRecommendation)
        .filter(
            AgentRecommendation.user_id == current_user.id,
            AgentRecommendation.type == "alert",
            AgentRecommendation.status == "Active",
        )
        .order_by(AgentRecommendation.score.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "reference_entity": a.reference_entity,
            "reason_text": a.reason_text,
            "score": a.score,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


# ─── POST /agent/scan ────────────────────────────────────────────────


@router.post("/scan")
def trigger_agent_scan(
    current_user: User = Depends(require_role("Administrator", "Faculty")),
    db: Session = Depends(get_db),
):
    """Trigger an on-demand agent progress scan."""
    result = run_agent_scans(db)
    return {"success": True, "details": result}
