"""
Tests for the matching algorithms — C2: FR-025 to FR-028.

Verifies the deterministic scoring formula from the development plan (Section 5):
  score = 10 × |shared skills| + 5 × [domain ∈ interests] + 3 × |required ∩ interests|
"""
import pytest

from agent_service.explainer import DeterministicExplainer
from agent_service.matching import match_collaborators, match_opportunities, match_resources
from agent_service.schemas import (
    CandidateSlice,
    MatchCollaboratorsRequest,
    MatchOpportunitiesRequest,
    MatchResourcesRequest,
    OpportunitySlice,
    ProjectSlice,
    ResourceSlice,
    StudentProfile,
)

explainer = DeterministicExplainer()


# ═══════════════════════════════════════════════════════════════════════
# Opportunity matching (FR-025 / FR-026)
# ═══════════════════════════════════════════════════════════════════════


class TestMatchOpportunities:
    """Test opportunity matching with deterministic scoring."""

    def test_plan_example_score_25(self):
        """Exact example from the development plan Section 5.

        student: skills=[python, ml], interests=[ai]
        opportunity: id=7, domain=AI, required=[python, ml, statistics]
        Expected: score = 10*2 + 5*1 + 3*0 = 25
        """
        request = MatchOpportunitiesRequest(
            student=StudentProfile(skills=["python", "ml"], interests=["ai"]),
            opportunities=[
                OpportunitySlice(
                    id=7, domain="AI", required_skills=["python", "ml", "statistics"]
                ),
            ],
        )
        result = match_opportunities(request, explainer)

        assert len(result.items) == 1
        match = result.items[0]
        assert match.opportunity_id == 7
        assert match.score == 25
        assert "2 of 3 required skills" in match.reason
        assert "ml" in match.reason
        assert "python" in match.reason
        assert "interest in AI" in match.reason

    def test_no_match_returns_empty(self):
        """Zero-score opportunities are excluded from results."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(skills=["java"], interests=["web"]),
            opportunities=[
                OpportunitySlice(
                    id=1, domain="Biology", required_skills=["r", "statistics"]
                ),
            ],
        )
        result = match_opportunities(request, explainer)
        assert result.items == []

    def test_case_insensitive_matching(self):
        """Skills and interests are compared case-insensitively."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(skills=["Python", "ML"], interests=["AI"]),
            opportunities=[
                OpportunitySlice(id=1, domain="ai", required_skills=["python", "ml"]),
            ],
        )
        result = match_opportunities(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].score == 25  # 10*2 + 5*1 + 3*0

    def test_multiple_opportunities_sorted_by_score_desc(self):
        """Results are sorted by score descending."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(
                skills=["python", "ml", "statistics"], interests=["ai"]
            ),
            opportunities=[
                OpportunitySlice(id=1, domain="Web", required_skills=["python"]),
                OpportunitySlice(
                    id=2,
                    domain="AI",
                    required_skills=["python", "ml", "statistics"],
                ),
            ],
        )
        result = match_opportunities(request, explainer)

        assert len(result.items) == 2
        assert result.items[0].opportunity_id == 2
        assert result.items[0].score > result.items[1].score

    def test_interest_skill_overlap_adds_3_per_match(self):
        """required ∩ interests contributes 3 points per overlapping item."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(skills=[], interests=["python", "ml"]),
            opportunities=[
                OpportunitySlice(
                    id=1, domain="Web", required_skills=["python", "ml"]
                ),
            ],
        )
        result = match_opportunities(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].score == 6  # 10*0 + 5*0 + 3*2

    def test_empty_opportunities_list(self):
        """Empty input returns empty results."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(skills=["python"], interests=["ai"]),
            opportunities=[],
        )
        result = match_opportunities(request, explainer)
        assert result.items == []

    def test_domain_only_match_gives_5(self):
        """Domain match alone contributes 5 points."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(skills=[], interests=["ai"]),
            opportunities=[
                OpportunitySlice(
                    id=1, domain="AI", required_skills=["statistics"]
                ),
            ],
        )
        result = match_opportunities(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].score == 5  # 10*0 + 5*1 + 3*0

    def test_all_three_scoring_components(self):
        """All three scoring components contribute to the total."""
        request = MatchOpportunitiesRequest(
            student=StudentProfile(
                skills=["python", "ml"], interests=["ai", "python"]
            ),
            opportunities=[
                OpportunitySlice(
                    id=1,
                    domain="AI",
                    required_skills=["python", "ml", "statistics"],
                ),
            ],
        )
        result = match_opportunities(request, explainer)

        assert len(result.items) == 1
        # shared = {python, ml} → 2, domain AI in {ai, python} → yes,
        # required ∩ interests = {python} → 1
        # score = 10*2 + 5*1 + 3*1 = 28
        assert result.items[0].score == 28


