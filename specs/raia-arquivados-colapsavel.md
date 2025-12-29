# Plano: Raia de Cards Arquivados Colapsável

**Tipo:** Feature (Refatoração da funcionalidade de arquivamento)

---

## 1. Resumo

Refatorar a funcionalidade de arquivamento de cards para criar uma **nova raia (coluna) dedicada** chamada "Archived" no final do board. Esta raia será **colapsável** (ao clicar no topo, os cards ficam escondidos, mostrando apenas o cabeçalho). A implementação atual permite arquivar cards dentro da coluna Done com toggle de visibilidade - essa abordagem será substituída por uma coluna separada e visual mais intuitivo.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar nova coluna "Archived" como última raia do board (após "Done")
- [x] Mover cards arquivados para essa nova coluna automaticamente
- [x] Implementar funcionalidade de colapsar/expandir a raia ao clicar no cabeçalho
- [x] Remover a lógica atual de toggle "Show/Hide Archived" da coluna Done
- [x] Manter a funcionalidade de arquivar cards (botão em cada card)
- [x] Permitir desarquivar cards (movendo-os de volta para Done)
- [x] Persistir estado de colapso da raia (localStorage ou estado local)

### Fora do Escopo
- Colapsar outras raias além de "Archived"
- Arrastar cards para dentro ou fora da raia Archived (apenas via botão de arquivar/desarquivar)
- Animações complexas de transição
- Filtros ou busca específica para cards arquivados

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | Adicionar 'archived' ao tipo ColumnId |
| `frontend/src/components/Board/Board.tsx` | Modificar | Passar estado de colapso e handlers para Column |
| `frontend/src/components/Column/Column.tsx` | Modificar | Implementar lógica de colapso e remover toggle antigo |
| `frontend/src/components/Column/Column.module.css` | Modificar | Adicionar estilos para coluna colapsada e indicador visual |
| `frontend/src/App.tsx` | Modificar | Adicionar estado para controlar colapso da raia Archived |
| `backend/src/repositories/card_repository.py` | Modificar | Atualizar lógica de arquivamento para mover para coluna 'archived' |
| `backend/src/schemas/card.py` | Modificar | Adicionar 'archived' como ColumnId válido (se necessário) |

### Detalhes Técnicos

#### 1. Frontend - Types

**Arquivo:** `frontend/src/types/index.ts`

```typescript
// Adicionar 'archived' como nova coluna
export type ColumnId = 'backlog' | 'plan' | 'in-progress' | 'test' | 'review' | 'done' | 'archived';

// Atualizar COLUMNS para incluir a nova raia
export const COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'plan', title: 'Plan' },
  { id: 'in-progress', title: 'In Progress' },
  { id: 'test', title: 'Test' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' },
  { id: 'archived', title: 'Archived' }, // Nova coluna
];

// Atualizar ALLOWED_TRANSITIONS para permitir done → archived
export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'backlog': ['plan'],
  'plan': ['in-progress'],
  'in-progress': ['test'],
  'test': ['review'],
  'review': ['done'],
  'done': ['archived'], // Permitir mover para archived
  'archived': ['done'], // Permitir desarquivar (voltar para done)
};

// Remover campo archived? do Card interface (não é mais necessário)
export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId; // Agora pode ser 'archived'
  specPath?: string;
  // archived?: boolean; <- REMOVER
}
```

#### 2. Frontend - App State

**Arquivo:** `frontend/src/App.tsx`

```typescript
function App() {
  const [cards, setCards] = useState<CardType[]>([]);
  const [activeCard, setActiveCard] = useState<CardType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isArchivedCollapsed, setIsArchivedCollapsed] = useState(false); // Novo estado
  // ... remover showArchived e setShowArchived

  // Remover ou ajustar useEffect que depende de showArchived
  useEffect(() => {
    const loadCards = async () => {
      try {
        // Buscar todos os cards (incluindo arquivados, pois agora estão na coluna 'archived')
        const loadedCards = await cardsApi.fetchCards(true); // Sempre incluir arquivados
        setCards(loadedCards);
      } catch (error) {
        console.error('[App] Failed to load cards:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadCards();
  }, []); // Sem dependência de showArchived

  // Remover função toggleArchiveCard (não é mais necessária)
  // A lógica de arquivar agora é apenas mover card para coluna 'archived'

  // Passar props para Board
  return (
    <Board
      columns={COLUMNS}
      cards={cards}
      onAddCard={addCard}
      onRemoveCard={removeCard}
      getExecutionStatus={getExecutionStatus}
      getWorkflowStatus={getWorkflowStatus}
      onRunWorkflow={runWorkflow}
      isArchivedCollapsed={isArchivedCollapsed}
      onToggleArchivedCollapse={() => setIsArchivedCollapsed(!isArchivedCollapsed)}
      // Remover: showArchived, onToggleShowArchived, onArchiveCard
    />
  );
}
```

