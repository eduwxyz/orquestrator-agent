# Automação UI: Botão "Run" para Workflow Automatizado

## 1. Resumo

Implementar um botão "Run" dentro dos cards na coluna de backlog que executa automaticamente todo o fluxo SDLC (plan → in-progress → test → review → done), refletindo visualmente em qual etapa o card se encontra atualmente na UI. Este botão automatiza o processo que hoje requer arrastar manualmente o card entre as colunas, executando sequencialmente os comandos `/plan`, `/implement`, `/test-implementation` e `/review`, movendo o card automaticamente entre as colunas conforme cada etapa é concluída com sucesso.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar botão "Run" apenas nos cards da coluna backlog
- [x] Implementar lógica de execução sequencial do workflow completo (plan → implement → test → review → done)
- [x] Mover automaticamente o card entre colunas conforme cada etapa é concluída
- [x] Exibir visualmente o progresso atual da automação no card
- [x] Adicionar estado de loading/execução durante o workflow
- [x] Permitir interromper execução caso ocorra erro em alguma etapa
- [x] Persistir o specPath gerado na etapa de plan
- [x] Exibir logs e resultados de cada etapa executada

### Fora do Escopo
- Execução paralela de múltiplos workflows
- Rollback automático em caso de erro
- Retry automático de etapas falhadas
- Agendamento de execuções
- Persistência do estado de workflow no banco de dados

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos para workflow automation (WorkflowStage, WorkflowStatus) |
| `frontend/src/hooks/useWorkflowAutomation.ts` | Criar | Hook customizado para gerenciar execução automatizada do workflow |
| `frontend/src/components/Card/Card.tsx` | Modificar | Adicionar botão "Run" visível apenas em backlog e indicador de progresso |
| `frontend/src/components/Card/Card.module.css` | Modificar | Adicionar estilos para botão Run e indicadores de progresso |
| `frontend/src/App.tsx` | Modificar | Integrar hook useWorkflowAutomation e passar funções necessárias |
| `frontend/src/hooks/useAgentExecution.ts` | Modificar | Retornar também updateCardSpecPath para ser usado no workflow |

### Detalhes Técnicos

#### 3.1. Tipos e Interfaces (`types/index.ts`)

Adicionar novos tipos para gerenciar o workflow:

```typescript
export type WorkflowStage = 'idle' | 'planning' | 'implementing' | 'testing' | 'reviewing' | 'completed' | 'error';

export interface WorkflowStatus {
  cardId: string;
  stage: WorkflowStage;
  currentColumn: ColumnId;
  error?: string;
}
```

#### 3.2. Hook useWorkflowAutomation (`hooks/useWorkflowAutomation.ts`)

Criar hook que orquestra a execução sequencial:

