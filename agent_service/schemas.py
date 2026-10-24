"""
Pydantic schemas for the Agent Service internal API.

All request/response models for the internal endpoints defined in
the development plan (Section 5: Agent service internal API).

Data minimisation (NFR-009): only structured fields are exchanged —
skills, interests, domain, timestamps. No names, emails, or free text.
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Shared components ───────────────────────────────────────────────


class StudentProfile(BaseModel):
    """Minimal student data sent by the backend (NFR-009)."""

    skills: List[str] = Field(default_factory=list, description="Normalised skill names")
    interests: List[str] = Field(
        default_factory=list, description="Research interest areas"
    )


class OpportunitySlice(BaseModel):
    """Minimal opportunity data for matching (NFR-009)."""

    id: int
    domain: str
    required_skills: List[str] = Field(default_factory=list)


class CandidateSlice(BaseModel):
    """Minimal candidate data for collaborator matching (NFR-009)."""

    id: int
    skills: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)


class ProjectSlice(BaseModel):
    """Minimal project data for collaborator/resource matching."""

    id: int
    domain: str
    required_skills: List[str] = Field(default_factory=list)


class ResourceSlice(BaseModel):
    """Minimal resource metadata for matching."""

    id: int
    title: str
    type: str
    keywords: List[str] = Field(default_factory=list)


class MilestoneSlice(BaseModel):
    """Minimal milestone data for progress detection (NFR-009)."""

    id: int
    target_date: date
    status: str
    last_activity_at: Optional[datetime] = None


class OpportunityProgressSlice(BaseModel):
    """Minimal opportunity data for FR-035 alert detection."""

    id: int
    deadline: Optional[date] = None
    application_count: int = 0
    capacity: int = 1


# ─── Match Opportunities (POST /internal/v1/match/opportunities) ─────


class MatchOpportunitiesRequest(BaseModel):
    student: StudentProfile
    opportunities: List[OpportunitySlice]


class OpportunityMatch(BaseModel):
    opportunity_id: int
    score: int
    reason: str


class MatchOpportunitiesResponse(BaseModel):
    items: List[OpportunityMatch]


# ─── Match Collaborators (POST /internal/v1/match/collaborators) ─────


class MatchCollaboratorsRequest(BaseModel):
    project: ProjectSlice
    current_team_skills: List[str] = Field(default_factory=list)
    candidates: List[CandidateSlice]


class CollaboratorMatch(BaseModel):
    user_id: int
    score: int
    reason: str


class MatchCollaboratorsResponse(BaseModel):
    items: List[CollaboratorMatch]


# ─── Match Resources (POST /internal/v1/match/resources) ─────────────


class MatchResourcesRequest(BaseModel):
    project: ProjectSlice
    resources: List[ResourceSlice]


class ResourceMatch(BaseModel):
    resource_id: int
    score: int
    reason: str


class MatchResourcesResponse(BaseModel):
    items: List[ResourceMatch]


# ─── Progress Milestones (POST /internal/v1/progress/milestones) ─────


class ProgressMilestonesRequest(BaseModel):
    milestones: List[MilestoneSlice]


class MilestoneAlert(BaseModel):
    milestone_id: int
    type: str  # "overdue" or "inactive"
    reason: str
    recommended_action: str


class ProgressMilestonesResponse(BaseModel):
    alerts: List[MilestoneAlert]


# ─── Progress Opportunities (POST /internal/v1/progress/opportunities)


class ProgressOpportunitiesRequest(BaseModel):
    opportunities: List[OpportunityProgressSlice]


class OpportunityAlert(BaseModel):
    opportunity_id: int
    type: str  # "low_applications", "nearing_deadline", "past_deadline"
    reason: str
    recommended_action: str  # one of: "broaden required skills", "extend deadline", "promote"


class ProgressOpportunitiesResponse(BaseModel):
    alerts: List[OpportunityAlert]