#### 3. Frontend - Board Component

**Arquivo:** `frontend/src/components/Board/Board.tsx`

```typescript
interface BoardProps {
  columns: ColumnType[];
  cards: CardType[];
  onAddCard: (title: string, description: string, columnId: ColumnId) => void;
  onRemoveCard: (cardId: string) => void;
  getExecutionStatus?: (cardId: string) => ExecutionStatus | undefined;
  getWorkflowStatus?: (cardId: string) => WorkflowStatus | undefined;
  onRunWorkflow?: (card: CardType) => void;
  isArchivedCollapsed?: boolean; // Novo prop
  onToggleArchivedCollapse?: () => void; // Novo prop
  // Remover: showArchived, onToggleShowArchived, onArchiveCard
}

export function Board({
  columns,
  cards,
  onAddCard,
  onRemoveCard,
  getExecutionStatus,
  getWorkflowStatus,
  onRunWorkflow,
  isArchivedCollapsed,
  onToggleArchivedCollapse,
}: BoardProps) {
  return (
    <div className={styles.board}>
      {columns.map(column => {
        const isArchived = column.id === 'archived';

        return (
          <Column
            key={column.id}
            column={column}
            cards={cards.filter(card => card.columnId === column.id)}
            onAddCard={onAddCard}
            onRemoveCard={onRemoveCard}
            getExecutionStatus={getExecutionStatus}
            getWorkflowStatus={getWorkflowStatus}
            onRunWorkflow={onRunWorkflow}
            isCollapsed={isArchived ? isArchivedCollapsed : false}
            onToggleCollapse={isArchived ? onToggleArchivedCollapse : undefined}
            // Remover: showArchived, onToggleShowArchived, onArchiveCard
          />
        );
      })}
    </div>
  );
}
```

#### 4. Frontend - Column Component

**Arquivo:** `frontend/src/components/Column/Column.tsx`

```typescript
interface ColumnProps {
  column: ColumnType;
  cards: CardType[];
  onAddCard: (title: string, description: string, columnId: ColumnId) => void;
  onRemoveCard: (cardId: string) => void;
  getExecutionStatus?: (cardId: string) => ExecutionStatus | undefined;
  getWorkflowStatus?: (cardId: string) => WorkflowStatus | undefined;
  onRunWorkflow?: (card: CardType) => void;
  isCollapsed?: boolean; // Novo prop
  onToggleCollapse?: () => void; // Novo prop
  // Remover: showArchived, onToggleShowArchived, onArchiveCard
}

export function Column({
  column,
  cards,
  onAddCard,
  onRemoveCard,
  getExecutionStatus,
  getWorkflowStatus,
  onRunWorkflow,
  isCollapsed,
  onToggleCollapse,
}: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  const isArchivedColumn = column.id === 'archived';

  return (
    <div
      ref={setNodeRef}
      className={`${styles.column} ${styles[`column_${column.id}`]} ${isOver ? styles.columnOver : ''} ${isCollapsed ? styles.collapsed : ''}`}
    >
      <div
        className={`${styles.header} ${isArchivedColumn ? styles.clickableHeader : ''}`}
        onClick={isArchivedColumn ? onToggleCollapse : undefined}
        style={isArchivedColumn ? { cursor: 'pointer' } : undefined}
      >
        <h2 className={styles.title}>{column.title}</h2>
        <span className={styles.count}>{cards.length}</span>
        {isArchivedColumn && (
          <span className={styles.collapseIndicator}>
            {isCollapsed ? '▶' : '▼'}
          </span>
        )}
      </div>

      {!isCollapsed && (
        <div className={styles.cards}>
          {cards.map(card => (
            <Card
              key={card.id}
              card={card}
              onRemove={() => onRemoveCard(card.id)}
              executionStatus={getExecutionStatus?.(card.id)}
              workflowStatus={getWorkflowStatus?.(card.id)}
              onRunWorkflow={onRunWorkflow}
              // Remover: onArchive
            />
          ))}
        </div>
      )}

      {column.id === 'backlog' && !isCollapsed && (
        <AddCard columnId={column.id} onAdd={onAddCard} />
      )}
    </div>
  );
}
```