```typescript
import { useState, useCallback } from 'react';
import { Card, ColumnId, WorkflowStatus, WorkflowStage } from '../types';
import * as cardsApi from '../api/cards';

interface UseWorkflowAutomationProps {
  executePlan: (card: Card) => Promise<{ success: boolean; specPath?: string; error?: string }>;
  executeImplement: (card: Card) => Promise<{ success: boolean; error?: string }>;
  executeTest: (card: Card) => Promise<{ success: boolean; error?: string }>;
  executeReview: (card: Card) => Promise<{ success: boolean; error?: string }>;
  onCardMove: (cardId: string, columnId: ColumnId) => void;
  onSpecPathUpdate: (cardId: string, specPath: string) => void;
}

export function useWorkflowAutomation({
  executePlan,
  executeImplement,
  executeTest,
  executeReview,
  onCardMove,
  onSpecPathUpdate,
}: UseWorkflowAutomationProps) {
  const [workflowStatuses, setWorkflowStatuses] = useState<Map<string, WorkflowStatus>>(new Map());

  const runWorkflow = useCallback(async (card: Card) => {
    // Validar que o card está em backlog
    if (card.columnId !== 'backlog') {
      console.warn('Workflow só pode ser iniciado de cards em backlog');
      return;
    }

    const updateStatus = (stage: WorkflowStage, currentColumn: ColumnId, error?: string) => {
      setWorkflowStatuses(prev => {
        const next = new Map(prev);
        next.set(card.id, { cardId: card.id, stage, currentColumn, error });
        return next;
      });
    };

    try {
      // Etapa 1: Plan (backlog → plan)
      updateStatus('planning', 'backlog');

      const planResult = await executePlan(card);
      if (!planResult.success) {
        updateStatus('error', 'backlog', planResult.error);
        return;
      }

      // Mover para plan e persistir specPath
      await cardsApi.moveCard(card.id, 'plan');
      onCardMove(card.id, 'plan');

      if (planResult.specPath) {
        await cardsApi.updateSpecPath(card.id, planResult.specPath);
        onSpecPathUpdate(card.id, planResult.specPath);
        card.specPath = planResult.specPath; // Atualizar referência local
      }

      // Etapa 2: Implement (plan → in-progress)
      updateStatus('implementing', 'plan');

      const implementResult = await executeImplement(card);
      if (!implementResult.success) {
        updateStatus('error', 'plan', implementResult.error);
        return;
      }

      await cardsApi.moveCard(card.id, 'in-progress');
      onCardMove(card.id, 'in-progress');

      // Etapa 3: Test (in-progress → test)
      updateStatus('testing', 'in-progress');

      const testResult = await executeTest(card);
      if (!testResult.success) {
        updateStatus('error', 'in-progress', testResult.error);
        return;
      }

      await cardsApi.moveCard(card.id, 'test');
      onCardMove(card.id, 'test');

      // Etapa 4: Review (test → review)
      updateStatus('reviewing', 'test');

      const reviewResult = await executeReview(card);
      if (!reviewResult.success) {
        updateStatus('error', 'test', reviewResult.error);
        return;
      }

      await cardsApi.moveCard(card.id, 'review');
      onCardMove(card.id, 'review');

      // Finalizar (review → done)
      await cardsApi.moveCard(card.id, 'done');
      onCardMove(card.id, 'done');

      updateStatus('completed', 'done');

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      updateStatus('error', card.columnId, errorMsg);
      console.error('[useWorkflowAutomation] Workflow failed:', errorMsg);
    }
  }, [executePlan, executeImplement, executeTest, executeReview, onCardMove, onSpecPathUpdate]);

  const getWorkflowStatus = useCallback((cardId: string) => {
    return workflowStatuses.get(cardId);
  }, [workflowStatuses]);

  const clearWorkflowStatus = useCallback((cardId: string) => {
    setWorkflowStatuses(prev => {
      const next = new Map(prev);
      next.delete(cardId);
      return next;
    });
  }, []);

  return {
    runWorkflow,
    getWorkflowStatus,
    clearWorkflowStatus,
  };
}
```

#### 3.3. Componente Card (`components/Card/Card.tsx`)

Adicionar botão Run e indicador de progresso:

```typescript
// Adicionar no início do componente
const workflowStatus = props.workflowStatus;
const isRunning = workflowStatus && workflowStatus.stage !== 'idle' && workflowStatus.stage !== 'completed';

// No JSX, antes do botão de remover
{card.columnId === 'backlog' && !isRunning && (
  <button
    className={styles.runButton}
    onClick={(e) => {
      e.stopPropagation();
      props.onRunWorkflow?.(card);
    }}
    aria-label="Run workflow"
    title="Executar workflow completo automaticamente"
  >
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="currentColor"
    >
      <path d="M4 2l10 6-10 6V2z" />
    </svg>
    Run
  </button>
)}

{workflowStatus && workflowStatus.stage !== 'idle' && (
  <div className={styles.workflowProgress}>
    <span className={styles.progressBadge}>
      {workflowStatus.stage === 'planning' && '📋 Planning...'}
      {workflowStatus.stage === 'implementing' && '⚙️ Implementing...'}
      {workflowStatus.stage === 'testing' && '🧪 Testing...'}
      {workflowStatus.stage === 'reviewing' && '👁️ Reviewing...'}
      {workflowStatus.stage === 'completed' && '✅ Completed'}
      {workflowStatus.stage === 'error' && '❌ Failed'}
    </span>
  </div>
)}
```

