# Correção do Feed de Atividade Recente com Timestamps Reais

## 1. Resumo

O feed de "Atividade Recente" atualmente exibe timestamps simulados (gerados aleatoriamente) em vez de usar os timestamps reais do banco de dados. Esta implementação corrigirá o problema criando um sistema de log de atividades persistente que rastreia todas as mudanças dos cards em tempo real, permitindo que o feed exiba informações precisas sobre quando as ações realmente ocorreram.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Criar tabela `activity_logs` no banco de dados para armazenar histórico de atividades
- [x] Implementar sistema de logging automático para todas as mudanças de cards
- [x] Substituir timestamps simulados por dados reais do banco
- [x] Adicionar endpoint API para recuperar atividades ordenadas por timestamp
- [x] Integrar o frontend com a nova API de atividades reais
- [ ] Manter compatibilidade com WebSocket para atualizações em tempo real

### Fora do Escopo
- Migração de dados históricos (começaremos a registrar a partir da implementação)
- Interface de administração para gerenciar logs
- Exportação de relatórios de atividades

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/alembic/versions/xxx_create_activity_logs_table.py` | Criar | Migration para criar tabela activity_logs |
| `backend/src/models/activity_log.py` | Criar | Modelo SQLAlchemy para logs de atividade |
| `backend/src/repositories/activity_repository.py` | Criar | Repositório para gerenciar logs de atividade |
| `backend/src/routes/activities.py` | Criar | Endpoint API para buscar atividades |
| `backend/src/repositories/card_repository.py` | Modificar | Adicionar logging automático em operações de cards |
| `backend/src/main.py` | Modificar | Registrar nova rota de atividades |
| `frontend/src/api/activities.ts` | Criar | Cliente API para buscar atividades |
| `frontend/src/components/Dashboard/ActivityFeed.tsx` | Modificar | Usar dados reais em vez de simulados |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos para atividades da API |

### Detalhes Técnicos

#### 3.1 Modelo de Banco de Dados

```python
# backend/src/models/activity_log.py
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.src.database import Base

