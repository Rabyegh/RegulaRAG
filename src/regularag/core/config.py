"""
Application configuration management.

Uses Pydantic Settings to load configuration from environment variables
and optional .env files. Credentials are never hardcoded.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="RegulaRAG", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    app_debug: bool = Field(default=False, description="Enable debug mode")

    # API server
    api_host: str = Field(default="0.0.0.0", description="API bind host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API bind port")
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for signing tokens (must be changed in production)",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application log level",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format",
    )

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated allowed CORS origins",
    )

    # ---------------------------------------------------------------------------
    # Regulatory Document Ingestion & Acquisition (Phase 2)
    # ---------------------------------------------------------------------------
    ingestion_raw_storage_dir: Path = Field(
        default=Path("data/raw"),
        description="Root directory for raw acquired regulatory documents",
    )
    ingestion_http_timeout_connect: float = Field(
        default=10.0,
        gt=0,
        description="HTTP connection timeout in seconds",
    )
    ingestion_http_timeout_read: float = Field(
        default=60.0,
        gt=0,
        description="HTTP read timeout in seconds",
    )
    ingestion_max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for transient HTTP failures",
    )
    ingestion_backoff_factor: float = Field(
        default=2.0,
        gt=0,
        description="Exponential backoff multiplier for retries",
    )
    ingestion_min_retry_delay: float = Field(
        default=1.0,
        ge=0,
        description="Minimum initial retry delay in seconds",
    )
    ingestion_max_retry_delay: float = Field(
        default=30.0,
        gt=0,
        description="Maximum retry delay ceiling in seconds",
    )
    ingestion_request_rate_limit: float = Field(
        default=1.0,
        ge=0,
        description="Minimum seconds between outbound requests to the same domain (request pacing)",
    )
    ingestion_user_agent: str = Field(
        default="RegulaRAG-Bot/0.1.0 (+https://github.com/Rabyegh/RegulaRAG; compliance-research)",
        description="User-Agent header for official regulatory repository acquisition",
    )

    # ---------------------------------------------------------------------------
    # Database (PostgreSQL) — optional until Phase 3
    # ---------------------------------------------------------------------------
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="regularag", description="PostgreSQL database name")
    postgres_user: str = Field(default="regularag_user", description="PostgreSQL user")
    postgres_password: str = Field(
        default="",
        description="PostgreSQL password (set via environment variable)",
    )
    database_url: str | None = Field(
        default=None,
        description="Full database DSN (overrides individual postgres_* settings)",
    )

    # ---------------------------------------------------------------------------
    # Elasticsearch — optional until Phase 4
    # ---------------------------------------------------------------------------
    elasticsearch_host: str = Field(default="localhost", description="Elasticsearch host")
    elasticsearch_port: int = Field(default=9200, description="Elasticsearch port")
    elasticsearch_scheme: Literal["http", "https"] = Field(
        default="http", description="Elasticsearch connection scheme"
    )
    elasticsearch_api_key: str | None = Field(default=None, description="Elasticsearch API key")

    # ---------------------------------------------------------------------------
    # Neo4j — optional until Phase 5
    # ---------------------------------------------------------------------------
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j bolt URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(
        default="",
        description="Neo4j password (set via environment variable)",
    )

    # ---------------------------------------------------------------------------
    # LLM Provider — optional until Phase 4
    # ---------------------------------------------------------------------------
    llm_provider: Literal["openai", "anthropic", "azure_openai", "ollama"] = Field(
        default="openai", description="LLM provider"
    )
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI chat model name")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model name"
    )
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic model name"
    )

    # ---------------------------------------------------------------------------
    # Embedding
    # ---------------------------------------------------------------------------
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-Transformers embedding model",
    )
    embedding_dimension: int = Field(default=384, ge=1, description="Embedding vector dimension")

    @field_validator("secret_key")
    @classmethod
    def warn_default_secret_key(cls, value: str) -> str:
        """Emit a warning when the default insecure secret key is used."""
        if value == "dev-secret-key-change-in-production":
            import warnings

            warnings.warn(
                "Using the default SECRET_KEY. Set a strong secret key before deploying.",
                stacklevel=2,
            )
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.app_env == "production"

    @property
    def effective_database_url(self) -> str:
        """Return the database DSN, preferring the explicit DATABASE_URL if set."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return the cached application settings singleton.

    Using ``lru_cache`` ensures the settings object is constructed once and
    reused throughout the application lifetime, which is also compatible with
    FastAPI's ``Depends`` dependency-injection pattern.
    """
    return AppSettings()
