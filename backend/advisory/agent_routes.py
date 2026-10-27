"""Advisory endpoints mounted by the host API after auth and storage contracts land."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from .recommendations import RecommendationStore


def create_agent_router(current_user: Callable[..., Any], store: RecommendationStore,
                        list_for_user: Callable[[int], list[dict[str, Any]]]) -> APIRouter:
    router = APIRouter(prefix="/agent", tags=["agent"])

    def read_recommendations(user: Any = Depends(current_user)) -> dict[str, Any]:
        if getattr(user, "role", None) not in {"Student", "Faculty", "Coordinator"}:
            raise HTTPException(status_code=403, detail="Role is not allowed to view recommendations")
        return {"available": True, "items": list_for_user(int(user.id))}

    def dismiss_recommendation(recommendation_id: int, user: Any = Depends(current_user)) -> dict[str, bool]:
        if getattr(user, "role", None) not in {"Student", "Faculty", "Coordinator"}:
            raise HTTPException(status_code=403, detail="Role is not allowed to dismiss recommendations")
        if not store.dismiss(int(user.id), recommendation_id):
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return {"dismissed": True}

    router.add_api_route("/recommendations", read_recommendations, methods=["GET"])
    router.add_api_route("/recommendations/{recommendation_id}/dismiss", dismiss_recommendation, methods=["POST"])
    return router