# ═══════════════════════════════════════════════════════════════════════
# Collaborator matching (FR-027)
# ═══════════════════════════════════════════════════════════════════════


class TestMatchCollaborators:
    """Test collaborator matching — fills skill gaps in a project team."""

    def test_fills_single_skill_gap(self):
        """Candidate fills the statistics gap for an AI project."""
        request = MatchCollaboratorsRequest(
            project=ProjectSlice(
                id=1, domain="AI", required_skills=["python", "ml", "statistics"]
            ),
            current_team_skills=["python", "ml"],
            candidates=[
                CandidateSlice(id=5, skills=["statistics", "r"], interests=["ai"]),
            ],
        )
        result = match_collaborators(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].user_id == 5
        assert result.items[0].score == 15  # 10*1 gap + 5*1 domain
        assert "statistics" in result.items[0].reason

    def test_no_gaps_to_fill_no_domain_match(self):
        """Candidate with no relevant skills or domain interest scores 0."""
        request = MatchCollaboratorsRequest(
            project=ProjectSlice(id=1, domain="AI", required_skills=["python"]),
            current_team_skills=["python"],
            candidates=[
                CandidateSlice(id=5, skills=["python"], interests=["web"]),
            ],
        )
        result = match_collaborators(request, explainer)
        assert result.items == []

    def test_multiple_candidates_sorted_by_score(self):
        """Candidates ranked by gap-filling ability."""
        request = MatchCollaboratorsRequest(
            project=ProjectSlice(
                id=1, domain="AI", required_skills=["python", "ml", "statistics"]
            ),
            current_team_skills=["python"],
            candidates=[
                CandidateSlice(
                    id=1, skills=["r"], interests=["ai"]
                ),  # 0 gaps + domain = 5
                CandidateSlice(
                    id=2, skills=["ml", "statistics"], interests=["ai"]
                ),  # 2 gaps + domain = 25
            ],
        )
        result = match_collaborators(request, explainer)

        assert len(result.items) == 2
        assert result.items[0].user_id == 2
        assert result.items[0].score == 25
        assert result.items[1].user_id == 1
        assert result.items[1].score == 5

    def test_domain_interest_only(self):
        """Candidate with domain interest but no gap skills still scores 5."""
        request = MatchCollaboratorsRequest(
            project=ProjectSlice(
                id=1, domain="AI", required_skills=["python", "ml"]
            ),
            current_team_skills=["python", "ml"],
            candidates=[
                CandidateSlice(id=3, skills=["java"], interests=["ai"]),
            ],
        )
        result = match_collaborators(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].score == 5


# ═══════════════════════════════════════════════════════════════════════
# Resource matching (FR-028)
# ═══════════════════════════════════════════════════════════════════════


class TestMatchResources:
    """Test platform-indexed resource suggestions."""

    def test_keyword_skill_match(self):
        """Resources with keywords matching project skills are scored."""
        request = MatchResourcesRequest(
            project=ProjectSlice(
                id=1, domain="AI", required_skills=["python", "ml"]
            ),
            resources=[
                ResourceSlice(
                    id=10,
                    title="ML Tutorial",
                    type="Paper",
                    keywords=["ml", "python"],
                ),
            ],
        )
        result = match_resources(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].resource_id == 10
        assert result.items[0].score == 20  # 10*2 + 5*0

    def test_domain_keyword_match(self):
        """Resource keyword matching the project domain adds 5 points."""
        request = MatchResourcesRequest(
            project=ProjectSlice(id=1, domain="AI", required_skills=["python"]),
            resources=[
                ResourceSlice(
                    id=1, title="AI Overview", type="Paper", keywords=["ai"]
                ),
            ],
        )
        result = match_resources(request, explainer)

        assert len(result.items) == 1
        assert result.items[0].score == 5  # 10*0 + 5*1

    def test_no_matching_resources_excluded(self):
        """Resources with no relevant keywords are excluded."""
        request = MatchResourcesRequest(
            project=ProjectSlice(id=1, domain="AI", required_skills=["python"]),
            resources=[
                ResourceSlice(
                    id=1, title="Cooking Guide", type="Link", keywords=["cooking"]
                ),
            ],
        )
        result = match_resources(request, explainer)
        assert result.items == []

    def test_multiple_resources_sorted(self):
        """Resources sorted by score descending."""
        request = MatchResourcesRequest(
            project=ProjectSlice(
                id=1, domain="AI", required_skills=["python", "ml"]
            ),
            resources=[
                ResourceSlice(
                    id=1, title="Python Basics", type="Paper", keywords=["python"]
                ),
                ResourceSlice(
                    id=2,
                    title="Full ML Course",
                    type="Dataset",
                    keywords=["python", "ml", "ai"],
                ),
            ],
        )
        result = match_resources(request, explainer)

        assert len(result.items) == 2
        assert result.items[0].resource_id == 2  # Higher score
        assert result.items[0].score > result.items[1].score

