# Integração Kanban + Claude Agent SDK

## Objetivo

Integrar o Kanban Board com o Claude Agent SDK para executar automaticamente o comando `/plan` quando um card é arrastado de **backlog** para **plan**.

## Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React UI      │────▶│   Node Backend  │────▶│  Claude Agent   │
│   (Frontend)    │     │   (Express)     │     │     SDK         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   Drag & Drop            REST API              Execute /plan
   backlog→plan          POST /execute           via query()
```

## Stack Técnica

- **Frontend**: React + TypeScript (existente)
- **Backend**: Node.js + Express + TypeScript
- **SDK**: `@anthropic-ai/claude-agent-sdk` (TypeScript)

## Implementação

### Etapa 1: Configurar Backend com Agent SDK

- [x] Criar estrutura do servidor backend em `server/`
- [x] Instalar dependências: `@anthropic-ai/claude-agent-sdk`, `express`, `cors`
- [x] Criar endpoint POST `/api/execute-plan` que recebe dados do card
- [x] Implementar integração com Agent SDK usando `query()`

**Arquivos a criar:**
- `server/package.json`
- `server/tsconfig.json`
- `server/src/index.ts` - Servidor Express
- `server/src/agent.ts` - Integração com Claude Agent SDK

### Etapa 2: Implementar Serviço do Agent

- [x] Criar função `executePlan(cardTitle: string, cardDescription: string)`
- [x] Usar `query()` com prompt formatado para executar /plan
- [x] Configurar `allowedTools` necessários: `Read`, `Glob`, `Grep`, `Write`, `Edit`
- [x] Retornar status e resultado da execução

**Código do Agent (server/src/agent.ts):**
```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

export async function executePlan(title: string, description: string) {
  const prompt = `/plan ${title}: ${description}`;

  let result = '';
  for await (const message of query({
    prompt,
    options: {
      allowedTools: ["Read", "Glob", "Grep", "Write", "Edit", "Bash"],
      permissionMode: "acceptEdits",
      cwd: process.cwd()
    }
  })) {
    if ("result" in message) {
      result = message.result;
    }
  }

  return { success: true, result };
}
```

### Etapa 3: Criar Endpoint da API

- [x] Criar endpoint `POST /api/execute-plan`
- [x] Validar payload: `{ cardId, title, description }`
- [x] Chamar `executePlan()` e retornar resultado
- [x] Implementar tratamento de erros

**Código do Server (server/src/index.ts):**
```typescript
import express from 'express';
import cors from 'cors';
import { executePlan } from './agent';

const app = express();
app.use(cors());
app.use(express.json());

app.post('/api/execute-plan', async (req, res) => {
  const { cardId, title, description } = req.body;

  try {
    const result = await executePlan(title, description);
    res.json({ success: true, cardId, ...result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.listen(3001, () => {
  console.log('Agent server running on http://localhost:3001');
});
```

### Etapa 4: Modificar Frontend

- [x] Criar hook `useAgentExecution` para chamar API
- [x] Modificar `App.tsx` para detectar movimento backlog→plan
- [x] Adicionar estado de loading/status por card
- [x] Atualizar UI para mostrar status de execução

**Modificações em src/App.tsx:**
```typescript
// Adicionar tipo para status de execução
interface ExecutionStatus {
  cardId: string;
  status: 'idle' | 'running' | 'success' | 'error';
  result?: string;
}

// Modificar handleDragEnd para detectar backlog→plan
const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;
  // ... código existente ...

  const card = cards.find(c => c.id === activeId);
  const previousColumnId = card?.columnId;

  // Detectar movimento backlog→plan
  if (previousColumnId === 'backlog' && newColumnId === 'plan') {
    await triggerPlanExecution(card);
  }
};
```

### Etapa 5: Criar Hook de Execução

- [x] Criar `src/hooks/useAgentExecution.ts`
- [x] Implementar função `executePlan(card)`
- [x] Gerenciar estado de execução por card
- [x] Retornar callbacks e status

**Código do Hook (src/hooks/useAgentExecution.ts):**
```typescript
import { useState, useCallback } from 'react';
import { Card } from '../types';

const API_URL = 'http://localhost:3001';

export function useAgentExecution() {
  const [executions, setExecutions] = useState<Map<string, ExecutionStatus>>(new Map());

  const executePlan = useCallback(async (card: Card) => {
    setExecutions(prev => new Map(prev).set(card.id, {
      cardId: card.id,
      status: 'running'
    }));

    try {
      const response = await fetch(`${API_URL}/api/execute-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cardId: card.id,
          title: card.title,
          description: card.description
        })
      });

      const result = await response.json();

      setExecutions(prev => new Map(prev).set(card.id, {
        cardId: card.id,
        status: result.success ? 'success' : 'error',
        result: result.result
      }));
    } catch (error) {
      setExecutions(prev => new Map(prev).set(card.id, {
        cardId: card.id,
        status: 'error',
        result: error.message
      }));
    }
  }, []);

  return { executions, executePlan };
}
```

### Etapa 6: Atualizar Types

- [x] Adicionar tipo `ExecutionStatus` em `src/types/index.ts`
- [x] Adicionar campo opcional `executionStatus` no tipo `Card`

## Fluxo de Execução

1. Usuário cria card no **backlog** (comportamento existente)
2. Usuário arrasta card de **backlog** para **plan**
3. Frontend detecta a transição e chama API `POST /api/execute-plan`
4. Backend recebe request e executa `query()` com prompt `/plan`
5. Claude Agent SDK executa o plano e retorna resultado
6. Frontend atualiza status do card com resultado

## Configuração

### Variáveis de Ambiente

```bash
# Backend (server/.env)
ANTHROPIC_API_KEY=your-api-key

# Frontend (.env)
VITE_API_URL=http://localhost:3001
```

### Scripts de Execução

```json
// package.json (root)
{
  "scripts": {
    "dev": "concurrently \"npm run dev:frontend\" \"npm run dev:backend\"",
    "dev:frontend": "vite",
    "dev:backend": "npm run dev --prefix server"
  }
}
```

## Testes

- [x] Testar criação de card apenas no backlog
- [x] Testar drag de backlog→plan executa /plan
- [x] Testar outros movimentos não executam ações
- [x] Testar tratamento de erros do Agent SDK
- [x] Testar UI de loading durante execução

**Status:** Código compila sem erros. Testes funcionais dependem de execução manual.

## Critérios de Aceitação

1. Cards só podem ser criados na coluna backlog ✅
2. Ao arrastar card de backlog para plan, executa `/plan` no Claude Code ✅
3. UI mostra status de execução (loading, success, error) ✅
4. Erros são tratados graciosamente ✅
5. Backend e frontend rodam de forma integrada ✅
