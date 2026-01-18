# Kanban Flow Expert - Knowledge Base

## Dominio

Expert em fluxo do Kanban: workflow de cards, transicoes de status, automacoes SDLC, ciclo de vida, sistema de experts e regras de negocio.

## Arquivos Core

### Frontend - Componentes UI

| Path | Responsabilidade |
|------|------------------|
| `frontend/src/components/Board/Board.tsx` | Board principal com drag-drop |
| `frontend/src/components/Column/Column.tsx` | Coluna com droppable zone |
| `frontend/src/components/Card/Card.tsx` | Card draggable com status + ExpertBadges |
| `frontend/src/components/ExpertBadges/ExpertBadges.tsx` | **NEW**: Badges dos experts identificados |
| `frontend/src/pages/KanbanPage.tsx` | Page container com DndContext |

### Frontend - Hooks de Automacao

| Path | Responsabilidade |
|------|------------------|
| `frontend/src/hooks/useWorkflowAutomation.ts` | **CORE**: Automacao SDLC, transicoes, recovery, expert triage |
| `frontend/src/hooks/useAgentExecution.ts` | Polling de execucoes, callbacks, executeExpertTriage, executeExpertSync |

### Frontend - API e Types

| Path | Responsabilidade |
|------|------------------|
| `frontend/src/types/live.ts` | Novo arquivo (revisar descrição) |
| `frontend/src/api/cards.ts` | Cliente API: moveCard, updateWorkflowState |
| `frontend/src/api/config.ts` | Endpoints incluindo /execute-expert-triage (AI) e /expert-sync |
| `frontend/src/types/index.ts` | **CORE**: Card, Column, ALLOWED_TRANSITIONS, ExpertMatch, CardExperts |

### Backend - Models

| Path | Responsabilidade |
|------|------------------|
| `backend/src/models/card.py` | **CORE**: Model Card com todos campos (inclui experts) |
| `backend/src/models/activity_log.py` | Rastreamento de mudancas |
| `backend/src/models/execution.py` | Execucoes de cards |

### Backend - Schemas e Validacao

| Path | Responsabilidade |
|------|------------------|
| `backend/src/schemas/card.py` | **CORE**: CardMove, validacao SDLC |
| `backend/src/schemas/expert.py` | **NEW**: ExpertMatch, TriageRequest, SyncRequest |

### Backend - Repository

| Path | Responsabilidade |
|------|------------------|
| `backend/src/repositories/card_repository.py` | **CORE**: CRUD + SDLC validation + update_experts |
| `backend/src/repositories/activity_repository.py` | Log de atividades |

### Backend - Routes

| Path | Responsabilidade |
|------|------------------|
| `backend/src/routes/cards_ws.py` | Novo arquivo (revisar descrição) |
| `backend/src/routes/cards.py` | Endpoints CRUD + move com validacao |
| `backend/src/routes/activities.py` | Endpoints de atividades |
| `backend/src/routes/experts.py` | **NEW**: Endpoints /expert-triage e /expert-sync |

### Backend - Services

| Path | Responsabilidade |
|------|------------------|
| `backend/src/services/auto_cleanup_service.py` | **CORE**: Move done -> completed |
| `backend/src/services/diff_analyzer.py` | Analise de diffs |
| `backend/src/services/expert_triage_service.py` | build_expert_context_for_plan (fallback keywords) |
| `backend/src/services/expert_sync_service.py` | Atualiza KNOWLEDGE.md dos experts |

### Backend - Agent (Execucao AI)

| Path | Responsabilidade |
|------|------------------|
| `backend/src/agent.py` | **CORE**: execute_expert_triage() - Triage via Claude AI |
| `backend/src/main.py` | Endpoint POST /api/execute-expert-triage |

### Claude Commands

| Path | Responsabilidade |
|------|------------------|
| `.claude/commands/expert-triage.md` | **NEW**: Comando AI para identificar experts |

### Backend - Config

| Path | Responsabilidade |
|------|------------------|
| `backend/src/config/experts.py` | **NEW**: AVAILABLE_EXPERTS com keywords e file_patterns |

## Colunas do Kanban (SDLC)

```
backlog -> plan -> implement -> test -> review -> done -> completed -> archived
                                                    |
                                                    v
                                               cancelado (terminal)
```

## Transicoes Permitidas

```python
ALLOWED_TRANSITIONS = {
    "backlog": ["plan", "cancelado"],
    "plan": ["implement", "cancelado"],
    "implement": ["test", "cancelado"],
    "test": ["review", "cancelado"],
    "review": ["done", "cancelado"],
    "done": ["completed", "archived", "cancelado"],
    "completed": ["archived"],
    "archived": ["done"],
    "cancelado": [],  # Terminal
}
```

## Workflow Stages

