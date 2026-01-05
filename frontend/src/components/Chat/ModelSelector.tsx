import { useState, useRef, useEffect } from 'react';
import { AIModel, ModelSelectorProps } from './ModelSelector.types';
import { useClickOutside } from '../../hooks/useClickOutside';
import styles from './ModelSelector.module.css';

/**
 * Lista de modelos disponíveis com informações detalhadas
 */
export const AVAILABLE_MODELS: AIModel[] = [
  {
    id: 'opus-4.5',
    name: 'Opus 4.5',
    displayName: 'Opus 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Most powerful model for complex reasoning and advanced tasks',
    performance: 'powerful',
    icon: '🧠',
    accent: 'anthropic',
    badge: 'Most Capable'
  },
  {
    id: 'sonnet-4.5',
    name: 'Sonnet 4.5',
    displayName: 'Sonnet 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Balanced performance and speed for most tasks',
    performance: 'balanced',
    icon: '⚡',
    accent: 'anthropic',
    badge: 'Best Value'
  },
  {
    id: 'haiku-4.5',
    name: 'Haiku 4.5',
    displayName: 'Haiku 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Fast responses for simple tasks and quick interactions',
    performance: 'fastest',
    icon: '🚀',
    accent: 'anthropic'
  },
  {
    id: 'claude-3-sonnet',
    name: 'Claude 3 Sonnet',
    displayName: 'Sonnet (3.0)',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Previous generation balanced model',
    performance: 'balanced',
    icon: '💫',
    accent: 'anthropic'
  },
  {
    id: 'claude-3-opus',
    name: 'Claude 3 Opus',
    displayName: 'Opus (3.0)',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Previous generation powerful model',
    performance: 'powerful',
    icon: '🔮',
    accent: 'anthropic'
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    displayName: 'GPT-4 Turbo',
    provider: 'openai',
    maxTokens: 128000,
    description: 'OpenAI\'s most advanced and capable model',
    performance: 'powerful',
    icon: '🤖',
    accent: 'openai',
    badge: 'OpenAI'
  },
  // Modelos Gemini
  {
    id: 'gemini-1.5-pro',
    name: 'Gemini 1.5 Pro',
    displayName: 'Gemini Pro',
    provider: 'google',
    maxTokens: 1000000,
    description: 'Google\'s most capable multimodal model with long context',
    performance: 'powerful',
    icon: '🌟',
    accent: 'google',
    badge: 'Long Context'
  },
  {
    id: 'gemini-1.5-flash',
    name: 'Gemini 1.5 Flash',
    displayName: 'Gemini Flash',
    provider: 'google',
    maxTokens: 1000000,
    description: 'Fast and efficient model for quick tasks',
    performance: 'fastest',
    icon: '⚡',
    accent: 'google'
  },
  {
    id: 'gemini-1.0-pro',
    name: 'Gemini 1.0 Pro',
    displayName: 'Gemini 1.0',
    provider: 'google',
    maxTokens: 32000,
    description: 'Balanced model for general tasks',
    performance: 'balanced',
    icon: '💎',
    accent: 'google'
  }
];

/**
 * Retorna o ícone correspondente ao nível de performance
 */
function getPerformanceIcon(performance: AIModel['performance']): string {
  switch (performance) {
    case 'fastest':
      return '⚡';
    case 'balanced':
      return '⚖️';
    case 'powerful':
      return '💪';
  }
}

/**
 * Componente de seleção de modelo de IA com dropdown customizado
 */
export function ModelSelector({ selectedModel, onModelChange, disabled = false }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const currentModel = AVAILABLE_MODELS.find(m => m.id === selectedModel) || AVAILABLE_MODELS[0];

  // Fecha o dropdown quando clicar fora
  useClickOutside(dropdownRef, () => setIsOpen(false));

  // Suporte a teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
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
        aria-label="Select AI Model"
      >
        <div className={styles.triggerContent}>
          <span className={styles.label}>AI MODEL:</span>
          <div className={styles.selected}>
            <span className={styles.modelIcon}>{currentModel.icon}</span>
            <span className={styles.modelName}>{currentModel.displayName}</span>
            <span className={`${styles.providerBadge} ${styles[currentModel.accent]}`}>
              {currentModel.provider}
            </span>
          </div>
          <svg
            className={`${styles.chevron} ${isOpen ? styles.rotate : ''}`}
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M4 6L8 10L12 6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className={styles.dropdown} role="listbox">
          <div className={styles.dropdownHeader}>
            <h3>Select AI Model</h3>
            <p>Choose the best model for your task</p>
          </div>

          <div className={styles.modelList}>
            {AVAILABLE_MODELS.map(model => (
              <button
                key={model.id}
                className={`${styles.modelCard} ${model.id === selectedModel ? styles.selectedCard : ''}`}
                onClick={() => {
                  onModelChange(model.id);
                  setIsOpen(false);
                }}
                role="option"
                aria-selected={model.id === selectedModel}
              >
                <div className={styles.modelHeader}>
                  <span className={styles.modelCardIcon}>{model.icon}</span>
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
                    <span className={styles.performanceIcon}>{getPerformanceIcon(model.performance)}</span>
                    {model.performance}
                  </span>
                  <span className={styles.tokens}>
                    {(model.maxTokens / 1000).toFixed(0)}K
                  </span>
                </div>

                {model.id === selectedModel && (
                  <div className={styles.selectedIndicator}>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path
                        d="M13 4L6 11L3 8"
                        stroke="white"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
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
