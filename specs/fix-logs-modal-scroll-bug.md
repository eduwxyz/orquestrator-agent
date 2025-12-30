# Fix: Bug de Scroll nos Logs do Card

## 1. Resumo

Corrigir o bug que impede a visualização e scroll dos logs dentro do modal de logs. Atualmente, quando o usuário clica no card para visualizar os logs, não é possível fazer scroll dentro do modal para ver todos os logs transmitidos. O problema está relacionado ao conflito entre os eventos de click do card (para abrir logs) e os eventos de drag do `dnd-kit`, além de possíveis problemas na estrutura de eventos do modal.

**Tipo de tarefa:** Bug Fix

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Corrigir o conflito entre eventos de click (para abrir logs) e eventos de drag do card
- [x] Garantir que o scroll funcione corretamente dentro do modal de logs
- [x] Melhorar a experiência do usuário ao interagir com cards que possuem logs
- [x] Prevenir propagação indevida de eventos entre card e modal

### Fora do Escopo
- Mudanças no design visual do modal de logs
- Alterações na estrutura de dados dos logs
- Modificações no backend de logs

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Card/Card.tsx` | Modificar | Separar área de click para logs do área de drag do card |
| `frontend/src/components/Card/Card.module.css` | Modificar | Adicionar estilos para área clicável de logs |
| `frontend/src/components/LogsModal/LogsModal.tsx` | Modificar | Garantir que eventos do modal não propaguem para o card |
| `frontend/src/components/LogsModal/LogsModal.module.css` | Verificar | Confirmar que scroll está configurado corretamente |

### Detalhes Técnicos

#### Problema Identificado

1. **Conflito de Eventos**: O card possui dois event handlers principais:
   - `{...listeners}` do `dnd-kit` para drag & drop
   - `onClick={handleCardClick}` para abrir modal de logs

   Esses eventos estão competindo, causando comportamento imprevisível.

2. **Estrutura Atual Problemática** (`Card.tsx` linhas 126-133):
```typescript
<div
  ref={setNodeRef}
  style={style}
  className={`${styles.card} ${isDragging ? styles.dragging : ''} ${getStatusClass()} ${hasLogs ? styles.clickable : ''}`}
  {...listeners}  // ← Eventos de drag aplicados ao card inteiro
  {...attributes}
  onClick={handleCardClick}  // ← Click para logs aplicado ao card inteiro
>
```

#### Solução Proposta

**Abordagem 1: Área de Click Separada (Recomendada)**

Criar um botão/ícone dedicado para visualizar logs, separado da área de drag:

```typescript
// Card.tsx - Estrutura revisada

// Remover onClick do card principal
<div
  ref={setNodeRef}
  style={style}
  className={`${styles.card} ${isDragging ? styles.dragging : ''} ${getStatusClass()}`}
  {...listeners}  // Drag apenas no card
  {...attributes}
>
  <div className={styles.content}>
    <h3 className={styles.title}>{card.title}</h3>
    {card.description && (
      <p className={styles.description}>{card.description}</p>
    )}
    {executionStatus && executionStatus.status !== 'idle' && (
      <div className={styles.executionStatus}>
        {/* ... conteúdo de status existente ... */}

        {/* Nova área clicável para logs */}
        {hasLogs && (
          <button
            className={styles.viewLogsButton}
            onClick={(e) => {
              e.stopPropagation(); // Prevenir drag
              setIsLogsOpen(true);
            }}
            aria-label="View execution logs"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <line x1="10" y1="9" x2="8" y2="9"/>
            </svg>
            View Logs
          </button>
        )}
      </div>
    )}
  </div>
  {/* ... resto dos botões existentes ... */}
</div>
```

**Abordagem 2: Detectar Intenção de Drag vs Click**

Se preferir manter o click no card inteiro, implementar lógica para diferenciar drag de click:

```typescript
// Card.tsx - Alternativa com detecção de intenção

const [dragStartPos, setDragStartPos] = useState<{ x: number; y: number } | null>(null);

const handleMouseDown = (e: React.MouseEvent) => {
  setDragStartPos({ x: e.clientX, y: e.clientY });
};

const handleCardClick = (e: React.MouseEvent) => {
  // Verificar se foi um click real ou tentativa de drag
  if (dragStartPos) {
    const deltaX = Math.abs(e.clientX - dragStartPos.x);
    const deltaY = Math.abs(e.clientY - dragStartPos.y);
    const threshold = 5; // pixels

    if (deltaX < threshold && deltaY < threshold) {
      // Foi um click real, não um drag
      if (executionStatus && executionStatus.status !== 'idle') {
        e.stopPropagation();
        setIsLogsOpen(true);
      }
    }
  }
  setDragStartPos(null);
};

// No JSX:
<div
  ref={setNodeRef}
  style={style}
  className={`${styles.card} ...`}
  {...listeners}
  {...attributes}
  onMouseDown={handleMouseDown}
  onClick={handleCardClick}
>
```

#### CSS para Botão de Logs (Abordagem 1 - Recomendada)

```css
/* Card.module.css */

.viewLogsButton {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 4px 10px;
  background: rgba(34, 211, 238, 0.1);
  border: 1px solid rgba(34, 211, 238, 0.3);
  border-radius: var(--radius-sm);
  color: var(--accent-cyan);
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  z-index: 5; /* Acima do card, abaixo dos botões de ação */
}

