# Fix Plan Execution + Add Execution Logs UI

## Problema

Quando um card é movido para a coluna "Plan":
1. Após ~2 segundos mostra que o plano foi completado
2. Mas nenhum arquivo é criado no repositório (nenhuma spec gerada)
3. Não há forma de ver os logs da execução

## Análise

O código atual em `server/src/agent.ts`:
- Usa `@anthropic-ai/claude-agent-sdk` com `query()`
- Captura mensagens do stream mas não está armazenando os logs detalhados
- O resultado final pode estar vindo vazio ou com erro silencioso

## Solução

### Parte 1: Corrigir a execução do plano

- [x] 1.1. Atualizar `server/src/agent.ts` para capturar todos os tipos de mensagens do SDK (text, tool_use, result, etc.)
- [x] 1.2. Armazenar logs detalhados de cada execução em memória no servidor
- [x] 1.3. Retornar logs junto com o resultado da execução

### Parte 2: Adicionar sistema de logs

- [x] 2.1. Criar estrutura para armazenar logs por cardId no servidor
- [x] 2.2. Criar endpoint GET `/api/logs/:cardId` para buscar logs de uma execução
- [x] 2.3. Atualizar o endpoint POST `/api/execute-plan` para retornar os logs

### Parte 3: Adicionar visualização de logs no Card

- [x] 3.1. Atualizar o tipo `ExecutionStatus` para incluir `logs: ExecutionLog[]`
- [x] 3.2. Atualizar o hook `useAgentExecution` para armazenar logs
- [x] 3.3. Modificar o componente `Card` para ser clicável e mostrar um modal/drawer com logs
- [x] 3.4. Criar componente `LogsModal` para exibir os logs de execução
- [x] 3.5. Adicionar CSS para o modal de logs

## Arquivos a modificar

1. `server/src/agent.ts` - Captura detalhada de logs
2. `server/src/index.ts` - Endpoint de logs
3. `src/types/index.ts` - Tipos atualizados
4. `src/hooks/useAgentExecution.ts` - Armazenar logs
5. `src/components/Card/Card.tsx` - Clicável para abrir logs
6. `src/components/Card/Card.module.css` - Estilos para card clicável
7. `src/components/LogsModal/LogsModal.tsx` - Novo componente
8. `src/components/LogsModal/LogsModal.module.css` - Estilos do modal

## Detalhes técnicos

### Estrutura de logs no servidor

```typescript
interface ExecutionLog {
  timestamp: Date;
  type: 'info' | 'tool' | 'text' | 'error' | 'result';
  content: string;
}

interface ExecutionRecord {
  cardId: string;
  startedAt: Date;
  completedAt?: Date;
  status: 'running' | 'success' | 'error';
  logs: ExecutionLog[];
  result?: string;
}

// Map<cardId, ExecutionRecord>
const executions = new Map<string, ExecutionRecord>();
```

### Captura de mensagens do SDK

O Claude Agent SDK emite diferentes tipos de mensagens:
- `assistant` - Texto do assistente
- `user` - Mensagens do usuário
- `tool` - Uso de ferramentas
- `result` - Resultado final

Precisamos capturar todas para debug:

```typescript
for await (const message of query({ ... })) {
  logs.push({
    timestamp: new Date(),
    type: getMessageType(message),
    content: JSON.stringify(message, null, 2)
  });
}
```

### UI do modal de logs

```
┌─────────────────────────────────────────┐
│ Execution Logs - [Card Title]        [X]│
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ [12:30:01] Starting plan execution  │ │
│ │ [12:30:02] Tool: Read - reading...  │ │
│ │ [12:30:03] Tool: Write - creating...│ │
│ │ [12:30:05] Result: Plan created     │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Testes

1. Mover um card de backlog → plan
2. Verificar se os logs aparecem em tempo real (ou ao clicar)
3. Verificar se o arquivo de spec é criado em `specs/`
4. Verificar se erros são exibidos corretamente nos logs
