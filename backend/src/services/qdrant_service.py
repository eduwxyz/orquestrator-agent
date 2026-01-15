"""Qdrant service for long-term memory vector storage."""

import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from ..config.qdrant import get_qdrant_settings
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for Qdrant vector database operations."""

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._settings = get_qdrant_settings()
        self._embedding_service = get_embedding_service()

    @property
    def client(self) -> QdrantClient:
        """Lazy initialize Qdrant client."""
        if self._client is None:
            logger.info(f"Connecting to Qdrant at {self._settings.url}")
            self._client = QdrantClient(
                host=self._settings.host,
                port=self._settings.port,
                api_key=self._settings.api_key,
                https=self._settings.https,
            )
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        """Ensure the learnings collection exists."""
        try:
            self._client.get_collection(self._settings.collection_name)
            logger.info(f"Collection '{self._settings.collection_name}' exists")
        except (UnexpectedResponse, Exception):
            logger.info(f"Creating collection '{self._settings.collection_name}'")
            self._client.create_collection(
                collection_name=self._settings.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self._settings.vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(f"Collection '{self._settings.collection_name}' created")

    def store_learning(
        self,
        goal_description: str,
        learning: str,
        cards_created: List[str],
        outcome: str,
        error_encountered: Optional[str] = None,
        fix_applied: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a learning in Qdrant.

        Args:
            goal_description: Original goal description
            learning: What was learned from this goal execution
            cards_created: List of card IDs created for this goal
            outcome: Result - 'success', 'partial', 'failed'
            error_encountered: Error message if any
            fix_applied: Fix that was applied if any
            tokens_used: Total tokens used
            cost_usd: Total cost in USD
            metadata: Additional metadata

        Returns:
            ID of the stored learning
        """
        # Generate embedding from goal + learning combined
        text_to_embed = f"{goal_description}\n\n{learning}"
        vector = self._embedding_service.embed_text(text_to_embed)

        # Create point
        point_id = str(uuid4())
        payload = {
            "goal_description": goal_description,
            "learning": learning,
            "cards_created": cards_created,
            "outcome": outcome,
            "error_encountered": error_encountered,
            "fix_applied": fix_applied,
            "timestamp": datetime.utcnow().isoformat(),
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            **(metadata or {}),
        }

        self.client.upsert(
            collection_name=self._settings.collection_name,
            points=[
                qdrant_models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        logger.info(f"Stored learning {point_id}: {learning[:50]}...")
        return point_id

    def query_learnings(
        self,
        query_text: str,
        limit: int = 5,
        score_threshold: float = 0.5,
        outcome_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query relevant learnings from Qdrant.

        Args:
            query_text: Text to search for similar learnings
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            outcome_filter: Filter by outcome ('success', 'partial', 'failed')

        Returns:
            List of relevant learnings with scores
        """
        vector = self._embedding_service.embed_text(query_text)

        # Build filter if needed
        query_filter = None
        if outcome_filter:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="outcome",
                        match=qdrant_models.MatchValue(value=outcome_filter),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self._settings.collection_name,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        learnings = []
        for result in results:
            learnings.append({
                "id": result.id,
                "score": result.score,
                **result.payload,
            })

        logger.info(f"Found {len(learnings)} relevant learnings for query")
        return learnings

    def get_learning_by_id(self, learning_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific learning by ID."""
        try:
            results = self.client.retrieve(
                collection_name=self._settings.collection_name,
                ids=[learning_id],
            )
            if results:
                return {"id": results[0].id, **results[0].payload}
        except Exception as e:
            logger.error(f"Error retrieving learning {learning_id}: {e}")
        return None

    def delete_learning(self, learning_id: str) -> bool:
        """Delete a learning by ID."""
        try:
            self.client.delete(
                collection_name=self._settings.collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=[learning_id],
                ),
            )
            logger.info(f"Deleted learning {learning_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting learning {learning_id}: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self._settings.collection_name)
            return {
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False


@lru_cache
def get_qdrant_service() -> QdrantService:
    """Get cached Qdrant service instance."""
    return QdrantService()
