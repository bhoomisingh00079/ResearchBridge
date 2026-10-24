"""Dashboards router (Task C5: FR-032, FR-033, FR-034)."""
from datetime import date
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import (
    AgentRecommendation,
    Application,
    Milestone,
    Opportunity,
    Project,
    ProjectMember,
    StudentProfile,
    User,
)

router = APIRouter(prefix="/dashboard", tags=["dashboards"])


# ─── GET /dashboard/student (FR-032) ─────────────────────────────────


@router.get("/student")
def get_student_dashboard(
    current_user: User = Depends(require_role("Student")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Student dashboard (FR-032).

    Contains:
      - Active applications + status
      - Enrolled projects + their milestones
      - Active recommendations count (advisory panel loads independently per NFR-002, 3.1.1)
    """
    # 1. Applications
    applications = (
        db.query(Application)
        .filter(Application.student_id == current_user.id)
        .all()
    )
    apps_data = [
        {
            "id": app.id,
            "opportunity_id": app.opportunity_id,
            "opportunity_title": app.opportunity.title if app.opportunity else "Unknown",
            "status": app.status,
            "submitted_at": app.submitted_at.isoformat(),
            "faculty_comment": app.faculty_comment,
        }
        for app in applications
    ]

    # 2. Projects & Milestones
    memberships = (
        db.query(ProjectMember)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    )
    projects_data = []
    for m in memberships:
        p = m.project
        if p and p.status == "Active":
            milestones = (
                db.query(Milestone)
                .filter(Milestone.project_id == p.id)
                .order_by(Milestone.target_date.asc())
                .all()
            )
            projects_data.append({
                "project_id": p.id,
                "title": p.title,
                "domain": p.domain,
                "role_in_project": m.role_in_project,
                "milestones": [
                    {
                        "id": ms.id,
                        "description": ms.description,
                        "target_date": str(ms.target_date),
                        "status": ms.status,
                    }
                    for ms in milestones
                ],
            })

    # 3. Recommendations count
    rec_count = (
        db.query(AgentRecommendation)
        .filter(
            AgentRecommendation.user_id == current_user.id,
            AgentRecommendation.status == "Active",
        )
        .count()
    )

    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
        },
        "applications": apps_data,
        "projects": projects_data,
        "recommendations_count": rec_count,
        "agent_panel_url": "/agent/recommendations",
    }


# ─── GET /dashboard/faculty (FR-033) ─────────────────────────────────


@router.get("/faculty")
def get_faculty_dashboard(
    current_user: User = Depends(require_role("Faculty")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Faculty dashboard (FR-033).

    Contains:
      - Pending applicant count and list
      - Active projects
      - Overdue milestones count across own projects
      - Agent alerts (low applications, nearing deadline, etc.)
    """
    today = date.today()

    # 1. Opportunities & Pending Applicants
    opportunities = (
        db.query(Opportunity)
        .filter(Opportunity.faculty_id == current_user.id)
        .all()
    )
    opp_ids = [o.id for o in opportunities]

    pending_apps = (
        db.query(Application)
        .filter(
            Application.opportunity_id.in_(opp_ids),
            Application.status.in_(["Submitted", "Shortlisted"]),
        )
        .all()
    ) if opp_ids else []

    pending_apps_data = [
        {
            "application_id": a.id,
            "opportunity_id": a.opportunity_id,
            "opportunity_title": a.opportunity.title if a.opportunity else "Unknown",
            "student_id": a.student_id,
            "student_name": a.student.name if a.student else "Student",
            "status": a.status,
            "submitted_at": a.submitted_at.isoformat(),
        }
        for a in pending_apps
    ]

    # 2. Faculty's projects
    # A faculty owns projects linked to their opportunities or where they are Lead
    projects = (
        db.query(Project)
        .filter(
            (Project.opportunity_id.in_(opp_ids))
            | (
                Project.id.in_(
                    db.query(ProjectMember.project_id).filter(
                        ProjectMember.user_id == current_user.id
                    )
                )
            )
        )
        .all()
    ) if opp_ids else []

    projects_data = []
    overdue_count = 0
    for p in projects:
        overdue_ms = (
            db.query(Milestone)
            .filter(
                Milestone.project_id == p.id,
                Milestone.status != "Completed",
                Milestone.target_date < today,
            )
            .count()
        )
        overdue_count += overdue_ms
        projects_data.append({
            "id": p.id,
            "title": p.title,
            "domain": p.domain,
            "status": p.status,
            "overdue_milestones": overdue_ms,
        })

    # 3. Agent Alerts (FR-035)
    alerts = (
        db.query(AgentRecommendation)
        .filter(
            AgentRecommendation.user_id == current_user.id,
            AgentRecommendation.type == "alert",
            AgentRecommendation.status == "Active",
        )
        .all()
    )
    alerts_data = [
        {
            "id": al.id,
            "reference": al.reference_entity,
            "reason": al.reason_text,
            "score": al.score,
        }
        for al in alerts
    ]

    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        },
        "opportunities_count": len(opportunities),
        "pending_applicants_count": len(pending_apps_data),
        "pending_applicants": pending_apps_data,
        "active_projects": projects_data,
        "overdue_milestones_total": overdue_count,
        "agent_alerts": alerts_data,
    }


# ─── GET /dashboard/coordinator (FR-034) ─────────────────────────────


@router.get("/coordinator")
def get_coordinator_dashboard(
    current_user: User = Depends(require_role("Coordinator", "Administrator")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Coordinator dashboard (FR-034).

    Platform aggregates:
      - Total users by role
      - Opportunities summary by status
      - Projects summary by status
      - Total applications count
    """
    # 1. Users by role
    users_by_role = (
        db.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )
    users_summary = {role: count for role, count in users_by_role}

    # 2. Opportunities by status
    opps_by_status = (
        db.query(Opportunity.status, func.count(Opportunity.id))
        .group_by(Opportunity.status)
        .all()
    )
    opps_summary = {st: count for st, count in opps_by_status}

    # 3. Projects by status
    projects_by_status = (
        db.query(Project.status, func.count(Project.id))
        .group_by(Project.status)
        .all()
    )
    projects_summary = {st: count for st, count in projects_by_status}

    # 4. Total applications
    total_apps = db.query(Application).count()

    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "role": current_user.role,
        },
        "metrics": {
            "users_by_role": users_summary,
            "opportunities_by_status": opps_summary,
            "projects_by_status": projects_summary,
            "total_applications": total_apps,
        },
    }
