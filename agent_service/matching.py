"""Explainable matching functions; these accept only authorized structured data."""

from __future__ import annotations

import re
from typing import Any


def _norm(values: list[str]) -> set[str]:
    return {value.strip().casefold() for value in values if value and value.strip()}


def match_opportunities(student: dict[str, Any], opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skills, interests = _norm(student.get("skills", [])), _norm(student.get("interests", []))
    items = []
    for opportunity in opportunities:
        required = _norm(opportunity.get("required_skills", []))
        shared = sorted(skills & required)
        domain = str(opportunity.get("domain", "")).strip()
        domain_match = bool(domain) and domain.casefold() in interests
        interest_skills = sorted(required & interests)
        score = 10 * len(shared) + 5 * int(domain_match) + 3 * len(interest_skills)
        reasons = []
        if required:
            reasons.append(f"You have {len(shared)} of {len(required)} required skills: {', '.join(shared) if shared else 'none'}")
        if domain_match:
            reasons.append(f"Matches your interest in {domain}")
        if interest_skills:
            reasons.append(f"Matches your skill interests: {', '.join(interest_skills)}")
        if not reasons:
            reasons.append("No matching skills or interests were found")
        items.append({"opportunity_id": opportunity["id"], "score": score, "reason": "; ".join(reasons)})
    return sorted(items, key=lambda item: (-item["score"], str(item["opportunity_id"])))


def suggest_collaborators(team_skills: list[str], project_requirements: list[str], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    team, required = _norm(team_skills), _norm(project_requirements)
    gaps = required - team
    suggestions = []
    for candidate in candidates:
        fills = sorted((_norm(candidate.get("skills", [])) & gaps))
        if fills:
            suggestions.append({"candidate_id": candidate["id"], "fills": fills,
                                "reason": f"Fills skill gap: {', '.join(fills)}"})
    return sorted(suggestions, key=lambda item: (-len(item["fills"]), str(item["candidate_id"])))


def suggest_resources(required_topics: list[str], resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    topics = _norm(required_topics)
    suggestions = []
    for resource in resources:
        searchable = _norm([*re.findall(r"[\w]+", resource.get("title", "")),
                            resource.get("type", ""), *resource.get("tags", [])])
        matches = sorted(topics & searchable)
        if matches:
            suggestions.append({"resource_id": resource["id"], "matches": matches,
                                "reason": f"Related to: {', '.join(matches)}"})
    return sorted(suggestions, key=lambda item: (item["matches"][0], str(item["resource_id"])))
