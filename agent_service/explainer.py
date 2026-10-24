"""
Explainer interface and deterministic implementation.

The Explainer generates human-readable reason text for agent recommendations.
The deterministic implementation constructs reasons from scoring factors
(FR-025/026: explainable recommendations).

An LLM-based implementation can be substituted via the interface (TBD-001).
Tests use the deterministic implementation as the default.
"""
from abc import ABC, abstractmethod
from typing import List


class Explainer(ABC):
    """Interface for generating recommendation explanations (TBD-001).

    An LLM is optional and sits behind this interface; the deterministic
    implementation is the default (development plan, section 0.3, TBD-001).
    """

    @abstractmethod
    def explain_opportunity_match(
        self,
        shared_skills: List[str],
        total_required: int,
        domain_match: bool,
        domain: str,
        interest_skill_overlap: List[str],
    ) -> str:
        """Generate reason text for an opportunity recommendation."""
        ...

    @abstractmethod
    def explain_collaborator_match(
        self,
        filled_gaps: List[str],
        domain_match: bool,
        domain: str,
    ) -> str:
        """Generate reason text for a collaborator recommendation."""
        ...

    @abstractmethod
    def explain_resource_match(
        self,
        matching_keywords: List[str],
        domain_match: bool,
        domain: str,
    ) -> str:
        """Generate reason text for a resource recommendation."""
        ...


class DeterministicExplainer(Explainer):
    """Constructs reason text directly from scoring factors (FR-025/026).

    Produces human-readable explanations listing the concrete match
    factors so that every recommendation is fully explainable.
    """

    def explain_opportunity_match(
        self,
        shared_skills: List[str],
        total_required: int,
        domain_match: bool,
        domain: str,
        interest_skill_overlap: List[str],
    ) -> str:
        parts: List[str] = []
        if shared_skills:
            skills_str = ", ".join(sorted(shared_skills))
            parts.append(
                f"You have {len(shared_skills)} of {total_required} "
                f"required skills: {skills_str}"
            )
        if domain_match:
            parts.append(f"Matches your interest in {domain}")
        if interest_skill_overlap:
            overlap_str = ", ".join(sorted(interest_skill_overlap))
            parts.append(f"Aligns with your interests: {overlap_str}")
        return "; ".join(parts) if parts else "No strong match factors found"

    def explain_collaborator_match(
        self,
        filled_gaps: List[str],
        domain_match: bool,
        domain: str,
    ) -> str:
        parts: List[str] = []
        if filled_gaps:
            parts.append(f"Fills skill gap: {', '.join(sorted(filled_gaps))}")
        if domain_match:
            parts.append(f"Interest aligns with project domain {domain}")
        return "; ".join(parts) if parts else "No strong match factors found"

    def explain_resource_match(
        self,
        matching_keywords: List[str],
        domain_match: bool,
        domain: str,
    ) -> str:
        parts: List[str] = []
        if matching_keywords:
            parts.append(
                f"Matches project skills: {', '.join(sorted(matching_keywords))}"
            )
        if domain_match:
            parts.append(f"Related to project domain {domain}")
        return "; ".join(parts) if parts else "No strong match factors found"

