"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # JWT Configuration
    jwt_secret_key: str = "dev-secret-key-change-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Database - Principal database centralizado no backend
    # Usa caminho absoluto para evitar problemas de diretório de trabalho
    database_url: str = "sqlite+aiosqlite:///auth.db"

    # Multi-Database Configuration
    project_data_dir: str = ".project_data"

    # NOVO: Flag para controlar local do database do projeto
    store_db_in_project: bool = True  # Store project database in .claude folder (True) or .project_data (False)

    # Flag para auto-migração de databases legados
    auto_migrate_legacy_db: bool = True  # Automatically migrate databases from .project_data to .claude

    # Server
    port: int = 3001

    # Orchestrator settings
    orchestrator_enabled: bool = True
    orchestrator_loop_interval_seconds: int = 180  # 3 minutes
    orchestrator_log_file: str = "orchestrator.log"
    orchestrator_usage_limit_percent: int = 80  # Pause if usage > 80%

    # Short-term memory settings
    short_term_memory_retention_hours: int = 24


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
