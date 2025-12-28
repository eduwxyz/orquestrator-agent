## 1. Resumo

Simplificar o design das raias do Kanban para uma abordagem **minimalista**, mantendo identidade visual única para cada etapa do SDLC, mas removendo animações complexas, múltiplas camadas de pseudo-elementos e efeitos elaborados. O objetivo é criar distinção visual clara através de **cores sutis, bordas simples e design limpo**.

**Problema/Necessidade**: As raias atualmente têm um design muito elaborado com gradientes animados, múltiplos pseudo-elementos (::before e ::after), box-shadows complexos e várias animações simultâneas. O usuário prefere algo mais minimalista e limpo, mantendo a distinção entre as raias mas com uma estética mais sóbria.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Simplificar drasticamente o CSS das raias, removendo animações complexas
- [x] Manter cores únicas para cada raia, mas de forma mais sutil
- [x] Remover ou simplificar pseudo-elementos (::before e ::after)
- [x] Usar bordas sólidas simples com cores distintivas
- [x] Reduzir uso de gradientes, box-shadows e efeitos visuais pesados
- [x] Manter a legibilidade e distinção visual entre as raias
- [x] Preservar a funcionalidade de drag-and-drop e estados hover/over

### Fora do Escopo
- Mudança na estrutura de dados ou lógica de negócio
- Modificação dos componentes Card ou AddCard
- Alteração na arquitetura TypeScript/React

---

## 3. Implementação

### Conceito de Design: "Minimal SDLC Indicators"

Cada raia terá:
- **Borda superior colorida** (3-4px) como indicador principal
- **Cor de fundo sutil** opcional para reforço visual
- **Sem animações** (ou apenas 1 animação muito sutil se necessário)
- **Sem pseudo-elementos** complexos (máximo 1 se realmente necessário)
- **Tipografia como elemento diferenciador** (title com cor da raia)

#### Paleta Minimalista por Raia:

1. **Backlog** (Roxo)
   - Borda superior: `border-top: 3px solid rgba(168, 85, 247, 0.6)`
   - Background: `background: var(--glass-bg)` (padrão, sem mudanças)
   - Title color ao hover: roxo sutil

2. **Plan** (Azul/Cyan)
   - Borda superior: `border-top: 3px solid rgba(0, 212, 255, 0.6)`
   - Background: `background: var(--glass-bg)`
   - Title color ao hover: cyan sutil

3. **In Progress** (Cyan vibrante)
   - Borda superior: `border-top: 3px solid rgba(0, 212, 255, 0.8)`
   - Background: `rgba(0, 212, 255, 0.03)` (só um toque)
   - Title color ao hover: cyan vibrante

4. **Test** (Verde)
   - Borda superior: `border-top: 3px solid rgba(52, 211, 153, 0.6)`
   - Background: `var(--glass-bg)`
   - Title color ao hover: verde sutil

5. **Review** (Amarelo/Âmbar)
   - Borda superior: `border-top: 3px solid rgba(251, 191, 36, 0.6)`
   - Background: `var(--glass-bg)`
   - Title color ao hover: âmbar sutil

6. **Done** (Verde escuro/esmeralda)
   - Borda superior: `border-top: 3px solid rgba(52, 211, 153, 0.8)`
   - Background: `rgba(52, 211, 153, 0.02)`
   - Opcional: borda lateral esquerda também

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Column/Column.module.css` | Modificar | **Simplificar drasticamente** os estilos das raias, removendo animações, pseudo-elementos complexos e efeitos pesados |
| `frontend/src/components/Column/Column.tsx` | Nenhuma mudança | A estrutura de classes já existe e funciona |

---

## 4. Detalhes Técnicos

### Substituir Estilos Complexos por Minimalistas

**Antes (exemplo do BACKLOG atual):**
```css
.column_backlog {
  border: 2px dashed rgba(168, 85, 247, 0.3);
  position: relative;
}

.column_backlog::before {
  background: linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.4) 50%, transparent);
  opacity: 0.3;
  animation: dormantGlow 3s ease-in-out infinite;
}

.column_backlog::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-xl);
  padding: 2px;
  background: linear-gradient(45deg, rgba(168, 85, 247, 0.1), transparent, rgba(168, 85, 247, 0.1));
  /* ... mais 5 linhas de mask complexo ... */
}

@keyframes dormantGlow {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}
```

**Depois (minimalista):**
```css
.column_backlog {
  border-top: 3px solid rgba(168, 85, 247, 0.6);
}

.column_backlog .title {
  color: rgba(168, 85, 247, 0.8);
}
```

### Nova Implementação Completa (Column.module.css)

```css
/* ========================================
   UNIQUE LANE BORDERS - Minimal Approach
   ======================================== */

/* Remove todos os estilos antigos complexos e substitui por: */

/* BACKLOG - Purple */
.column_backlog {
  border-top: 3px solid rgba(168, 85, 247, 0.6);
}

