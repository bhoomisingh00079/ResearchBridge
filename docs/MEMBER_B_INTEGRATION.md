# Member B integration notes

The Member B router is mounted by `backend/app/main.py`. The project workspace UI is served at `/workspace?project=<project_id>`.

## Current integration boundary

The router is mounted in the shared FastAPI app and uses its `current_user` dependency. On each request it reads the shared `ProjectMember` and `User` records to enforce access and roles. Member B's resource metadata, milestones, tasks, activity, notifications and letter state currently use an integration-fake in-process repository and reset when the process restarts. Replace the fake `Workspace` repository with shared database models before deployment. Private file bytes are stored separately under `PRIVATE_FILE_DIR` (default `./private-files`).

Authentication and token verification are provided by the shared backend; route-level membership is loaded from the shared project tables.

## Workspace routes

- Resources: `POST/GET /projects/{id}/resources`, `PUT/DELETE /resources/{id}`, `POST /projects/{id}/resources/upload`, `GET /resources/{id}/download`.
- Milestones and tasks: create/list milestones, update status, create/list tasks, update task status, and list overdue milestones.
- Activity: `GET /projects/{id}/activity?page=1&page_size=20` returns newest-first items with `total` and `has_more`.
- Notifications: `GET /notifications`, `POST /notifications/{id}/read`; `run_reminder_job()` is available to the scheduler and rechecks current incomplete milestone state.
- Recommendation letters: issue, request, participant-only summary, decision, and current-user list under `/lor`.

Uploads use the raw request body with `X-Filename`, `Content-Type`, and title/description query parameters. The adapter accepts PDF, TXT, CSV, ZIP, DOCX and XLSX up to 20 MiB, validates extension/type and basic file signatures, and never returns its storage reference to clients. File bytes are streamed only after project membership is checked.

## Integration requirements

1. Replace the in-process `Workspace` with shared tables and transactions; keep the route-level authorization and activity behavior.
2. Configure `PRIVATE_FILE_DIR` as a private persistent volume. Configure SMTP only if optional mail delivery is enabled; in-app notifications remain the source of truth.
