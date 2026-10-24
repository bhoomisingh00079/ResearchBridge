"""ResearchBridge Backend - Main Application Entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db import init_db
from app.routers import agent, dashboards


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="ResearchBridge API",
    description="REST API for the Student Research Collaboration Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(dashboards.router)
app.include_router(agent.router)


@app.get("/")
def root():
    return {
        "message": "ResearchBridge API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
