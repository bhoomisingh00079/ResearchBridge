"""Background scanner jobs invoking agent progress checks (Task C4: FR-029, FR-035)."""
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models import Opportunity, Milestone, Application, Project, ProjectMember
from app.services.agent_client import agent_client, persist_recommendations


def run_agent_scans(db: Session) -> Dict[str, Any]:
    """Execute progress scans for opportunities and milestones.

    Adheres strictly to FR-030 / BR-005 / SRS 5.2:
      - Reads data, calls agent internal API for advisory analysis.
      - Never writes to applications.status or project_members.
    """
    results = {"opportunities_alerted": 0, "milestones_alerted": 0}

    # 1. Scan active opportunities for faculty alerts (FR-035)
    opportunities = db.query(Opportunity).filter(Opportunity.status == "Published").all()
    opp_slices = []
    for opp in opportunities:
        app_count = db.query(Application).filter(
            Application.opportunity_id == opp.id,
            Application.status != "Withdrawn",
        ).count()
        opp_slices.append({
            "id": opp.id,
            "deadline": str(opp.deadline) if opp.deadline else None,
            "application_count": app_count,
            "capacity": opp.capacity,
            "faculty_id": opp.faculty_id,
        })

    opp_res = agent_client.progress_opportunities(opp_slices)
    if opp_res.get("available") and opp_res.get("alerts"):
        for alert in opp_res["alerts"]:
            opp_id = alert["opportunity_id"]
            opp = next((o for o in opportunities if o.id == opp_id), None)
            if opp:
                raw_item = [{
                    "opp_id": opp.id,
                    "score": 10 if alert["type"] == "past_deadline" else 5,
                    "reason": f"{alert['reason']} (Recommended: {alert['recommended_action']})",
                }]
                persist_recommendations(db, opp.faculty_id, "alert", raw_item, "opp_id")
                results["opportunities_alerted"] += 1

    # 2. Scan project milestones for overdue/inactive alerts (FR-029)
    milestones = db.query(Milestone).filter(Milestone.status != "Completed").all()
    ms_slices = [
        {
            "id": ms.id,
            "target_date": str(ms.target_date),
            "status": ms.status,
            "last_activity_at": ms.last_activity_at.isoformat() if ms.last_activity_at else None,
            "project_id": ms.project_id,
        }
        for ms in milestones
    ]

    ms_res = agent_client.progress_milestones(ms_slices)
    if ms_res.get("available") and ms_res.get("alerts"):
        for alert in ms_res["alerts"]:
            ms_id = alert["milestone_id"]
            ms = next((m for m in milestones if m.id == ms_id), None)
            if ms:
                # Notify project leads
                leads = db.query(ProjectMember).filter(
                    ProjectMember.project_id == ms.project_id,
                    ProjectMember.role_in_project == "Lead",
                ).all()
                for lead in leads:
                    raw_item = [{
                        "ms_id": ms.id,
                        "score": 10 if alert["type"] == "overdue" else 5,
                        "reason": f"{alert['reason']} (Recommended: {alert['recommended_action']})",
                    }]
                    persist_recommendations(db, lead.user_id, "alert", raw_item, "ms_id")
                    results["milestones_alerted"] += 1

    return results

