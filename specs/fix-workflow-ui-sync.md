# Fix: Sincronização UI do Workflow com Status de Execução

## 1. Resumo

Corrigir a lógica do workflow automation para que o card seja movido para a coluna correta ANTES de iniciar cada etapa de execução, garantindo que a UI sempre reflita o estado atual do workflow. Atualmente, há um atraso de 1 passo: quando o card está executando `/plan`, ele ainda aparece em `backlog` na UI, quando deveria estar em `plan`.

**Problema identificado:** O `updateStatus` é chamado com a coluna atual (onde o card está) ao invés da coluna de destino (onde o card deveria estar durante aquela etapa).

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Mover o card para a coluna correta ANTES de iniciar cada comando do workflow
- [x] Garantir que `updateStatus` sempre reflita a coluna de destino, não a de origem
- [x] Manter a lógica de persistência (salvar no backend) após movimentação
- [x] Preservar o comportamento de rollback em caso de erro

### Fora do Escopo
- Mudanças na UI dos cards
- Alterações nos componentes visuais
- Modificações nas APIs do backend

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/hooks/useWorkflowAutomation.ts` | Modificar | Reordenar a lógica de movimentação do card para acontecer ANTES da execução |

### Detalhes Técnicos

A correção consiste em reorganizar a sequência de operações em cada etapa do workflow. Atualmente:

```typescript
// ERRADO - Estado atual
updateStatus('planning', 'backlog');  // Card ainda está em backlog
const planResult = await executePlan(card);
await cardsApi.moveCard(card.id, 'plan');  // Só move depois
onCardMove(card.id, 'plan');
```

Deve ser alterado para:

```typescript
// CORRETO - Novo comportamento
await cardsApi.moveCard(card.id, 'plan');  // Move primeiro
onCardMove(card.id, 'plan');
updateStatus('planning', 'plan');  // Atualiza com a coluna correta
const planResult = await executePlan(card);
```

**Fluxo correto para cada etapa:**

1. **Planning (backlog → plan)**
   - Mover card para `plan`
   - Atualizar status para `('planning', 'plan')`
   - Executar `/plan`
   - Se falhar: mover de volta para `backlog`

2. **Implementing (plan → in-progress)**
   - Salvar `specPath` no card
   - Mover card para `in-progress`
   - Atualizar status para `('implementing', 'in-progress')`
   - Executar `/implement`
   - Se falhar: mover de volta para `plan`

3. **Testing (in-progress → test)**
   - Mover card para `test`
   - Atualizar status para `('testing', 'test')`
   - Executar `/test-implementation`
   - Se falhar: mover de volta para `in-progress`

4. **Reviewing (test → review)**
   - Mover card para `review`
   - Atualizar status para `('reviewing', 'review')`
   - Executar `/review`
   - Se falhar: mover de volta para `test`

5. **Completion (review → done)**
   - Mover card para `done`
   - Atualizar status para `('completed', 'done')`

### Implementação detalhada

```typescript
// Etapa 1: Plan (backlog → plan)
await cardsApi.moveCard(card.id, 'plan');
onCardMove(card.id, 'plan');
updateStatus('planning', 'plan');

const planResult = await executePlan(card);
if (!planResult.success) {
  // Rollback: voltar para backlog
  await cardsApi.moveCard(card.id, 'backlog');
  onCardMove(card.id, 'backlog');
  updateStatus('error', 'backlog', planResult.error);
  return;
}

// Persistir specPath
if (planResult.specPath) {
  await cardsApi.updateSpecPath(card.id, planResult.specPath);
  onSpecPathUpdate(card.id, planResult.specPath);
  card.specPath = planResult.specPath;
}

// Etapa 2: Implement (plan → in-progress)
await cardsApi.moveCard(card.id, 'in-progress');
onCardMove(card.id, 'in-progress');
updateStatus('implementing', 'in-progress');

const implementResult = await executeImplement(card);
if (!implementResult.success) {
  // Rollback: voltar para plan
  await cardsApi.moveCard(card.id, 'plan');
  onCardMove(card.id, 'plan');
  updateStatus('error', 'plan', implementResult.error);
  return;
}

// Etapa 3: Test (in-progress → test)
await cardsApi.moveCard(card.id, 'test');
onCardMove(card.id, 'test');
updateStatus('testing', 'test');

const testResult = await executeTest(card);
if (!testResult.success) {
  // Rollback: voltar para in-progress
  await cardsApi.moveCard(card.id, 'in-progress');
  onCardMove(card.id, 'in-progress');
  updateStatus('error', 'in-progress', testResult.error);
  return;
}

// Etapa 4: Review (test → review)
await cardsApi.moveCard(card.id, 'review');
onCardMove(card.id, 'review');
updateStatus('reviewing', 'review');

const reviewResult = await executeReview(card);
if (!reviewResult.success) {
  // Rollback: voltar para test
  await cardsApi.moveCard(card.id, 'test');
  onCardMove(card.id, 'test');
  updateStatus('error', 'test', reviewResult.error);
  return;
}

// Finalizar (review → done)
await cardsApi.moveCard(card.id, 'done');
onCardMove(card.id, 'done');
updateStatus('completed', 'done');
```

---

## 4. Testes

### Validação Manual
- [ ] Iniciar workflow de um card em backlog
- [ ] Verificar que durante `/plan`, o card está visualmente na coluna "Plan"
- [ ] Verificar que durante `/implement`, o card está na coluna "In Progress"
- [ ] Verificar que durante `/test`, o card está na coluna "Test"
- [ ] Verificar que durante `/review`, o card está na coluna "Review"
- [ ] Verificar que ao finalizar, o card está na coluna "Done"

### Teste de Erro
- [ ] Simular erro no `/plan` e verificar rollback para backlog
- [ ] Simular erro no `/implement` e verificar rollback para plan
- [ ] Simular erro no `/test` e verificar rollback para in-progress
- [ ] Simular erro no `/review` e verificar rollback para test

### Integração
- [ ] Verificar que o badge de workflow status (`workflowStatus.stage`) corresponde à coluna atual
- [ ] Verificar que não há race conditions ou estados intermediários inconsistentes
- [ ] Confirmar que a persistência no backend está funcionando corretamente

---

## 5. Considerações

- **Riscos:**
  - Race conditions se múltiplos workflows forem executados simultaneamente (mitigado pelo fato de que cada card tem seu próprio workflow)
  - Possível inconsistência entre backend e frontend se houver falha de rede durante movimentação (já existe esse risco, não estamos aumentando)

- **Dependências:**
  - Nenhuma dependência externa
  - Mudança isolada no hook `useWorkflowAutomation`

- **Performance:**
  - Não há impacto significativo de performance
  - A movimentação já estava sendo feita, apenas mudamos a ordem

- **Observações:**
  - Esta mudança torna o fluxo mais intuitivo e alinhado com as expectativas do usuário
  - O comportamento de rollback garante que em caso de erro, o card volte para a coluna anterior
