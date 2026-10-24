"""Backend client for the Agent Service (Task C4: FR-030, FR-031, NFR-002, NFR-009).

Key architectural invariants:
  1. 10s maximum timeout (NFR-002).
  2. Graceful degradation: if the agent service fails, times out, or is unreachable,
     the client catches exceptions and returns an unavailable status without crashing
     the dashboard or caller (PLAN Section 1, SRS 5.4 Reliability).
  3. Data minimisation: only sends structured slices (skills, interests, domain, timestamps)
     without user names, emails, passwords, or free text (NFR-009).
  4. Backend persists AgentRecommendation rows; agent has NO database write access (FR-030).
  5. Respects dismissed recommendations so they are never re-created or re-shown (FR-031).
"""
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.config import AGENT_SERVICE_TOKEN, AGENT_SERVICE_URL, AGENT_TIMEOUT_SECONDS
from app.models import AgentRecommendation

logger = logging.getLogger(__name__)


class AgentClient:
    """HTTP client communicating with the isolated agent service."""

    def __init__(
        self,
        base_url: str = AGENT_SERVICE_URL,
        service_token: str = AGENT_SERVICE_TOKEN,
        timeout: float = AGENT_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Service-Token": self.service_token,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform POST with 10s timeout and graceful degradation (NFR-002)."""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=self._headers())
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    "Agent service returned status %s for %s: %s",
                    response.status_code,
                    path,
                    response.text,
                )
                return None
        except httpx.TimeoutException:
            logger.warning("Agent service timed out after %s seconds for %s", self.timeout, path)
            return None
        except Exception as exc:
            logger.warning("Agent service call failed for %s: %s", path, exc)
            return None

    def match_opportunities(
        self,
        student_skills: List[str],
        student_interests: List[str],
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Request opportunity recommendations for a student (FR-025, FR-026).

        Payload minimised (NFR-009):
          student: {skills, interests}
          opportunities: [{id, domain, required_skills}]
        """
        payload = {
            "student": {
                "skills": student_skills,
                "interests": student_interests,
            },
            "opportunities": [
                {
                    "id": opp["id"],
                    "domain": opp["domain"],
                    "required_skills": opp.get("required_skills", []),
                }
                for opp in opportunities
            ],
        }
        res = self._post("/internal/v1/match/opportunities", payload)
        if res is None:
            return {"available": False, "items": []}
        return {"available": True, "items": res.get("items", [])}

    def match_collaborators(
        self,
        project_id: int,
        project_domain: str,
        project_required_skills: List[str],
        current_team_skills: List[str],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Request collaborator recommendations (FR-027).

        Payload minimised (NFR-009):
          project: {id, domain, required_skills}
          candidates: [{id, skills, interests}]
        """
        payload = {
            "project": {
                "id": project_id,
                "domain": project_domain,
                "required_skills": project_required_skills,
            },
            "current_team_skills": current_team_skills,
            "candidates": [
                {
                    "id": c["id"],
                    "skills": c.get("skills", []),
                    "interests": c.get("interests", []),
                }
                for c in candidates
            ],
        }
        res = self._post("/internal/v1/match/collaborators", payload)
        if res is None:
            return {"available": False, "items": []}
        return {"available": True, "items": res.get("items", [])}

    def match_resources(
        self,
        project_id: int,
        project_domain: str,
        project_required_skills: List[str],
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Request resource recommendations (FR-028).

        Payload minimised (NFR-009):
          project: {id, domain, required_skills}
          resources: [{id, title, type, keywords}]
        """
        payload = {
            "project": {
                "id": project_id,
                "domain": project_domain,
                "required_skills": project_required_skills,
            },
            "resources": [
                {
                    "id": r["id"],
                    "title": r.get("title", ""),
                    "type": r.get("type", "Paper"),
                    "keywords": r.get("keywords", []),
                }
                for r in resources
            ],
        }
        res = self._post("/internal/v1/match/resources", payload)
        if res is None:
            return {"available": False, "items": []}
        return {"available": True, "items": res.get("items", [])}

    def progress_milestones(self, milestones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Request milestone overdue/inactivity progress alerts (FR-029)."""
        payload = {
            "milestones": [
                {
                    "id": ms["id"],
                    "target_date": ms["target_date"],
                    "status": ms["status"],
                    "last_activity_at": ms.get("last_activity_at"),
                }
                for ms in milestones
            ]
        }
        res = self._post("/internal/v1/progress/milestones", payload)
        if res is None:
            return {"available": False, "alerts": []}
        return {"available": True, "alerts": res.get("alerts", [])}

    def progress_opportunities(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Request faculty opportunity progress alerts (FR-035)."""
        payload = {
            "opportunities": [
                {
                    "id": opp["id"],
                    "deadline": opp.get("deadline"),
                    "application_count": opp.get("application_count", 0),
                    "capacity": opp.get("capacity", 1),
                }
                for opp in opportunities
            ]
        }
        res = self._post("/internal/v1/progress/opportunities", payload)
        if res is None:
            return {"available": False, "alerts": []}
        return {"available": True, "alerts": res.get("alerts", [])}


# Singleton client instance
agent_client = AgentClient()


def persist_recommendations(
    db: Session,
    user_id: int,
    rec_type: str,
    raw_items: List[Dict[str, Any]],
    id_key: str,
) -> List[AgentRecommendation]:
    """Persist agent recommendations while respecting status='Dismissed' (FR-031).

    If an item already exists in the database:
      - If it was 'Dismissed', DO NOT re-activate or re-show it (FR-031).
      - If it is 'Active', update the score and reason.
    If it is new:
      - Insert with status='Active'.
    """
    saved_records = []
    for item in raw_items:
        entity_ref = f"{rec_type}:{item[id_key]}"
        existing = (
            db.query(AgentRecommendation)
            .filter(
                AgentRecommendation.user_id == user_id,
                AgentRecommendation.type == rec_type,
                AgentRecommendation.reference_entity == entity_ref,
            )
            .first()
        )

        if existing:
            if existing.status == "Dismissed":
                # FR-031: Dismissed items are never re-created or re-shown
                continue
            existing.score = item["score"]
            existing.reason_text = item["reason"]
            saved_records.append(existing)
        else:
            rec = AgentRecommendation(
                user_id=user_id,
                type=rec_type,
                reference_entity=entity_ref,
                reason_text=item["reason"],
                score=item["score"],
                status="Active",
            )
            db.add(rec)
            saved_records.append(rec)

    db.commit()
    for rec in saved_records:
        db.refresh(rec)
    return saved_records
