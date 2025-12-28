# Melhorar Logs do Backend com Contexto de Card

## 1. Resumo

Adicionar contexto de identificação (card ID e título) em todos os logs do backend para facilitar a depuração quando múltiplos cards são executados simultaneamente em diferentes estágios (plan, implement, test, review). Atualmente, não é possível distinguir qual log pertence a qual card quando há execuções concorrentes.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar prefixo `[Card: {card_id}]` ou `[{título_do_card}]` em todos os logs do backend
- [x] Implementar um logger centralizado que recebe contexto do card
- [x] Modificar todas as funções de execução (plan, implement, test, review) para usar o logger contextualizado
- [x] Garantir que o contexto seja propagado através da função `add_log()`

### Fora do Escopo
- Implementação de biblioteca de logging profissional (como `structlog` ou `loguru`)
- Persistência de logs em arquivo ou banco de dados
- Logs no frontend

---

## 3. Implementação

### Problema Atual

No arquivo `backend/src/agent.py`, a função `add_log()` (linha 38-46) imprime logs assim:

```python
def add_log(record: ExecutionRecord, log_type: LogType, content: str) -> None:
    """Add a log entry to the execution record."""
    log = ExecutionLog(
        timestamp=datetime.now().isoformat(),
        type=log_type,
        content=content,
    )
    record.logs.append(log)
    print(f"[Agent] [{log_type.value.upper()}] {content}")
```

Quando há múltiplas execuções simultâneas, todos os logs aparecem misturados:

```
[Agent] [INFO] Starting plan execution for: Feature A
[Agent] [INFO] Starting implementation for: specs/feature-b.md
[Agent] [TOOL] Using tool: Read
[Agent] [TOOL] Using tool: Write
[Agent] [INFO] Plan execution completed successfully
```

É impossível saber qual log pertence a qual card.

### Solução Proposta

**Opção 1: Adicionar Card ID no prefixo (Recomendada)**

Modificar `add_log()` para incluir informações do card:

```python
def add_log(record: ExecutionRecord, log_type: LogType, content: str) -> None:
    """Add a log entry to the execution record."""
    log = ExecutionLog(
        timestamp=datetime.now().isoformat(),
        type=log_type,
        content=content,
    )
    record.logs.append(log)

    # Incluir card_id no prefixo do log
    card_prefix = f"[Card:{record.card_id}]"
    print(f"{card_prefix} [Agent] [{log_type.value.upper()}] {content}")
```

**Opção 2: Adicionar metadados adicionais (título do card)**

Para facilitar ainda mais a identificação visual, podemos adicionar também o título do card (limitado a N caracteres):

