"""Centralized Settings — single source of truth for all configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app config in one typed object. Required fields fail at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    # ---- Vault ----
    vault_addr: str = Field(..., min_length=1)
    vault_root_token: str = Field(..., min_length=1)

    # ---- App database ----
    db_user: str
    db_password: str
    db_name: str
    db_host: str = "db"
    db_port: int = 5432

    # ---- Redis ----
    redis_host: str = "redis"
    redis_port: int = 6379

    # ---- MinIO ----
    minio_endpoint: str = "minio:9000"
    minio_root_user: str
    minio_root_password: str
    minio_secure: bool = False  # http in dev

    # ---- Langfuse ----
    langfuse_host: str = "http://langfuse-web:3000"

    # ---- Auth ----
    jwt_lifetime_seconds: int = 900  # 15 min access token
    refresh_lifetime_seconds: int = 604800  # 7 days refresh token
    cookie_secure: bool = False  # set True in prod

    # ---- Widget bundle origin (where the React build is served from) ----
    # Used by the iframe wrapper in widget_loader to point at the static widget bundle.
    widget_bundle_origin: str = "http://localhost:8080"

    # ---- App ----
    log_level: str = "INFO"
    environment: str = "dev"

    @property
    def db_dsn(self) -> str:
        """Builds the async Postgres DSN from individual components."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns the same Settings instance every call (cached)."""
    return Settings()  # type: ignore[call-arg]
