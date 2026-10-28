from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
try:
    from member_b import router as member_b_router
except ImportError:
    from ..member_b import router as member_b_router

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
                               allow_headers=["*"])

    import re

    @application.middleware("http")
    async def normalize_slashes_middleware(request, call_next):
        if "//" in request.scope.get("path", ""):
            request.scope["path"] = re.sub(r"/+", "/", request.scope["path"])
        return await call_next(request)
    # Member B's paths precede the earlier workspace prototypes where paths
    # overlap, so membership-checked handlers remain the active endpoints.
    application.include_router(member_b_router)
    application.include_router(auth.router)
    application.include_router(opportunities.router)
    application.include_router(applications.router)
    application.include_router(projects.router)
    application.include_router(admin.router)
    application.include_router(milestones.router)
    application.include_router(dashboards.router)
    application.include_router(agent.router)

    static_dir = Path(__file__).resolve().parent.parent / "static"

    @application.get("/workspace", include_in_schema=False)
    def project_workspace_page():
        page = static_dir / "project-workspace.html"
        if not page.is_file():
            from fastapi import HTTPException
            raise HTTPException(404, "Project workspace UI is not installed")
        return FileResponse(page)

    @application.get("/workspace/{asset_name}", include_in_schema=False)
    def project_workspace_asset(asset_name: str):
        if asset_name not in {"project-workspace.css", "project-workspace.js"}:
            from fastapi import HTTPException
            raise HTTPException(404, "Asset not found")
        asset = static_dir / asset_name
        if not asset.is_file():
            from fastapi import HTTPException
            raise HTTPException(404, "Asset not found")
        return FileResponse(asset)

    @application.get("/")
    def root():
        return {"message": "ResearchBridge API is running"}

    @application.get("/health")
    def health():
        return {"status": "healthy"}

    return application


app = create_app()
