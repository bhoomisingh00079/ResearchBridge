"""
WHITE-BOX TESTING - Basis Path Testing
Unit under test: rules.check_application_eligibility()   (SRS FR-009, BR-002, FR-010)

Control-flow graph (nodes = numbered statements, predicates p1..p4):
  1 start
  2 p1: opp_status != "Published"          T -> 3 return (False,"not open")
  4 p2: deadline is not None               F -> 7
  5 p3: deadline < today                   T -> 6 return (False,"Deadline passed")
  7 p4: already_applied                    T -> 8 return (False,"Already applied")
  9 return (True,"OK")

Cyclomatic complexity  V(G) = P + 1 = 4 + 1 = 5   (= E - N + 2)
=> 5 linearly independent paths must be executed (basis set).
A 6th path (BP6) exists; it is a linear combination BP5 + BP2 - BP3 and is tested as an extra.
Run:  pytest -v test_whitebox_basis_path.py --cov=rules --cov-branch --cov-report=term-missing
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from rules import check_application_eligibility as f

TODAY = dt.date(2026, 10, 22)
FUT, PAST = TODAY + dt.timedelta(days=5), TODAY - dt.timedelta(days=1)

# id, path (predicate outcomes), inputs (status, deadline, already), expected
CASES = [
    ("BP1", "p1=T",                 ("Draft",     FUT,  False), (False, "Opportunity is not open")),
    ("BP2", "p1=F,p2=F,p4=T",       ("Published", None, True),  (False, "Already applied")),
    ("BP3", "p1=F,p2=F,p4=F",       ("Published", None, False), (True,  "OK")),
    ("BP4", "p1=F,p2=T,p3=T",       ("Published", PAST, False), (False, "Deadline passed")),
    ("BP5", "p1=F,p2=T,p3=F,p4=F",  ("Published", FUT,  False), (True,  "OK")),
    ("BP6 (extra)", "p1=F,p2=T,p3=F,p4=T", ("Published", FUT, True), (False, "Already applied")),
]

@pytest.mark.parametrize("tc_id,path,args,expected", CASES, ids=[c[0] for c in CASES])
def test_basis_paths(tc_id, path, args, expected):
    status, deadline, already = args
    assert f(status, deadline, TODAY, already) == expected

@pytest.mark.parametrize("status", ["Closed", "Archived", "Draft", ""])
def test_every_non_published_status_rejected(status):                 # p1 true-branch variants
    assert f(status, None, TODAY, False)[0] is False

def test_deadline_boundary_today_is_still_open():                     # BVA on p3: deadline == today
    assert f("Published", TODAY, TODAY, False) == (True, "OK")

def test_deadline_boundary_yesterday_is_closed():
    assert f("Published", TODAY - dt.timedelta(days=1), TODAY, False) == (False, "Deadline passed")

