"""Application configuration for ResearchBridge Backend."""
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./rb_dev.db")
AGENT_SERVICE_URL = os.environ.get("AGENT_SERVICE_URL", "http://localhost:8100")
AGENT_SERVICE_TOKEN = os.environ.get("AGENT_SERVICE_TOKEN", "dev-secret-token")
AGENT_TIMEOUT_SECONDS = float(os.environ.get("AGENT_TIMEOUT_SECONDS", "10.0"))  # NFR-002: 10s max

