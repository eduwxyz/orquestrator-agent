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

    # Database
    database_url: str = "sqlite+aiosqlite:///./auth.db"

    # Multi-Database Configuration
    project_data_dir: str = ".project_data"

    # Server
    port: int = 3001


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
