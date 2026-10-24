"""Pure business rules (no DB / no HTTP) for isolated white-box testing (SRS FR-009, BR-002)."""
import datetime as dt
from typing import Optional, Tuple


def check_application_eligibility(
    opp_status: str,
    deadline: Optional[dt.date],
    today: dt.date,
    already_applied: bool,
) -> Tuple[bool, str]:
    """FR-009 / BR-002: a student may apply only to a Published opportunity whose
    deadline (if any) has not passed, and only once (Withdrawn applications are ignored
    by the caller). Returns (allowed, reason)."""
    if opp_status != "Published":  # decision p1
        return False, "Opportunity is not open"
    if deadline is not None and deadline < today:  # decisions p2 and p3
        return False, "Deadline passed"
    if already_applied:  # decision p4
        return False, "Already applied"
    return True, "OK"

