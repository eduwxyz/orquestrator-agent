# Unique Lane Borders Design

## 1. Resumo

Transformar as raias (colunas) do Kanban em elementos visualmente distintos através de **bordas criativas e únicas** que representam visualmente cada etapa do SDLC. Cada raia terá um tratamento de borda diferenciado usando gradientes dinâmicos, padrões geométricos, animações sutis e efeitos de profundidade que comunicam a natureza de cada fase do fluxo de trabalho.

**Problema/Necessidade**: Atualmente, todas as raias têm bordas similares (apenas `border: 1px solid var(--border-subtle)`), dificultando a distinção visual rápida entre as etapas do processo. O usuário deseja que cada raia tenha um detalhe diferente nas bordas para ilustrar claramente a diferença entre as etapas.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Criar identidade visual única para cada uma das 6 raias (backlog, plan, in-progress, test, review, done)
- [x] Usar bordas criativas e diferenciadas (gradientes, padrões, animações, sombras)
- [x] Manter a coesão visual com o tema cosmic dark existente
- [x] Garantir que as diferenças sejam sutis o suficiente para manter elegância, mas distintas o suficiente para identificação rápida
- [x] Aplicar skill frontend-design para criar algo memorável e não-genérico

### Fora do Escopo
- Mudança na estrutura de dados ou lógica de negócio
- Modificação dos componentes Card ou AddCard
- Alteração de cores de fundo das raias (apenas bordas e detalhes)

---

## 3. Implementação

### Conceito de Design: "SDLC Energy States"

Cada etapa do SDLC será representada por um "estado de energia" visual diferente através das bordas:

1. **Backlog** → Estado **"Dormant"** (Dormente)
   - Borda pontilhada sutil com glow suave
   - Representa potencial não ativado

2. **Plan** → Estado **"Awakening"** (Despertando)
   - Borda com gradiente diagonal animado
   - Representa ideias se formando

3. **In Progress** → Estado **"Active Pulse"** (Pulso Ativo)
   - Borda dupla com animação de pulso
   - Representa trabalho ativo e energia

4. **Test** → Estado **"Scanning"** (Escaneando)
   - Borda com padrão de linhas escaneadas
   - Representa análise e verificação

5. **Review** → Estado **"Resonance"** (Ressonância)
   - Borda com ondas de energia
   - Representa refinamento e feedback

6. **Done** → Estado **"Crystallized"** (Cristalizado)
   - Borda sólida com facetas geométricas
   - Representa completude e solidez

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Column/Column.module.css` | Modificar | Adicionar estilos específicos para cada raia com bordas únicas |
| `frontend/src/components/Column/Column.tsx` | Modificar | Adicionar classe CSS específica para cada tipo de coluna |
| `frontend/src/App.module.css` | Modificar (opcional) | Ajustar variáveis CSS se necessário para novas cores de acento |

### Detalhes Técnicos

#### 1. Modificação em `Column.tsx`

Adicionar classe dinâmica baseada no `column.id`:

```tsx
export function Column({ column, cards, onAddCard, onRemoveCard, getExecutionStatus }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  return (
    <div
      ref={setNodeRef}
      className={`${styles.column} ${styles[`column_${column.id}`]} ${isOver ? styles.columnOver : ''}`}
    >
      {/* resto do código permanece igual */}
    </div>
  );
}
```

#### 2. Estilos Únicos em `Column.module.css`

Adicionar estilos específicos para cada raia:

```css
/* ========================================
   BACKLOG - Dormant State
   ======================================== */
.column_backlog {
  border: 2px dashed rgba(168, 85, 247, 0.3);
  position: relative;
}

.column_backlog::before {
  background: linear-gradient(90deg,
    transparent,
    rgba(168, 85, 247, 0.4) 50%,
    transparent
  );
  opacity: 0.3;
  animation: dormantGlow 3s ease-in-out infinite;
}

.column_backlog::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-xl);
  padding: 2px;
  background: linear-gradient(45deg,
    rgba(168, 85, 247, 0.1),
    transparent,
    rgba(168, 85, 247, 0.1)
  );
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.5;
}

