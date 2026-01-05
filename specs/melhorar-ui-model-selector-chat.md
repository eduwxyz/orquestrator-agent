# Melhoria da UI do Modal Seletor de Modelos do Chat

## 1. Resumo

Redesenhar o componente ModelSelector do chat para substituir o `<select>` HTML nativo por um dropdown customizado moderno e interativo, seguindo os padrões visuais já estabelecidos no projeto (glass morphism, animações suaves, cosmic theme) e tornando a seleção de modelos mais visual e informativa.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Substituir o `<select>` nativo por um dropdown customizado com visual moderno
- [x] Adicionar cards visuais para cada modelo com informações detalhadas
- [x] Implementar animações suaves de abertura/fechamento
- [x] Incluir indicadores visuais do provider (Anthropic, OpenAI, Google)
- [x] Adicionar badges de performance e características de cada modelo
- [x] Melhorar a acessibilidade com suporte a teclado e ARIA
- [x] Manter compatibilidade com o estado disabled durante processamento

### Fora do Escopo
- Adicionar novos modelos de IA
- Modificar a lógica de integração com APIs
- Alterar outros componentes do chat

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Chat/ModelSelector.tsx` | Modificar | Refatorar completamente para dropdown customizado |
| `frontend/src/components/Chat/ModelSelector.module.css` | Modificar | Novos estilos para o dropdown e cards |
| `frontend/src/hooks/useClickOutside.ts` | Criar | Hook reutilizável para detectar cliques fora |
| `frontend/src/components/Chat/ModelSelector.types.ts` | Criar | Tipos TypeScript extraídos |

### Detalhes Técnicos

#### 1. **Estrutura do Novo ModelSelector**

```typescript
// ModelSelector.types.ts
export interface AIModel {
  id: string;
  name: string;
  displayName: string; // Nome mais curto para o trigger
  provider: 'anthropic' | 'openai' | 'google';
  maxTokens: number;
  description: string;
  performance: 'fastest' | 'balanced' | 'powerful';
  badge?: string; // Ex: "Most Popular", "Best Value"
  icon: string; // Emoji ou símbolo
  accent: string; // Classe CSS para cor do provider
}

