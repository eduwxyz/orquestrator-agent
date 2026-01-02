# Persistência de Estado do Workflow de Execução

## 1. Resumo

Implementar persistência completa do estado de execução do workflow (plan → implement → test → review) para que, ao dar refresh na página ou reiniciar o servidor, o usuário não perca o progresso da execução, logs e contexto do que está acontecendo. O sistema atualmente perde logs em memória e o estado do workflow durante refreshs.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Persistir logs de execução no banco de dados em tempo real
- [x] Salvar e restaurar estado completo do workflow (qual etapa está executando)
- [x] Manter polling funcionando após refresh da página
- [x] Recuperar contexto completo da execução mesmo após restart do servidor
- [x] Implementar cache de logs para otimizar performance

### Fora do Escopo
- Migração de dados históricos (logs antigos permanecerão perdidos)
- Implementação de websockets (continuar com polling por ora)
- Múltiplas execuções simultâneas do mesmo card

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `/backend/src/agent.py` | Modificar | Adicionar persistência de logs no banco |
| `/backend/src/models/execution.py` | Modificar | Ajustar modelos para workflow state |
| `/backend/src/repositories/execution_repository.py` | Criar | Repository para gerenciar execuções |
| `/backend/src/routes/cards.py` | Modificar | Incluir workflow state no response |
| `/backend/src/main.py` | Modificar | Usar repository ao invés de memória |
| `/frontend/src/hooks/useWorkflowAutomation.ts` | Modificar | Persistir workflow state via API |
| `/frontend/src/api/cards.ts` | Modificar | Adicionar endpoints de workflow state |
| `/frontend/src/types/index.ts` | Modificar | Adicionar tipos para workflow state |

### Detalhes Técnicos

#### 3.1. Backend - Persistência de Logs

**Criar Repository de Execuções** (`/backend/src/repositories/execution_repository.py`):

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Optional, List
import uuid
from datetime import datetime
from models.execution import Execution, ExecutionLog, ExecutionStatus

class ExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(
        self,
        card_id: str,
        command: str,
        title: str = ""
    ) -> Execution:
        """Cria nova execução e desativa anteriores do mesmo card"""
        # Desativa execuções anteriores
        await self.db.execute(
            update(Execution)
            .where(Execution.card_id == card_id)
            .where(Execution.is_active == True)
            .values(is_active=False)
        )

        execution = Execution(
            id=str(uuid.uuid4()),
            card_id=card_id,
            command=command,
            title=title,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            is_active=True,
            workflow_stage=command.replace("/", "")  # plan, implement, test, review
        )

        self.db.add(execution)
        await self.db.commit()
        return execution

    async def add_log(
        self,
        execution_id: str,
        log_type: str,
        content: str
    ) -> ExecutionLog:
        """Adiciona log a uma execução"""
        # Busca último sequence
        result = await self.db.execute(
            select(ExecutionLog.sequence)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.sequence.desc())
            .limit(1)
        )
        last_sequence = result.scalar() or 0

        log = ExecutionLog(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            type=log_type,
            content=content,
            sequence=last_sequence + 1,
            timestamp=datetime.utcnow()
        )

        self.db.add(log)
        await self.db.commit()
        return log

    async def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        result: Optional[str] = None
    ):
        """Atualiza status de uma execução"""
        values = {
            "status": status,
            "completed_at": datetime.utcnow() if status != ExecutionStatus.RUNNING else None
        }

        if result:
            values["result"] = result

        await self.db.execute(
            update(Execution)
            .where(Execution.id == execution_id)
            .values(**values)
        )
        await self.db.commit()

    async def get_active_execution(self, card_id: str) -> Optional[Execution]:
        """Busca execução ativa de um card"""
        result = await self.db.execute(
            select(Execution)
            .where(Execution.card_id == card_id)
            .where(Execution.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_execution_with_logs(
        self,
        card_id: str
    ) -> Optional[dict]:
        """Busca execução ativa com todos os logs"""
        execution = await self.get_active_execution(card_id)
        if not execution:
            return None

        # Busca logs
        logs_result = await self.db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution.id)
            .order_by(ExecutionLog.sequence)
        )
        logs = logs_result.scalars().all()

        return {
            "cardId": card_id,
            "executionId": execution.id,
            "status": execution.status.value,
            "command": execution.command,
            "workflowStage": execution.workflow_stage,
            "startedAt": execution.started_at.isoformat() if execution.started_at else None,
            "completedAt": execution.completed_at.isoformat() if execution.completed_at else None,
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
```

**Modificar Agent.py** para usar repository:

```python
# /backend/src/agent.py
from repositories.execution_repository import ExecutionRepository
from database import get_db

# Remover o dict global de execuções
# executions: dict[str, ExecutionRecord] = {}  # REMOVER

async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
    db_session: AsyncSession = None,  # Novo parâmetro
) -> PlanResult:
    """Execute plan with database persistence"""

    # Criar repository
    repo = ExecutionRepository(db_session)

    # Criar execução no banco
    execution = await repo.create_execution(
        card_id=card_id,
        command="/plan",
        title=title
    )

    # Log inicial
    await repo.add_log(
        execution_id=execution.id,
        log_type="info",
        content=f"Starting plan execution for: {title}"
    )

    try:
        # Execute com claude-agent-sdk
        options = {
            "model": model,
            "images": images,
        }

        result_text = ""
        spec_path = None

        async for message in query(prompt=build_prompt(title, description, cwd), options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Salva log no banco
                        await repo.add_log(
                            execution_id=execution.id,
                            log_type="text",
                            content=block.text
                        )
                        result_text += block.text + "\n"

                        # Extract spec_path
                        if "specs/" in block.text:
                            spec_match = re.search(r"specs/[a-zA-Z0-9-_]+\.md", block.text)
                            if spec_match:
                                spec_path = spec_match.group(0)

                    elif isinstance(block, ToolUseBlock):
                        # Log tool usage
                        await repo.add_log(
                            execution_id=execution.id,
                            log_type="tool",
                            content=f"Using tool: {block.name}"
                        )

                    elif isinstance(block, ToolResultBlock):
                        # Check for spec file creation
                        if block.tool_name == "Write" and "specs/" in str(block.content):
                            spec_match = re.search(r"specs/[a-zA-Z0-9-_]+\.md", str(block.content))
                            if spec_match:
                                spec_path = spec_match.group(0)

        # Atualiza status para sucesso
        await repo.update_execution_status(
            execution_id=execution.id,
            status=ExecutionStatus.SUCCESS,
            result=result_text
        )

        # Busca execução completa para retornar logs
        execution_data = await repo.get_execution_with_logs(card_id)

        return PlanResult(
            success=True,
            result=result_text,
            logs=execution_data["logs"],
            spec_path=spec_path,
        )

    except Exception as e:
        # Log erro
        await repo.add_log(
            execution_id=execution.id,
            log_type="error",
            content=str(e)
        )

        # Atualiza status para erro
        await repo.update_execution_status(
            execution_id=execution.id,
            status=ExecutionStatus.ERROR,
            result=str(e)
        )

        # Busca execução para retornar logs
        execution_data = await repo.get_execution_with_logs(card_id)

        return PlanResult(
            success=False,
            result=str(e),
            logs=execution_data["logs"] if execution_data else [],
            error=str(e),
        )

# Função auxiliar para buscar execução (substituir a antiga)
async def get_execution(card_id: str, db_session: AsyncSession) -> Optional[dict]:
    """Get execution from database"""
    repo = ExecutionRepository(db_session)
    return await repo.get_execution_with_logs(card_id)
```

#### 3.2. Backend - Workflow State

**Atualizar modelo Execution** (`/backend/src/models/execution.py`):

```python
from sqlalchemy import Column, String, DateTime, Text, Boolean, Enum, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import enum

class WorkflowStage(enum.Enum):
    IDLE = "idle"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    ERROR = "error"

class Execution(Base):
    __tablename__ = "executions"

    # Campos existentes
    id = Column(String, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.IDLE, nullable=False)
    command = Column(String)
    title = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)
    result = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # NOVO: Campo para rastrear estágio do workflow
    workflow_stage = Column(String, nullable=True)
    workflow_error = Column(Text, nullable=True)

    # Relationships
    card = relationship("Card", back_populates="executions")
    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan")