@keyframes dormantGlow {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

/* ========================================
   PLAN - Awakening State
   ======================================== */
.column_plan {
  border: 2px solid transparent;
  background:
    linear-gradient(var(--bg-elevated), var(--bg-elevated)) padding-box,
    linear-gradient(135deg,
      rgba(0, 212, 255, 0.6),
      rgba(168, 85, 247, 0.6),
      rgba(0, 212, 255, 0.6)
    ) border-box;
  background-size: 100% 100%, 200% 200%;
  animation: awakeningGradient 4s ease infinite;
}

.column_plan::before {
  background: linear-gradient(135deg,
    transparent,
    rgba(0, 212, 255, 0.2) 30%,
    rgba(168, 85, 247, 0.2) 70%,
    transparent
  );
  opacity: 0.4;
}

@keyframes awakeningGradient {
  0%, 100% { background-position: 0% 0%, 0% 0%; }
  50% { background-position: 0% 0%, 100% 100%; }
}

/* ========================================
   IN-PROGRESS - Active Pulse State
   ======================================== */
.column_in-progress {
  border: 2px solid rgba(0, 212, 255, 0.5);
  box-shadow:
    0 0 20px rgba(0, 212, 255, 0.3),
    inset 0 0 20px rgba(0, 212, 255, 0.05);
  animation: activePulse 2s ease-in-out infinite;
}

.column_in-progress::before {
  background: linear-gradient(90deg,
    transparent,
    rgba(0, 212, 255, 0.6) 50%,
    transparent
  );
  opacity: 0.5;
  animation: energyFlow 2s linear infinite;
}

.column_in-progress::after {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: calc(var(--radius-xl) - 4px);
  pointer-events: none;
  animation: innerPulse 2s ease-in-out infinite;
}

@keyframes activePulse {
  0%, 100% {
    border-color: rgba(0, 212, 255, 0.5);
    box-shadow:
      0 0 20px rgba(0, 212, 255, 0.3),
      inset 0 0 20px rgba(0, 212, 255, 0.05);
  }
  50% {
    border-color: rgba(0, 212, 255, 0.8);
    box-shadow:
      0 0 30px rgba(0, 212, 255, 0.5),
      inset 0 0 30px rgba(0, 212, 255, 0.1);
  }
}

@keyframes energyFlow {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes innerPulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.7; }
}

/* ========================================
   TEST - Scanning State
   ======================================== */
.column_test {
  border: 2px solid rgba(52, 211, 153, 0.4);
  background-image:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 10px,
      rgba(52, 211, 153, 0.05) 10px,
      rgba(52, 211, 153, 0.05) 11px
    );
  position: relative;
  overflow: hidden;
}

.column_test::before {
  background: linear-gradient(180deg,
    rgba(52, 211, 153, 0.4) 0%,
    transparent 30%,
    transparent 70%,
    rgba(52, 211, 153, 0.4) 100%
  );
  height: 100%;
  opacity: 0.6;
  animation: scanningBeam 3s linear infinite;
}

.column_test::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg,
    transparent,
    rgba(52, 211, 153, 0.8),
    transparent
  );
  animation: scanLine 2s ease-in-out infinite;
}

@keyframes scanningBeam {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(200%); }
}

@keyframes scanLine {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(calc(100vh - 200px)); }
}

/* ========================================
   REVIEW - Resonance State
   ======================================== */
.column_review {
  border: 2px solid rgba(251, 191, 36, 0.4);
  position: relative;
}

.column_review::before {
  background: radial-gradient(
    ellipse at center,
    rgba(251, 191, 36, 0.3) 0%,
    transparent 70%
  );
  opacity: 0.5;
  animation: resonance 3s ease-in-out infinite;
}

.column_review::after {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at 20% 30%, rgba(251, 191, 36, 0.3) 0%, transparent 30%),
    radial-gradient(circle at 80% 70%, rgba(251, 191, 36, 0.3) 0%, transparent 30%),
    radial-gradient(circle at 50% 50%, rgba(251, 191, 36, 0.2) 0%, transparent 50%);
  opacity: 0;
  animation: echoRings 3s ease-in-out infinite;
  pointer-events: none;
  z-index: -1;
}

@keyframes resonance {
  0%, 100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.02);
  }
}

@keyframes echoRings {
  0% {
    opacity: 0;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.05);
  }
  100% {
    opacity: 0;
    transform: scale(1.1);
  }
}

/* ========================================
   DONE - Crystallized State
   ======================================== */
.column_done {
  border: 3px solid rgba(52, 211, 153, 0.6);
  background:
    linear-gradient(135deg, transparent 30%, rgba(52, 211, 153, 0.05) 30%, rgba(52, 211, 153, 0.05) 32%, transparent 32%),
    linear-gradient(225deg, transparent 30%, rgba(52, 211, 153, 0.05) 30%, rgba(52, 211, 153, 0.05) 32%, transparent 32%),
    var(--glass-bg);
  background-size: 40px 40px;
  box-shadow:
    0 0 30px rgba(52, 211, 153, 0.2),
    inset 0 2px 10px rgba(52, 211, 153, 0.1);
  position: relative;
}

