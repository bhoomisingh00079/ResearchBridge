"""
Progress monitoring and alert detection for the Agent Service (C3).

Detects:
  - Overdue milestones: target_date < today, not Completed (FR-029)
  - Inactive milestones: no activity for INACTIVE_THRESHOLD_DAYS (FR-029)
  - Opportunity alerts: low applications, nearing/past deadline (FR-035)

Recommended actions for opportunities name one of:
  ``broaden required skills``, ``extend deadline``, ``promote``
  (development plan, Section 5).
"""
import os
from datetime import date, datetime, timezone
from typing import List, Optional

from .schemas import (
    MilestoneAlert,
    OpportunityAlert,
    ProgressMilestonesRequest,
    ProgressMilestonesResponse,
    ProgressOpportunitiesRequest,
    ProgressOpportunitiesResponse,
)

# Configurable thresholds via environment (plan section 0.4)
INACTIVE_THRESHOLD_DAYS: int = int(os.environ.get("INACTIVE_THRESHOLD_DAYS", "7"))
DEADLINE_WARNING_DAYS: int = int(os.environ.get("DEADLINE_WARNING_DAYS", "7"))


def detect_milestone_issues(
    request: ProgressMilestonesRequest,
    today: Optional[date] = None,
    now: Optional[datetime] = None,
) -> ProgressMilestonesResponse:
    """Detect overdue and inactive milestones (FR-029).

    Parameters ``today`` and ``now`` are injectable for deterministic testing.
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    if now is None:
        now = datetime.now(timezone.utc)

    alerts: List[MilestoneAlert] = []

    for ms in request.milestones:
        # ── Overdue: target_date has passed and milestone is not completed ──
        if ms.status != "Completed" and ms.target_date < today:
            days_overdue = (today - ms.target_date).days
            alerts.append(
                MilestoneAlert(
                    milestone_id=ms.id,
                    type="overdue",
                    reason=(
                        f"{days_overdue} day{'s' if days_overdue != 1 else ''} "
                        f"past target date"
                    ),
                    recommended_action="Update status or request deadline extension",
                )
            )

        # ── Inactive: no activity for threshold days, still in progress ──
        if (
            ms.status in ("In Progress", "Not Started")
            and ms.last_activity_at is not None
        ):
            last_activity = ms.last_activity_at
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)

            inactive_days = (now - last_activity).days
            if inactive_days >= INACTIVE_THRESHOLD_DAYS:
                alerts.append(
                    MilestoneAlert(
                        milestone_id=ms.id,
                        type="inactive",
                        reason=(
                            f"No activity for {inactive_days} days "
                            f"(status: {ms.status})"
                        ),
                        recommended_action="Check in with team members and update progress",
                    )
                )

    return ProgressMilestonesResponse(alerts=alerts)


def detect_opportunity_issues(
    request: ProgressOpportunitiesRequest,
    today: Optional[date] = None,
) -> ProgressOpportunitiesResponse:
    """Detect opportunity alerts for faculty (FR-035).

    Recommended action names one of (development plan, Section 5):
      - ``promote``                — zero applications (no visibility)
      - ``broaden required skills`` — < 50 % filled (requirements too narrow)
      - ``extend deadline``        — some interest but not enough time
    """
    if today is None:
        today = datetime.now(timezone.utc).date()

    alerts: List[OpportunityAlert] = []

    for opp in request.opportunities:
        if opp.deadline is None:
            continue

        days_until = (opp.deadline - today).days
        fill_ratio = opp.application_count / max(opp.capacity, 1)

        # ── Past deadline with unfilled capacity ──
        if days_until < 0 and opp.application_count < opp.capacity:
            days_past = abs(days_until)
            alerts.append(
                OpportunityAlert(
                    opportunity_id=opp.id,
                    type="past_deadline",
                    reason=(
                        f"Deadline passed {days_past} "
                        f"day{'s' if days_past != 1 else ''} ago; "
                        f"{opp.application_count} of {opp.capacity} spots filled"
                    ),
                    recommended_action="extend deadline",
                )
            )

        # ── Nearing deadline with low applications ──
        elif (
            0 <= days_until <= DEADLINE_WARNING_DAYS
            and opp.application_count < opp.capacity
        ):
            if opp.application_count == 0:
                action = "promote"
            elif fill_ratio < 0.5:
                action = "broaden required skills"
            else:
                action = "extend deadline"

            alerts.append(
                OpportunityAlert(
                    opportunity_id=opp.id,
                    type="low_applications",
                    reason=(
                        f"{opp.application_count} of {opp.capacity} spots filled, "
                        f"deadline in {days_until} "
                        f"day{'s' if days_until != 1 else ''}"
                    ),
                    recommended_action=action,
                )
            )

    return ProgressOpportunitiesResponse(alerts=alerts)