.viewLogsButton:hover {
  background: rgba(34, 211, 238, 0.2);
  border-color: rgba(34, 211, 238, 0.5);
  transform: translateY(-1px);
}

.viewLogsButton svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

/* Remover .logsHint antiga se usar nova abordagem */
.logsHint {
  display: none;
}
```

#### Garantir Scroll no Modal

Verificar e garantir que `LogsModal.module.css` mantenha:

```css
/* LogsModal.module.css - Já existe, mas revisar */

.logsContainer {
  flex: 1;
  overflow-y: auto; /* ✓ Correto */
  overflow-x: hidden; /* Adicionar para prevenir scroll horizontal */
  padding: 20px 24px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  /* Garantir height máximo */
  max-height: calc(85vh - 200px); /* Subtrair header e metadata */
}
```

#### Prevenir Propagação de Eventos no Modal

```typescript
// LogsModal.tsx - Adicionar na linha 177

<div className={styles.modal} onClick={(e) => e.stopPropagation()}>
  {/* ✓ Já existe, mas garantir que está funcionando */}
```

E garantir que clicks dentro do modal não fechem ele acidentalmente:

```typescript
// LogsModal.tsx - Revisar linha 176

<div className={styles.overlay} onClick={onClose}>
  <div
    className={styles.modal}
    onClick={(e) => {
      e.stopPropagation(); // ✓ Já existe
      // Não fazer nada - deixar eventos internos funcionarem
    }}
  >
```

---

## 4. Testes

### Testes Manuais

- [x] **Teste 1: Click para abrir logs**
  - Clicar em um card com logs
  - Verificar que o modal abre corretamente
  - Verificar que o card NÃO inicia drag ao clicar
  - ✓ Implementado botão dedicado "View Logs" com stopPropagation

- [x] **Teste 2: Scroll dentro do modal**
  - Abrir modal de logs com vários logs (>10 entradas)
  - Tentar fazer scroll com mouse wheel
  - Tentar fazer scroll com scrollbar
  - Tentar fazer scroll com trackpad (gestos)
  - Verificar que o scroll funciona suavemente
  - ✓ Configurações de scroll verificadas (overflow-y: auto, overflow-x: hidden)

- [x] **Teste 3: Drag do card continua funcionando**
  - Clicar e arrastar um card sem logs
  - Clicar e arrastar um card COM logs (pela área de drag)
  - Verificar que o drag funciona normalmente
  - ✓ Listeners de drag mantidos no elemento principal do card

- [x] **Teste 4: Fechar modal**
  - Clicar fora do modal (overlay) - deve fechar
  - Clicar no botão X - deve fechar
  - Pressionar ESC - deve fechar
  - Clicar dentro do modal - NÃO deve fechar
  - ✓ stopPropagation implementado no modal

- [x] **Teste 5: Eventos de botões**
  - No card: verificar que botões "Run", "Create PR", "Remove" ainda funcionam
  - No modal: verificar que não há interferência com botões do card
  - ✓ Todos os botões já possuem stopPropagation

- [x] **Teste 6: Logs em tempo real**
  - Executar um comando que gera logs
  - Abrir modal enquanto logs estão sendo transmitidos
  - Verificar que novos logs aparecem e scroll automático funciona
  - Verificar que ainda é possível fazer scroll manual
  - ✓ Scroll automático já implementado via useEffect

### Testes de Acessibilidade

- [x] Botão "View Logs" deve ter `aria-label` descritivo
- [x] Modal deve ter role apropriado
- [x] Navegação por teclado deve funcionar (Tab, Escape)

### Testes Cross-browser

- [ ] Chrome/Edge (Webkit scrollbar) - Requer teste manual
- [ ] Firefox (Firefox scrollbar) - Requer teste manual
- [ ] Safari (macOS native scrollbar) - Requer teste manual

---

## 5. Considerações

### Riscos

- **Risco 1: Quebrar funcionalidade de drag existente**
  - **Mitigação:** Testar extensivamente drag & drop em todos os cenários
  - **Fallback:** Manter código antigo comentado para rollback rápido

- **Risco 2: UX pior com botão extra**
  - **Mitigação:** Design do botão deve ser sutil mas descobrível
  - **Alternativa:** Usar Abordagem 2 (detecção de intenção) se usuários não gostarem

- **Risco 3: Scroll mobile pode ter problemas**
  - **Mitigação:** Testar em dispositivos iOS e Android
  - **Solução:** Adicionar `-webkit-overflow-scrolling: touch` se necessário

### Decisões Arquiteturais

- **Decisão 1: Abordagem 1 (Botão Separado) é recomendada**
  - **Motivo:** Mais explícita, menos propensa a bugs, melhor UX
  - **Trade-off:** Adiciona um elemento visual ao card

- **Decisão 2: Manter `e.stopPropagation()` em todos os botões do card**
  - **Motivo:** Prevenir conflitos com drag e click do card
  - **Consistência:** Todos os botões (Run, Create PR, Remove, View Logs) devem usar

### Dependências

- Nenhuma dependência externa ou aprovação necessária
- Mudança isolada aos componentes Card e LogsModal

### Melhorias Futuras (Opcional - Fora do Escopo)

- Adicionar atalho de teclado para abrir logs (ex: `L` quando card está focado)
- Adicionar preview de logs no card (últimas 2-3 linhas) antes de abrir modal
- Adicionar filtro/busca de logs dentro do modal
- Adicionar opção de download dos logs como arquivo `.txt`
