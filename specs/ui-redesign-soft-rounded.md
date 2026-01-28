# UI Redesign — Soft & Rounded

## 1. Resumo

Redesign completo da UI do Zenflow substituindo o tema "Deep Dark Minimalist" com glassmorphism por um novo design system "Soft & Rounded" — dark, clean, premium, com cantos arredondados, sombras suaves e cores pastel. A navegação muda de sidebar lateral para top nav horizontal, ganhando espaço para o Kanban board.

**Design de referência:** `frontend/design-preview-soft.html`

---

## 2. Objetivos e Escopo

### Objetivos
- [ ] Substituir sidebar por top navigation horizontal
- [ ] Aplicar nova paleta de cores (pastel suave, sem neon/glow)
- [ ] Aumentar border-radius em toda a aplicação (8px-20px)
- [ ] Substituir glassmorphism por sombras suaves e bordas sutis
- [ ] Redesign de todas as 4 páginas (Dashboard, Kanban, Chat, Settings)
- [ ] Manter toda funcionalidade existente intacta

### Fora do Escopo
- Mudanças no backend/API
- Novas funcionalidades
- Light mode (manter dark only)
- Mudanças em hooks ou lógica de negócio

---

## 3. Implementação

### Design Tokens — Nova Paleta

Substituir completamente as variáveis em `dashboard-theme.css`:

```css
:root {
  /* Backgrounds */
  --bg-primary: #121215;
  --bg-secondary: #1A1A1F;    /* was: #16161a */
  --bg-tertiary: #1A1A1F;     /* surface — cards, containers */
  --bg-elevated: #222228;     /* was: #25252b */
  --bg-hover: #2A2A31;
  --bg-inset: #0E0E11;        /* NEW — inputs, recessed areas */

  /* Borders — mais visíveis que antes */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.06);
  --border-strong: rgba(255, 255, 255, 0.12);
  --border-highlight: rgba(255, 255, 255, 0.12);

  /* Text — off-white ao invés de branco puro */
  --text-primary: #F0F0F3;    /* was: #ffffff */
  --text-secondary: #9494A0;  /* was: #a1a1aa */
  --text-tertiary: #5C5C68;   /* was: #71717a */

  /* Accent — roxo mais suave */
  --accent-primary: #8B7BF5;       /* was: #7c3aed */
  --accent-primary-hover: #9D8FF7;
  --accent-primary-subtle: rgba(139,123,245,0.12);
  --accent-primary-soft: rgba(139,123,245,0.06);

  /* Semantic — tons pastel */
  --accent-success: #4ADE80;   /* was: #10b981 */
  --accent-warning: #FBBF24;   /* was: #f59e0b */
  --accent-danger: #F87171;    /* was: #ef4444 */
  --accent-info: #60A5FA;      /* was: #3b82f6 */
  --accent-cyan: #22D3EE;      /* was: #06b6d4 */

  /* NEW colors */
  --accent-orange: #FB923C;
  --accent-pink: #F472B6;

  /* Subtle backgrounds para tags */
  --success-subtle: rgba(74,222,128,0.10);
  --warning-subtle: rgba(251,191,36,0.10);
  --danger-subtle: rgba(248,113,113,0.10);
  --info-subtle: rgba(96,165,250,0.10);
  --cyan-subtle: rgba(34,211,238,0.08);
  --orange-subtle: rgba(251,146,60,0.10);
  --pink-subtle: rgba(244,114,182,0.10);

  /* Column Colors (Kanban) — mantém mapeamento */
  --col-backlog: #5C5C68;
  --col-plan: #60A5FA;
  --col-implement: #8B7BF5;
  --col-test: #FB923C;
  --col-review: #4ADE80;
  --col-done: #22D3EE;

  /* Radius — MAIOR que antes */
  --radius-sm: 8px;     /* was: 4px */
  --radius-md: 12px;    /* was: 8px */
  --radius-lg: 16px;    /* was: 12px */
  --radius-xl: 20px;    /* was: 16px */
  --radius-full: 100px; /* was: 9999px */

  /* Shadows — suaves, sem glow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.2), 0 1px 3px rgba(0,0,0,0.1);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.25), 0 1px 3px rgba(0,0,0,0.15);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.3), 0 2px 6px rgba(0,0,0,0.2);
  --shadow-card: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.06);

  /* REMOVER todas glow shadows */
  /* --shadow-glow, --shadow-glow-cyan, etc. → deletar */
}
```

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `src/styles/dashboard-theme.css` | Modificar | Substituir TODOS os tokens de design (cores, radius, shadows) |
| `src/styles/animations.css` | Modificar | Simplificar animações, remover glows |
| `src/layouts/WorkspaceLayout.tsx` | Modificar | Trocar Sidebar por TopNav, remover breadcrumb header |
| `src/layouts/WorkspaceLayout.module.css` | Modificar | Layout flex-column ao invés de flex-row |
| `src/components/Navigation/Sidebar.tsx` | Renomear/Reescrever | → `TopNav.tsx` — navegação horizontal |
| `src/components/Navigation/Sidebar.module.css` | Renomear/Reescrever | → `TopNav.module.css` |
| `src/pages/HomePage.tsx` | Modificar | Redesign do dashboard |
| `src/pages/HomePage.module.css` | Modificar | Novos estilos soft/rounded |
| `src/pages/KanbanPage.tsx` | Modificar | Ajustar layout de colunas |
| `src/pages/KanbanPage.module.css` | Modificar | Novos estilos de colunas e board |
| `src/pages/ChatPage.tsx` | Modificar | Redesign do chat |
| `src/pages/ChatPage.module.css` | Modificar | Novos estilos chat soft |
| `src/pages/SettingsPage.tsx` | Modificar | Redesign settings |
| `src/pages/SettingsPage.module.css` | Modificar | Novos estilos settings |
| `src/components/Card/Card.module.css` | Modificar | Cards com radius maior, sombras suaves |
| `src/components/Column/Column.module.css` | Modificar | Colunas com dot colorido ao invés de border |
| `src/components/Board/Board.module.css` | Modificar | Grid do board |
| `src/components/Dashboard/*.module.css` | Modificar | Todos os 7 componentes do dashboard |
| `src/components/Chat/*.module.css` | Modificar | Todos os 5 componentes de chat |
| `src/components/AddCardModal/AddCardModal.module.css` | Modificar | Modal com radius maior |
| `src/components/CardEditModal/CardEditModal.module.css` | Modificar | Modal com radius maior |
| `src/components/LogsModal/LogsModal.module.css` | Modificar | Modal com radius maior |
| `src/components/ExpertsModal/ExpertsModal.module.css` | Modificar | Modal com radius maior |
| `src/components/EmptyState/EmptyState.module.css` | Modificar | Empty states sem emoji |
| `src/components/ThemeToggle/ThemeToggle.module.css` | Modificar | Mover para TopNav |
| `src/components/Tooltip/Tooltip.module.css` | Modificar | Radius e sombras |
| `src/components/ExpertBadges/ExpertBadges.module.css` | Modificar | Tags pill-shaped |
| `src/App.module.css` | Modificar | Estilos globais base |

