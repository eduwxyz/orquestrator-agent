# Plano: Opção Arquivar/Colapsar Cards na Coluna Done

**Tipo:** Feature

---

## 1. Resumo

Implementar uma funcionalidade para arquivar ou colapsar cards que estão na coluna "Done", permitindo que o board mantenha um histórico de trabalhos completos sem sobrecarregar visualmente a interface. O usuário mencionou que cards em "done" estão acumulando e tornando o board difícil de visualizar. A solução deve preservar os cards (não deletá-los) mas oferecer uma forma de "escondê-los" da visualização principal.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar campo `archived` ao modelo de Card (banco de dados)
- [x] Criar botão de toggle na coluna Done para mostrar/esconder cards arquivados
- [x] Implementar estado visual diferenciado para cards arquivados
- [x] Adicionar opção individual para arquivar/desarquivar cards na coluna Done
- [x] Garantir que cards arquivados sejam filtrados da visualização padrão
- [x] Persistir estado de arquivamento no backend

### Fora do Escopo
- Funcionalidade de arquivamento para outras colunas além de "Done"
- Busca/filtros avançados de cards arquivados
- Relatórios ou analytics sobre cards arquivados
- Exclusão permanente de cards arquivados (essa funcionalidade já existe via botão X)

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/models/card.py` | Modificar | Adicionar campo `archived: bool` ao modelo Card |
| `backend/src/schemas/card.py` | Modificar | Adicionar campo `archived` aos schemas de resposta e update |
| `backend/src/repositories/card_repository.py` | Modificar | Atualizar queries para filtrar cards arquivados por padrão |
| `backend/src/routes/cards.py` | Modificar | Adicionar endpoint PATCH `/cards/{card_id}/archive` |
| `frontend/src/types/index.ts` | Modificar | Adicionar campo `archived?: boolean` à interface Card |
| `frontend/src/api/cards.ts` | Modificar | Adicionar função `archiveCard()` e atualizar `fetchCards()` |
| `frontend/src/components/Column/Column.tsx` | Modificar | Adicionar botão toggle para mostrar/esconder arquivados na coluna Done |
| `frontend/src/components/Card/Card.tsx` | Modificar | Adicionar botão de arquivar e estado visual para cards arquivados |
| `frontend/src/components/Column/Column.module.css` | Modificar | Adicionar estilos para botão toggle e cards arquivados |
| `frontend/src/components/Card/Card.module.css` | Modificar | Adicionar estilos para indicador de arquivamento e botão |
| `frontend/src/App.tsx` | Modificar | Adicionar estado para controlar visualização de arquivados |

### Detalhes Técnicos

#### 1. Backend - Modelo de Dados

**Arquivo:** `backend/src/models/card.py`

```python
# Adicionar novo campo ao modelo Card
archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

**Migração de banco de dados necessária:**
```sql
ALTER TABLE cards ADD COLUMN archived BOOLEAN DEFAULT FALSE NOT NULL;
```

#### 2. Backend - Schemas

**Arquivo:** `backend/src/schemas/card.py`

```python
# Adicionar ao CardResponse
archived: bool = False

# Adicionar ao CardUpdate
archived: Optional[bool] = None

# Novo schema para arquivamento
class CardArchive(BaseModel):
    """Schema for archiving/unarchiving a card."""
    archived: bool
```

#### 3. Backend - Repository

**Arquivo:** `backend/src/repositories/card_repository.py`

```python
# Modificar get_all para aceitar filtro opcional
def get_all(self, include_archived: bool = False) -> list[Card]:
    """Get all cards, optionally including archived ones."""
    query = self.db.query(Card)
    if not include_archived:
        query = query.filter(Card.archived == False)
    return query.order_by(Card.created_at.desc()).all()

# Adicionar método para arquivar/desarquivar
def archive_card(self, card_id: str, archived: bool) -> Card | None:
    """Archive or unarchive a card."""
    card = self.get_by_id(card_id)
    if card:
        card.archived = archived
        card.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(card)
    return card
```

#### 4. Backend - Routes

**Arquivo:** `backend/src/routes/cards.py`

```python
@router.patch("/{card_id}/archive", response_model=CardSingleResponse)
def archive_card(
    card_id: str,
    archive_data: CardArchive,
    db: Session = Depends(get_db)
):
    """Archive or unarchive a card."""
    repo = CardRepository(db)
    card = repo.archive_card(card_id, archive_data.archived)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return CardSingleResponse(card=CardResponse.model_validate(card))

# Modificar GET /cards para aceitar query param
@router.get("", response_model=CardsListResponse)
def get_cards(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all cards, optionally including archived ones."""
    repo = CardRepository(db)
    cards = repo.get_all(include_archived=include_archived)
    return CardsListResponse(
        cards=[CardResponse.model_validate(card) for card in cards]
    )
```