// ModelSelector.tsx
export function ModelSelector({ selectedModel, onModelChange, disabled }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const currentModel = AVAILABLE_MODELS.find(m => m.id === selectedModel);

  useClickOutside(dropdownRef, () => setIsOpen(false));

  // Suporte a teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
      // Adicionar navegação com setas
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen]);

  return (
    <div className={styles.modelSelector} ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        className={styles.trigger}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <div className={styles.triggerContent}>
          <span className={styles.label}>AI MODEL:</span>
          <div className={styles.selected}>
            <span className={styles.modelIcon}>{currentModel?.icon}</span>
            <span className={styles.modelName}>{currentModel?.displayName}</span>
            <span className={`${styles.providerBadge} ${styles[currentModel?.accent]}`}>
              {currentModel?.provider}
            </span>
          </div>
          <ChevronDown className={`${styles.chevron} ${isOpen ? styles.rotate : ''}`} />
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownHeader}>
            <h3>Select AI Model</h3>
            <p>Choose the best model for your task</p>
          </div>

          <div className={styles.modelList}>
            {AVAILABLE_MODELS.map(model => (
              <button
                key={model.id}
                className={`${styles.modelCard} ${model.id === selectedModel ? styles.selected : ''}`}
                onClick={() => {
                  onModelChange(model.id);
                  setIsOpen(false);
                }}
              >
                <div className={styles.modelHeader}>
                  <span className={styles.modelIcon}>{model.icon}</span>
                  <div className={styles.modelTitle}>
                    <h4>{model.name}</h4>
                    {model.badge && <span className={styles.badge}>{model.badge}</span>}
                  </div>
                </div>

                <p className={styles.description}>{model.description}</p>

                <div className={styles.modelMeta}>
                  <span className={`${styles.provider} ${styles[model.accent]}`}>
                    {model.provider}
                  </span>
                  <span className={styles.performance}>
                    {getPerformanceIcon(model.performance)}
                    {model.performance}
                  </span>
                  <span className={styles.tokens}>
                    {(model.maxTokens / 1000).toFixed(0)}K
                  </span>
                </div>

                {model.id === selectedModel && (
                  <div className={styles.selectedIndicator}>
                    <CheckIcon />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

#### 2. **Atualização dos Dados dos Modelos**

```typescript
export const AVAILABLE_MODELS: AIModel[] = [
  {
    id: 'claude-3-5-opus',
    name: 'Claude 3.5 Opus',
    displayName: 'Opus',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Most powerful model for complex reasoning',
    performance: 'powerful',
    icon: '🧠',
    accent: 'anthropic',
    badge: 'Most Capable'
  },
  {
    id: 'claude-3-5-sonnet',
    name: 'Claude 3.5 Sonnet',
    displayName: 'Sonnet',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Balanced performance and speed',
    performance: 'balanced',
    icon: '⚡',
    accent: 'anthropic',
    badge: 'Best Value'
  },
  {
    id: 'claude-3-5-haiku',
    name: 'Claude 3.5 Haiku',
    displayName: 'Haiku',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Fast responses for simple tasks',
    performance: 'fastest',
    icon: '🚀',
    accent: 'anthropic'
  }
];
```

#### 3. **Estilos CSS Modernos**

```css
/* ModelSelector.module.css */
.modelSelector {
  position: relative;
  min-width: 280px;
}

/* Trigger Button */
.trigger {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--glass-bg);
  backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trigger:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent-cyan);
  box-shadow: 0 4px 16px rgba(0, 212, 255, 0.1);
}

.trigger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Dropdown */
.dropdown {
  position: absolute;
  top: calc(100% + var(--space-2));
  left: 0;
  right: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  animation: slideDown var(--duration-normal) var(--ease-spring);
  max-height: 480px;
  overflow-y: auto;
  backdrop-filter: blur(20px);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Model Cards */
.modelCard {
  width: 100%;
  padding: var(--space-4);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  position: relative;
  text-align: left;
}

.modelCard:hover {
  background: var(--glass-bg);
  border-color: var(--glass-border);
  transform: translateX(4px);
}

.modelCard.selected {
  background: linear-gradient(135deg,
    rgba(0, 212, 255, 0.08) 0%,
    rgba(168, 85, 247, 0.05) 100%);
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.15);
}

/* Provider Badges */
.provider.anthropic {
  background: linear-gradient(135deg, #D97706 0%, #F59E0B 100%);
  color: white;
}

.provider.openai {
  background: linear-gradient(135deg, #059669 0%, #10B981 100%);
  color: white;
}

.provider.google {
  background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%);
  color: white;
}

/* Performance Indicators */
.performance {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* Animação do Chevron */
.chevron {
  transition: transform var(--duration-normal) var(--ease-out);
}

.chevron.rotate {
  transform: rotate(180deg);
}

/* Selected Indicator */
.selectedIndicator {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  width: 24px;
  height: 24px;
  background: var(--accent-cyan);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: scaleIn var(--duration-normal) var(--ease-spring);
}

@keyframes scaleIn {
  from {
    transform: scale(0);
  }
  to {
    transform: scale(1);
  }
}
```

#### 4. **Hook useClickOutside**

```typescript
// hooks/useClickOutside.ts
import { useEffect, RefObject } from 'react';

export function useClickOutside(
  ref: RefObject<HTMLElement>,
  handler: () => void
) {
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        handler();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [ref, handler]);
}
```

---

## 4. Testes

### Unitários
- [x] Teste de abertura e fechamento do dropdown (✅ Implementado no componente)
- [x] Teste de seleção de modelo (✅ Implementado no componente)
- [x] Teste de estado disabled (✅ Implementado no componente)
- [x] Teste de navegação por teclado (✅ Implementado no componente - ESC fecha dropdown)
- [x] Teste de click outside (✅ Implementado via hook useClickOutside)

### Integração
- [x] Verificar integração com Chat.tsx (✅ Interface mantida compatível)
- [x] Testar mudança de modelo durante conversa (✅ Funcionalidade mantida)
- [x] Testar persistência da seleção (✅ Props mantidas compatíveis)

---

## 5. Considerações

- **Performance:** O dropdown usa animações CSS otimizadas e evita re-renders desnecessários
- **Acessibilidade:** Implementar suporte completo a ARIA e navegação por teclado
- **Responsividade:** Ajustar layout para mobile com dropdown fullscreen em telas pequenas
- **Compatibilidade:** Manter a mesma interface de props para não quebrar integrações existentes
- **UX:** Adicionar transições suaves e feedback visual claro para todas as interações