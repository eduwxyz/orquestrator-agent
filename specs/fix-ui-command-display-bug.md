# Fix: Exibição Dinâmica do Comando Executado na UI do Card

## 1. Resumo

Corrigir a exibição do status de execução no componente Card para mostrar dinamicamente qual comando está sendo executado com base no `workflowStatus.stage` atual, ao invés de sempre exibir "Executing /plan...". Atualmente, mesmo quando o card está em "in-progress" e executando `/implement` no backend, a UI ainda mostra "Executing /plan..." porque o texto está hardcoded.

**Problema identificado:** O componente `Card.tsx` nas linhas 68-70 exibe sempre "Executing /plan..." quando `executionStatus.status === 'running'`, sem considerar qual etapa do workflow está realmente executando.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Exibir dinamicamente qual comando está sendo executado (/plan, /implement, /test-implementation, /review) com base no `workflowStatus.stage`
- [x] Manter compatibilidade com execuções manuais (quando o card é arrastado manualmente entre raias)
- [x] Preservar a lógica de exibição do badge de workflow progress (linhas 133-144)
- [x] Garantir que as mensagens de sucesso/erro também sejam específicas para cada comando

### Fora do Escopo
- Mudanças na lógica de workflow automation (hook `useWorkflowAutomation`)
- Alterações no backend ou nas APIs
- Modificações nos estilos visuais dos badges (apenas o texto)

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Card/Card.tsx` | Modificar | Tornar a exibição do status de execução dinâmica com base no `workflowStatus.stage` |

### Detalhes Técnicos

O componente `Card` já recebe tanto `executionStatus` quanto `workflowStatus` como props. Precisamos usar `workflowStatus.stage` para determinar qual comando está sendo executado.

**Mapeamento de stages para comandos:**

| Stage | Comando exibido | Mensagem de sucesso | Mensagem de erro |
|-------|----------------|---------------------|------------------|
| `planning` | Executing /plan... | Plan completed | Plan failed |
| `implementing` | Executing /implement... | Implementation completed | Implementation failed |
| `testing` | Executing /test-implementation... | Tests completed | Tests failed |
| `reviewing` | Executing /review... | Review completed | Review failed |
| `completed` | - | Workflow completed | - |
| `error` | - | - | Workflow failed |
| `idle` | - | - | - |

**Abordagem de implementação:**

1. Criar uma função helper `getExecutionMessage()` que retorna a mensagem apropriada com base em:
   - `executionStatus.status` (running, success, error)
   - `workflowStatus?.stage` (planning, implementing, testing, reviewing)

2. Substituir os badges hardcoded nas linhas 68-84 pela chamada a essa função

**Código proposto:**

```typescript
// Função helper para determinar a mensagem de execução
const getExecutionMessage = () => {
  if (!executionStatus || executionStatus.status === 'idle') return null;

  const { status } = executionStatus;
  const stage = workflowStatus?.stage;

  // Mapear stage para comando
  const stageToCommand: Record<string, { running: string; success: string; error: string }> = {
    planning: {
      running: 'Executing /plan...',
      success: 'Plan completed',
      error: 'Plan failed',
    },
    implementing: {
      running: 'Executing /implement...',
      success: 'Implementation completed',
      error: 'Implementation failed',
    },
    testing: {
      running: 'Executing /test-implementation...',
      success: 'Tests completed',
      error: 'Tests failed',
    },
    reviewing: {
      running: 'Executing /review...',
      success: 'Review completed',
      error: 'Review failed',
    },
  };

  // Se temos workflowStatus.stage, usar ele para determinar a mensagem
  if (stage && stage in stageToCommand) {
    return stageToCommand[stage][status];
  }

  // Fallback: determinar com base na coluna do card (para execuções manuais)
  const columnToCommand: Record<string, { running: string; success: string; error: string }> = {
    plan: {
      running: 'Executing /plan...',
      success: 'Plan completed',
      error: 'Plan failed',
    },
    'in-progress': {
      running: 'Executing /implement...',
      success: 'Implementation completed',
      error: 'Implementation failed',
    },
    test: {
      running: 'Executing /test-implementation...',
      success: 'Tests completed',
      error: 'Tests failed',
    },
    review: {
      running: 'Executing /review...',
      success: 'Review completed',
      error: 'Review failed',
    },
  };

  if (card.columnId in columnToCommand) {
    return columnToCommand[card.columnId][status];
  }

  // Fallback genérico
  const genericMessages = {
    running: 'Executing...',
    success: 'Execution completed',
    error: 'Execution failed',
  };

  return genericMessages[status];
};
```

**Substituir o bloco de badges (linhas 65-88) por:**

```typescript
{executionStatus && executionStatus.status !== 'idle' && (
  <div className={styles.executionStatus}>
    {(() => {
      const message = getExecutionMessage();
      if (!message) return null;

      return (
        <>
          {executionStatus.status === 'running' && (
            <span className={styles.statusBadge}>
              <span className={styles.spinner} />
              {message}
            </span>
          )}
          {executionStatus.status === 'success' && (
            <span className={styles.statusBadge}>
              <span className={styles.checkIcon}>✓</span>
              {message}
            </span>
          )}
          {executionStatus.status === 'error' && (
            <span className={styles.statusBadge}>
              <span className={styles.errorIcon}>✗</span>
              {message}
            </span>
          )}
          {hasLogs && (
            <span className={styles.logsHint}>Click to view logs</span>
          )}
        </>
      );
    })()}
  </div>
)}
```

---

## 4. Testes

### Validação Manual
- [ ] **[REQUER TESTE MANUAL]** Iniciar workflow automático (botão "Run") de um card em backlog
- [ ] **[REQUER TESTE MANUAL]** Verificar que durante a etapa de planning, exibe "Executing /plan..."
- [ ] **[REQUER TESTE MANUAL]** Verificar que durante a etapa de implementing, exibe "Executing /implement..."
- [ ] **[REQUER TESTE MANUAL]** Verificar que durante a etapa de testing, exibe "Executing /test-implementation..."
- [ ] **[REQUER TESTE MANUAL]** Verificar que durante a etapa de reviewing, exibe "Executing /review..."
- [ ] **[REQUER TESTE MANUAL]** Verificar mensagens de sucesso específicas para cada etapa
- [ ] **[REQUER TESTE MANUAL]** Verificar mensagens de erro específicas para cada etapa

### Teste de Execução Manual (Drag & Drop)
- [ ] **[REQUER TESTE MANUAL]** Arrastar card de backlog para plan manualmente
- [ ] **[REQUER TESTE MANUAL]** Verificar que durante execução manual de /plan, exibe "Executing /plan..."
- [ ] **[REQUER TESTE MANUAL]** Arrastar card de plan para in-progress manualmente
- [ ] **[REQUER TESTE MANUAL]** Verificar que durante execução manual de /implement, exibe "Executing /implement..."
- [ ] **[REQUER TESTE MANUAL]** Verificar comportamento similar para test e review

### Teste de Fallback
- [x] Verificar que se não houver workflowStatus, usa card.columnId como fallback (implementado nas linhas 79-100)
- [x] Verificar mensagem genérica se card estiver em coluna não mapeada (implementado nas linhas 107-113)

### Integração
- [x] Verificar que o badge de workflow progress (linhas 133-144) continua funcionando corretamente (código não foi modificado)
- [x] Confirmar que não há conflito visual entre executionStatus badge e workflowProgress badge (lógica mantida separada)
- [x] Verificar que logs continuam acessíveis via modal (código não foi modificado)

---

## 5. Considerações

- **Riscos:**
  - Possível confusão se `executionStatus` e `workflowStatus` estiverem dessincronizados (mitigado pela lógica de fallback)
  - Necessidade de garantir que workflowStatus.stage seja atualizado corretamente no hook useWorkflowAutomation (já implementado)

- **Dependências:**
  - Nenhuma dependência externa
  - Mudança isolada no componente Card

- **Performance:**
  - Não há impacto de performance
  - A função helper é leve e executa apenas mapeamentos simples

- **Observações:**
  - Esta mudança melhora significativamente a experiência do usuário, fornecendo feedback visual preciso sobre qual etapa está executando
  - A lógica de fallback garante compatibilidade com execuções manuais (drag & drop)
  - O mapeamento por coluna (`columnToCommand`) garante que mesmo sem workflowStatus, a mensagem seja relevante

- **Alternativas consideradas:**
  - **Opção 1 (escolhida):** Usar `workflowStatus.stage` com fallback para `card.columnId`
    - ✅ Mais preciso
    - ✅ Funciona tanto para workflow automático quanto manual
  - **Opção 2 (descartada):** Usar apenas `card.columnId`
    - ❌ Menos preciso durante transições de workflow
    - ❌ Pode exibir mensagem incorreta se card estiver em coluna diferente do comando executando
  - **Opção 3 (descartada):** Adicionar novo campo `currentCommand` no executionStatus
    - ❌ Requer mudanças no backend
    - ❌ Adiciona complexidade desnecessária

---

## 6. Próximos Passos (Fora do Escopo desta Spec)

Melhorias futuras que podem ser consideradas separadamente:
- Adicionar animação de transição suave ao trocar mensagens de status
- Adicionar timestamp de início/fim de cada comando
- Exibir progresso percentual de cada etapa (requer mudanças no backend)