#### 5. Frontend - Types

**Arquivo:** `frontend/src/types/index.ts`

```typescript
export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
  specPath?: string;
  archived?: boolean; // Novo campo
}
```

#### 6. Frontend - API Client

**Arquivo:** `frontend/src/api/cards.ts`

```typescript
/**
 * Archive or unarchive a card.
 */
export async function archiveCard(cardId: string, archived: boolean): Promise<Card> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/archive`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ archived }),
  });

  if (!response.ok) {
    throw new Error(`Failed to archive card: ${response.statusText}`);
  }

  const data: CardSingleResponse = await response.json();
  return mapCardResponseToCard(data.card);
}

/**
 * Fetch all cards from the API.
 */
export async function fetchCards(includeArchived: boolean = false): Promise<Card[]> {
  const url = `${API_BASE}/cards${includeArchived ? '?include_archived=true' : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch cards: ${response.statusText}`);
  }

  const data: CardsListResponse = await response.json();
  return data.cards.map(mapCardResponseToCard);
}
```

#### 7. Frontend - App State

**Arquivo:** `frontend/src/App.tsx`

```typescript
function App() {
  // ... código existente ...
  const [showArchived, setShowArchived] = useState(false);

  // Modificar loadCards para incluir arquivados quando necessário
  useEffect(() => {
    const loadCards = async () => {
      try {
        const loadedCards = await cardsApi.fetchCards(showArchived);
        setCards(loadedCards);
      } catch (error) {
        console.error('[App] Failed to load cards:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadCards();
  }, [showArchived]); // Adicionar showArchived como dependência

  // Adicionar função para arquivar cards
  const toggleArchiveCard = async (cardId: string, archived: boolean) => {
    try {
      await cardsApi.archiveCard(cardId, archived);
      // Atualizar estado local
      setCards(prev =>
        prev.map(card =>
          card.id === cardId ? { ...card, archived } : card
        )
      );
    } catch (error) {
      console.error('[App] Failed to archive card:', error);
      alert('Falha ao arquivar card.');
    }
  };

  // Passar props para Board
  // <Board ... showArchived={showArchived} onToggleShowArchived={setShowArchived} onArchiveCard={toggleArchiveCard} />
}
```

#### 8. Frontend - Column Component

**Arquivo:** `frontend/src/components/Column/Column.tsx`

```typescript
interface ColumnProps {
  // ... props existentes ...
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
  onArchiveCard?: (cardId: string, archived: boolean) => void;
}

export function Column({
  column,
  cards,
  showArchived,
  onToggleShowArchived,
  onArchiveCard,
  // ... outros props ...
}: ColumnProps) {
  // ... código existente ...

  const isDoneColumn = column.id === 'done';
  const archivedCards = cards.filter(c => c.archived);
  const activeCards = cards.filter(c => !c.archived);
  const displayCards = showArchived ? cards : activeCards;

  return (
    <div className={`${styles.column} ${styles[`column_${column.id}`]} ${isOver ? styles.columnOver : ''}`}>
      <div className={styles.header}>
        <h2 className={styles.title}>{column.title}</h2>
        <span className={styles.count}>
          {activeCards.length}
          {archivedCards.length > 0 && ` (+${archivedCards.length})`}
        </span>
        {isDoneColumn && archivedCards.length > 0 && (
          <button
            className={styles.toggleArchived}
            onClick={onToggleShowArchived}
            title={showArchived ? 'Hide archived cards' : 'Show archived cards'}
          >
            {showArchived ? '📦 Hide Archived' : '📦 Show Archived'}
          </button>
        )}
      </div>
      <div className={styles.cards}>
        {displayCards.map(card => (
          <Card
            key={card.id}
            card={card}
            onRemove={() => onRemoveCard(card.id)}
            onArchive={isDoneColumn ? (archived) => onArchiveCard?.(card.id, archived) : undefined}
            // ... outros props ...
          />
        ))}
      </div>
      {/* ... resto do código ... */}
    </div>
  );
}
```

#### 9. Frontend - Card Component

**Arquivo:** `frontend/src/components/Card/Card.tsx`

```typescript
interface CardProps {
  // ... props existentes ...
  onArchive?: (archived: boolean) => void;
}

export function Card({
  card,
  onRemove,
  onArchive,
  // ... outros props ...
}: CardProps) {
  // ... código existente ...

  const isArchived = card.archived || false;

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={`
          ${styles.card}
          ${isDragging ? styles.dragging : ''}
          ${isArchived ? styles.archived : ''}
          ${getStatusClass()}
          ${hasLogs ? styles.clickable : ''}
        `}
        {...listeners}
        {...attributes}
        onClick={handleCardClick}
      >
        {isArchived && (
          <div className={styles.archivedBadge}>
            📦 Archived
          </div>
        )}
        {/* ... conteúdo existente do card ... */}

        {/* Adicionar botão de arquivar apenas para cards na coluna Done */}
        {card.columnId === 'done' && onArchive && (
          <button
            className={styles.archiveButton}
            onClick={(e) => {
              e.stopPropagation();
              onArchive(!isArchived);
            }}
            aria-label={isArchived ? 'Unarchive card' : 'Archive card'}
            title={isArchived ? 'Restore this card' : 'Archive this card'}
          >
            {isArchived ? '↩️' : '📦'}
          </button>
        )}

        {/* Botão de remover existente */}
        <button className={styles.removeButton} /* ... */ >
          {/* ... */}
        </button>
      </div>
      {/* ... modal de logs ... */}
    </>
  );
}
```

#### 10. Frontend - Estilos

**Arquivo:** `frontend/src/components/Card/Card.module.css`

```css
.archived {
  opacity: 0.6;
  border-left: 4px solid #9ca3af;
  background: linear-gradient(135deg, #f9fafb 0%, #e5e7eb 100%);
}

.archivedBadge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #6b7280;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.archiveButton {
  position: absolute;
  bottom: 8px;
  left: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 16px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.archiveButton:hover {
  opacity: 1;
}
```

**Arquivo:** `frontend/src/components/Column/Column.module.css`

```css
.toggleArchived {
  margin-left: 8px;
  padding: 4px 8px;
  font-size: 12px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.toggleArchived:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

.count {
  /* Ajustar para acomodar contador de arquivados */
  font-size: 14px;
  color: #6b7280;
}
```

---

## 4. Testes

### Unitários
- [ ] Testar campo `archived` no modelo Card (backend)
- [ ] Testar endpoint PATCH `/cards/{id}/archive`
- [ ] Testar filtro `include_archived` no GET `/cards`
- [ ] Testar função `archiveCard()` na API client (frontend)
- [ ] Testar renderização de cards arquivados vs ativos

### Integração
- [ ] Testar fluxo completo: arquivar card → verificar que desaparece da visualização padrão
- [ ] Testar fluxo: mostrar arquivados → verificar que cards arquivados aparecem
- [ ] Testar fluxo: desarquivar card → verificar que volta à visualização normal
- [ ] Verificar que cards arquivados persistem após reload da página
- [ ] Verificar que contador na coluna Done mostra quantidade correta (ativos + arquivados)

### Manual
- [ ] Criar vários cards na coluna Done
- [ ] Arquivar alguns cards e verificar que ficam visualmente diferenciados
- [ ] Clicar em "Show Archived" e verificar que todos aparecem
- [ ] Clicar em "Hide Archived" e verificar que apenas ativos aparecem
- [ ] Desarquivar um card e verificar que volta ao estado normal
- [ ] Verificar que botão de arquivar só aparece em cards da coluna Done

---

## 5. Considerações

### Riscos
- **Migração de banco de dados:** Adicionar coluna `archived` requer migração. Se houver muitos cards, pode levar tempo. Mitigar: fazer backup antes da migração.
- **Performance:** Se houver muitos cards arquivados, a query pode ficar lenta. Mitigar: adicionar índice na coluna `archived` se necessário.

### Dependências
- Nenhuma dependência externa ou PRs bloqueantes

### Decisões Arquiteturais
1. **Arquivar vs Colapsar:** Optamos por "arquivar" (mover para estado inativo) ao invés de "colapsar" (apenas esconder visualmente) porque:
   - Permite queries mais eficientes (filtrar no backend vs filtrar no frontend)
   - Facilita features futuras como relatórios de cards arquivados
   - Mantém interface mais limpa (cards arquivados não ocupam espaço até serem explicitamente mostrados)

2. **Apenas coluna Done:** Restringimos arquivamento apenas à coluna "Done" porque:
   - É onde há acúmulo de cards (problema original do usuário)
   - Cards em outras colunas representam trabalho em andamento e não devem ser "escondidos"
   - Simplifica UX e evita confusão

3. **Toggle global vs individual:** Implementamos ambos:
   - Toggle na coluna (mostrar/esconder todos arquivados) para visualização rápida
   - Botão individual em cada card para arquivar/desarquivar especificamente

### Alternativas Consideradas
- **Deletar automaticamente após X dias:** Rejeitada porque usuário quer manter histórico
- **Mover para coluna "Archive" separada:** Rejeitada porque adiciona complexidade ao board e ao fluxo SDLC
- **Paginação na coluna Done:** Possível alternativa, mas arquivamento é mais semântico e útil
