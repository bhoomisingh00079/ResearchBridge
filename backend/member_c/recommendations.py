"""Backend-owned recommendation lifecycle abstraction.

The production adapter should implement this protocol with the shared database model.
The agent service must never receive this store or any application/membership writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class Recommendation:
    user_id: int
    kind: str
    reference_id: int
    reason: str
    score: int
    status: str = "Active"
    created_at: datetime = datetime.min.replace(tzinfo=timezone.utc)


class RecommendationStore(Protocol):
    def upsert_unseen(self, recommendation: Recommendation) -> bool: ...
    def dismiss(self, user_id: int, recommendation_id: int) -> bool: ...


class InMemoryRecommendationStore:
    """Deterministic local fake; dismissed keys cannot be recreated (FR-031)."""

    def __init__(self) -> None:
        self._items: dict[tuple[int, str, int], Recommendation] = {}
        self._dismissed: set[tuple[int, str, int]] = set()

    def upsert_unseen(self, recommendation: Recommendation) -> bool:
        key = (recommendation.user_id, recommendation.kind, recommendation.reference_id)
        if key in self._items or key in self._dismissed:
            return False
        self._items[key] = recommendation
        return True

    def dismiss(self, user_id: int, recommendation_id: int) -> bool:
        match = next((key for key in self._items if key[0] == user_id and key[2] == recommendation_id), None)
        if match is None:
            return False
        self._dismissed.add(match)
        del self._items[match]
        return True
