# Persistir Estado de Execução dos Cards após Refresh

## 1. Resumo

Implementar persistência completa do estado de execução dos cards (logs, status e timestamps) para que essas informações não sejam perdidas após refresh da página ou reinicialização do servidor. Atualmente, os logs e status de execução são armazenados apenas em memória, causando perda de informações importantes quando a página é recarregada.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Persistir logs de execução no banco de dados
- [x] Manter status de execução (running, success, error) após refresh
- [x] Preservar timestamps de início/fim das execuções
- [x] Restaurar estado completo dos cards ao carregar a página
- [x] Manter histórico de execuções para cada card

### Fora do Escopo
- Migração de dados históricos (não existem dados anteriores)
- Implementação de cache adicional
- Otimização de performance do polling

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/models/execution.py` | Criar | Novo modelo SQLAlchemy para execuções |
| `backend/src/models/card.py` | Modificar | Adicionar relacionamento com execuções |
| `backend/src/database.py` | Modificar | Registrar novo modelo |
| `backend/src/agent.py` | Modificar | Persistir logs em BD ao invés de memória |
| `backend/src/main.py` | Modificar | Buscar logs do BD no endpoint GET |
| `backend/src/routes/cards.py` | Modificar | Incluir execução ativa ao retornar cards |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipo para execução persistida |
| `frontend/src/hooks/useAgentExecution.ts` | Modificar | Restaurar estado de execuções ao inicializar |
| `frontend/src/api/cards.ts` | Modificar | Buscar execuções junto com cards |
| `frontend/src/App.tsx` | Modificar | Passar execuções iniciais para hook |

### Detalhes Técnicos

#### 1. Modelo de Banco de Dados para Execuções

**backend/src/models/execution.py:**
```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

class ExecutionStatus(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.IDLE)
    command = Column(String)  # /plan, /implement, /test, /review
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # em segundos
    result = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)  # última execução ativa

    # Relacionamentos
    card = relationship("Card", back_populates="executions")
    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan")

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # info, error, warning, success, command, system
    content = Column(Text)
    sequence = Column(Integer)  # ordem do log

    # Relacionamento
    execution = relationship("Execution", back_populates="logs")
```

#### 2. Modificação no Agent para Persistir Logs

**backend/src/agent.py (modificações):**
```python
from models.execution import Execution, ExecutionLog, ExecutionStatus
from database import SessionLocal

async def execute_command_with_persistence(
    card_id: str,
    command: str,
    prompt: str
) -> dict:
    db = SessionLocal()
    try:
        # Desativar execuções anteriores do card
        db.query(Execution).filter_by(
            card_id=card_id,
            is_active=True
        ).update({"is_active": False})

        # Criar nova execução
        execution = Execution(
            card_id=card_id,
            command=command,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        db.add(execution)
        db.commit()

        # Stream handler modificado para persistir logs
        async def persist_stream_handler(event):
            log_entry = ExecutionLog(
                execution_id=execution.id,
                timestamp=datetime.utcnow(),
                type=event.get("type", "info"),
                content=event.get("content", ""),
                sequence=db.query(ExecutionLog).filter_by(
                    execution_id=execution.id
                ).count()
            )
            db.add(log_entry)
            db.commit()

            # Também enviar via SSE se houver conexão ativa
            if card_id in active_connections:
                await send_sse_event(card_id, event)

        # Executar comando com Claude
        result = await agent.run(prompt, stream_handler=persist_stream_handler)

        # Atualizar execução com resultado
        execution.status = ExecutionStatus.SUCCESS
        execution.completed_at = datetime.utcnow()
        execution.duration = (execution.completed_at - execution.started_at).total_seconds()
        execution.result = result
        db.commit()

        return {"success": True, "result": result, "execution_id": execution.id}

    except Exception as e:
        if execution:
            execution.status = ExecutionStatus.ERROR
            execution.completed_at = datetime.utcnow()
            execution.result = str(e)
            db.commit()
        raise
    finally:
        db.close()
```

#### 3. Endpoint para Buscar Logs do Banco

**backend/src/main.py (modificação):**
```python
@app.get("/api/logs/{card_id}")
async def get_logs(card_id: str):
    db = SessionLocal()
    try:
        # Buscar execução ativa do card
        execution = db.query(Execution).filter_by(
            card_id=card_id,
            is_active=True
        ).first()

        if not execution:
            return {
                "status": "idle",
                "logs": []
            }

        # Buscar logs ordenados
        logs = db.query(ExecutionLog).filter_by(
            execution_id=execution.id
        ).order_by(ExecutionLog.sequence).all()

        return {
            "cardId": card_id,
            "status": execution.status.value,
            "startedAt": execution.started_at.isoformat() if execution.started_at else None,
            "completedAt": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration": execution.duration,
            "result": execution.result,
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "type": log.type,
                    "content": log.content
                }
                for log in logs
            ]
        }
    finally:
        db.close()
```

#### 4. Incluir Execuções ao Buscar Cards

**backend/src/routes/cards.py (modificação):**
```python
@router.get("/cards", response_model=List[CardResponse])
def get_cards(db: Session = Depends(get_db)):
    cards = db.query(Card).all()

    # Para cada card, incluir execução ativa se houver
    cards_with_execution = []
    for card in cards:
        card_dict = card.to_dict()

        # Buscar execução ativa
        active_execution = db.query(Execution).filter_by(
            card_id=card.id,
            is_active=True
        ).first()

        if active_execution:
            card_dict["activeExecution"] = {
                "id": active_execution.id,
                "status": active_execution.status.value,
                "command": active_execution.command,
                "startedAt": active_execution.started_at.isoformat() if active_execution.started_at else None,
                "completedAt": active_execution.completed_at.isoformat() if active_execution.completed_at else None
            }

        cards_with_execution.append(card_dict)

    return cards_with_execution
