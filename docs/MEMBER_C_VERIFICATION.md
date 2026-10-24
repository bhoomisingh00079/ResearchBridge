# Member C implementation and verification

This guide records what Member C owns, the runnable pieces in this checkout, and the integration gaps that remain until the other workstreams provide their contracts.

## Run the isolated checks

From the repository root, install `experiment/requirements.txt`, then run:

```bash
python -m pytest agent_service/tests backend/member_c/tests experiment/test_whitebox_basis_path.py
```

Agent service entry point:

```bash
SERVICE_TOKEN=local-development-token backend/venv/bin/uvicorn agent_service.app:app --host 127.0.0.1 --port 8100
```

The internal endpoints require `X-Service-Token`; `/health` is the only unauthenticated route. Set a non-empty `SERVICE_TOKEN` in deployment. The service intentionally has no database package or database configuration. It consumes only the structured fields supplied by the backend.

## Member C handoffs

- `agent_service/` implements the token-protected internal matching and progress API.
- `backend/member_c/agent_client.py` filters opportunity payloads to IDs, domains, skills, and interests; caps the timeout at 10 seconds; and returns an unavailable result on agent errors.
- `backend/member_c/recommendations.py` defines the backend-owned persistence seam and an in-memory fake. Replace the fake with the shared database adapter when Member A's model arrives. Dismissed recommendation keys cannot be re-created.
- `backend/member_c/agent_routes.py` and `dashboard.py` provide route factories that accept Member A's authentication dependency and dashboard/store providers. Mount them from the production API after those contracts are available.
- `experiment/` contains the basis-path test and Selenium examples for the public practice sites.

The agent API has no endpoint or code path that can change application statuses or project membership. Recommendation ranking is advisory; only the host backend persists recommendations and handles dismissals.

## Verification status and integration gaps

The agent matching, progress boundaries, service-token checks, client failure shape, role gate, recommendation dismissal and application eligibility rule have local tests. Third-party Selenium runs are manual because they use shared public sites and require a locally installed browser; record their actual outcomes in `docs/PLAN.md` after running them.

The checkout currently contains only the root/health FastAPI scaffold. Authentication, opportunities, applications, milestones, shared database models, dashboards in the production app, and all frontend code are absent. Therefore the plan's API-level EP/BVA suite, own-platform Selenium suite, visual accessibility checks, end-to-end safety checks against real application/membership writes, and 100-concurrent-user NFR measurement cannot yet produce meaningful pass results. Do not report those gates as passed until the corresponding A/B endpoints and UI exist. Member C's router factories are integration-ready seams and deliberately do not modify `backend/main.py`, the shared CI workflow, or A/B-owned modules.

## Traceability snapshot

| Member C work | Evidence in this checkout | Current status |
|---|---|---|
| C1 internal API, auth, schemas, timeout | `agent_service/app.py`, `backend/member_c/agent_client.py` | Implemented in isolated packages |
| C2 opportunity, collaborator, resource matching | `agent_service/matching.py` and unit tests | Implemented with deterministic ranking/reasons |
| C3 milestone and opportunity alerts | `agent_service/progress.py` and boundary tests | Implemented |
| C4 data minimization, fail-safe, persistence seam, dismissal | `backend/member_c/` | Adapter seam ready; durable DB wiring awaits A's models |
| C5 dashboards and advisory panels | `backend/member_c/dashboard.py`, `agent_routes.py` | Route factories ready; production mount/UI awaits A and B contracts |
| C6 safety, EP/BVA, Selenium, performance | `agent_service/tests/`, `experiment/` | Unit/basis-path checks implemented; integrated API/UI/performance gates pending |
| C7 run docs and traceability | This guide | Handoffs and gaps documented |

## Third-party Selenium manual evidence

Install Chrome or Edge and run:

```bash
cd experiment
python -m pytest -v selenium_orangehrm_login_ep.py selenium_selectorshub_form.py
```

Use `HEADLESS=1` for headless runs. Selenium Manager may need network access to obtain a matching driver. The public sites can change locators or expected copy; calibrate the relevant test and record the change rather than treating a third-party page failure as a ResearchBridge defect.

For a basic 100-request latency check against an available endpoint, run `python experiment/performance_check.py http://127.0.0.1:8000/dashboard/student --token TOKEN`. It reports the success count and p95 latency and exits non-zero if any request fails or p95 exceeds 2 seconds. Run it against a representative database-backed deployment before using the measurement for NFR sign-off.

For manual evidence, record an OrangeHRM demo login with Selenium IDE and export the SelectorsHub practice steps with TestCase Studio. The demo credentials and live-site observations are test data only.

## Integration acceptance checklist

- [ ] Mount the route factories using the shared auth dependency and a durable recommendation adapter.
- [ ] Verify role-specific dashboard provider payloads and isolate recommendation failures from the core dashboard response.
- [ ] Add platform API EP/BVA tests for registration, capacity, milestone dates and status after A/B routes are available.
- [ ] Add own-platform Selenium selectors from the shipped `data-testid` contract when the frontend exists.
- [ ] Verify keyboard focus, readable errors, palette-token use, contrast, responsive navigation, reduced motion and truthful progress transitions against rendered screens.
- [ ] Confirm with an integration test that agent scans cannot write `applications.status` or create/delete `project_members`.
- [ ] Measure the specified 100 concurrent users against NFR-001/003 with a representative deployment and record latency/error results.
