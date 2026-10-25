from datetime import date


def check_application_eligibility(status: str, deadline: date | None, today: date,
                                  already_applied: bool) -> tuple[bool, str]:
    if status != "Published":
        return False, "Opportunity is not open"
    if deadline is not None and deadline < today:
        return False, "Deadline passed"
    if already_applied:
        return False, "Already applied"
    return True, "OK"
