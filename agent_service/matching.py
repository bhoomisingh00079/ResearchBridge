"""
Deterministic matching algorithms for the Agent Service (C2).

Scoring formula (FR-025/026, development plan Section 5):

    score = 10 × |shared_skills| + 5 × [domain ∈ interests] + 3 × |required ∩ interests|

Where:
  |shared_skills|        = student skills ∩ opportunity required skills
  [domain ∈ interests]   = 1 if opportunity domain appears in student interests, else 0
  |required ∩ interests| = required skills that overlap with student interests

All string comparisons are case-insensitive. Results sorted by score descending.
Zero-score items are excluded (no noise in recommendations).
"""
from typing import List

from .explainer import Explainer
from .schemas import (
    CollaboratorMatch,
    MatchCollaboratorsRequest,
    MatchCollaboratorsResponse,
    MatchOpportunitiesRequest,
    MatchOpportunitiesResponse,
    MatchResourcesRequest,
    MatchResourcesResponse,
    OpportunityMatch,
    ResourceMatch,
)


def _normalise(items: list[str]) -> set[str]:
    """Lowercase, strip, and deduplicate a list of strings."""
    return {s.strip().lower() for s in items if s.strip()}


def match_opportunities(
    request: MatchOpportunitiesRequest,
    explainer: Explainer,
) -> MatchOpportunitiesResponse:
    """Score and rank opportunities for a student (FR-025/026).

    Uses the deterministic formula from the development plan:
    ``score = 10*|shared| + 5*[domain in interests] + 3*|required ∩ interests|``
    """
    student_skills = _normalise(request.student.skills)
    student_interests = _normalise(request.student.interests)
    items: List[OpportunityMatch] = []

    for opp in request.opportunities:
        required = _normalise(opp.required_skills)
        domain_lower = opp.domain.strip().lower()

        shared = student_skills & required
        domain_match = domain_lower in student_interests
        interest_overlap = required & student_interests

        score = 10 * len(shared) + 5 * int(domain_match) + 3 * len(interest_overlap)

        if score > 0:
            reason = explainer.explain_opportunity_match(
                shared_skills=sorted(shared),
                total_required=len(required),
                domain_match=domain_match,
                domain=opp.domain,
                interest_skill_overlap=sorted(interest_overlap),
            )
            items.append(
                OpportunityMatch(
                    opportunity_id=opp.id,
                    score=score,
                    reason=reason,
                )
            )

    items.sort(key=lambda m: m.score, reverse=True)
    return MatchOpportunitiesResponse(items=items)


def match_collaborators(
    request: MatchCollaboratorsRequest,
    explainer: Explainer,
) -> MatchCollaboratorsResponse:
    """Find candidates who fill skill gaps in a project team (FR-027).

    Scoring: ``10 * |gaps_filled| + 5 * [domain in candidate interests]``
    Reason text names the specific skills each candidate brings.
    """
    team_skills = _normalise(request.current_team_skills)
    required = _normalise(request.project.required_skills)
    domain_lower = request.project.domain.strip().lower()
    skill_gaps = required - team_skills
    items: List[CollaboratorMatch] = []

    for candidate in request.candidates:
        cand_skills = _normalise(candidate.skills)
        cand_interests = _normalise(candidate.interests)

        filled_gaps = cand_skills & skill_gaps
        domain_match = domain_lower in cand_interests

        score = 10 * len(filled_gaps) + 5 * int(domain_match)

        if score > 0:
            reason = explainer.explain_collaborator_match(
                filled_gaps=sorted(filled_gaps),
                domain_match=domain_match,
                domain=request.project.domain,
            )
            items.append(
                CollaboratorMatch(
                    user_id=candidate.id,
                    score=score,
                    reason=reason,
                )
            )

    items.sort(key=lambda m: m.score, reverse=True)
    return MatchCollaboratorsResponse(items=items)


def match_resources(
    request: MatchResourcesRequest,
    explainer: Explainer,
) -> MatchResourcesResponse:
    """Suggest platform-indexed resources relevant to a project (FR-028).

    Only resources already on the platform are considered (plan Section 5).
    Scoring: ``10 * |keyword ∩ project_skills| + 5 * [domain in keywords]``
    """
    project_skills = _normalise(request.project.required_skills)
    domain_lower = request.project.domain.strip().lower()
    items: List[ResourceMatch] = []

    for resource in request.resources:
        keywords = _normalise(resource.keywords)

        matching_kw = keywords & project_skills
        domain_match = domain_lower in keywords

        score = 10 * len(matching_kw) + 5 * int(domain_match)

        if score > 0:
            reason = explainer.explain_resource_match(
                matching_keywords=sorted(matching_kw),
                domain_match=domain_match,
                domain=request.project.domain,
            )
            items.append(
                ResourceMatch(
                    resource_id=resource.id,
                    score=score,
                    reason=reason,
                )
            )

    items.sort(key=lambda m: m.score, reverse=True)
    return MatchResourcesResponse(items=items)