```
idle -> planning -> implementing -> testing -> reviewing -> completed | error
```

## Sistema de Experts

### Arquitetura

```
BACKLOG ────► PLAN ────────────────────────────► IMPLEMENT ─► TEST ─► REVIEW ─► DONE
               │                                                                  │
               ▼                                                                  ▼
        ┌─────────────┐                                                   ┌─────────────┐
        │ TRIAGE      │                                                   │ SYNC        │
        │ - Identifica│                                                   │ - Atualiza  │
        │   experts   │                                                   │   KNOWLEDGE │
        │ - Injeta    │                                                   │   dos       │
        │   contexto  │                                                   │   experts   │
        └─────────────┘                                                   └─────────────┘
```

### Expert Triage (backlog → plan) - AI-Powered

Quando um card move para `plan`, o sistema usa **IA (Claude)** para identificar experts:

1. Executa comando `/expert-triage` via Claude Agent SDK
2. IA descobre experts via Glob em `.claude/commands/experts/*/KNOWLEDGE.md`
3. IA le cada KNOWLEDGE.md e entende o dominio do expert
4. IA usa **raciocinio semantico** (nao keywords) para decidir relevancia
5. Retorna JSON com experts e confidence (high/medium/low)
6. Salva experts no campo `card.experts`
7. Injeta contexto do KNOWLEDGE.md no prompt do plan

**Arquivos:**

| Arquivo | Funcao |
|---------|--------|
| `.claude/commands/expert-triage.md` | Comando que a IA executa |
| `backend/src/agent.py` | `execute_expert_triage()` - executa via SDK |
| `backend/src/main.py` | Endpoint `POST /api/execute-expert-triage` |
| `frontend/src/hooks/useAgentExecution.ts` | `executeExpertTriage()` - chama endpoint |

**Fluxo:**
```
Frontend                    Backend                     Claude AI
    │                          │                            │
    │ POST /execute-expert-triage                           │
    ├─────────────────────────►│                            │
    │                          │ execute_expert_triage()    │
    │                          ├───────────────────────────►│
    │                          │                            │ Glob experts/*/KNOWLEDGE.md
    │                          │                            │ Read cada KNOWLEDGE.md
    │                          │                            │ Raciocinio semantico
    │                          │◄───────────────────────────┤ JSON com experts
    │                          │ Salva card.experts         │
    │◄─────────────────────────┤                            │
    │ {success, experts}       │                            │
```

### Expert Sync (review → done)

Quando um card completa (vai para `done`), o sistema:
1. Analisa arquivos modificados pelo card (diffStats)
2. Identifica quais experts foram afetados
3. Atualiza KNOWLEDGE.md de cada expert

**Arquivo:** `backend/src/services/expert_sync_service.py`

### Experts Disponiveis

Configurados em `backend/src/config/experts.py`:

| Expert ID | Keywords | File Patterns |
|-----------|----------|---------------|
| `database` | model, migration, SQL, repository, ORM... | backend/src/models/, backend/migrations/ |
| `kanban-flow` | card, coluna, workflow, drag, drop, SDLC... | frontend/src/components/Board/, hooks/useWorkflow... |

### Tipos TypeScript

`frontend/src/types/index.ts`:
```typescript
interface ExpertMatch {
  reason: string;
  confidence: 'high' | 'medium' | 'low';
  identified_at: string;
  knowledge_summary?: string;
  matched_keywords?: string[];
}

interface CardExperts {
  [expertId: string]: ExpertMatch;
}

interface Card {
  // ...
  experts?: CardExperts;
}
```

## Regras de Negocio

1. **Novo card sempre em backlog** - Forcado no create
2. **Workflow e linear** - Nao pode pular etapas
3. **Card em execucao e read-only** - Disabled draggable
4. **Execucoes preservadas em done** - Historico acessivel
5. **Auto-cleanup apos 30min** - done -> completed
6. **Fix cards automaticos** - Criados em falha de teste
7. **Expert triage via IA** - Claude analisa titulo/descricao e decide experts (backlog -> plan)
8. **Expert sync automatico** - Executado apos review (review -> done)
9. **Experts salvos no card** - Persistidos no campo `card.experts`
10. **Contexto injetado no plan** - KNOWLEDGE.md dos experts vai pro prompt
11. **Triage logado no backend** - Toda execucao de triage e persistida

## Specs Relacionadas

- `specs/kanban-board.md`
- `specs/auto-fix-workflow-complete.md`
- `specs/workflow-recovery-after-refresh.md`
- `specs/bloquear-arrasto-cards-nao-finalizados.md`
- `specs/auto-limpeza-cards-done.md`
- `specs/expert-system-integration.md` - **NEW**: Sistema autonomo de experts

## Ultima Atualizacao

2026-01-11 - Atualizado para Expert Triage via IA (substituiu keywords)
