"""Dashboard route factory that can be mounted after Member A's auth contracts land."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException


DashboardProvider = Callable[[str, int], dict[str, Any]]


def create_dashboard_router(current_user: Callable[..., Any], provider: DashboardProvider) -> APIRouter:
    router = APIRouter(prefix="/dashboard", tags=["dashboards"])
    route_roles = {"student": {"Student"}, "faculty": {"Faculty"},
                   "coordinator": {"Coordinator", "Administrator"}}

    def endpoint(expected: str):
        def read_dashboard(user: Any = Depends(current_user)) -> dict[str, Any]:
            role = getattr(user, "role", None)
            if role not in route_roles[expected]:
                raise HTTPException(status_code=403, detail="Role is not allowed to view this dashboard")
            user_id = getattr(user, "id", None)
            if user_id is None:
                raise HTTPException(status_code=401, detail="Authenticated user is missing an id")
            return provider(expected, int(user_id))
        return read_dashboard

    for dashboard in route_roles:
        router.add_api_route(f"/{dashboard}", endpoint(dashboard), methods=["GET"], name=f"{dashboard}_dashboard")
    return router