.column_done::before {
  background: linear-gradient(135deg,
    rgba(52, 211, 153, 0.3) 0%,
    transparent 30%,
    transparent 70%,
    rgba(52, 211, 153, 0.3) 100%
  );
  opacity: 0.4;
}

.column_done::after {
  content: '';
  position: absolute;
  top: -3px;
  left: -3px;
  right: -3px;
  bottom: -3px;
  border-radius: var(--radius-xl);
  background:
    linear-gradient(45deg,
      rgba(52, 211, 153, 0.3) 0%,
      transparent 20%,
      transparent 40%,
      rgba(52, 211, 153, 0.2) 50%,
      transparent 60%,
      transparent 80%,
      rgba(52, 211, 153, 0.3) 100%
    );
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  padding: 3px;
  pointer-events: none;
  animation: crystallineShimmer 5s linear infinite;
}

@keyframes crystallineShimmer {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 200%; }
}
```

#### 3. Ajustes em variáveis CSS (App.module.css)

Adicionar novas cores de acento se necessário:

```css
:root {
  /* Cores existentes mantidas... */

  /* Novas cores para estados das raias */
  --accent-purple: #a855f7;
  --accent-green: #34d399;
  --accent-amber: #fbbf24;

  /* Já existem no código atual */
}
```

---

## 4. Testes

### Visuais
- [x] Verificar que cada raia tem borda visualmente distinta
- [x] Confirmar que animações funcionam suavemente (60fps)
- [x] Testar em diferentes tamanhos de tela (responsividade)
- [x] Validar que o estado `isOver` (drag over) ainda funciona e sobrepõe os estilos personalizados adequadamente

### Funcionais
- [x] Drag and drop continua funcionando normalmente
- [x] Transições SDLC não são afetadas
- [x] Performance não degradada (verificar com DevTools)

### Acessibilidade
- [x] Contraste adequado entre bordas e fundo
- [x] Animações podem ser pausadas se usuário preferir `prefers-reduced-motion`

---

## 5. Considerações

### Decisões de Design

**Por que "Energy States"?**
- Representa visualmente a progressão natural do trabalho: de ideia dormante → ativa → verificada → cristalizada
- Cada estado tem personalidade visual única e memorável
- Metáfora coesa que faz sentido intuitivamente

**Escolhas Técnicas:**
- Uso de pseudo-elementos `::before` e `::after` para adicionar camadas visuais sem poluir o DOM
- Animações CSS puras para máxima performance
- Gradientes e sombras para criar profundidade sem imagens
- Classes modulares específicas por coluna para fácil manutenção

### Performance

- **Risco**: Animações múltiplas podem impactar performance em dispositivos mais fracos
- **Mitigação**:
  - Usar `transform` e `opacity` (properties otimizadas por GPU)
  - Considerar `@media (prefers-reduced-motion: reduce)` para desabilitar animações se necessário
  - Limitar número de keyframes simultâneos

### Manutenção

- Cada raia tem um bloco CSS claramente separado e comentado
- Fácil ajustar ou desabilitar efeitos individuais
- Possibilidade futura: extrair para um arquivo `LaneStyles.module.css` dedicado se crescer muito

### Acessibilidade

Adicionar suporte para usuários que preferem movimento reduzido:

```css
@media (prefers-reduced-motion: reduce) {
  .column_backlog::before,
  .column_plan,
  .column_in-progress,
  .column_in-progress::before,
  .column_in-progress::after,
  .column_test::before,
  .column_test::after,
  .column_review::before,
  .column_review::after,
  .column_done::after {
    animation: none !important;
  }
}
```

---

## 6. Resultado Esperado

Após a implementação, o usuário verá:

1. **Backlog**: Borda pontilhada roxa suave com glow pulsante
2. **Plan**: Borda com gradiente cyan/roxo que flui diagonalmente
3. **In Progress**: Borda dupla cyan brilhante com pulso energético
4. **Test**: Borda verde com padrão de scan lines verticais
5. **Review**: Borda âmbar com ondas de ressonância que emanam
6. **Done**: Borda sólida verde com padrão geométrico cristalino

Cada raia será instantaneamente reconhecível pelo seu tratamento visual único, mantendo a coesão com o tema cosmic dark do aplicativo.
