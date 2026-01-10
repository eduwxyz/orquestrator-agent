"""Auto cleanup service for moving old cards from Done to Completed."""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import asyncio
import logging

from ..models.card import Card

logger = logging.getLogger(__name__)


class AutoCleanupService:
    """Service for automatically cleaning up Done cards."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.cleanup_after_days = 7  # Configurável
        self.enabled = True  # Configurável

    async def cleanup_done_cards(self) -> int:
        """Move cards antigos de Done para Completed.

        Returns:
            Number of cards moved.
        """
        if not self.enabled:
            logger.info("Auto-cleanup is disabled")
            return 0

        cutoff_date = datetime.utcnow() - timedelta(days=self.cleanup_after_days)

        # Buscar cards em Done há mais tempo que o configurado
        result = await self.db.execute(
            select(Card).where(
                Card.column_id == "done",
                Card.completed_at < cutoff_date
            )
        )
        old_cards = result.scalars().all()

        # Mover para Completed
        moved_count = 0
        for card in old_cards:
            await self.db.execute(
                update(Card).where(Card.id == card.id).values(
                    column_id="completed",
                    updated_at=datetime.utcnow()
                )
            )
            logger.info(f"Auto-moved card {card.id} from Done to Completed")
            moved_count += 1

        await self.db.commit()
        return moved_count

    async def run_periodic_cleanup(self):
        """Executa limpeza periodicamente (1x por dia)."""
        while True:
            try:
                moved_count = await self.cleanup_done_cards()
                if moved_count > 0:
                    logger.info(f"Auto-cleanup moved {moved_count} cards to Completed")
            except Exception as e:
                logger.error(f"Error in auto-cleanup: {e}")

            # Executar uma vez por dia
            await asyncio.sleep(86400)