.column_backlog .title {
  color: rgba(168, 85, 247, 0.8);
}

/* PLAN - Cyan/Blue */
.column_plan {
  border-top: 3px solid rgba(0, 212, 255, 0.6);
}

.column_plan .title {
  color: rgba(0, 212, 255, 0.8);
}

/* IN-PROGRESS - Bright Cyan */
.column_in-progress {
  border-top: 3px solid rgba(0, 212, 255, 0.9);
  background: rgba(0, 212, 255, 0.03);
}

.column_in-progress .title {
  color: var(--accent-cyan);
}

/* TEST - Green */
.column_test {
  border-top: 3px solid rgba(52, 211, 153, 0.6);
}

.column_test .title {
  color: rgba(52, 211, 153, 0.8);
}

/* REVIEW - Amber */
.column_review {
  border-top: 3px solid rgba(251, 191, 36, 0.6);
}

.column_review .title {
  color: rgba(251, 191, 36, 0.8);
}

/* DONE - Emerald Green */
.column_done {
  border-top: 3px solid rgba(52, 211, 153, 0.8);
  border-left: 2px solid rgba(52, 211, 153, 0.4);
  background: rgba(52, 211, 153, 0.02);
}

.column_done .title {
  color: rgba(52, 211, 153, 0.9);
}
```

### Alterações Necessárias no Arquivo

**Remover completamente:**
- Todas as 12 animações `@keyframes` (dormantGlow, awakeningGradient, activePulse, energyFlow, innerPulse, scanningBeam, scanLine, resonance, echoRings, crystallineShimmer)
- Todos os blocos `::before` e `::after` das raias específicas
- Todos os box-shadows animados
- Todos os gradientes complexos
- A seção `@media (prefers-reduced-motion: reduce)` (não será mais necessária)

**Manter:**
- Estilos base `.column` (linhas 1-13)
- `.columnOver` para estado de drag (linhas 31-47)
- `.header`, `.title`, `.count`, `.cards` (linhas 49-110)

**Adicionar:**
- Nova seção minimalista com ~40 linhas (substituindo as ~300 linhas atuais)

---

## 5. Testes

### Visuais
- [x] Verificar que cada raia tem borda top colorida distinta
- [x] Confirmar que titles das raias têm cores correspondentes
- [x] Validar que não há animações indesejadas
- [ ] Testar em diferentes tamanhos de tela (responsividade)
- [ ] Validar que o estado `columnOver` (drag over) ainda funciona

### Funcionais
- [ ] Drag and drop continua funcionando normalmente
- [ ] Transições SDLC não são afetadas
- [ ] Performance melhorada (verificar com DevTools - deve ser mais leve)

### Comparação Visual
- [ ] Capturar screenshot antes/depois
- [ ] Confirmar com usuário se o nível de minimalismo está adequado

---

## 6. Considerações

### Decisões de Design

**Por que Minimalismo?**
- Reduz distração visual
- Melhora performance (sem animações pesadas)
- Design mais atemporal e profissional
- Foco no conteúdo (cards) ao invés dos containers

**Por que Borda Superior?**
- Elemento mais visível ao escanear horizontalmente o board
- Não interfere com conteúdo interno
- Padrão comum em interfaces modernas (tabs, sections)
- Fácil de identificar de relance

### Performance

**Melhoria esperada:**
- Redução de ~300 linhas de CSS para ~40 linhas
- Remoção de 12 animações CSS
- Eliminação de múltiplos pseudo-elementos com gradientes
- Menos recalculations e repaints no navegador
- Melhor performance em dispositivos móveis/baixo desempenho

### Manutenção

- CSS drasticamente mais simples e legível
- Fácil adicionar novas raias no futuro
- Sem complexidade de debugar animações ou pseudo-elementos
- Cores centralizadas e fáceis de ajustar

### Extensibilidade Futura (Opcional)

Se no futuro o usuário quiser **um pouco** mais de sofisticação sem voltar ao design anterior, pode-se adicionar:
- Uma leve transição de cor no hover: `transition: border-color 0.2s ease`
- Um box-shadow muito sutil: `box-shadow: 0 2px 0 0 rgba(cor-da-raia, 0.1) inset`
- Um ícone no header com a cor da raia

Mas por enquanto, mantemos **estritamente minimalista**.

---

## 7. Resultado Esperado

Após a implementação, o usuário verá:

1. **Backlog**: Borda superior roxa (3px)
2. **Plan**: Borda superior cyan (3px)
3. **In Progress**: Borda superior cyan vibrante (3px) + background sutil
4. **Test**: Borda superior verde (3px)
5. **Review**: Borda superior âmbar/amarela (3px)
6. **Done**: Borda superior + esquerda verde (3px + 2px) + background sutil

Cada raia será **imediatamente reconhecível pela cor da borda superior**, sem distrações de animações ou efeitos complexos. O design será limpo, profissional e focado no conteúdo.

**Redução estimada:** De ~300 linhas de CSS complexo para ~40 linhas simples.
