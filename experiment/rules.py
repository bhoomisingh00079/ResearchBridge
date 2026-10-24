"""Pure application eligibility rule used for basis-path testing (FR-009/BR-002)."""

import datetime as dt
from typing import Optional


def check_application_eligibility(opp_status: str, deadline: Optional[dt.date], today: dt.date,
                                  already_applied: bool) -> tuple[bool, str]:
    if opp_status != "Published":
        return False, "Opportunity is not open"
    if deadline is not None and deadline < today:
        return False, "Deadline passed"
    if already_applied:
        return False, "Already applied"
    return True, "OK"
