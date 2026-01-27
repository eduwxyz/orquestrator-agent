# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zenflow is an AI-powered workflow management system with Kanban board, automated task execution via Claude Agent SDK, and real-time WebSocket communication. Cards flow through stages: Backlog → Plan → Implement → Test → Review → Done.

## Development Commands

### Quick Start
```bash
npm run dev              # Run both frontend (5173) and backend (3001)
make dev-parallel        # Alternative: run both in background
```

### Individual Services
```bash
# Frontend
cd frontend && npm run dev      # Vite dev server on port 5173
cd frontend && npm run build    # Production build (tsc + vite)

# Backend
cd backend && python -m src.main    # FastAPI on port 3001
```

### Testing
```bash
# Backend tests (pytest with async support)
cd backend && pytest
cd backend && pytest tests/test_specific.py -v    # Single test file

# Frontend has Playwright configured but tests are minimal
```

### Setup
```bash
npm run setup            # Install all dependencies
make install-backend     # Python venv + requirements.txt
make install-frontend    # npm install
```

## Architecture

### Frontend (`frontend/`)
- **React 18 + TypeScript + Vite**
- Proxy config: `/api` → `localhost:3001`, `/ws` → WebSocket
- Entry: `src/main.tsx` (routes), `src/App.tsx` (main state)
- Key patterns:
  - Pages in `src/pages/` (KanbanPage, ChatPage, LivePage, etc.)
  - Components in `src/components/` (Board, Card, Chat, Live)
  - Custom hooks in `src/hooks/` (useAgentExecution, useCardWebSocket, useLiveWebSocket)
  - API layer in `src/api/` (REST + WebSocket clients)
  - CSS Modules for styling

### Backend (`backend/src/`)
- **FastAPI + SQLAlchemy 2 (async) + SQLite**
- Entry: `main.py` (app setup, routers)
- Key directories:
  - `models/` - SQLAlchemy models (Card, Execution, Goal, Action)
  - `repositories/` - Data access layer
  - `services/` - Business logic (orchestrator_service, live_broadcast_service)
  - `routes/` - API endpoints (REST + WebSocket)
  - `config/` - Pydantic settings, pricing config

### Core Subsystems

**Orchestrator** (`services/orchestrator_service.py`): Autonomous THINK/DO loop that decomposes goals into actions, manages card execution, and broadcasts progress.

**Agent Execution** (`agent.py`): Executes Claude Agent SDK commands per workflow stage (plan, implement, test, review). Each stage is configurable with different models.

**WebSocket Communication**: Real-time updates for card changes (`routes/cards_ws.py`), execution streaming (`routes/execution_ws.py`), and live broadcast events (`routes/live.py`).

**Multi-Model Support**: Claude (Opus 4.5, Sonnet 4.5, Haiku 4.5) and Gemini models, with per-card model selection and cost tracking.

### Database
- Main DB: `backend/auth.db` (SQLite)
- Per-project: `.claude/database.db`
- Vector DB: Qdrant on Docker (port 6333) for embeddings

## Claude Agent SDK Integration

Custom commands in `.claude/commands/`:
- `/plan` - Generate implementation spec → `specs/<name>.md`
- `/implement` - Execute spec file
- `/test-implementation` - Validate implementation
- `/review` - Code review
- `/dev-workflow` - Full pipeline (plan → implement → test → review)
- `/expert-triage` - Identify relevant experts for a task

Post-tool hooks sync Kanban flow knowledge base on Edit/Write operations.

## Key Files

- `backend/src/main.py` - FastAPI app, CORS, routers
- `backend/src/agent.py` - Agent execution core (~2600 lines)
- `backend/src/services/orchestrator_service.py` - Autonomous task execution
- `frontend/src/App.tsx` - Main component, workspace state
- `frontend/src/hooks/useAgentExecution.ts` - Frontend workflow automation
- `frontend/vite.config.ts` - Dev server proxy configuration
