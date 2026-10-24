"""
Tests for progress detection algorithms — C3: FR-029, FR-035.

Verifies overdue/inactive milestone detection and opportunity alerts
with the three recommended actions from the development plan (Section 5):
  promote, broaden required skills, extend deadline.
"""
import pytest
from datetime import date, datetime, timedelta, timezone

from agent_service.progress import detect_milestone_issues, detect_opportunity_issues
from agent_service.schemas import (
    MilestoneSlice,
    OpportunityProgressSlice,
    ProgressMilestonesRequest,
    ProgressOpportunitiesRequest,
)

TODAY = date(2026, 10, 22)
NOW = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)


# ═══════════════════════════════════════════════════════════════════════
# Milestone issues (FR-029)
# ═══════════════════════════════════════════════════════════════════════


class TestMilestoneOverdue:
    """Test overdue milestone detection."""

    def test_overdue_in_progress(self):
        """Milestone 2 days past target_date and In Progress → overdue."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY - timedelta(days=2),
                    status="In Progress",
                    last_activity_at=NOW,
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        overdue = [a for a in result.alerts if a.type == "overdue"]

        assert len(overdue) == 1
        assert overdue[0].milestone_id == 1
        assert "2 days past target date" in overdue[0].reason
        assert overdue[0].recommended_action == "Update status or request deadline extension"

    def test_completed_milestone_never_overdue(self):
        """Completed milestones are never flagged as overdue."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY - timedelta(days=5),
                    status="Completed",
                    last_activity_at=NOW,
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        assert not any(a.type == "overdue" for a in result.alerts)

    def test_one_day_overdue_singular_text(self):
        """Singular 'day' for exactly 1 day overdue."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY - timedelta(days=1),
                    status="Not Started",
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        overdue = [a for a in result.alerts if a.type == "overdue"]
        assert "1 day past" in overdue[0].reason

    def test_blocked_milestone_can_be_overdue(self):
        """Blocked milestones can still be flagged as overdue."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY - timedelta(days=3),
                    status="Blocked",
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        assert any(a.type == "overdue" for a in result.alerts)

    def test_future_target_not_overdue(self):
        """Milestone with future target_date is not overdue."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY + timedelta(days=5),
                    status="In Progress",
                    last_activity_at=NOW,
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        assert not any(a.type == "overdue" for a in result.alerts)


class TestMilestoneInactive:
    """Test inactive milestone detection."""

    def test_inactive_after_threshold_days(self):
        """No activity for 8 days (> 7 threshold) → inactive alert."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY + timedelta(days=30),
                    status="In Progress",
                    last_activity_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        inactive = [a for a in result.alerts if a.type == "inactive"]

        assert len(inactive) == 1
        assert inactive[0].milestone_id == 1
        assert "No activity" in inactive[0].reason
        assert inactive[0].recommended_action == "Check in with team members and update progress"

    def test_recently_active_not_flagged(self):
        """Activity within threshold window → no inactive alert."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY + timedelta(days=10),
                    status="In Progress",
                    last_activity_at=NOW,
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        assert result.alerts == []

    def test_no_activity_timestamp_not_flagged(self):
        """Milestone with null last_activity_at is not flagged inactive."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY + timedelta(days=10),
                    status="Not Started",
                    last_activity_at=None,
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        assert result.alerts == []

    def test_completed_milestone_not_flagged_inactive(self):
        """Completed milestones are not flagged as inactive regardless of activity."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY - timedelta(days=10),
                    status="Completed",
                    last_activity_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        inactive = [a for a in result.alerts if a.type == "inactive"]
        assert inactive == []

    def test_naive_datetime_treated_as_utc(self):
        """Naive datetime (no tzinfo) is treated as UTC."""
        request = ProgressMilestonesRequest(
            milestones=[
                MilestoneSlice(
                    id=1,
                    target_date=TODAY + timedelta(days=30),
                    status="In Progress",
                    last_activity_at=datetime(2026, 10, 14, 0, 0, 0),  # naive
                ),
            ]
        )
        result = detect_milestone_issues(request, today=TODAY, now=NOW)
        inactive = [a for a in result.alerts if a.type == "inactive"]
        assert len(inactive) == 1  # 8 days inactive


# ═══════════════════════════════════════════════════════════════════════
# Opportunity issues (FR-035)
# ═══════════════════════════════════════════════════════════════════════


class TestOpportunityIssues:
    """Test opportunity alert detection with the three recommended actions."""

    def test_past_deadline_unfilled_extend(self):
        """Past deadline with unfilled spots → 'extend deadline'."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=7,
                    deadline=TODAY - timedelta(days=2),
                    application_count=1,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)

        assert len(result.alerts) == 1
        alert = result.alerts[0]
        assert alert.opportunity_id == 7
        assert alert.type == "past_deadline"
        assert alert.recommended_action == "extend deadline"
        assert "2 days ago" in alert.reason
        assert "1 of 5 spots filled" in alert.reason

    def test_nearing_deadline_zero_apps_promote(self):
        """Nearing deadline with 0 applications → 'promote'."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1,
                    deadline=TODAY + timedelta(days=3),
                    application_count=0,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)

        assert len(result.alerts) == 1
        assert result.alerts[0].recommended_action == "promote"
        assert result.alerts[0].type == "low_applications"

    def test_nearing_deadline_low_fill_broaden(self):
        """Nearing deadline, < 50% filled → 'broaden required skills'."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1,
                    deadline=TODAY + timedelta(days=5),
                    application_count=2,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)

        assert len(result.alerts) == 1
        assert result.alerts[0].recommended_action == "broaden required skills"

    def test_nearing_deadline_moderate_fill_extend(self):
        """Nearing deadline, >= 50% but not full → 'extend deadline'."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1,
                    deadline=TODAY + timedelta(days=3),
                    application_count=3,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)

        assert len(result.alerts) == 1
        assert result.alerts[0].recommended_action == "extend deadline"

    def test_no_deadline_no_alert(self):
        """Opportunities without a deadline produce no alerts."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1, deadline=None, application_count=0, capacity=5
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)
        assert result.alerts == []

    def test_fully_filled_no_alert(self):
        """Opportunity with enough applications is not flagged."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1,
                    deadline=TODAY + timedelta(days=3),
                    application_count=5,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)
        assert result.alerts == []

    def test_far_deadline_no_alert(self):
        """Deadline far in the future produces no alert."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1,
                    deadline=TODAY + timedelta(days=30),
                    application_count=0,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)
        assert result.alerts == []

    def test_deadline_today_is_nearing(self):
        """Deadline equal to today counts as 'nearing'."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1, deadline=TODAY, application_count=0, capacity=5
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)

        assert len(result.alerts) == 1
        assert result.alerts[0].type == "low_applications"
        assert result.alerts[0].recommended_action == "promote"

    def test_one_day_past_singular_text(self):
        """Singular 'day' for exactly 1 day past deadline."""
        request = ProgressOpportunitiesRequest(
            opportunities=[
                OpportunityProgressSlice(
                    id=1,
                    deadline=TODAY - timedelta(days=1),
                    application_count=0,
                    capacity=5,
                ),
            ]
        )
        result = detect_opportunity_issues(request, today=TODAY)
        assert "1 day ago" in result.alerts[0].reason

