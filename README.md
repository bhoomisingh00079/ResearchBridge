# ResearchBridge

ResearchBridge is a student and faculty research-collaboration platform. The backend API is built with FastAPI and SQLAlchemy; PostgreSQL is used by Docker Compose and SQLite is the default local development database.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
alembic upgrade head
python -m app.seed
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with interactive OpenAPI docs at `/docs`. Development mode creates missing tables on startup for convenience; use Alembic migrations for clean installs and production.

## Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Compose starts PostgreSQL and the API, applies migrations before serving traffic, builds the React client, and places the app behind Caddy for HTTPS. Open `https://localhost` for local use; Caddy creates a local certificate, which browsers may ask you to trust. For a public deployment, set `SITE_ADDRESS` and `PUBLIC_BASE_URL` to a DNS name pointing at the host and open ports 80/443. The sample database password is for local development only. Set a strong `POSTGRES_PASSWORD` and `SECRET_KEY` before any deployment; set `APP_ENV=production` to require `SECRET_KEY`, SMTP verification delivery, and disable development verification-token output.

Create the first administrator interactively from the backend directory with `python -m app.create_admin admin@ves.ac.in "ResearchBridge Admin"`. The command reads the password without echoing it and refuses to create a second initial administrator.

`ALLOWED_DOMAINS` is a comma-separated list used for registration. The default is `ves.ac.in`.

To create the first administrator in Compose, run `docker compose exec api python -m app.create_admin admin@ves.ac.in "ResearchBridge Admin"` and enter a password when prompted. From a local backend run, use the same command after changing into `backend/`.

For Vite development with hot reload, keep the API running in one terminal and run `npm install` then `VITE_API_BASE_URL=http://localhost:8000 npm run dev` from `frontend/`. The API's default CORS allowlist includes `http://localhost:5173`.

## Tests

```bash
cd backend
python -m pytest
```

The API test suite uses isolated temporary SQLite databases. Member C's internal service and experiment suites are documented in [docs/MEMBER_C_VERIFICATION.md](docs/MEMBER_C_VERIFICATION.md).

## Current API coverage

Identity and profiles, opportunity lifecycle and discovery, applications and faculty decisions, accepted-application project teams, and administrator user/audit endpoints are implemented. The project workspace, resources, milestones, notifications, recommendation letters, and frontend screens remain assigned to their respective workstreams and are not represented as complete here.
