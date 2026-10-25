from functools import lru_cache
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./researchbridge.db")
AGENT_SERVICE_URL = os.environ.get("AGENT_SERVICE_URL", "http://localhost:8100")
AGENT_SERVICE_TOKEN = os.environ.get("AGENT_SERVICE_TOKEN", "dev-secret-token")
AGENT_TIMEOUT_SECONDS = float(os.environ.get("AGENT_TIMEOUT_SECONDS", "10.0"))


class Settings:
    app_env: str = os.getenv("APP_ENV", "development").lower()
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./researchbridge.db")
    secret_key: str = os.getenv("SECRET_KEY", "")
    allowed_domains: frozenset[str] = frozenset(
        domain.strip().casefold().lstrip("@")
        for domain in os.getenv("ALLOWED_DOMAINS", "ves.ac.in").split(",")
        if domain.strip()
    )
    token_ttl_seconds: int = int(os.getenv("TOKEN_TTL_SECONDS", "43200"))
    frontend_origins: tuple[str, ...] = tuple(
        origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()
    )
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "researchbridge@localhost")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "https://localhost")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def signing_key(self) -> bytes:
        if self.secret_key:
            if self.is_production and len(self.secret_key.encode("utf-8")) < 32:
                raise RuntimeError("SECRET_KEY must contain at least 32 bytes in production")
            return self.secret_key.encode("utf-8")
        if self.is_production:
            raise RuntimeError("SECRET_KEY must be set in production")
        return b"researchbridge-local-development-key-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