### Detalhes Técnicos por Fase

---

### FASE 1: Design Tokens e Base Global

**1.1 — `dashboard-theme.css`**
Substituir completamente com os novos tokens listados acima. Remover:
- Todas as variáveis `*-glow`
- Todas as variáveis `*-vibrant`
- `--glass-*` (glassmorphism)
- `.glass-panel` e `.text-gradient` classes

**1.2 — `animations.css`**
Simplificar — manter apenas:
- fadeIn, fadeOut
- slideUp, slideDown
- scaleIn
- Remover: spring, elastic, shake, glow animations
- Transições padrão: 180ms ease (ao invés de 150ms)

**1.3 — `App.module.css`**
- Atualizar scrollbar styling para tons mais suaves
- Remover qualquer referência a glassmorphism

---

### FASE 2: Layout — Sidebar → Top Nav

**2.1 — Criar `src/components/Navigation/TopNav.tsx`**

```tsx
import { ModuleType } from '../../layouts/WorkspaceLayout';
import styles from './TopNav.module.css';

interface TopNavProps {
  currentModule: ModuleType;
  onNavigate: (module: ModuleType) => void;
}

const navItems: { id: ModuleType; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'kanban', label: 'Workflow' },
  { id: 'chat', label: 'Chat' },
  { id: 'settings', label: 'Settings' },
];

const TopNav = ({ currentModule, onNavigate }: TopNavProps) => {
  return (
    <nav className={styles.topnav}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          {/* SVG bolt icon */}
        </div>
        <span className={styles.logoText}>Zenflow</span>
      </div>

      <div className={styles.navCenter}>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`${styles.navLink} ${currentModule === item.id ? styles.active : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className={styles.navRight}>
        {/* Search button, notifications, avatar */}
      </div>
    </nav>
  );
};

export default TopNav;
```

**2.2 — `TopNav.module.css`** (ver design-preview-soft.html para estilos completos)

Key styles:
- `height: 56px`, sticky top, `backdrop-filter: blur(16px)`
- Nav center: `background: var(--bg-secondary)`, `border-radius: 12px`, padding 4px
- Nav links: `border-radius: 9px`, `font-size: 13px`, font-weight 500
- Active state: `background: var(--bg-elevated)`, `box-shadow: var(--shadow-sm)`

**2.3 — Atualizar `WorkspaceLayout.tsx`**

```tsx
import TopNav from '../components/Navigation/TopNav';
import styles from './WorkspaceLayout.module.css';

const WorkspaceLayout = ({ children, currentModule, onNavigate }) => {
  return (
    <div className={styles.workspace}>
      <TopNav currentModule={currentModule} onNavigate={onNavigate} />
      <main className={styles.content}>
        {children}
      </main>
    </div>
  );
};
```

**2.4 — `WorkspaceLayout.module.css`**

```css
.workspace {
  display: flex;
  flex-direction: column;  /* era: row (por causa da sidebar) */
  min-height: 100vh;
  background: var(--bg-primary);
}

