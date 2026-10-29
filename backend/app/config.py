from functools import lru_cache
from pathlib import Path
import os

# Automatically load .env from the project root or working directory
for _env_candidate in [
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _env_candidate.is_file():
        try:
            with open(_env_candidate, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        _k, _v = _k.strip(), _v.strip().strip("'\"")
                        if _k and _k not in os.environ:
                            os.environ[_k] = _v
        except Exception:
            pass
        break

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
        origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "*,https://research-bridge-pi.vercel.app,http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()
    )
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "researchbridge.091416@gmail.com")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "orni myau qjwm mlos")
    smtp_from: str = os.getenv("SMTP_FROM", "researchbridge.091416@gmail.com")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "https://research-bridge-pi.vercel.app")

    @property
    def allows_all_domains(self) -> bool:
        return "*" in self.allowed_domains or "all" in self.allowed_domains

    def allows_domain(self, domain: str) -> bool:
        if self.allows_all_domains:
            return True
        return domain.strip().casefold().lstrip("@") in self.allowed_domains

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
