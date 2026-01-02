from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

class ExecutionCache:
    """Cache em memória para logs de execução com TTL"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutos default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def get(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Busca execução do cache se não expirou"""
        if card_id not in self._cache:
            return None

        # Verifica TTL
        if datetime.utcnow() - self._timestamps[card_id] > self.ttl:
            # Expirou, remove do cache
            del self._cache[card_id]
            del self._timestamps[card_id]
            return None

        return self._cache[card_id]

    def set(self, card_id: str, data: Dict[str, Any]):
        """Adiciona ou atualiza execução no cache"""
        self._cache[card_id] = data
        self._timestamps[card_id] = datetime.utcnow()

    def invalidate(self, card_id: str):
        """Remove execução do cache"""
        if card_id in self._cache:
            del self._cache[card_id]
            del self._timestamps[card_id]

    async def cleanup(self):
        """Remove entradas expiradas periodicamente"""
        while True:
            await asyncio.sleep(60)  # Limpa a cada minuto
            now = datetime.utcnow()
            expired = [
                card_id
                for card_id, timestamp in self._timestamps.items()
                if now - timestamp > self.ttl
            ]
            for card_id in expired:
                self.invalidate(card_id)

# Instância global
execution_cache = ExecutionCache()