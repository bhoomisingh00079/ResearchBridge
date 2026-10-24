# ResearchBridge: Student Research Collaboration Platform

ResearchBridge connects undergraduate and postgraduate students with faculty research projects. It enforces institutional access, collaborative milestone tracking, deterministic recommendation engines, and advisory artificial intelligence guidance without autonomous agent decisions.

Baseline specification: **SRS v1.2** (FR-001 to FR-038, NFR-001 to NFR-010, BR-001 to BR-006).

---

## 1. System Architecture

```
 Browser (React SPA)  --HTTPS/JSON-->  Reverse Proxy (TLS)
                                            |
                                    +-------v--------+   internal HTTP + X-Service-Token   +----------------+
                                    |  Backend API   |------------------------------------>|  Agent Service |
                                    |  FastAPI       |<------------------------------------|  (Python)      |
                                    |  auth, RBAC,   |   ranked matches / alerts           |  NO DB ACCESS  |
                                    |  business rules|                                     +----------------+
                                    +---+--------+---+
                                        |        |
                                    Database   Private Volume
```

### Architectural Invariants (SRS 5.2, FR-030, BR-005)
1. **Isolated Agent Container**: The agent service has **no database credentials or drivers**. The backend extracts minimal JSON slices (NFR-009) and persists recommendations.
2. **Advisory Role Only**: Agent code paths cannot alter `applications.status` or `project_members`. Autonomous decisions are strictly prohibited.
3. **Resilience & 10s Timeout (NFR-002)**: If the agent service times out or is unreachable, dashboards render gracefully with an advisory "unavailable" notice rather than failing.
4. **Permanent Dismissals (FR-031)**: Recommendations dismissed by the user are never re-created or re-shown.

---

## 2. Repository Layout

```
ResearchBridge/
├── backend/
│   ├── app/
│   │   ├── config.py             # Environment configuration & timeout limits
│   │   ├── db.py                 # SQLAlchemy session factory
│   │   ├── deps.py               # Auth & role verification dependencies
│   │   ├── models.py             # Relational data model (PostgreSQL / SQLite)
│   │   ├── rules.py              # Pure business rules (FR-009, BR-002)
│   │   ├── security.py           # PBKDF2 password hashing & token generation
│   │   ├── jobs/agent_scan.py    # Background scanner for progress alerts
│   │   ├── routers/              # auth, opportunities, applications, projects,
│   │   │                         # milestones, dashboards, agent
│   │   └── services/agent_client.py # HTTP client with 10s timeout & graceful fallback
│   ├── member_c/                 # Member C contract implementation & test suite
│   ├── tests/                    # Backend API, dashboard, and safety invariant tests
│   ├── Dockerfile
│   └── requirements.txt
├── agent_service/
│   ├── app.py                    # Internal authenticated API (port 8100)
│   ├── matching.py               # Deterministic scoring algorithms (FR-025..028)
│   ├── progress.py               # Overdue/inactivity & deadline alerts (FR-029, FR-035)
│   ├── tests/                    # Agent test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/AgentPanel.jsx  # Distinct advisory UI with 4 states & dismissal
│       └── pages/                     # Student, Faculty, and Coordinator dashboards
├── experiment/                   # Part II: Software Testing & Automation
│   ├── rules.py
│   ├── test_whitebox_basis_path.py    # Basis path testing (V(G)=5, 100% coverage)
│   ├── test_blackbox_ep_bva.py        # Equivalence partitioning & boundary value analysis
│   ├── selenium_orangehrm_login_ep.py # Selenium EP UI suite
│   ├── selenium_selectorshub_form.py  # Selenium BVA UI suite
│   └── performance_check.py
├── docker-compose.yml
└── docs/
    ├── PLAN.md                   # End-to-end technical plan
    └── MEMBER_C_VERIFICATION.md  # Verification records & test evidence
```

---

## 3. Quickstart Guide

### Option A: Docker Compose (Production-like)
```bash
# Clone the repository
git clone https://github.com/bhoomisingh00079/ResearchBridge.git
cd ResearchBridge

# Copy environment variables
cp .env.example .env

# Build and start services
docker compose up --build
```
- Backend API: `http://localhost:8000`
- Interactive API Docs: `http://localhost:8000/docs`
- Agent Service (Internal): `http://localhost:8100`

### Option B: Local Development
```bash
# 1. Install backend dependencies
cd backend
pip install -r requirements.txt

# 2. Run backend API
uvicorn main:app --reload --port 8000

# 3. In a separate terminal, run agent service
cd ../agent_service
pip install -r requirements.txt
uvicorn app:app --reload --port 8100
```

---

## 4. Verification & Testing Guide

### 1. Agent Service Unit & Integration Tests
```bash
pytest agent_service/tests/ -v
```
Verifies service token authentication, deterministic matching formulas, milestone overdue detection, and opportunity deadline alert generation.

### 2. Backend API & Safety Invariant Tests
```bash
pytest backend/tests/ -v
pytest backend/member_c/tests/ -v
```
Verifies:
- 10-second timeout enforcement (`NFR-002`)
- Data minimisation payload allowlisting (`NFR-009`)
- Dismissal persistence (`FR-031`)
- Server-side role gates on Student, Faculty, and Coordinator dashboards (`FR-032..034`)
- **Safety Invariant Check**: Agent routines cannot alter `applications.status` or `project_members` (`FR-030`, `SRS 5.2`)
- **Static Check**: Inspects AST to guarantee `agent_service/` contains zero database drivers or connection strings.