.content {
  flex: 1;
  padding: var(--space-5) var(--space-6);
  overflow-y: auto;
  overflow-x: hidden;
}
```

---

### FASE 3: Páginas

**3.1 — HomePage (Dashboard)**

Principais mudanças CSS:
- Metric cards: `border-radius: 16px`, `box-shadow: var(--shadow-card)`, gradient top border (3px)
- Ícones dentro de metric cards com fundo sutil
- Feed card e overview card: `border-radius: 16px`
- Overview bars: `border-radius: 100px` (pill), `height: 8px`
- Metric change badges: pill-shaped com fundo sutil
- Cards hover: `translateY(-2px)`, `box-shadow: var(--shadow-lg)`

**3.2 — KanbanPage**

Principais mudanças:
- Colunas sem border-top, usar **dot colorido** ao lado do título
- Cards: `border-radius: 12px`, `box-shadow: var(--shadow-card)`
- Tags: `border-radius: 100px` (pill-shaped)
- Empty state: `border: 2px dashed`, `border-radius: 12px`
- Board gap: `10px` entre colunas

**3.3 — ChatPage**

Principais mudanças:
- Container: `border-radius: 20px`
- Messages AI: `border-radius: 4px 16px 16px 16px`
- Messages User: `border-radius: 16px 4px 16px 16px`
- Avatars: gradient backgrounds (accent→pink para AI, info→cyan para user)
- Input: `border-radius: 12px`, focus com `box-shadow: 0 0 0 3px accent-soft`
- Send button: gradient background, `border-radius: 12px`

**3.4 — SettingsPage**

Principais mudanças:
- Section cards: `border-radius: 16px`
- Inputs: `border-radius: 8px`, bg-inset background
- Toggles e controles: rounded styling

---

### FASE 4: Componentes Compartilhados

**4.1 — Card.module.css**
- `border-radius: var(--radius-md)` (12px)
- `box-shadow: var(--shadow-card)`
- Hover: `translateY(-2px)`, `box-shadow: var(--shadow-lg)`
- Remover qualquer glow effect

**4.2 — Column.module.css**
- Header com dot colorido (10px circle) ao invés de border-left/top
- `col-title`: `font-size: 13px`, `font-weight: 600`, normal case (não uppercase)
- `col-count`: pill badge com `border-radius: 100px`

**4.3 — Modais (AddCardModal, CardEditModal, LogsModal, ExpertsModal)**
- Container: `border-radius: 20px`
- Overlay: semi-transparente
- Inputs: `border-radius: 8px`
- Buttons: `border-radius: 8px`

**4.4 — Tags/Badges (ExpertBadges, etc.)**
- Todos pill-shaped: `border-radius: 100px`
- Background sutil: `rgba(color, 0.10)`
- Font-size: 11px, font-weight: 500

**4.5 — EmptyState**
- Remover emojis, usar ícones SVG ou texto simples
- `border: 2px dashed var(--border)`, `border-radius: 12px`

**4.6 — Tooltip**
- `border-radius: 8px`
- `box-shadow: var(--shadow-md)`

---

### FASE 5: Limpeza

- Deletar `src/components/Navigation/Sidebar.tsx` e `Sidebar.module.css`
- Remover header breadcrumb do WorkspaceLayout
- Remover imports de Font Awesome icons não utilizados (a sidebar usava `fa-solid`)
- Usar SVGs inline (Lucide icons que já existe no projeto) ao invés de Font Awesome no TopNav

---

## 4. Testes

### Manuais (Visual)
- [ ] Dashboard renderiza corretamente com novos estilos
- [ ] Kanban drag-and-drop funciona normalmente
- [ ] Chat envia/recebe mensagens sem quebrar
- [ ] Settings salva configurações
- [ ] Top nav navega entre todas as páginas
- [ ] Modais abrem/fecham corretamente
- [ ] Responsividade em diferentes tamanhos de tela
- [ ] Hover states funcionam em todos os elementos interativos

### Funcionalidade (não deve quebrar)
- [ ] WebSocket conexão e reconexão
- [ ] Drag and drop entre colunas
- [ ] Execução de pipeline (plan → implement → test → review → done)
- [ ] Expert triage ao mover card
- [ ] Chat streaming
- [ ] Project switching

---

## 5. Considerações

- **Riscos:** A mudança de sidebar para top nav requer ajustar o WorkspaceLayout e garantir que o conteúdo ocupe toda a largura. O Kanban board se beneficia do espaço extra.
- **Abordagem:** Fazer por fases — primeiro tokens globais, depois layout, depois páginas individuais, depois componentes menores. Isso permite testar incrementalmente.
- **Backward compat:** Manter os nomes das CSS variables existentes quando possível (ex: `--bg-primary`, `--accent-primary`) para que componentes que ainda não foram atualizados continuem funcionando com as novas cores.
- **Font Awesome → Lucide:** A sidebar usa Font Awesome para ícones. O TopNav deve usar Lucide (já usado no resto do app) com SVG inline, eliminando dependência de FA para navegação.
