"""Modelserver Settings — mirror of backend but only the fields modelserver needs."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Modelserver-side config."""

    model_config = SettingsConfigDict(env_file=".env", extra="forbid", case_sensitive=False)

    # ---- Vault ----
    vault_addr: str = Field(..., min_length=1)
    vault_root_token: str = Field(..., min_length=1)

    # ---- MinIO ----
    minio_endpoint: str = "minio:9000"
    minio_root_user: str
    minio_root_password: str
    minio_secure: bool = False

    # ---- Models ----
    classifier_model_key: str = "classifier/roberta-issue-cls-v1"

    # ---- Prompts ----
    prompts_dir: Path = Path("/app/prompts")

    # ---- LLM (Azure OpenAI; deployment name comes from Vault) ----
    llm_request_timeout: float = 60.0

    # ---- Embedders ----
    embedder_primary: str = "BAAI/bge-small-en-v1.5"
    embedder_challenger: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ---- Reranker ----
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
