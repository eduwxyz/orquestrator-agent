# Seleção de Modelo de Execução por Etapa do Card

## 1. Resumo

Implementar a funcionalidade que permite ao usuário selecionar qual modelo Claude (Opus 4.5, Sonnet 4.5 ou Haiku 4.5) será utilizado em cada etapa do desenvolvimento (planejar, implementar, testar, revisar) ao criar um card no Kanban. Esta feature também modificará os comandos do Claude Code para aceitar o parâmetro de modelo, com Opus 4.5 como padrão. Esta necessidade surge da demanda por flexibilidade e controle de custos, permitindo usar modelos mais rápidos/econômicos em certas etapas e modelos mais robustos em outras.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar seleção de modelos por etapa na UI de criação de cards
- [x] Persistir configuração de modelos no banco de dados
- [x] Modificar backend para aceitar e passar parâmetros de modelo para Claude Agent SDK
- [x] Atualizar comandos slash (.claude/commands/*.md) para aceitar parâmetro de modelo
- [x] Definir Opus 4.5 como modelo padrão para todas as etapas
- [x] Suportar modelos: Opus 4.5, Sonnet 4.5 e Haiku 4.5

### Fora do Escopo
- Validação de créditos/custos por modelo
- Configurações globais de modelo (apenas por card)
- Modelos além dos três especificados

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/migrations/002_add_model_config_to_cards.sql` | Criar | Migration para adicionar campos de modelos na tabela cards |
| `backend/src/models/card.py` | Modificar | Adicionar campos model_plan, model_implement, model_test, model_review |
| `backend/src/schemas/card.py` | Modificar | Adicionar campos de modelo nos schemas (CardCreate, CardResponse, etc.) |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos ModelType e campos de modelo no Card |
| `frontend/src/components/AddCard/AddCard.tsx` | Modificar | Adicionar seletores de modelo na UI de criação |
| `frontend/src/components/AddCard/AddCard.module.css` | Modificar | Estilizar seletores de modelo |
| `backend/src/agent.py` | Modificar | Aceitar e usar parâmetro de modelo em ClaudeAgentOptions |
| `backend/src/main.py` | Modificar | Passar modelo nos endpoints execute-* |
| `backend/src/execution.py` | Modificar | Adicionar campo model nos requests |
| `.claude/commands/plan.md` | Modificar | Documentar parâmetro de modelo opcional |
| `.claude/commands/implement.md` | Modificar | Documentar parâmetro de modelo opcional |
| `.claude/commands/test-implementation.md` | Modificar | Documentar parâmetro de modelo opcional |
| `.claude/commands/review.md` | Modificar | Documentar parâmetro de modelo opcional |

### Detalhes Técnicos

#### 1. Migration de Banco de Dados

Criar `backend/migrations/002_add_model_config_to_cards.sql`:

```sql
-- Add model configuration columns to cards table
ALTER TABLE cards ADD COLUMN model_plan VARCHAR(20) DEFAULT 'opus-4.5';
ALTER TABLE cards ADD COLUMN model_implement VARCHAR(20) DEFAULT 'opus-4.5';
ALTER TABLE cards ADD COLUMN model_test VARCHAR(20) DEFAULT 'opus-4.5';
ALTER TABLE cards ADD COLUMN model_review VARCHAR(20) DEFAULT 'opus-4.5';
```

#### 2. Backend - Modelo de Dados

Em `backend/src/models/card.py`, adicionar:

```python
from sqlalchemy import String

class Card(Base):
    # ... campos existentes ...
    model_plan: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    model_implement: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    model_test: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    model_review: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
```

#### 3. Backend - Schemas

Em `backend/src/schemas/card.py`:

```python
from typing import Literal

ModelType = Literal["opus-4.5", "sonnet-4.5", "haiku-4.5"]

class CardBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    model_plan: ModelType = "opus-4.5"
    model_implement: ModelType = "opus-4.5"
    model_test: ModelType = "opus-4.5"
    model_review: ModelType = "opus-4.5"

class CardCreate(CardBase):
    pass

class CardResponse(BaseModel):
    # ... campos existentes ...
    model_plan: str = Field(..., alias="modelPlan")
    model_implement: str = Field(..., alias="modelImplement")
    model_test: str = Field(..., alias="modelTest")
    model_review: str = Field(..., alias="modelReview")
```

#### 4. Frontend - Types

Em `frontend/src/types/index.ts`:

```typescript
export type ModelType = 'opus-4.5' | 'sonnet-4.5' | 'haiku-4.5';

export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
  specPath?: string;
  modelPlan: ModelType;
  modelImplement: ModelType;
  modelTest: ModelType;
  modelReview: ModelType;
}
```

#### 5. Frontend - Componente AddCard

Em `frontend/src/components/AddCard/AddCard.tsx`:

```typescript
import { ModelType } from '../../types';

interface AddCardProps {
  columnId: ColumnId;
  onAdd: (
    title: string,
    description: string,
    columnId: ColumnId,
    modelPlan: ModelType,
    modelImplement: ModelType,
    modelTest: ModelType,
    modelReview: ModelType
  ) => void;
}

export function AddCard({ columnId, onAdd }: AddCardProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [modelPlan, setModelPlan] = useState<ModelType>('opus-4.5');
  const [modelImplement, setModelImplement] = useState<ModelType>('opus-4.5');
  const [modelTest, setModelTest] = useState<ModelType>('opus-4.5');
  const [modelReview, setModelReview] = useState<ModelType>('opus-4.5');

  const MODEL_OPTIONS: { value: ModelType; label: string }[] = [
    { value: 'opus-4.5', label: 'Opus 4.5' },
    { value: 'sonnet-4.5', label: 'Sonnet 4.5' },
    { value: 'haiku-4.5', label: 'Haiku 4.5' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      onAdd(
        title.trim(),
        description.trim(),
        columnId,
        modelPlan,
        modelImplement,
        modelTest,
        modelReview
      );
      // Reset states...
    }
  };

  // Renderizar selects para cada etapa
  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input type="text" placeholder="Card title" ... />
      <textarea placeholder="Description" ... />

      <div className={styles.modelSelectors}>
        <label>
          <span>Plan:</span>
          <select value={modelPlan} onChange={(e) => setModelPlan(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </label>

        <label>
          <span>Implement:</span>
          <select value={modelImplement} onChange={(e) => setModelImplement(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </label>

        <label>
          <span>Test:</span>
          <select value={modelTest} onChange={(e) => setModelTest(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </label>

        <label>
          <span>Review:</span>
          <select value={modelReview} onChange={(e) => setModelReview(e.target.value as ModelType)}>
            {MODEL_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </label>
      </div>

      <div className={styles.actions}>...</div>
    </form>
  );
}
```

#### 6. Frontend - Estilos

Em `frontend/src/components/AddCard/AddCard.module.css`:

```css
.modelSelectors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin: 0.75rem 0;
}

.modelSelectors label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #6b7280;
}

.modelSelectors span {
  font-weight: 500;
}

.modelSelectors select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
  cursor: pointer;
}

.modelSelectors select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}
```

#### 7. Backend - Agent Execution

Em `backend/src/execution.py`:

```python
class ExecutePlanRequest(BaseModel):
    card_id: str = Field(..., alias="cardId")
    title: str
    description: Optional[str] = None
    model: Optional[str] = "opus-4.5"  # Novo campo

class ExecuteImplementRequest(BaseModel):
    card_id: str = Field(..., alias="cardId")
    spec_path: str = Field(..., alias="specPath")
    model: Optional[str] = "opus-4.5"  # Novo campo
```

Em `backend/src/agent.py`, modificar as funções `execute_plan`, `execute_implement`, `execute_test_implementation`, `execute_review`:

```python
async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str = "opus-4.5",  # Novo parâmetro
) -> PlanResult:
    """Execute a plan using Claude Agent SDK."""
    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/plan {title}: {description}"

    # ... código existente ...

    options = ClaudeAgentOptions(
        cwd=Path(cwd),
        setting_sources=["user", "project"],
        allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
        permission_mode="acceptEdits",
        model=sdk_model,  # NOVO: passar modelo
    )

    # ... resto do código ...
```

Aplicar mesma modificação para `execute_implement`, `execute_test_implementation`, e `execute_review`.

#### 8. Backend - Endpoints

Em `backend/src/main.py`, modificar os endpoints para buscar o modelo correto do card e passar para as funções:

```python
@app.post("/api/execute-plan", response_model=ExecutePlanResponse)
async def execute_plan_endpoint(request: ExecutePlanRequest):
    # ... validação existente ...

    # Buscar card do banco para obter o modelo configurado
    async with async_session_maker() as session:
        repo = CardRepository(session)
        card = await repo.get_by_id(request.card_id)
        model = card.model_plan if card else "opus-4.5"

    result = await execute_plan(
        card_id=request.card_id,
        title=request.title,
        description=request.description or "",
        cwd=cwd,
        model=model,  # Passar modelo
    )
    # ... resto do código ...

@app.post("/api/execute-implement", response_model=ExecuteImplementResponse)
async def execute_implement_endpoint(request: ExecuteImplementRequest):
    # ... validação existente ...

    async with async_session_maker() as session:
        repo = CardRepository(session)
        card = await repo.get_by_id(request.card_id)
        model = card.model_implement if card else "opus-4.5"

    result = await execute_implement(
        card_id=request.card_id,
        spec_path=request.spec_path,
        cwd=cwd,
        model=model,
    )
    # ... resto do código ...
```

Aplicar mesma modificação para `/api/execute-test` e `/api/execute-review`.

#### 9. Frontend - App.tsx

Em `frontend/src/App.tsx`, modificar a função `addCard`:

```typescript
const addCard = async (
  title: string,
  description: string,
  columnId: ColumnId,
  modelPlan: ModelType,
  modelImplement: ModelType,
  modelTest: ModelType,
  modelReview: ModelType
) => {
  if (columnId !== 'backlog') {
    console.warn('Cards só podem ser criados na raia backlog');
    return;
  }

  try {
    const newCard = await cardsApi.createCard(
      title,
      description,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview
    );
    setCards(prev => [...prev, newCard]);
  } catch (error) {
    console.error('[App] Failed to create card:', error);
    alert('Falha ao criar card. Verifique se o servidor está rodando.');
  }
};
```

#### 10. Frontend - API Cards

Em `frontend/src/api/cards.ts`, modificar `createCard`:

```typescript
export async function createCard(
  title: string,
  description: string,
  modelPlan: ModelType,
  modelImplement: ModelType,
  modelTest: ModelType,
  modelReview: ModelType
): Promise<Card> {
  const response = await fetch(`${API_URL}/api/cards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      description,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to create card');
  }

  const data = await response.json();
  return data.card;
}
```

#### 11. Comandos Slash - Documentação

Em `.claude/commands/plan.md`, adicionar nota sobre modelo:

```markdown
---
description: Cria planos de implementação detalhados para features, bugs ou refatorações. Use antes de implementar tarefas complexas.
argument-hint: [descrição da tarefa]
allowed-tools: Read, Glob, Grep, Write, Task
model: opus  # Modelo padrão: opus 4.5 (pode ser sobrescrito pela UI)
---
```

Aplicar mesma modificação para `implement.md`, `test-implementation.md`, e `review.md`.

---

## 4. Testes

### Unitários
- [ ] Testar criação de card com modelos customizados via API
- [ ] Validar que modelos inválidos são rejeitados
- [ ] Verificar defaults (opus-4.5) quando modelos não são especificados
- [ ] Testar mapeamento de modelos (opus-4.5 → opus) no backend

### Integração
- [ ] Criar card pela UI com modelos diferentes por etapa
- [ ] Executar workflow completo e verificar se modelos corretos são usados
- [ ] Verificar persistência dos modelos no banco de dados
- [ ] Validar que logs mostram qual modelo foi usado

### Manuais
- [ ] Verificar UI: selects de modelo aparecem corretamente
- [ ] Testar cada combinação de modelo em diferentes etapas
- [ ] Validar que Opus 4.5 é o padrão em todos os selects

---

## 5. Considerações

### Riscos
- **Incompatibilidade do SDK**: Verificar se `ClaudeAgentOptions` aceita parâmetro `model` (consultar documentação do claude-agent-sdk)
- **Migração de dados**: Cards existentes precisarão ter valores default aplicados pela migration
- **Custos**: Usuários podem não perceber diferença de custo entre modelos (fora do escopo, mas considerar futura feature)

### Dependências
- Documentação do `claude-agent-sdk` para confirmar parâmetro `model`
- Migration precisa ser executada antes de deploy
- Frontend e backend devem ser deployados juntos para evitar incompatibilidades de schema

### Notas de Implementação
- O mapeamento de nomes (`opus-4.5` → `opus`) é necessário pois a UI usa nomes versionados mas o SDK usa nomes curtos
- Os valores default devem ser sempre `opus-4.5` para manter qualidade máxima por padrão
- Considerar adicionar tooltip/info na UI explicando diferenças entre modelos