#### 5. Frontend - Column Styles

**Arquivo:** `frontend/src/components/Column/Column.module.css`

```css
/* Adicionar ao final do arquivo */

/* ARCHIVED - Gray/Muted */
.column_archived {
  border-top: 3px solid rgba(156, 163, 175, 0.6);
  background: rgba(156, 163, 175, 0.02);
}

.column_archived .title {
  color: rgba(156, 163, 175, 0.8);
}

/* Collapsed state */
.column.collapsed {
  flex: 0 0 80px; /* Largura reduzida quando colapsada */
  min-width: 80px;
}

.column.collapsed .header {
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.column.collapsed .title {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  transform: rotate(180deg);
}

/* Clickable header (apenas para Archived) */
.clickableHeader {
  position: relative;
  user-select: none;
  transition: background 0.2s;
}

.clickableHeader:hover {
  background: rgba(156, 163, 175, 0.05);
  border-radius: var(--radius-md);
}

/* Collapse indicator */
.collapseIndicator {
  font-size: 12px;
  color: var(--text-muted);
  transition: transform 0.2s;
  margin-left: 4px;
}

/* Remover ou comentar o estilo .toggleArchived (não é mais usado) */
/*
.toggleArchived {
  ...
}
*/
```

#### 6. Frontend - Card Component (Ajustes menores)

**Arquivo:** `frontend/src/components/Card/Card.tsx`

```typescript
// Remover prop onArchive e toda a lógica relacionada
interface CardProps {
  card: CardType;
  onRemove: () => void;
  executionStatus?: ExecutionStatus;
  workflowStatus?: WorkflowStatus;
  onRunWorkflow?: (card: CardType) => void;
  isDragging?: boolean;
  // Remover: onArchive?: (archived: boolean) => void;
}

// Remover:
// - Botão de arquivar (📦)
// - Badge "Archived"
// - Lógica relacionada a isArchived
```

**Arquivo:** `frontend/src/components/Card/Card.module.css`

```css
/* Remover ou comentar estilos não usados */
/*
.archived { ... }
.archivedBadge { ... }
.archiveButton { ... }
*/
```

#### 7. Backend - Schemas (Ajustes)

**Arquivo:** `backend/src/schemas/card.py`

```python
# Verificar se ColumnId já inclui 'archived' como valor válido
# Se usar Enum, adicionar:

class ColumnId(str, Enum):
    """Valid column IDs for cards."""
    BACKLOG = "backlog"
    PLAN = "plan"
    IN_PROGRESS = "in-progress"
    TEST = "test"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"  # Adicionar

# Remover schema CardArchive (não é mais necessário, pois arquivamento é via move)
```

#### 8. Backend - Repository (Ajustes)

**Arquivo:** `backend/src/repositories/card_repository.py`

```python
# Atualizar ALLOWED_TRANSITIONS
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "backlog": ["plan"],
    "plan": ["in-progress"],
    "in-progress": ["test"],
    "test": ["review"],
    "review": ["done"],
    "done": ["archived"],  # Adicionar
    "archived": ["done"],  # Permitir desarquivar
}

# Remover método archive_card (não é mais necessário)
# Arquivamento agora é feito via move()

# Atualizar get_all para sempre incluir cards arquivados
async def get_all(self, include_archived: bool = True) -> list[Card]:
    """Get all cards ordered by creation date."""
    query = select(Card).order_by(Card.created_at)
    # Não precisa mais filtrar por archived, pois está na coluna
    result = await self.session.execute(query)
    return list(result.scalars().all())
```

#### 9. Backend - Routes (Ajustes)

**Arquivo:** `backend/src/routes/cards.py`

```python
# Remover endpoint /archive (linha 109-122)
# Arquivamento agora é via PATCH /move

# Atualizar GET /cards para remover param include_archived
@router.get("", response_model=CardsListResponse)
async def get_all_cards(db: AsyncSession = Depends(get_db)):
    """Get all cards."""
    repo = CardRepository(db)
    cards = await repo.get_all()
    return CardsListResponse(
        cards=[CardResponse.model_validate(card) for card in cards]
    )
```

#### 10. Backend - Migrations

