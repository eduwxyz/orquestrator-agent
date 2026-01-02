# Bloquear Arrasto de Cards Não Finalizados

## 1. Resumo

Implementar uma nova regra de validação no sistema de drag and drop do kanban que impede que cards sejam arrastados para outras raias enquanto não estiverem finalizados. Um card será considerado finalizado quando estiver nas colunas "Done", "Archived" ou "Cancelado". Esta regra reforça o fluxo SDLC sequencial e evita que cards inacabados sejam movidos prematuramente.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar propriedade computada `isFinalized` aos cards para identificar seu status de finalização
- [x] Bloquear drag and drop de cards não finalizados no frontend
- [x] Adicionar validação no backend para prevenir movimentações inválidas via API
- [x] Exibir feedback visual claro quando o arrasto for bloqueado
- [x] Manter compatibilidade com o fluxo SDLC existente

### Fora do Escopo
- Alterar o fluxo SDLC existente (ALLOWED_TRANSITIONS)
- Modificar a lógica de execução automática dos comandos
- Alterar a estrutura do banco de dados

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | Adicionar função helper `isCardFinalized` para verificar se um card está finalizado |
| `frontend/src/components/Card/Card.tsx` | Modificar | Desabilitar drag para cards não finalizados e adicionar indicador visual |
| `frontend/src/App.tsx` | Modificar | Adicionar validação no handleDragStart para prevenir arrasto de cards não finalizados |
| `backend/src/repositories/card_repository.py` | Modificar | Adicionar validação de finalização antes de permitir movimentação |
| `backend/src/schemas/card.py` | Modificar | Adicionar propriedade computada `is_finalized` ao CardResponse |

### Detalhes Técnicos

#### 1. Frontend - Adicionar helper function em types/index.ts:

```typescript
// Adicionar após a função isValidTransition
export function isCardFinalized(columnId: ColumnId): boolean {
  return columnId === 'done' || columnId === 'archived' || columnId === 'cancelado';
}
```

#### 2. Frontend - Modificar Card.tsx para desabilitar drag:

```typescript
// No componente Card, modificar a configuração do useDraggable
const { attributes, listeners, setNodeRef, transform } = useDraggable({
  id: card.id,
  disabled: !isCardFinalized(card.columnId) // Desabilitar drag para cards não finalizados
});

// Adicionar classe CSS para indicar visualmente que o card não pode ser arrastado
<div
  ref={setNodeRef}
  style={style}
  className={`${styles.card} ${isDragging ? styles.dragging : ''} ${getStatusClass()} ${card.isFixCard ? styles.fixCard : ''} ${!isCardFinalized(card.columnId) ? styles.notDraggable : ''}`}
  {...listeners}
  {...attributes}
>
```

#### 3. Frontend - Adicionar validação em App.tsx:

```typescript
const handleDragStart = (event: DragStartEvent) => {
  const { active } = event;
  const card = cards.find(c => c.id === active.id);
  if (card) {
    // Verificar se o card está finalizado antes de permitir o drag
    if (!isCardFinalized(card.columnId)) {
      event.preventDefault?.();
      alert('Este card precisa ser finalizado (movido para Done, Archived ou Cancelado) antes de poder ser arrastado para outras raias.');
      return;
    }
    setActiveCard(card);
    dragStartColumnRef.current = card.columnId;
  }
};
```

#### 4. Backend - Adicionar validação em card_repository.py:

```python
async def move(self, card_id: str, new_column_id: str) -> tuple[Card | None, str | None]:
    """Move card to another column with SDLC and finalization validation."""
    card = await self.get_by_id(card_id)
    if not card:
        return None, "Card not found"

    # Verificar se o card está finalizado
    finalized_columns = ['done', 'archived', 'cancelado']
    if card.column_id not in finalized_columns and new_column_id != card.column_id:
        # Permitir apenas movimentação dentro do fluxo SDLC normal se não estiver finalizado
        if not self._is_valid_transition(card.column_id, new_column_id):
            return None, f"Card precisa ser finalizado antes de poder ser movido. Finalize movendo para Done, Archived ou Cancelado."

    # Validação SDLC existente
    if not self._is_valid_transition(card.column_id, new_column_id):
        return None, f"Transição inválida: {card.column_id} → {new_column_id}"

    card.column_id = new_column_id
    await self.db.commit()
    await self.db.refresh(card)
    return card, None
```

#### 5. Backend - Adicionar propriedade em schemas/card.py:

```python
class CardResponse(BaseModel):
    # ... campos existentes ...

    @property
    def is_finalized(self) -> bool:
        """Check if card is in a finalized state."""
        return self.column_id in ['done', 'archived', 'cancelado']

    class Config:
        populate_by_name = True
        from_attributes = True
```

#### 6. Frontend - Adicionar estilos CSS em Card.module.css:

```css
.notDraggable {
  opacity: 0.8;
  cursor: not-allowed !important;
  position: relative;
}

.notDraggable::after {
  content: '🔒';
  position: absolute;
  top: 8px;
  right: 40px;
  font-size: 14px;
  opacity: 0.6;
  title: 'Card não finalizado - não pode ser arrastado';
}
```

---

## 4. Testes

### Unitários
- [x] Testar função `isCardFinalized` com diferentes columnIds
- [x] Testar que cards em 'done', 'archived' e 'cancelado' podem ser arrastados
- [x] Testar que cards em outras colunas não podem ser arrastados

### Integração
- [x] Testar drag and drop bloqueado no frontend para cards não finalizados
- [x] Testar que API retorna erro ao tentar mover card não finalizado
- [x] Testar que cards finalizados continuam podendo ser movidos normalmente
- [x] Verificar feedback visual do bloqueio (cursor not-allowed, ícone de cadeado)

---

## 5. Considerações

### Riscos
- **Mudança de comportamento:** Usuários acostumados com o fluxo atual podem estranhar a nova restrição
- **Mitigação:** Adicionar mensagens claras explicando por que o card não pode ser movido

### Alternativas Consideradas
1. **Permitir movimentação apenas no fluxo SDLC:** Já implementado, mas a nova regra adiciona uma camada extra de validação
2. **Criar estado "finalizado" no banco:** Desnecessário, pois a coluna já indica o estado

### Notas de Implementação
- A regra se aplica apenas ao drag and drop manual - o workflow automático continua funcionando normalmente
- Cards podem continuar sendo movidos dentro do fluxo SDLC normal (backlog → plan → in-progress → test → review → done)
- A restrição só impede movimentação "para trás" ou "pular etapas" quando o card não está finalizado