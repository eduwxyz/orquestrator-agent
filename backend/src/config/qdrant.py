"""Qdrant configuration for long-term memory."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class QdrantSettings(BaseSettings):
    """Qdrant connection and collection settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="QDRANT_",
        extra="ignore",
    )

    # Connection
    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    api_key: str | None = None
    https: bool = False

    # Collection settings
    collection_name: str = "zenflow_learnings"
    vector_size: int = 384  # all-MiniLM-L6-v2 dimension

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"

    @property
    def url(self) -> str:
        """Get Qdrant URL."""
        protocol = "https" if self.https else "http"
        return f"{protocol}://{self.host}:{self.port}"


@lru_cache
def get_qdrant_settings() -> QdrantSettings:
    """Get cached Qdrant settings instance."""
    return QdrantSettings()
