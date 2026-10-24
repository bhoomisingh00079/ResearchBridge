import datetime as dt

import pytest

from experiment.rules import check_application_eligibility as eligible

TODAY = dt.date(2026, 10, 22)
FUTURE, PAST = TODAY + dt.timedelta(days=5), TODAY - dt.timedelta(days=1)
CASES = [
    ("BP1", ("Draft", FUTURE, False), (False, "Opportunity is not open")),
    ("BP2", ("Published", None, True), (False, "Already applied")),
    ("BP3", ("Published", None, False), (True, "OK")),
    ("BP4", ("Published", PAST, False), (False, "Deadline passed")),
    ("BP5", ("Published", FUTURE, False), (True, "OK")),
    ("BP6-extra", ("Published", FUTURE, True), (False, "Already applied")),
]


@pytest.mark.parametrize("case,args,expected", CASES, ids=[row[0] for row in CASES])
def test_basis_paths(case, args, expected):
    status, deadline, already_applied = args
    assert eligible(status, deadline, TODAY, already_applied) == expected


@pytest.mark.parametrize("status", ["Closed", "Archived", "Draft", ""])
def test_non_published_opportunity_is_rejected(status):
    assert eligible(status, None, TODAY, False)[0] is False


def test_deadline_today_is_open():
    assert eligible("Published", TODAY, TODAY, False) == (True, "OK")


def test_deadline_yesterday_is_closed():
    assert eligible("Published", PAST, TODAY, False) == (False, "Deadline passed")