#### 3.4. Estilos do Card (`components/Card/Card.module.css`)

```css
.runButton {
  position: absolute;
  top: 8px;
  right: 40px;
  padding: 4px 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  z-index: 10;
}

.runButton:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.runButton svg {
  width: 12px;
  height: 12px;
}

.workflowProgress {
  margin-top: 8px;
  padding: 6px 10px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 4px;
  border-left: 3px solid #667eea;
}

.progressBadge {
  font-size: 12px;
  font-weight: 500;
  color: #667eea;
  display: flex;
  align-items: center;
  gap: 6px;
}
```

#### 3.5. Integração no App (`App.tsx`)

```typescript
// Importar hook
import { useWorkflowAutomation } from './hooks/useWorkflowAutomation';

// Dentro do componente App
const {
  runWorkflow,
  getWorkflowStatus,
  clearWorkflowStatus,
} = useWorkflowAutomation({
  executePlan,
  executeImplement,
  executeTest,
  executeReview,
  onCardMove: moveCard,
  onSpecPathUpdate: updateCardSpecPath,
});

// Passar para Board e Card via props
getWorkflowStatus={getWorkflowStatus}
onRunWorkflow={runWorkflow}
```

---

## 4. Testes

### Unitários
- [ ] Teste do hook useWorkflowAutomation com mock das funções de execução
- [ ] Teste de renderização do botão Run apenas em cards de backlog
- [ ] Teste de atualização de status durante workflow
- [ ] Teste de handling de erros em cada etapa

### Integração
- [ ] Teste de workflow completo end-to-end (backlog → done)
- [ ] Teste de interrupção em caso de falha na etapa de plan
- [ ] Teste de interrupção em caso de falha na etapa de implement
- [ ] Teste de persistência do specPath após execução do plan
- [ ] Teste de movimentação automática entre colunas
- [ ] Teste visual de indicadores de progresso

### Manual
- [ ] Verificar que botão Run aparece apenas em cards de backlog
- [ ] Executar workflow completo e verificar transições visuais
- [ ] Verificar logs de execução em cada etapa
- [ ] Testar cenário de erro e verificar que card permanece na coluna correta
- [ ] Verificar que card não pode ser arrastado manualmente durante execução do workflow

---

## 5. Considerações

### Riscos
- **Execuções longas:** Workflows podem demorar vários minutos. Usuário pode fechar a página e perder progresso.
  - **Mitigação:** Considerar adicionar aviso ao usuário e, futuramente, implementar persistência de estado de workflow.

- **Conflitos com drag-and-drop manual:** Usuário pode tentar mover card manualmente durante execução automática.
  - **Mitigação:** Desabilitar drag durante workflow ativo (adicionar classe CSS que desabilita listeners).

- **Erros em etapas intermediárias:** Se uma etapa falha, card pode ficar "preso" em uma coluna.
  - **Mitigação:** Exibir claramente o erro e permitir que usuário continue manualmente ou tente novamente.

### Dependências
- Backend deve manter endpoints `/api/execute-plan`, `/api/execute-implement`, `/api/execute-test`, `/api/execute-review` funcionais
- Hook `useAgentExecution` deve retornar resultados consistentes com `success`, `specPath`, e `error`
- API de movimentação de cards (`moveCard`) deve ser confiável

### Melhorias Futuras
- Adicionar botão de "pause/resume" para workflows longos
- Persistir estado de workflow no banco de dados para sobreviver a page refresh
- Adicionar opção de "dry run" para testar workflow sem executar de fato
- Implementar retry automático com backoff exponencial
- Adicionar notificações desktop quando workflow for concluído
- Permitir configurar quais etapas executar (ex: apenas plan + implement)