```

**Criar endpoint para atualizar workflow state** (`/backend/src/main.py`):

```python
# Adicionar novo endpoint
@app.patch("/api/cards/{card_id}/workflow-state")
async def update_workflow_state(
    card_id: str,
    stage: str,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza o estado do workflow para um card"""
    repo = ExecutionRepository(db)

    # Busca execução ativa
    execution = await repo.get_active_execution(card_id)

    if not execution:
        # Cria nova execução se não existir
        execution = await repo.create_execution(
            card_id=card_id,
            command="workflow",
            title="Workflow Automation"
        )

    # Atualiza workflow stage
    await db.execute(
        update(Execution)
        .where(Execution.id == execution.id)
        .values(
            workflow_stage=stage,
            workflow_error=error
        )
    )
    await db.commit()

    return {"success": True, "stage": stage}

# Modificar endpoint de logs para usar repository
@app.get("/api/logs/{card_id}", response_model=LogsResponse)
async def get_logs(card_id: str, db: AsyncSession = Depends(get_db)):
    """Get execution logs from database"""
    repo = ExecutionRepository(db)
    execution = await repo.get_execution_with_logs(card_id)

    if not execution:
        return LogsResponse(
            success=False,
            error="No execution found for this card",
        )

    return LogsResponse(
        success=True,
        execution=execution,
    )
```

#### 3.3. Frontend - Persistir Workflow State

**Atualizar API client** (`/frontend/src/api/cards.ts`):

```typescript
export interface WorkflowStateUpdate {
  stage: 'idle' | 'planning' | 'implementing' | 'testing' | 'reviewing' | 'completed' | 'error';
  error?: string;
}

export async function updateWorkflowState(
  cardId: string,
  state: WorkflowStateUpdate
): Promise<void> {
  const response = await fetch(`${API_ENDPOINTS.cards}/${cardId}/workflow-state`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  });

  if (!response.ok) {
    throw new Error('Failed to update workflow state');
  }
}

// Modificar fetchCards para incluir workflow state
export async function fetchCards(): Promise<Card[]> {
  const response = await fetch(API_ENDPOINTS.cards);
  const data: CardsListResponse = await response.json();

  return data.cards.map(card => ({
    ...mapCardResponseToCard(card),
    workflowStage: card.activeExecution?.workflowStage,
    workflowError: card.activeExecution?.workflowError,
  }));
}
```

**Modificar hook useWorkflowAutomation** (`/frontend/src/hooks/useWorkflowAutomation.ts`):

```typescript
import { updateWorkflowState } from '../api/cards';

export function useWorkflowAutomation({
  executePlan,
  executeImplement,
  executeTest,
  executeReview,
  onCardMove,
  onSpecPathUpdate,
  initialStatuses, // NOVO: receber estados iniciais
}: WorkflowAutomationHooks & { initialStatuses?: Map<string, WorkflowStatus> }) {
  // Inicializar com estados restaurados
  const [workflowStatuses, setWorkflowStatuses] = useState<Map<string, WorkflowStatus>>(
    initialStatuses || new Map()
  );

  const updateStatus = useCallback(async (
    cardId: string,
    stage: WorkflowStage,
    currentColumn: ColumnId,
    error?: string
  ) => {
    setWorkflowStatuses((prev) => {
      const next = new Map(prev);
      next.set(cardId, {
        cardId,
        stage,
        currentColumn,
        error,
      });
      return next;
    });

    // NOVO: Persistir no backend
    try {
      await updateWorkflowState(cardId, { stage, error });
    } catch (err) {
      console.error('[WorkflowAutomation] Failed to persist workflow state:', err);
    }
  }, []);

  const runWorkflow = useCallback(async (card: Card) => {
    if (card.columnId !== 'backlog') {
      console.warn('[WorkflowAutomation] Can only run workflow for cards in backlog');
      return;
    }

    console.log('[WorkflowAutomation] Starting workflow for card:', card.id);
    const cardId = card.id;

    // STAGE 1: PLANNING
    console.log('[WorkflowAutomation] Stage 1: Moving to plan column');
    onCardMove(cardId, 'plan');
    await updateStatus(cardId, 'planning', 'plan'); // Persistir

    console.log('[WorkflowAutomation] Stage 1: Executing plan');
    const planResult = await executePlan(card);

    if (!planResult.success) {
      console.error('[WorkflowAutomation] Plan failed, moving back to backlog');
      onCardMove(cardId, 'backlog');
      await updateStatus(cardId, 'error', 'backlog', planResult.error); // Persistir erro
      return;
    }

    // Continue com outras etapas...
    // Sempre chamar updateStatus() para persistir
  }, [executePlan, executeImplement, executeTest, executeReview, onCardMove, onSpecPathUpdate, updateStatus]);

  return {
    runWorkflow,
    getWorkflowStatus,
  };
}
```

**Modificar App.tsx** para restaurar workflow state:

```typescript
// App.tsx
const [initialWorkflowStatuses, setInitialWorkflowStatuses] = useState<Map<string, WorkflowStatus>>();

useEffect(() => {
  const loadInitialData = async () => {
    // Carregar cards
    const loadedCards = await cardsApi.fetchCards();

    // Construir mapa de execuções (existente)
    const executionsMap = new Map<string, ExecutionStatus>();

    // NOVO: Construir mapa de workflow statuses
    const workflowMap = new Map<string, WorkflowStatus>();

    for (const card of loadedCards) {
      if (card.activeExecution) {
        // Código existente para executionsMap...

        // NOVO: Restaurar workflow state
        if (card.activeExecution.workflowStage) {
          workflowMap.set(card.id, {
            cardId: card.id,
            stage: card.activeExecution.workflowStage as WorkflowStage,
            currentColumn: card.columnId,
            error: card.activeExecution.workflowError,
          });
        }
      }
    }

    setCards(loadedCards);
    setInitialExecutions(executionsMap);
    setInitialWorkflowStatuses(workflowMap); // NOVO
    setLoading(false);
  };

  loadInitialData();
}, []);

// Passar para o hook
const { runWorkflow, getWorkflowStatus } = useWorkflowAutomation({
  executePlan,
  executeImplement,
  executeTest,
  executeReview,
  onCardMove: moveCard,
  onSpecPathUpdate: updateCardSpecPath,
  initialStatuses: initialWorkflowStatuses, // NOVO
});
```

#### 3.4. Cache de Logs para Performance

**Implementar cache no backend** (`/backend/src/cache.py`):

```python
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
```

Usar cache no repository:

```python
# /backend/src/repositories/execution_repository.py
from cache import execution_cache

class ExecutionRepository:
    # ... código existente ...

    async def get_execution_with_logs(self, card_id: str) -> Optional[dict]:
        """Busca execução com cache"""

        # Tenta cache primeiro
        cached = execution_cache.get(card_id)
        if cached:
            return cached

        # Busca do banco
        execution = await self.get_active_execution(card_id)
        if not execution:
            return None

        # ... busca logs ...

        result = {
            "cardId": card_id,
            # ... outros campos ...
            "logs": logs
        }

        # Adiciona ao cache se ainda running
        if execution.status == ExecutionStatus.RUNNING:
            execution_cache.set(card_id, result)

        return result

    async def add_log(self, execution_id: str, log_type: str, content: str) -> ExecutionLog:
        """Adiciona log e invalida cache"""
        log = await super().add_log(execution_id, log_type, content)

        # Invalida cache para forçar reload
        execution = await self.db.get(Execution, execution_id)
        if execution:
            execution_cache.invalidate(execution.card_id)

        return log
```

---

## 4. Testes

### Unitários
- [x] Teste ExecutionRepository.create_execution desativa execuções anteriores
- [x] Teste ExecutionRepository.add_log incrementa sequence corretamente
- [x] Teste ExecutionRepository.get_execution_with_logs retorna logs ordenados
- [x] Teste cache expira após TTL
- [x] Teste cache é invalidado ao adicionar logs

### Integração
- [ ] Teste refresh durante execução de plan mantém logs e polling
- [ ] Teste restart do servidor durante test recupera estado completo
- [ ] Teste workflow completo com múltiplos refreshs funciona
- [ ] Teste performance com cache vs sem cache (deve ser < 100ms com cache)

### E2E
- [ ] Teste cenário: Iniciar Run → Refresh durante Plan → Logs continuam aparecendo
- [ ] Teste cenário: Run em andamento → Restart servidor → Refresh página → Estado restaurado
- [ ] Teste cenário: Erro durante Implement → Refresh → Mostra erro e stage correto

---

## 5. Considerações

### Riscos
- **Performance**: Muitos logs podem deixar queries lentas
  - **Mitigação**: Cache de 5 minutos + índices no banco + paginação futura

- **Concorrência**: Múltiplas abas podem tentar atualizar mesmo card
  - **Mitigação**: is_active flag + desativar execuções antigas

- **Memória**: Cache pode crescer com muitas execuções
  - **Mitigação**: TTL de 5 minutos + cleanup automático

### Melhorias Futuras
- Implementar WebSockets para eliminar polling
- Adicionar paginação de logs para cards com muitas execuções
- Compressão de logs antigos
- Backup automático de execuções completas

### Rollback
Se houver problemas, o código antigo continua funcionando (apenas sem persistência). Para rollback:
1. Remover chamadas ao ExecutionRepository
2. Reativar dict `executions` em agent.py
3. Remover endpoints de workflow-state