## 1. Resumo

Adicionar uma coluna "Cancelado" ao Kanban Board após a coluna "Arquivado", permitindo que cards não desejados sejam movidos para esta nova coluna. A coluna deve ter funcionalidade de colapsar similar à coluna "Arquivado".

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar coluna "Cancelado" após a coluna "Arquivado"
- [x] Implementar funcionalidade de colapsar/expandir para a coluna "Cancelado"
- [x] Permitir transições válidas de outras colunas para "Cancelado"
- [x] Adicionar estilo visual distintivo para a coluna "Cancelado"
- [x] Manter estado de colapso independente para cada coluna (Arquivado e Cancelado)

### Fora do Escopo
- Automação de movimentação para cancelado
- Criação de cards diretamente na coluna cancelado

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | Adicionar 'cancelado' ao tipo ColumnId e atualizar transições permitidas |
| `frontend/src/App.tsx` | Modificar | Adicionar estado para colapsar coluna cancelado e passar props |
| `frontend/src/components/Board/Board.tsx` | Modificar | Gerenciar props de colapso para a coluna cancelado |
| `frontend/src/components/Column/Column.tsx` | Modificar | Adicionar lógica para tornar a coluna cancelado colapsável |
| `frontend/src/components/Column/Column.module.css` | Modificar | Adicionar estilos visuais para a coluna cancelado |
| `backend/src/schemas/card.py` | Modificar | Adicionar 'cancelado' ao ColumnId literal |
| `backend/src/repositories/card_repository.py` | Modificar | Adicionar transições permitidas para cancelado |

### Detalhes Técnicos

#### 1. Frontend - Tipos e Constantes

```typescript
// frontend/src/types/index.ts
export type ColumnId = 'backlog' | 'plan' | 'in-progress' | 'test' | 'review' | 'done' | 'archived' | 'cancelado';

export const COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'plan', title: 'Plan' },
  { id: 'in-progress', title: 'In Progress' },
  { id: 'test', title: 'Test' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' },
  { id: 'archived', title: 'Archived' },
  { id: 'cancelado', title: 'Cancelado' },
];

// Permitir transição de qualquer coluna para cancelado (exceto archived e cancelado)
export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'backlog': ['plan', 'cancelado'],
  'plan': ['in-progress', 'cancelado'],
  'in-progress': ['test', 'cancelado'],
  'test': ['review', 'cancelado'],
  'review': ['done', 'cancelado'],
  'done': ['archived', 'cancelado'],
  'archived': ['done'],
  'cancelado': [], // Não permite sair de cancelado
};
```

#### 2. Frontend - Estado de Colapso

```typescript
// frontend/src/App.tsx
// Adicionar novo estado
const [isCanceladoCollapsed, setIsCanceladoCollapsed] = useState(false);

// Passar para o Board
<Board
  // ... outras props
  isArchivedCollapsed={isArchivedCollapsed}
  onToggleArchivedCollapse={() => setIsArchivedCollapsed(!isArchivedCollapsed)}
  isCanceladoCollapsed={isCanceladoCollapsed}
  onToggleCanceladoCollapse={() => setIsCanceladoCollapsed(!isCanceladoCollapsed)}
/>
```

#### 3. Frontend - Board Component

```typescript
// frontend/src/components/Board/Board.tsx
interface BoardProps {
  // ... outras props existentes
  isCanceladoCollapsed?: boolean;
  onToggleCanceladoCollapse?: () => void;
}

// No render
{columns.map(column => {
  const isArchived = column.id === 'archived';
  const isCancelado = column.id === 'cancelado';

  return (
    <Column
      key={column.id}
      column={column}
      cards={cards.filter(card => card.columnId === column.id)}
      // ... outras props
      isCollapsed={
        isArchived ? isArchivedCollapsed :
        isCancelado ? isCanceladoCollapsed :
        false
      }
      onToggleCollapse={
        isArchived ? onToggleArchivedCollapse :
        isCancelado ? onToggleCanceladoCollapse :
        undefined
      }
    />
  );
})}
```

#### 4. Frontend - Column Component

```typescript
// frontend/src/components/Column/Column.tsx
const isArchivedColumn = column.id === 'archived';
const isCanceladoColumn = column.id === 'cancelado';
const isCollapsible = isArchivedColumn || isCanceladoColumn;

// No header
<div
  className={`${styles.header} ${isCollapsible ? styles.clickableHeader : ''}`}
  onClick={isCollapsible ? onToggleCollapse : undefined}
  style={isCollapsible ? { cursor: 'pointer' } : undefined}
>
  <h2 className={styles.title}>{column.title}</h2>
  <span className={styles.count}>{cards.length}</span>
  {isCollapsible && (
    <span className={styles.collapseIndicator}>
      {isCollapsed ? '▶' : '▼'}
    </span>
  )}
</div>
```

#### 5. Frontend - Estilos

```css
/* frontend/src/components/Column/Column.module.css */
/* CANCELADO - Red/Warning */
.column_cancelado {
  border-top: 3px solid rgba(239, 68, 68, 0.6);
  background: rgba(239, 68, 68, 0.02);
  opacity: 0.85; /* Levemente mais transparente para indicar estado final */
}

.column_cancelado .title {
  color: rgba(239, 68, 68, 0.8);
}

.column_cancelado.collapsed {
  opacity: 0.7;
}
```

#### 6. Backend - Schemas

```python
# backend/src/schemas/card.py
ColumnId = Literal["backlog", "plan", "in-progress", "test", "review", "done", "archived", "cancelado"]
```

#### 7. Backend - Repository

```python
# backend/src/repositories/card_repository.py
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "backlog": ["plan", "cancelado"],
    "plan": ["in-progress", "cancelado"],
    "in-progress": ["test", "cancelado"],
    "test": ["review", "cancelado"],
    "review": ["done", "cancelado"],
    "done": ["archived", "cancelado"],
    "archived": ["done"],
    "cancelado": [],  # Não permite sair de cancelado
}
```

---

## 4. Testes

### Unitários
- [x] Verificar que a coluna "Cancelado" aparece após "Arquivado"
- [x] Testar transições de todas as colunas (exceto archived) para cancelado
- [x] Verificar que não é possível mover cards de cancelado para outras colunas
- [x] Testar funcionalidade de colapsar/expandir da coluna cancelado

### Integração
- [ ] Verificar persistência do estado de colapso após recarregar a página
- [ ] Testar drag-and-drop de cards para a coluna cancelado
- [ ] Validar contagem de cards na coluna cancelado quando colapsada

---

## 5. Considerações

- **Riscos:**
  - Cards movidos para cancelado não poderão voltar para outras colunas (decisão de design intencional)
  - Mitigação: Adicionar confirmação ao mover para cancelado (opcional, futuro)

- **Dependências:**
  - Nenhuma dependência externa
  - Requer apenas atualização do frontend e backend em sincronia

- **Melhorias Futuras:**
  - Adicionar confirmação ao mover cards para cancelado
  - Implementar opção de exclusão permanente de cards cancelados
  - Adicionar filtro para ocultar cards cancelados nas visualizações