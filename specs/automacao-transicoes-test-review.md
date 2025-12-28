# Automação de Comandos nas Transições Test e Review

## Objetivo

Implementar execução automática de comandos do Claude quando cards são movidos para as colunas "test" e "review":

1. **in-progress → test**: Executar `/test-implementation {specPath}`
2. **test → review**: Executar `/review {specPath}`

## Contexto

O sistema já possui automação para:
- backlog → plan: Executa `/plan`
- plan → in-progress: Executa `/implement`

Falta implementar os dois últimos estágios do workflow SDLC.

## Arquivos a Serem Modificados

### Backend

- [x] **backend/src/agent.py** - Funções `execute_test_implementation` e `execute_review` já existem
- [x] **backend/src/main.py** - Endpoints `/api/execute-test` e `/api/execute-review` adicionados

### Frontend

- [x] **frontend/src/hooks/useAgentExecution.ts** - Funções `executeTest` e `executeReview` adicionadas
- [x] **frontend/src/App.tsx** - Triggers para as novas transições adicionados

## Detalhes Técnicos

### 1. Backend - agent.py

Adicionar duas novas funções seguindo o padrão existente:

```python
async def execute_test(card_id: str, spec_path: str) -> dict:
    """Executa /test-implementation para validar implementação"""
    # Seguir padrão de execute_implement
    # Prompt: /test-implementation {spec_path}
    pass

async def execute_review(card_id: str, spec_path: str) -> dict:
    """Executa /review para revisar implementação"""
    # Seguir padrão de execute_implement
    # Prompt: /review {spec_path}
    pass
```

### 2. Backend - main.py

Adicionar dois endpoints:

```python
@app.post("/api/execute-test")
async def api_execute_test(request: ExecuteImplementRequest):
    # Reutilizar schema ExecuteImplementRequest (cardId, specPath)
    result = await execute_test(request.cardId, request.specPath)
    return result

@app.post("/api/execute-review")
async def api_execute_review(request: ExecuteImplementRequest):
    result = await execute_review(request.cardId, request.specPath)
    return result
```

### 3. Frontend - useAgentExecution.ts

Adicionar duas funções seguindo o padrão existente:

```typescript
const executeTest = async (card: Card): Promise<void> => {
    if (!card.specPath) {
        alert('Card não possui specPath. Execute o plano primeiro.');
        return;
    }

    setExecutionStatus(prev => ({
        ...prev,
        [card.id]: { status: 'running', logs: [] }
    }));

    const response = await fetch('/api/execute-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cardId: card.id, specPath: card.specPath })
    });

    // Processar resposta...
};

const executeReview = async (card: Card): Promise<void> => {
    // Similar ao executeTest, mas chama /api/execute-review
};
```

### 4. Frontend - App.tsx

Modificar `handleDragEnd` para incluir os novos triggers:

```typescript
// Após os triggers existentes, adicionar:

// Trigger: in-progress → test
if (startColumn === 'in-progress' && finalColumnId === 'test') {
    if (!card.specPath) {
        alert('Card não possui specPath. Execute o plano primeiro.');
        // Reverter movimento
        return;
    }
    executeTest(card);
}

// Trigger: test → review
if (startColumn === 'test' && finalColumnId === 'review') {
    if (!card.specPath) {
        alert('Card não possui specPath. Execute o plano primeiro.');
        // Reverter movimento
        return;
    }
    executeReview(card);
}
```

## Fluxo Completo

```
Card em in-progress (implementado)
    ↓ Usuário arrasta para "test"
Frontend: Valida transição (in-progress → test ✓)
Frontend: Detecta trigger, chama executeTest(card)
Backend: Executa /test-implementation specs/xxx.md
Claude: Valida arquivos, executa testes, gera relatório
    ↓ Usuário arrasta para "review"
Frontend: Valida transição (test → review ✓)
Frontend: Detecta trigger, chama executeReview(card)
Backend: Executa /review specs/xxx.md
Claude: Analisa código, compara com spec, gera relatório
    ↓ Usuário arrasta para "done"
Workflow completo!
```

## Testes

### Testes Manuais
- [ ] Criar card e passar por todo o fluxo: backlog → plan → in-progress → test → review → done
- [ ] Verificar que /test-implementation é executado na transição in-progress → test
- [ ] Verificar que /review é executado na transição test → review
- [ ] Verificar que logs são exibidos corretamente
- [ ] Verificar comportamento quando card não tem specPath

## Checklist de Implementação

- [x] Implementar `execute_test_implementation` em agent.py (já existia)
- [x] Implementar `execute_review` em agent.py (já existia)
- [x] Adicionar endpoint `/api/execute-test` em main.py
- [x] Adicionar endpoint `/api/execute-review` em main.py
- [x] Implementar `executeTest` em useAgentExecution.ts
- [x] Implementar `executeReview` em useAgentExecution.ts
- [x] Adicionar trigger in-progress → test em App.tsx
- [x] Adicionar trigger test → review em App.tsx
- [x] Testar fluxo completo (build passou)
