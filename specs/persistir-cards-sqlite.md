# Persistir Cards do Kanban em SQLite

## Objetivo
Implementar persistência dos cards do Kanban em banco de dados SQLite, permitindo que os dados sejam mantidos entre reinicializações do servidor.

## Contexto Atual
- Cards são armazenados em memória (React useState)
- SQLAlchemy já está configurado (`backend/src/database.py`)
- Banco SQLite disponível (`auth.db`)
- Model User já existe como referência

## Plano de Implementação

### 1. Backend - Model Card
- [x] Criar model `Card` em `backend/src/models/card.py`
  - id: String (UUID, PK)
  - title: String (não nulo)
  - description: String (opcional)
  - column_id: String (enum: backlog, plan, in-progress, test, review, done)
  - spec_path: String (opcional)
  - created_at: DateTime
  - updated_at: DateTime

### 2. Backend - Schema Pydantic
- [x] Criar schemas em `backend/src/schemas/card.py`
  - CardCreate: title, description
  - CardUpdate: title, description, column_id, spec_path
  - CardResponse: todos os campos

### 3. Backend - Repositório
- [x] Criar repositório em `backend/src/repositories/card_repository.py`
  - get_all(): Lista todos os cards
  - get_by_id(id): Busca card por ID
  - create(card): Cria novo card
  - update(id, card): Atualiza card existente
  - delete(id): Remove card
  - move(id, column_id): Move card para outra coluna

### 4. Backend - Rotas API
- [x] Criar rotas em `backend/src/routes/cards.py`
  - GET /api/cards - Listar todos
  - GET /api/cards/{id} - Buscar por ID
  - POST /api/cards - Criar card (sempre no backlog)
  - PUT /api/cards/{id} - Atualizar card
  - DELETE /api/cards/{id} - Remover card
  - PATCH /api/cards/{id}/move - Mover card entre colunas

### 5. Backend - Integração
- [x] Registrar rotas no `main.py`
- [x] Criar tabela no banco (init_db)
- [x] Atualizar `execute-plan` para salvar spec_path no banco

### 6. Frontend - API Client
- [x] Criar `frontend/src/api/cards.ts`
  - fetchCards(): GET /api/cards
  - createCard(data): POST /api/cards
  - updateCard(id, data): PUT /api/cards/{id}
  - deleteCard(id): DELETE /api/cards/{id}
  - moveCard(id, columnId): PATCH /api/cards/{id}/move

### 7. Frontend - Integração
- [x] Atualizar `App.tsx` para usar API ao invés de estado local
  - Carregar cards do banco ao iniciar
  - Chamar API em addCard, removeCard, moveCard
  - Atualizar spec_path via API após planejamento

## Arquivos Criados
1. `backend/src/models/card.py`
2. `backend/src/schemas/card.py`
3. `backend/src/repositories/card_repository.py`
4. `backend/src/routes/cards.py`
5. `frontend/src/api/cards.ts`

## Arquivos Modificados
1. `backend/src/main.py` - Registrar rotas e lifespan
2. `frontend/src/App.tsx` - Integrar com API

## Testes
- [x] Testar criação de card via API
- [x] Testar listagem de cards
- [x] Testar movimentação entre colunas
- [x] Testar persistência após reiniciar servidor
- [ ] Testar fluxo completo: criar → plan → implement (manual)

## Notas Técnicas
- Usar UUID para IDs (compatível com frontend atual)
- Manter validação de transições SDLC no backend
- Usar async/await para operações de banco
