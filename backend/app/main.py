from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routers import admin, agent, applications, auth, dashboards, milestones, opportunities, projects


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.is_production:
        settings.signing_key  # Validate production secrets during startup/import.
        if not settings.smtp_host:
            raise RuntimeError("SMTP_HOST must be set in production so users can verify accounts")
    @asynccontextmanager
    async def lifespan(_application):
        if settings.app_env == "development":
            Base.metadata.create_all(bind=engine)
        yield

    application = FastAPI(
        title="ResearchBridge API",
        description="REST API for the Student Research Collaboration Platform",
        version="1.0.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        lifespan=lifespan,
    )
    application.add_middleware(CORSMiddleware, allow_origins=list(settings.frontend_origins),
                               allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                               allow_headers=["Authorization", "Content-Type"])
    application.include_router(auth.router)
    application.include_router(opportunities.router)
    application.include_router(applications.router)
    application.include_router(projects.router)
    application.include_router(admin.router)
    application.include_router(milestones.router)
    application.include_router(dashboards.router)
    application.include_router(agent.router)

    @application.get("/")
    def root():
        return {"message": "ResearchBridge API is running"}

    @application.get("/health")
    def health():
        return {"status": "healthy"}

    return application


app = create_app()
