"""Embedding service using sentence-transformers for vector generation."""

import logging
from typing import List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lazy loading to avoid importing heavy model at startup
_model = None


def _get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from ..config.qdrant import get_qdrant_settings

        settings = get_qdrant_settings()
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Embedding model loaded. Vector size: {settings.vector_size}")
    return _model


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy load model on first access."""
        if self._model is None:
            self._model = _get_model()
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def get_vector_size(self) -> int:
        """Get the dimension of embedding vectors."""
        from ..config.qdrant import get_qdrant_settings
        return get_qdrant_settings().vector_size


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service instance."""
    return EmbeddingService()