```python
def add_log(
    record: ExecutionRecord,
    log_type: LogType,
    content: str,
    card_title: Optional[str] = None
) -> None:
    """Add a log entry to the execution record."""
    log = ExecutionLog(
        timestamp=datetime.now().isoformat(),
        type=log_type,
        content=content,
    )
    record.logs.append(log)

    # Criar prefixo contextualizado
    card_id_short = record.card_id[:8]  # Primeiros 8 chars do UUID
    if card_title:
        # Limitar título a 30 caracteres
        title_short = card_title[:30] + "..." if len(card_title) > 30 else card_title
        card_prefix = f"[{card_id_short}:{title_short}]"
    else:
        card_prefix = f"[{card_id_short}]"

    print(f"{card_prefix} [Agent] [{log_type.value.upper()}] {content}")
```

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/agent.py` | Modificar | Atualizar função `add_log()` para incluir contexto do card |
| `backend/src/execution.py` | Modificar (opcional) | Adicionar campo `title` no `ExecutionRecord` se necessário |

### Detalhes Técnicos

#### Passo 1: Modificar `ExecutionRecord` (Opcional)

Se optar pela Opção 2, adicionar campo `title` no modelo:

```python
# backend/src/execution.py
class ExecutionRecord(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    title: Optional[str] = None  # NOVO CAMPO
    started_at: str = Field(alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    status: ExecutionStatus
    logs: list[ExecutionLog] = []
    result: Optional[str] = None
```

#### Passo 2: Atualizar `add_log()` em `agent.py`

Implementar a Opção 1 (mais simples) ou Opção 2 (mais completa):

```python
# backend/src/agent.py

def add_log(record: ExecutionRecord, log_type: LogType, content: str) -> None:
    """Add a log entry to the execution record."""
    log = ExecutionLog(
        timestamp=datetime.now().isoformat(),
        type=log_type,
        content=content,
    )
    record.logs.append(log)

    # Criar prefixo com card_id (primeiros 8 caracteres para brevidade)
    card_id_short = record.card_id[:8] if len(record.card_id) > 8 else record.card_id

    # Se o record tiver título, incluir também (limitado)
    if hasattr(record, 'title') and record.title:
        title_short = record.title[:25] + "..." if len(record.title) > 25 else record.title
        card_prefix = f"[{card_id_short}|{title_short}]"
    else:
        card_prefix = f"[{card_id_short}]"

    print(f"{card_prefix} [Agent] [{log_type.value.upper()}] {content}")
```

#### Passo 3: Passar título ao criar ExecutionRecord

Se optar por incluir título, modificar as funções de execução:

```python
# backend/src/agent.py - função execute_plan() (linha 66-156)

async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
) -> PlanResult:
    """Execute a plan using Claude Agent SDK."""
    prompt = f"/plan {title}: {description}"

    # Initialize execution record COM TÍTULO
    record = ExecutionRecord(
        cardId=card_id,
        title=title,  # ADICIONAR AQUI
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record
    # ... resto do código
```

Repetir para `execute_implement()`, `execute_test_implementation()`, e `execute_review()`.

Para estas funções que não recebem `title`, podemos:
- Buscar o título do card no banco de dados usando `card_id`
- Ou apenas usar o `spec_path` como identificador visual

```python
# backend/src/agent.py - função execute_implement() (linha 159-229)

async def execute_implement(
    card_id: str,
    spec_path: str,
    cwd: str,
) -> PlanResult:
    """Execute /implement command with the spec file path."""
    prompt = f"/implement {spec_path}"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    record = ExecutionRecord(
        cardId=card_id,
        title=f"impl:{spec_name}",  # Prefixo para indicar que é implement
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    # ... resto do código
```

#### Exemplo de Output com Logs Melhorados

**Antes:**
```
[Agent] [INFO] Starting plan execution for: Feature A
[Agent] [INFO] Working directory: /path/to/project
[Agent] [INFO] Starting implementation for: specs/feature-b.md
[Agent] [TOOL] Using tool: Read
[Agent] [INFO] Plan execution completed successfully
```

**Depois (Opção 1 - apenas card_id):**
```
[abc12345] [Agent] [INFO] Starting plan execution for: Feature A
[abc12345] [Agent] [INFO] Working directory: /path/to/project
[def67890] [Agent] [INFO] Starting implementation for: specs/feature-b.md
[def67890] [Agent] [TOOL] Using tool: Read
[abc12345] [Agent] [INFO] Plan execution completed successfully
```

**Depois (Opção 2 - card_id + título):**
```
[abc12345|Feature A] [Agent] [INFO] Starting plan execution for: Feature A
[abc12345|Feature A] [Agent] [INFO] Working directory: /path/to/project
[def67890|impl:feature-b] [Agent] [INFO] Starting implementation for: specs/feature-b.md
[def67890|impl:feature-b] [Agent] [TOOL] Using tool: Read
[abc12345|Feature A] [Agent] [INFO] Plan execution completed successfully
```

---

## 4. Testes

### Unitários
- [ ] Testar que `add_log()` formata corretamente o prefixo com card_id curto
- [ ] Testar que `add_log()` trunca títulos longos corretamente
- [ ] Testar que `add_log()` funciona quando título é `None`

### Integração
- [ ] Executar 2-3 cards simultaneamente em diferentes estágios (plan, implement, test)
- [ ] Verificar que cada log no terminal tem prefixo único
- [ ] Verificar que é possível identificar visualmente logs de cada card
- [ ] Verificar que logs continuam sendo armazenados corretamente no `ExecutionRecord`

### Manual
- [ ] Criar 2 cards no backlog
- [ ] Mover um para "Plan" e outro para "In Progress" (com implement)
- [ ] Observar logs no terminal do backend
- [ ] Confirmar que cada linha de log é identificável por card

---

## 5. Considerações

### Riscos
- **Performance**: Nenhum impacto esperado, apenas concatenação de strings
- **Quebra de compatibilidade**: Não há, pois apenas mudamos o formato do print(), não a API

### Alternativas Consideradas

1. **Usar biblioteca de logging profissional (structlog/loguru)**
   - Pros: Logging estruturado, melhor performance, mais features
   - Contras: Adiciona dependência, maior complexidade
   - Decisão: Não implementar agora, deixar para futuro se necessário

2. **Colorir logs por card usando ANSI colors**
   - Pros: Distinção visual ainda melhor
   - Contras: Pode não funcionar em todos os terminais
   - Decisão: Não implementar agora, deixar para futuro

3. **Adicionar timestamp no prefixo**
   - Pros: Facilita correlação temporal
   - Contras: Logs já têm timestamp interno no ExecutionLog
   - Decisão: Não necessário, timestamp já existe

### Dependências
- Nenhuma dependência externa necessária
- Modificações são isoladas ao backend
- Não requer mudanças no frontend

### Melhorias Futuras

- Implementar logger estruturado (JSON logs) para facilitar parsing
- Adicionar cores ANSI para diferenciar cards visualmente
- Persistir logs em arquivo com rotação
- Adicionar níveis de log configuráveis (DEBUG, INFO, WARNING, ERROR)
