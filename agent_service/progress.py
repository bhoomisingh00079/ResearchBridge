"""Advisory progress alerts with injectable dates for deterministic checks."""

from __future__ import annotations

import datetime as dt
from typing import Any

INACTIVE_DAYS = 7
DEADLINE_WINDOW_DAYS = 14


def milestone_alerts(milestones: list[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    alerts = []
    for milestone in milestones:
        status = milestone.get("status")
        if status == "Completed":
            continue
        due = dt.date.fromisoformat(milestone["target_date"])
        last_activity = dt.date.fromisoformat(milestone["last_activity_at"])
        if due < today:
            alerts.append({"milestone_id": milestone["id"], "kind": "overdue",
                           "recommended_action": "Review the milestone and agree on a revised target date."})
        elif (today - last_activity).days >= INACTIVE_DAYS:
            alerts.append({"milestone_id": milestone["id"], "kind": "inactive",
                           "recommended_action": "Check in with the project team and update progress."})
    return alerts


def opportunity_alerts(opportunities: list[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    alerts = []
    for opportunity in opportunities:
        deadline = opportunity.get("deadline")
        if not deadline:
            continue
        days_left = (dt.date.fromisoformat(deadline) - today).days
        if days_left < 0 or days_left > DEADLINE_WINDOW_DAYS:
            continue
        capacity = opportunity.get("capacity", 0)
        applications = opportunity.get("application_count", 0)
        if applications >= capacity:
            continue
        action = "extend deadline" if days_left <= 3 else "promote"
        alerts.append({"opportunity_id": opportunity["id"], "kind": "deadline_capacity",
                       "days_left": days_left, "recommended_action": action,
                       "message": f"{capacity - applications} place(s) remain; consider whether to {action} the opportunity."})
    return alerts
