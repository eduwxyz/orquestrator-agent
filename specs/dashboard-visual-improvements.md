# Plan: Dashboard Visual Improvements

## 1. Resumo

Melhorar a aparência visual da aba Dashboard mantendo consistência com o design system do projeto. A dashboard atualmente tem elementos desalinhados, espaçamentos inconsistentes e não aproveita totalmente o tema dark minimalist já estabelecido. Utilizaremos a skill de frontend design para garantir coesão visual.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Aprimorar o visual da HomePage/Dashboard com design mais moderno e coeso
- [x] Melhorar hierarquia visual e legibilidade dos componentes
- [x] Adicionar micro-interações e animações sutis
- [x] Implementar glassmorphism effects consistentes com o tema
- [x] Otimizar responsividade para diferentes tamanhos de tela
- [x] Utilizar a skill frontend-design para criar componentes distintivos

### Fora do Escopo
- Mudanças funcionais nos componentes (apenas estética)
- Alteração da estrutura de dados ou APIs
- Modificação do layout principal do workspace

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/pages/HomePage.module.css` | Modificar | Refinar estilos da HomePage com glassmorphism e animações |
| `frontend/src/pages/HomePage.tsx` | Modificar | Adicionar elementos visuais decorativos e melhorar estrutura |
| `frontend/src/components/Dashboard/MetricCard.module.css` | Modificar | Aprimorar visual dos cards com gradientes e efeitos |
| `frontend/src/components/Dashboard/ActivityFeed.module.css` | Modificar | Melhorar timeline visual e animações |
| `frontend/src/components/Dashboard/ProgressChart.module.css` | Modificar | Adicionar visual mais moderno ao gráfico |
| `frontend/src/components/Dashboard/TokenUsagePanel.module.css` | Modificar | Aprimorar visualização de uso de tokens |
| `frontend/src/components/Dashboard/CostBreakdown.module.css` | Modificar | Melhorar gráficos e visualizações de custo |
| `frontend/src/components/Dashboard/ExecutionMetrics.module.css` | Modificar | Refinar métricas de execução |
| `frontend/src/styles/dashboard-theme.css` | Modificar | Adicionar novas variáveis CSS para efeitos especiais |

### Detalhes Técnicos

#### 3.1. Melhorias na HomePage

**Background Effects & Hero Section:**
```css
/* Adicionar efeitos de mesh gradient e noise texture */
.backgroundEffects {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.meshGradient {
  background: radial-gradient(circle at 20% 50%, var(--accent-cyan-glow) 0%, transparent 50%),
              radial-gradient(circle at 80% 80%, var(--accent-purple-glow) 0%, transparent 50%),
              radial-gradient(circle at 40% 20%, var(--accent-info-glow) 0%, transparent 50%);
  opacity: 0.15;
  filter: blur(80px);
  animation: floatGradient 20s ease-in-out infinite;
}

/* Hero section com glassmorphism */
.hero {
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  margin-bottom: var(--space-6);
}
```

**Métricas com Visual Cards Aprimorado:**
```css
/* Cards com hover effects e glows sutis */
.metricsGrid {
  display: grid;
  gap: var(--space-5);
  grid-auto-flow: dense;
}

/* Animações de entrada escalonadas */
.metricCard {
  animation: slideInUp 0.6s var(--ease-spring) both;
  animation-delay: calc(var(--index) * 0.1s);
}
```

#### 3.2. MetricCards com Design Distintivo

```css
/* Gradientes e bordas animadas */
.metricCard::before {
  content: '';
  position: absolute;
  inset: -1px;
  background: linear-gradient(
    135deg,
    var(--accent-color) 0%,
    transparent 40%,
    transparent 60%,
    var(--accent-color) 100%
  );
  border-radius: inherit;
  opacity: 0;
  transition: opacity 0.3s ease;
  animation: rotateBorder 3s linear infinite;
}

.metricCard:hover::before {
  opacity: 0.8;
}

/* Ícones com glow effects */
.iconWrapper {
  position: relative;
  background: var(--icon-gradient);
  box-shadow:
    0 0 20px var(--icon-shadow),
    inset 0 0 20px rgba(255, 255, 255, 0.1);
}
```

#### 3.3. ActivityFeed Timeline Aprimorado

```css
/* Timeline com conectores animados */
.timeline {
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 20px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(
    to bottom,
    var(--accent-cyan) 0%,
    var(--accent-purple) 100%
  );
  opacity: 0.3;
}

.activityItem {
  opacity: 0;
  animation: fadeInLeft 0.5s ease-out forwards;
}

/* Pulse animation nos ícones */
.iconContainer {
  animation: pulse 2s ease-in-out infinite;
}
```

#### 3.4. ProgressChart com Visualização Moderna

```css
/* Gráfico com gradientes e animações */
.flowChart {
  filter: drop-shadow(0 4px 20px var(--accent-cyan-glow));
}

.progressBar {
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
}

.progressFill {
  background: linear-gradient(90deg,
    var(--stage-color) 0%,
    var(--stage-color-light) 100%
  );
  box-shadow: 0 0 20px var(--stage-color-glow);
  animation: fillProgress 1s ease-out;
}

/* Shimmer effect */
.progressFill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 2s infinite;
}
```

#### 3.5. Skill Frontend Design Integration

Utilizaremos a skill `frontend-design` para:
- Criar componentes visuais distintivos e polidos
- Implementar micro-interações criativas
- Garantir que o design evite a estética genérica de AI
- Adicionar toques visuais únicos e memoráveis

```typescript
// Exemplo de componente com design distintivo
const AnimatedMetricCard = ({ data, index }) => {
  return (
    <div
      className={styles.metricCard}
      style={{ '--index': index }}
      data-glow-color={data.color}
    >
      <div className={styles.glowOrb} />
      <div className={styles.contentWrapper}>
        {/* Conteúdo com camadas visuais */}
      </div>
      <div className={styles.shimmerLayer} />
    </div>
  );
};
```

#### 3.6. Novas CSS Variables

```css
:root {
  /* Vibrant accent colors para dashboard */
  --accent-cyan-vibrant: #00d4ff;
  --accent-purple-vibrant: #b794f6;
  --accent-success-vibrant: #68d391;
  --accent-warning-vibrant: #f6ad55;
  --accent-info-vibrant: #63b3ed;
  --accent-danger-vibrant: #fc8181;

  /* Glass effects melhorados */
  --glass-blur-heavy: 40px;
  --glass-blur-light: 10px;
  --glass-refraction: rgba(255, 255, 255, 0.05);

  /* Animações */
  --spring-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
  --smooth-elastic: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

#### 3.7. Responsividade Melhorada

```css
/* Grid adaptativo para diferentes breakpoints */
@media (max-width: 1440px) {
  .metricsGrid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1024px) {
  .metricsGrid {
    grid-template-columns: repeat(2, 1fr);
  }

  .overviewGrid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .metricsGrid {
    grid-template-columns: 1fr;
  }
}
```

---

## 4. Testes

### Visuais
- [x] Verificar consistência de cores e temas (light/dark mode)
- [x] Testar animações e transições em diferentes navegadores
- [x] Validar responsividade em dispositivos móveis
- [x] Confirmar acessibilidade (contrast ratios, reduced motion)

### Performance
- [x] Verificar que animações não impactam performance
- [x] Testar com muitos cards/dados na dashboard
- [x] Validar tempo de renderização inicial

---

## 5. Considerações

### Riscos
- **Performance:** Muitos efeitos visuais podem impactar performance em dispositivos mais fracos
  - Mitigação: Usar CSS transforms/opacity para animações, implementar `prefers-reduced-motion`

- **Compatibilidade:** Alguns efeitos CSS podem não funcionar em navegadores antigos
  - Mitigação: Adicionar fallbacks progressivos

### Dependências
- Skill `frontend-design` para garantir design distintivo
- Testes em diferentes navegadores e dispositivos
- Feedback do usuário sobre melhorias visuais

### Notas de Implementação
- Manter todas as funcionalidades existentes intactas
- Focar em melhorias visuais incrementais
- Preservar a identidade visual dark/minimalist do projeto
- Adicionar comentários CSS explicativos para futuras manutenções