"""Internal-only FastAPI surface. It has no database integration by design."""

from __future__ import annotations

import datetime as dt
import hmac
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

try:
    from .matching import match_opportunities, suggest_collaborators, suggest_resources
    from .progress import milestone_alerts, opportunity_alerts
except ImportError:
    from matching import match_opportunities, suggest_collaborators, suggest_resources
    from progress import milestone_alerts, opportunity_alerts


class Student(BaseModel):
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    id: int
    domain: str = ""
    required_skills: list[str] = Field(default_factory=list)


class OpportunityMatchRequest(BaseModel):
    student: Student
    opportunities: list[Opportunity]


class CollaboratorRequest(BaseModel):
    team_skills: list[str]
    project_requirements: list[str]
    candidates: list[dict[str, Any]]


class ResourceRequest(BaseModel):
    required_topics: list[str]
    resources: list[dict[str, Any]]


class MilestoneRequest(BaseModel):
    today: dt.date | None = None
    milestones: list[dict[str, Any]]


class OpportunityAlertRequest(BaseModel):
    today: dt.date | None = None
    opportunities: list[dict[str, Any]]


def create_app(service_token: str | None = None) -> FastAPI:
    expected = service_token if service_token is not None else os.getenv("SERVICE_TOKEN", "")
    app = FastAPI(title="ResearchBridge Internal Agent", version="1.0.0", docs_url=None, redoc_url=None)

    def authenticate(x_service_token: str | None = Header(default=None, alias="X-Service-Token")) -> None:
        if not expected or not x_service_token or not hmac.compare_digest(expected, x_service_token):
            raise HTTPException(status_code=401, detail="Invalid service token")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.post("/internal/v1/match/opportunities", dependencies=[Depends(authenticate)])
    def opportunities_match(body: OpportunityMatchRequest) -> dict[str, Any]:
        return {"items": match_opportunities(body.student.model_dump(), [x.model_dump() for x in body.opportunities])}

    @app.post("/internal/v1/match/collaborators", dependencies=[Depends(authenticate)])
    def collaborators(body: CollaboratorRequest) -> dict[str, Any]:
        return {"items": suggest_collaborators(body.team_skills, body.project_requirements, body.candidates)}

    @app.post("/internal/v1/match/resources", dependencies=[Depends(authenticate)])
    def resources(body: ResourceRequest) -> dict[str, Any]:
        return {"items": suggest_resources(body.required_topics, body.resources)}

    @app.post("/internal/v1/progress/milestones", dependencies=[Depends(authenticate)])
    def milestones(body: MilestoneRequest) -> dict[str, Any]:
        return {"items": milestone_alerts(body.milestones, body.today or dt.date.today())}

    @app.post("/internal/v1/progress/opportunities", dependencies=[Depends(authenticate)])
    def opportunity_progress(body: OpportunityAlertRequest) -> dict[str, Any]:
        return {"items": opportunity_alerts(body.opportunities, body.today or dt.date.today())}

    return app


app = create_app()
