"""
Agent Service — FastAPI application (C1).

Internal API for the Student Research Collaboration Platform.
Listens on port 8100, authenticated via X-Service-Token header (SRS 3.3).
Has **NO** database credentials or drivers (SRS 5.2, FR-030).

Endpoints (development plan, Section 5):
  POST /internal/v1/match/opportunities     — FR-025, FR-026
  POST /internal/v1/match/collaborators     — FR-027
  POST /internal/v1/match/resources         — FR-028
  POST /internal/v1/progress/milestones     — FR-029
  POST /internal/v1/progress/opportunities  — FR-035
"""
from fastapi import Depends, FastAPI

from .auth import verify_service_token
from .explainer import DeterministicExplainer, Explainer
from .matching import match_collaborators, match_opportunities, match_resources
from .progress import detect_milestone_issues, detect_opportunity_issues
from .schemas import (
    MatchCollaboratorsRequest,
    MatchCollaboratorsResponse,
    MatchOpportunitiesRequest,
    MatchOpportunitiesResponse,
    MatchResourcesRequest,
    MatchResourcesResponse,
    ProgressMilestonesRequest,
    ProgressMilestonesResponse,
    ProgressOpportunitiesRequest,
    ProgressOpportunitiesResponse,
)

app = FastAPI(
    title="ResearchBridge Agent Service",
    description=(
        "Internal API for intelligent matching and progress monitoring. "
        "No database access; receives minimal JSON slices from the backend (NFR-009)."
    ),
    version="1.0.0",
    docs_url=None,  # Internal service — no public docs
    redoc_url=None,
)

# Singleton explainer — swap to LLM-backed implementation via TBD-001
_explainer: Explainer = DeterministicExplainer()


def get_explainer() -> Explainer:
    """Dependency: return the active Explainer implementation."""
    return _explainer


# ─── Health (no auth required) ────────────────────────────────────────


@app.get("/health")
def health():
    """Health check — no authentication required."""
    return {"status": "healthy", "service": "agent"}


# ─── Matching endpoints (FR-025 to FR-028) ───────────────────────────


@app.post(
    "/internal/v1/match/opportunities",
    response_model=MatchOpportunitiesResponse,
    dependencies=[Depends(verify_service_token)],
)
def api_match_opportunities(
    request: MatchOpportunitiesRequest,
    explainer: Explainer = Depends(get_explainer),
):
    """Score and rank opportunities for a student (FR-025/026)."""
    return match_opportunities(request, explainer)


@app.post(
    "/internal/v1/match/collaborators",
    response_model=MatchCollaboratorsResponse,
    dependencies=[Depends(verify_service_token)],
)
def api_match_collaborators(
    request: MatchCollaboratorsRequest,
    explainer: Explainer = Depends(get_explainer),
):
    """Find collaborators who fill skill gaps in a project team (FR-027)."""
    return match_collaborators(request, explainer)


@app.post(
    "/internal/v1/match/resources",
    response_model=MatchResourcesResponse,
    dependencies=[Depends(verify_service_token)],
)
def api_match_resources(
    request: MatchResourcesRequest,
    explainer: Explainer = Depends(get_explainer),
):
    """Suggest platform-indexed resources for a project (FR-028)."""
    return match_resources(request, explainer)


# ─── Progress endpoints (FR-029, FR-035) ─────────────────────────────


@app.post(
    "/internal/v1/progress/milestones",
    response_model=ProgressMilestonesResponse,
    dependencies=[Depends(verify_service_token)],
)
def api_progress_milestones(request: ProgressMilestonesRequest):
    """Detect overdue and inactive milestones (FR-029)."""
    return detect_milestone_issues(request)


@app.post(
    "/internal/v1/progress/opportunities",
    response_model=ProgressOpportunitiesResponse,
    dependencies=[Depends(verify_service_token)],
)
def api_progress_opportunities(request: ProgressOpportunitiesRequest):
    """Detect opportunity alerts for faculty (FR-035)."""
    return detect_opportunity_issues(request)

