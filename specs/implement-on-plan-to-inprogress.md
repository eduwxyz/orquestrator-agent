# Implementar /implement na transição Plan → In Progress

## Resumo
Quando um card for arrastado da coluna "Plan" para "In Progress", executar automaticamente o comando `/implement` passando o path do plano gerado na etapa de planejamento. Implementar também validação SDLC para garantir que cards sigam o fluxo correto.

## Requisitos

### 1. Validação SDLC
Cards devem seguir o fluxo obrigatório:
- `backlog` → `plan` (único destino permitido)
- `plan` → `in-progress` (único destino permitido)
- `in-progress` → `test` (único destino permitido)
- `test` → `review` (único destino permitido)
- `review` → `done` (único destino permitido)

**Transições proibidas:**
- Backlog não pode ir direto para in-progress, test, review ou done
- Nenhuma coluna pode pular etapas
- Cards só podem avançar, não retroceder

### 2. Armazenar Path do Plano
O Card precisa armazenar o caminho do arquivo de spec gerado durante a etapa de planejamento.

### 3. Executar /implement
Quando arrastar de `plan` → `in-progress`, executar `/implement` com o path do plano.

---

## Plano de Implementação

### Item 1: Atualizar tipo Card para incluir specPath
**Arquivo:** `frontend/src/types/index.ts`

```typescript
export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
  specPath?: string; // Caminho do arquivo de spec gerado
}
```

- [x] Adicionar campo `specPath?: string` ao interface Card

---

### Item 2: Implementar validação de transições SDLC
**Arquivo:** `frontend/src/types/index.ts`

Criar mapa de transições permitidas:

```typescript
export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'backlog': ['plan'],
  'plan': ['in-progress'],
  'in-progress': ['test'],
  'test': ['review'],
  'review': ['done'],
  'done': [],
};

export function isValidTransition(from: ColumnId, to: ColumnId): boolean {
  return ALLOWED_TRANSITIONS[from]?.includes(to) ?? false;
}
```

- [x] Adicionar constante ALLOWED_TRANSITIONS
- [x] Adicionar função isValidTransition

---

### Item 3: Aplicar validação no handleDragEnd
**Arquivo:** `frontend/src/App.tsx`

Modificar `handleDragEnd` para:
1. Verificar se a transição é válida antes de mover
2. Se inválida, reverter o card para a coluna original
3. Mostrar feedback visual (toast ou alerta)

- [x] Importar isValidTransition
- [x] Adicionar validação antes de mover
- [x] Reverter card se transição inválida
- [x] Adicionar trigger para plan→in-progress

---

### Item 4: Atualizar executePlan para salvar specPath
**Arquivo:** `frontend/src/hooks/useAgentExecution.ts`

Modificar para:
1. Extrair o path do spec dos logs de execução
2. Retornar o specPath para atualizar o card

**Arquivo:** `frontend/src/App.tsx`

- [x] Adicionar updateCardSpecPath em App.tsx
- [x] Modificar executePlan para chamar callback com specPath

---

### Item 5: Criar endpoint /api/execute-implement no backend
**Arquivo:** `backend/src/main.py`

- [x] Criar ExecuteImplementRequest model
- [x] Criar endpoint /api/execute-implement

---

### Item 6: Criar função execute_implement no backend
**Arquivo:** `backend/src/agent.py`

- [x] Criar função execute_implement em agent.py

---

### Item 7: Adicionar executeImplement no hook
**Arquivo:** `frontend/src/hooks/useAgentExecution.ts`

- [x] Adicionar executeImplement ao hook
- [x] Exportar executeImplement

---

### Item 8: Integrar executeImplement no App.tsx

- [x] Importar executeImplement do hook
- [x] Usar executeImplement na transição plan→in-progress

---

### Item 9: Atualizar backend para retornar specPath
**Arquivo:** `backend/src/agent.py`

Modificar `execute_plan` para:
1. Detectar quando um arquivo de spec é criado
2. Retornar o path no resultado

- [x] Adicionar spec_path ao PlanResult
- [x] Detectar criação de arquivo em specs/ e capturar path

---

## Testes

- [x] Build do frontend passou
- [x] Sintaxe do backend verificada
- [ ] Testar arrastar card de backlog→plan (deve executar /plan)
- [ ] Testar arrastar card de plan→in-progress (deve executar /implement)
- [ ] Testar arrastar card de backlog→in-progress (deve ser bloqueado)
- [ ] Testar arrastar card de backlog→test (deve ser bloqueado)
- [ ] Testar arrastar card de backlog→review (deve ser bloqueado)
- [ ] Testar arrastar card de backlog→done (deve ser bloqueado)
- [ ] Verificar que specPath é salvo corretamente após /plan
- [ ] Verificar que /implement recebe o specPath correto

---

## Arquivos Modificados

1. `frontend/src/types/index.ts` - Tipos e validação SDLC
2. `frontend/src/App.tsx` - Lógica de drag-and-drop com validação
3. `frontend/src/hooks/useAgentExecution.ts` - Hook com executeImplement
4. `backend/src/main.py` - Novo endpoint
5. `backend/src/agent.py` - Função execute_implement
6. `backend/src/execution.py` - Novos models