**Arquivo:** `backend/migrations/002_migrate_archived_to_column.sql` (NOVO)

```sql
-- Migrar cards arquivados para a nova coluna 'archived'
-- (Se houver cards com archived=true, movê-los para column_id='archived')

UPDATE cards
SET column_id = 'archived'
WHERE archived = true;

-- Opcional: Remover coluna 'archived' após migração (se quiser limpar)
-- ALTER TABLE cards DROP COLUMN archived;
```

---

## 4. Testes

### Unitários
- [x] Testar que 'archived' é um ColumnId válido
- [x] Testar transições done → archived e archived → done
- [x] Tetestar que coluna Archived renderiza corretamente
- [x] Testar estado de colapso (collapsed/expanded)

### Integração
- [x] Mover card de Done para Archived (via drag-and-drop ou API)
- [x] Mover card de Archived para Done (desarquivar)
- [x] Clicar no header da raia Archived para colapsar
- [x] Clicar novamente para expandir
- [x] Verificar que cards arquivados persistem após reload
- [x] Verificar que contador mostra quantidade correta na raia Archived

### Manual
- [x] Criar vários cards e movê-los até Done
- [x] Arrastar cards de Done para Archived
- [x] Verificar que aparecem na nova raia
- [x] Clicar no topo da raia Archived
- [x] Verificar que a raia colapsa, mostrando apenas o título vertical
- [x] Clicar novamente e verificar que expande
- [x] Arrastar card de Archived de volta para Done
- [x] Recarregar a página e verificar que tudo persiste

---

## 5. Considerações

### Riscos
- **Migração de dados:** Cards já arquivados (com `archived=true`) precisam ser migrados para `column_id='archived'`. Criar script de migração SQL.
- **Compatibilidade:** Se houver outros clientes ou integrações usando a API, podem quebrar com a remoção do endpoint `/archive`.
- **UX de drag-and-drop:** Ao colapsar a raia, pode ser confuso arrastar cards para ela. Considerar desabilitar drop quando colapsada.

### Dependências
- Nenhuma dependência externa ou PRs bloqueantes

### Decisões Arquiteturais

1. **Coluna dedicada vs campo booleano:**
   - **Escolhido:** Coluna dedicada (`columnId='archived'`)
   - **Motivo:** Torna o estado mais explícito no board, facilita drag-and-drop, e simplifica a lógica de renderização (não precisa filtrar, apenas renderizar coluna)

2. **Colapso apenas para Archived:**
   - **Escolhido:** Apenas a coluna Archived é colapsável
   - **Motivo:** Simplicidade. Outras colunas representam trabalho ativo e devem estar sempre visíveis. Archived é informacional/histórico.

3. **Persistência do estado de colapso:**
   - **Escolhido:** Estado local no App.tsx (não persistido entre sessões)
   - **Alternativa considerada:** localStorage para persistir preferência do usuário
   - **Decisão:** Começar com estado local; adicionar localStorage se usuários solicitarem

4. **Remoção do campo `archived`:**
   - **Escolhido:** Manter o campo `archived` no banco por enquanto (para compatibilidade), mas não usá-lo no frontend
   - **Alternativa:** Remover completamente após migração
   - **Decisão:** Manter por segurança, pode ser útil para rollback ou queries futuras

5. **Transições permitidas:**
   - `done → archived`: Permite arquivar
   - `archived → done`: Permite desarquivar
   - Não permitir outras transições para evitar confusão no fluxo SDLC

### Alternativas Consideradas

- **Botão "Archive All" na coluna Done:** Rejeitada, pois usuário quer controle individual de quando arquivar
- **Auto-arquivamento após X dias:** Rejeitada, usuário quer controle manual
- **Múltiplas raias colapsáveis:** Rejeitada por complexidade; apenas Archived precisa desse comportamento

---

## 6. Fluxo de Trabalho Esperado

1. Usuário move card até coluna "Done"
2. Com o tempo, Done acumula muitos cards
3. Usuário arrasta cards antigos de "Done" para "Archived" (nova raia no final)
4. Cards aparecem na raia "Archived"
5. Usuário clica no topo da raia "Archived"
6. Raia colapsa, mostrando apenas o título vertical e contador
7. Board fica mais limpo e focado em trabalho ativo
8. Se necessário, usuário pode expandir novamente para ver histórico
9. Se quiser "desarquivar", arrasta card de volta para "Done"
