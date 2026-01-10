## 1. Resumo

Implementar auto-limpeza de cards na coluna Done com opção de remoção automática após período configurável. A solução criará uma nova coluna "Completed" para histórico persistente, permitindo que cards sejam removidos automaticamente de Done após período configurável (ex: 7 dias), mantendo o histórico completo sem acúmulo visual.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Evitar acúmulo visual de cards em Done
- [x] Manter histórico completo de cards concluídos
- [x] Permitir configuração de tempo de permanência em Done
- [x] Adicionar coluna "Completed" para histórico permanente
- [x] Implementar job de limpeza automática

### Fora do Escopo
- Modificação do fluxo de cancelamento/arquivo existente
- Alteração na lógica de transições SDLC
- Remoção permanente de dados do banco

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | ✅ Adicionar coluna "completed" e atualizar transições |
| `backend/src/schemas/card.py` | Modificar | ✅ Adicionar campo completed_at e settings |
| `backend/src/models/card.py` | Modificar | ✅ Adicionar campo completed_at para timestamp |
| `frontend/src/components/Column/Column.tsx` | Modificar | ✅ Adicionar lógica para coluna completed |
| `backend/src/services/auto_cleanup_service.py` | Criar | ✅ Serviço para limpeza automática |
| `backend/src/routes/settings.py` | Criar | ✅ Endpoints para configurações de limpeza |
| `frontend/src/pages/SettingsPage.tsx` | Modificar | ✅ Adicionar configurações de auto-limpeza |
| `frontend/src/api/settings.ts` | Criar | ✅ Cliente API para configurações |
| `backend/migrations/011_add_completed_column.sql` | Criar | ✅ Migration para nova coluna e campo |

### Detalhes Técnicos

#### 1. Nova Coluna e Transições

```typescript
// frontend/src/types/index.ts
export type ColumnId = 'backlog' | 'plan' | 'implement' | 'test' | 'review' | 'done' | 'completed' | 'archived' | 'cancelado';

export const COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'plan', title: 'Plan' },
  { id: 'implement', title: 'Implement' },
  { id: 'test', title: 'Test' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' },
  { id: 'completed', title: 'Completed' }, // Nova coluna
  { id: 'archived', title: 'Archived' },
  { id: 'cancelado', title: 'Cancelado' },
];

export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'done': ['completed', 'archived', 'cancelado'], // Done pode ir para Completed
  'completed': ['archived'], // Completed pode ser arquivado se necessário
  // ... resto permanece igual
};
```

#### 2. Modelo com Timestamp de Conclusão

```python
# backend/src/models/card.py
class Card(Base):
    # ... campos existentes ...

    # Campo para rastrear quando foi movido para Done
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when card was moved to Done"
    )
```

#### 3. Serviço de Auto-Limpeza

```python
# backend/src/services/auto_cleanup_service.py
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..models.card import Card
from ..database import get_db
import asyncio
import logging

logger = logging.getLogger(__name__)

class AutoCleanupService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.cleanup_after_days = 7  # Configurável
        self.enabled = True  # Configurável

    async def cleanup_done_cards(self):
        """Move cards antigos de Done para Completed."""
        if not self.enabled:
            return

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
        for card in old_cards:
            await self.db.execute(
                update(Card).where(Card.id == card.id).values(
                    column_id="completed",
                    updated_at=datetime.utcnow()
                )
            )
            logger.info(f"Auto-moved card {card.id} from Done to Completed")

        await self.db.commit()
        return len(old_cards)

    async def run_periodic_cleanup(self):
        """Executa limpeza periodicamente."""
        while True:
            try:
                moved_count = await self.cleanup_done_cards()
                if moved_count > 0:
                    logger.info(f"Auto-cleanup moved {moved_count} cards to Completed")
            except Exception as e:
                logger.error(f"Error in auto-cleanup: {e}")

            # Executar uma vez por dia
            await asyncio.sleep(86400)
```

#### 4. Configurações na UI

```tsx
// frontend/src/pages/SettingsPage.tsx - adicionar seção
<div className={styles.settingSection}>
  <h3>Auto-limpeza de Cards Concluídos</h3>
  <div className={styles.settingItem}>
    <label>
      <input
        type="checkbox"
        checked={autoCleanupEnabled}
        onChange={(e) => updateAutoCleanup({ enabled: e.target.checked })}
      />
      Mover automaticamente cards de Done para Completed
    </label>
  </div>

  <div className={styles.settingItem}>
    <label>
      Mover após
      <input
        type="number"
        min="1"
        max="30"
        value={cleanupAfterDays}
        onChange={(e) => updateAutoCleanup({ days: parseInt(e.target.value) })}
      />
      dias
    </label>
    <small>Cards em Done há mais tempo serão movidos para Completed automaticamente</small>
  </div>

  <div className={styles.infoBox}>
    <p>Cards em Completed:</p>
    <ul>
      <li>Mantêm histórico completo</li>
      <li>Podem ser visualizados quando necessário</li>
      <li>Não poluem a visualização do board ativo</li>
      <li>Podem ser arquivados manualmente se desejar</li>
    </ul>
  </div>
</div>
```

#### 5. Atualização ao Mover para Done

```python
# backend/src/repositories/card_repository.py - no método move()
if new_column_id == "done" and card.column_id != "done":
    # Marcar timestamp de conclusão
    card.completed_at = datetime.utcnow()
```

---

## 4. Testes

### Unitários
- [ ] Teste do serviço de auto-limpeza
- [ ] Teste de transição Done → Completed
- [ ] Teste de configurações de tempo
- [ ] Teste de timestamp completed_at

### Integração
- [ ] Teste do job periódico de limpeza
- [ ] Teste da API de configurações
- [ ] Teste da visualização de cards em Completed

---

## 5. Considerações

- **Migração de Dados:** Cards atualmente em Done receberão completed_at retroativo baseado em updated_at
- **Performance:** Job de limpeza executará apenas 1x ao dia para minimizar impacto
- **Configuração:** Administradores poderão desabilitar ou ajustar período (1-30 dias)
- **Visualização:** Coluna Completed será colapsável como Archived/Cancelado para economia de espaço
- **Histórico:** Nenhum dado será perdido, apenas reorganizado visualmente