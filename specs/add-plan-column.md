# Feature: Adicionar Coluna "Plan" ao Kanban Board

## Descrição
Adicionar uma nova coluna chamada "Plan" entre "Backlog" e "In Progress" no Kanban Board.

## Objetivo
Permitir uma etapa intermediária de planejamento antes de mover cards para desenvolvimento ativo.

---

## Plano de Implementação

### 1. Atualizar Tipos TypeScript
**Arquivo:** `src/types/index.ts`

- [x] Adicionar `'plan'` ao union type `ColumnId`
- [x] Adicionar objeto `{ id: 'plan', title: 'Plan' }` no array `COLUMNS` na posição 1 (após 'backlog')

### 2. Verificar Componentes (Sem alterações necessárias)
Os componentes já iteram dinamicamente sobre `COLUMNS`, então não precisam de modificações:
- `Board.tsx` - Itera sobre `columns` prop
- `Column.tsx` - Renderiza baseado nos dados recebidos
- `App.tsx` - Passa `COLUMNS` para o Board

### 3. Verificar Drag-and-Drop (Sem alterações necessárias)
- `handleDragOver` e `handleDragEnd` usam `COLUMNS.some()` para detectar colunas
- O ID 'plan' será automaticamente reconhecido como zona de drop válida

---

## Arquivos a Modificar

| Arquivo | Mudança |
|---------|---------|
| `src/types/index.ts` | Adicionar 'plan' ao tipo e ao array COLUMNS |

---

## Ordem das Colunas Após Implementação

1. Backlog
2. **Plan** (nova)
3. In Progress
4. Test
5. Review
6. Done

---

## Critérios de Aceite

- [x] Coluna "Plan" aparece entre "Backlog" e "In Progress"
- [x] Cards podem ser arrastados para a coluna "Plan"
- [x] Cards podem ser arrastados da coluna "Plan" para outras colunas
- [x] Contador de cards funciona na nova coluna
- [x] Estilo visual consistente com as demais colunas

---

## Testes

### Testes Manuais
1. Verificar que a coluna "Plan" aparece na posição correta
2. Arrastar um card do Backlog para Plan
3. Arrastar um card de Plan para In Progress
4. Verificar contador de cards na coluna Plan

### Testes Automatizados (se existirem)
- Verificar se testes existentes passam após a mudança