class ActivityType(enum.Enum):
    CREATED = "created"
    MOVED = "moved"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    UPDATED = "updated"
    EXECUTED = "executed"
    COMMENTED = "commented"

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    activity_type = Column(Enum(ActivityType), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Metadados da atividade
    from_column = Column(String, nullable=True)  # Para movimentações
    to_column = Column(String, nullable=True)
    old_value = Column(Text, nullable=True)  # Para updates
    new_value = Column(Text, nullable=True)
    user_id = Column(String, nullable=True)  # Para rastrear quem fez a ação
    description = Column(Text, nullable=True)  # Descrição adicional

    # Relacionamentos
    card = relationship("Card", back_populates="activity_logs")
```

#### 3.2 Repositório de Atividades

```python
# backend/src/repositories/activity_repository.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.src.models.activity_log import ActivityLog, ActivityType
from backend.src.models.card import Card
import uuid

class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_activity(
        self,
        card_id: str,
        activity_type: ActivityType,
        from_column: Optional[str] = None,
        to_column: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        description: Optional[str] = None
    ) -> ActivityLog:
        """Registra uma nova atividade"""
        activity = ActivityLog(
            id=str(uuid.uuid4()),
            card_id=card_id,
            activity_type=activity_type,
            timestamp=datetime.utcnow(),
            from_column=from_column,
            to_column=to_column,
            old_value=old_value,
            new_value=new_value,
            description=description
        )

        self.session.add(activity)
        await self.session.commit()
        return activity

    async def get_recent_activities(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Busca atividades recentes com informações do card"""
        query = (
            select(ActivityLog, Card.title, Card.description)
            .join(Card, ActivityLog.card_id == Card.id)
            .order_by(desc(ActivityLog.timestamp))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        activities = []

        for activity, card_title, card_description in result:
            activities.append({
                "id": activity.id,
                "cardId": activity.card_id,
                "cardTitle": card_title,
                "cardDescription": card_description,
                "type": activity.activity_type.value,
                "timestamp": activity.timestamp.isoformat(),
                "fromColumn": activity.from_column,
                "toColumn": activity.to_column,
                "oldValue": activity.old_value,
                "newValue": activity.new_value,
                "description": activity.description
            })

        return activities
```

#### 3.3 Integração no CardRepository

```python
# backend/src/repositories/card_repository.py (modificações)

from backend.src.repositories.activity_repository import ActivityRepository
from backend.src.models.activity_log import ActivityType

class CardRepository:
    # ... código existente ...

    async def move_card(self, card_id: str, target_column_id: str) -> Card:
        """Move card para outra coluna com logging de atividade"""
        card = await self.get_card(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")

        old_column = card.columnId
        card.columnId = target_column_id
        card.updated_at = datetime.utcnow()

        # Registrar atividade
        activity_repo = ActivityRepository(self.session)

        # Determinar tipo de atividade
        if target_column_id == "done":
            activity_type = ActivityType.COMPLETED
        elif target_column_id == "archived":
            activity_type = ActivityType.ARCHIVED
        else:
            activity_type = ActivityType.MOVED

        await activity_repo.log_activity(
            card_id=card_id,
            activity_type=activity_type,
            from_column=old_column,
            to_column=target_column_id,
            description=f"Card movido de {old_column} para {target_column_id}"
        )

        await self.session.commit()
        return card

    async def create_card(self, card_data: Dict[str, Any]) -> Card:
        """Cria novo card com logging de atividade"""
        card = Card(**card_data)
        self.session.add(card)
        await self.session.commit()

        # Registrar atividade de criação
        activity_repo = ActivityRepository(self.session)
        await activity_repo.log_activity(
            card_id=card.id,
            activity_type=ActivityType.CREATED,
            to_column=card.columnId,
            description="Card criado"
        )

        return card
```

#### 3.4 Endpoint API

```python
# backend/src/routes/activities.py
from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.database import get_async_session
from backend.src.repositories.activity_repository import ActivityRepository

router = APIRouter(prefix="/api/activities", tags=["activities"])

@router.get("/recent")
async def get_recent_activities(
    limit: int = Query(default=10, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """Retorna atividades recentes ordenadas por timestamp"""
    repo = ActivityRepository(session)
    activities = await repo.get_recent_activities(limit=limit, offset=offset)
    return activities

@router.get("/card/{card_id}")
async def get_card_activities(
    card_id: str,
    session: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """Retorna histórico de atividades de um card específico"""
    repo = ActivityRepository(session)
    activities = await repo.get_card_activities(card_id)
    return activities
```

#### 3.5 Cliente API Frontend

```typescript
// frontend/src/api/activities.ts
import { API_BASE_URL } from './config';

export interface Activity {
  id: string;
  cardId: string;
  cardTitle: string;
  cardDescription?: string;
  type: 'created' | 'moved' | 'completed' | 'archived' | 'updated' | 'executed';
  timestamp: string;
  fromColumn?: string;
  toColumn?: string;
  oldValue?: string;
  newValue?: string;
  description?: string;
}

export const fetchRecentActivities = async (
  limit: number = 10,
  offset: number = 0
): Promise<Activity[]> => {
  const response = await fetch(
    `${API_BASE_URL}/activities/recent?limit=${limit}&offset=${offset}`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch activities: ${response.statusText}`);
  }

  return response.json();
};

export const fetchCardActivities = async (cardId: string): Promise<Activity[]> => {
  const response = await fetch(`${API_BASE_URL}/activities/card/${cardId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch card activities: ${response.statusText}`);
  }

  return response.json();
};
```

#### 3.6 Componente ActivityFeed Atualizado

```typescript
// frontend/src/components/Dashboard/ActivityFeed.tsx (modificações principais)
import React, { useEffect, useState } from 'react';
import { fetchRecentActivities, Activity } from '../../api/activities';
// ... outros imports ...

interface ActivityFeedProps {
  maxItems?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  maxItems = 10,
  autoRefresh = true,
  refreshInterval = 30000, // 30 segundos
}) => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadActivities = async () => {
    try {
      const data = await fetchRecentActivities(maxItems);
      setActivities(data);
      setError(null);
    } catch (err) {
      setError('Falha ao carregar atividades');
      console.error('Error loading activities:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();

    // Auto-refresh se habilitado
    if (autoRefresh) {
      const interval = setInterval(loadActivities, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [maxItems, autoRefresh, refreshInterval]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'agora mesmo';
    if (diffMins < 60) return `há ${diffMins} min`;
    if (diffHours < 24) return `há ${diffHours}h`;
    if (diffDays < 7) return `há ${diffDays}d`;

    return date.toLocaleDateString('pt-BR', {
      day: 'numeric',
      month: 'short'
    });
  };

  // ... resto do componente com renderização ...

  if (isLoading) {
    return <div className={styles.loading}>Carregando atividades...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (activities.length === 0) {
    return (
      <div className={styles.empty}>
        Nenhuma atividade recente
      </div>
    );
  }

  return (
    <div className={styles.activityFeed}>
      <div className={styles.header}>
        <h3>Atividade Recente</h3>
        <span className={styles.badge}>{activities.length}</span>
      </div>

      <div className={styles.timeline}>
        {activities.map((activity, index) => (
          <div
            key={activity.id}
            className={styles.timelineItem}
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <div className={`${styles.icon} ${styles[`icon-${activity.type}`]}`}>
              {getActivityIcon(activity.type)}
            </div>

            <div className={styles.content}>
              <div className={styles.title}>
                {getActivityTitle(activity)}
              </div>
              <div className={styles.timestamp}>
                {formatTimestamp(activity.timestamp)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {activities.length >= maxItems && (
        <button className={styles.viewAll}>
          Ver todo histórico
        </button>
      )}
    </div>
  );
};
```

---

## 4. Testes

### Unitários
- [ ] Teste do modelo ActivityLog (criação, validação de campos)
- [ ] Teste do ActivityRepository (log_activity, get_recent_activities)
- [ ] Teste de integração CardRepository com logging automático
- [ ] Teste do endpoint /api/activities/recent
- [ ] Teste do formatTimestamp com diferentes intervalos de tempo
- [ ] Teste do componente ActivityFeed com dados mockados

### Integração
- [ ] Teste de criação de card gerando log de atividade
- [ ] Teste de movimentação de card entre colunas
- [ ] Teste de arquivamento e conclusão de cards
- [ ] Teste de paginação de atividades
- [ ] Teste de auto-refresh do feed

### E2E
- [ ] Criar card e verificar aparição imediata no feed
- [ ] Mover card e verificar atualização do timestamp
- [ ] Verificar ordenação correta (mais recente primeiro)

---

## 5. Considerações

### Riscos
- **Volume de dados:** Com muitas atividades, a tabela pode crescer rapidamente
  - **Mitigação:** Implementar política de retenção (ex: deletar logs > 90 dias)
  - **Mitigação:** Adicionar índices apropriados na tabela

- **Performance:** Queries frequentes podem impactar performance
  - **Mitigação:** Implementar cache Redis para atividades recentes
  - **Mitigação:** Usar paginação eficiente

### Dependências
- Migration do banco deve ser executada antes do deploy
- Frontend e backend devem ser deployados em conjunto

### Melhorias Futuras
- Adicionar filtros por tipo de atividade
- Implementar busca por período de tempo
- Adicionar notificações push para atividades importantes
- Criar dashboard de analytics baseado nos logs