### 3. White-box Basis Path Testing (Part II Experiment)
```bash
pytest experiment/test_whitebox_basis_path.py -v --cov=experiment.rules --cov-branch
```
Executes all 5 linearly independent basis paths derived from the control flow graph of `check_application_eligibility` ($V(G) = 13 - 10 + 2 = 5$) to achieve 100% statement and branch coverage.

### 4. Black-box Equivalence Partitioning & Boundary Value Analysis
```bash
pytest experiment/test_blackbox_ep_bva.py -v
```
Verifies boundary conditions across registration password length (0, 7, 8, 9, 64), institutional email domains, capacity boundaries (-1, 0, 1, 2, 100), and milestone due dates.

### 5. Selenium WebDriver UI Automation
```bash
pip install selenium pytest
pytest -v experiment/selenium_orangehrm_login_ep.py experiment/selenium_selectorshub_form.py
```
*(Add `HEADLESS=1` to run without opening a browser window).*

---

## 5. Requirements Traceability Matrix (Appendix E)

| Requirement | Description | Owner | Verification Method | Status |
|---|---|---|---|---|
| **FR-001** | Institutional email registration & verification | Member A | EP/BVA Black-box Test | Complete |
| **FR-002** | Secure credential storage & generic errors | Member A | Security Test | Complete |
| **FR-003** | Server-side Role-Based Access Control (RBAC) | Member A | Route Matrix Test | Complete |
| **FR-004** | Student research profile & skill taxonomy | Member A | Functional Test | Complete |
| **FR-005** | Faculty expertise profile & bio | Member A | Functional Test | Complete |
| **FR-006** | Opportunity creation with positive capacity | Member A | BVA Test (capacity >= 1) | Complete |
| **FR-007** | Opportunity versioning & lifecycle states | Member A | State Transition Test | Complete |
| **FR-008** | Search and filter opportunities | Member A | Functional Test | Complete |
| **FR-009** | Application eligibility rules (BR-002) | Member A | White-box Basis Path Test | Complete |
| **FR-010** | Student application submission & withdrawal | Member A | Functional Test | Complete |
| **FR-011** | Faculty review & applicant comments | Member A | Functional Test | Complete |
| **FR-012** | Decision notifications & audit records | Member A | Audit Log Test | Complete |
| **FR-013** | Collaborative project creation | Member A | Functional Test | Complete |
| **FR-014** | Project workspace access control | Member A | Membership Access Test | Complete |
| **FR-015** | Resource metadata indexing | Member B | Functional Test | Complete |
| **FR-016** | Private file storage stream authorization | Member B | Security / Membership Test | Complete |
| **FR-017** | Resource modification and deletion | Member B | Functional Test | Complete |
| **FR-018** | Milestone creation & target date scheduling | Member B | Functional Test | Complete |
| **FR-019** | Milestone status lifecycle transitions | Member B | State Transition Test | Complete |
| **FR-020** | Overdue milestone boundary calculation | Member B | BVA Test (delta -1, 0, +1) | Complete |
| **FR-021** | Project audit trail and activity logging | Member B | Functional Test | Complete |
| **FR-022** | In-app notification delivery | Member B | Functional Test | Complete |
| **FR-023** | Notification read-state tracking | Member B | Functional Test | Complete |
| **FR-024** | Automated deadline reminder scheduler | Member B | Job Execution Test | Complete |
| **FR-025** | Deterministic student-opportunity matching | Member C | Agent Algorithm Test | Complete |
| **FR-026** | Explainable recommendation reason generation | Member C | Explainer Output Test | Complete |
| **FR-027** | Project team collaborator gap matching | Member C | Agent Gap-fill Test | Complete |
| **FR-028** | Platform-indexed resource recommendation | Member C | Agent Match Test | Complete |
| **FR-029** | Inactive & overdue milestone alert detection | Member C | Progress Scan Test | Complete |
| **FR-030** | Advisory agent restriction & database isolation | Member C | Safety Invariant & AST Test | Complete |
| **FR-031** | Permanent recommendation dismissal persistence | Member C | Persistence & Non-recreation Test | Complete |
| **FR-032** | Student Dashboard with independent agent panel | Member C | Dashboard API & UI Test | Complete |
| **FR-033** | Faculty Dashboard with pending & overdue tallies | Member C | Dashboard API & UI Test | Complete |
| **FR-034** | Coordinator Dashboard with aggregate platform metrics | Member C | Aggregates Test | Complete |
| **FR-035** | Opportunity deadline & low applicant alerts | Member C | Progress Action Test | Complete |
| **FR-036** | Letter of Recommendation request validation | Member B | Functional Test | Complete |
| **FR-037** | LOR performance summary generation | Member B | Functional Test | Complete |
| **FR-038** | Faculty LOR decision & delivery | Member B | Functional Test | Complete |

---

## 6. Non-Functional Requirements Verification

- **NFR-001 (Performance < 2.0s)**: Endpoints execute with database index coverage; tested via `experiment/performance_check.py`.
- **NFR-002 (Agent Timeout <= 10.0s)**: Client enforces strict 10s maximum timeout and fails open into graceful degradation.
- **NFR-003 (Concurrency 100 users)**: Asynchronous FastAPI architecture tested under locust benchmark profiles.
- **NFR-005 (Credential Security)**: PBKDF2-HMAC-SHA256 salted hashes with 100,000 iterations; passwords never stored in plaintext.
- **NFR-006 & NFR-007 (Authorization)**: Server-side token validation and explicit role checks on every non-public route.
- **NFR-009 (Data Minimisation)**: Agent service requests contain only non-identifying structured attributes.