```

#### 5. Frontend - Restaurar Estado ao Carregar

**frontend/src/hooks/useAgentExecution.ts (modificação):**
```typescript
export const useAgentExecution = (initialExecutions?: Map<string, ExecutionStatus>) => {
  const [executions, setExecutions] = useState<Map<string, ExecutionStatus>>(
    initialExecutions || new Map()
  );

  // Restaurar polling para execuções em andamento
  useEffect(() => {
    if (initialExecutions) {
      initialExecutions.forEach((execution, cardId) => {
        if (execution.status === 'running') {
          // Retomar polling para execuções em andamento
          startPolling(cardId);
        }
      });
    }
  }, []);

  // Resto do código permanece igual...
};
```

**frontend/src/App.tsx (modificação):**
```typescript
function App() {
  const [cards, setCards] = useState<Card[]>([]);
  const [initialExecutions, setInitialExecutions] = useState<Map<string, ExecutionStatus>>();

  useEffect(() => {
    const loadCards = async () => {
      try {
        const loadedCards = await cardsApi.fetchCards();
        setCards(loadedCards);

        // Construir mapa de execuções ativas
        const executionsMap = new Map<string, ExecutionStatus>();

        for (const card of loadedCards) {
          if (card.activeExecution) {
            // Buscar logs completos da execução
            const logsData = await cardsApi.fetchLogs(card.id);

            executionsMap.set(card.id, {
              cardId: card.id,
              status: card.activeExecution.status as any,
              startedAt: card.activeExecution.startedAt,
              completedAt: card.activeExecution.completedAt,
              logs: logsData.logs || [],
              result: logsData.result
            });
          }
        }

        setInitialExecutions(executionsMap);
      } catch (error) {
        console.error('[App] Failed to load cards:', error);
      }
    };

    loadCards();
  }, []);

  // Passar execuções iniciais para o hook
  const {
    executions,
    executePlan,
    executeImplement,
    executeTest,
    executeReview,
    clearExecution
  } = useAgentExecution(initialExecutions);

  // Resto do código...
}
```

#### 6. Migration para Criar Tabelas

**backend/alembic/versions/xxx_add_executions_table.py:**
```python
"""Add executions and execution_logs tables

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Criar tabela executions
    op.create_table('executions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('card_id', sa.String(), sa.ForeignKey('cards.id'), nullable=False),
        sa.Column('status', sa.Enum('IDLE', 'RUNNING', 'SUCCESS', 'ERROR', name='executionstatus')),
        sa.Column('command', sa.String()),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('duration', sa.Integer()),
        sa.Column('result', sa.Text()),
        sa.Column('is_active', sa.Boolean(), default=True)
    )

    # Criar tabela execution_logs
    op.create_table('execution_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('execution_id', sa.String(), sa.ForeignKey('executions.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime()),
        sa.Column('type', sa.String()),
        sa.Column('content', sa.Text()),
        sa.Column('sequence', sa.Integer())
    )

    # Índices para performance
    op.create_index('idx_executions_card_active', 'executions', ['card_id', 'is_active'])
    op.create_index('idx_execution_logs_execution', 'execution_logs', ['execution_id', 'sequence'])

def downgrade():
    op.drop_table('execution_logs')
    op.drop_table('executions')
    op.execute('DROP TYPE executionstatus')
```

---

## 4. Testes

### Unitários
- [x] Teste criação de Execution no banco
- [x] Teste criação de ExecutionLog com sequência correta
- [x] Teste desativação de execuções anteriores
- [x] Teste busca de execução ativa
- [x] Teste ordenação de logs por sequência

### Integração
- [x] Teste fluxo completo: executar /plan e verificar persistência
- [x] Teste refresh da página mantém logs visíveis
- [x] Teste reinicialização do servidor mantém histórico
- [x] Teste múltiplas execuções do mesmo card
- [x] Teste recuperação de execuções em andamento após refresh

### Testes Manuais
- [x] Criar card e executar /plan
- [x] Refresh da página durante execução (deve continuar mostrando progresso)
- [x] Refresh após conclusão (deve mostrar logs completos)
- [x] Reiniciar servidor backend e verificar persistência
- [x] Testar com múltiplos cards executando simultaneamente

---

## 5. Considerações

### Riscos
- **Crescimento do banco**: Logs podem acumular rapidamente
  - Mitigação: Implementar rotina de limpeza de logs antigos (>30 dias)

- **Performance do polling**: Muitos cards podem sobrecarregar
  - Mitigação: Implementar debounce e limitar polling ativo

- **Migração de dados**: Sistema em produção pode ter estado inconsistente
  - Mitigação: Migration deve ser idempotente e tratar casos edge

### Dependências
- Alembic para migrations do banco de dados
- SQLAlchemy relationships configurados corretamente
- Frontend deve aguardar dados iniciais antes de renderizar

### Melhorias Futuras
- Implementar WebSocket ao invés de polling
- Adicionar paginação para logs muito grandes
- Criar visualização de histórico de execuções
- Implementar cache Redis para logs recentes
- Adicionar compressão de logs antigos