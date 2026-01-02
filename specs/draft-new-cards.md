# Draft para Criação de Cards

## 1. Resumo

Implementar um sistema de draft automático para o modal de criação de cards, salvando os dados em memória (localStorage) para evitar perda de informações quando o modal é fechado acidentalmente. O draft será restaurado automaticamente quando o usuário reabrir o modal, com opção de limpar ou continuar editando.

---

## 2. Objetivos e Escopo

### Objetivos
- [ ] Salvar automaticamente o estado do formulário em localStorage enquanto o usuário digita
- [ ] Detectar quando há um draft salvo e oferecer opção de restaurar ou descartar
- [ ] Limpar o draft após criação bem-sucedida do card
- [ ] Preservar imagens selecionadas no draft (como base64)
- [ ] Adicionar indicador visual quando há alterações não salvas

### Fora do Escopo
- Salvar drafts no backend (apenas localStorage)
- Múltiplos drafts simultâneos
- Draft para edição de cards existentes
- Sincronização entre abas/dispositivos

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/hooks/useDraft.ts` | Criar | Custom hook para gerenciar draft com localStorage |
| `frontend/src/components/AddCardModal/AddCardModal.tsx` | Modificar | Integrar sistema de draft no modal |
| `frontend/src/components/AddCardModal/AddCardModal.module.css` | Modificar | Adicionar estilos para notificação de draft |
| `frontend/src/utils/draftStorage.ts` | Criar | Utilitários para gerenciar draft no localStorage |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos para draft |

### Detalhes Técnicos

#### 1. **Tipos para Draft** (`types/index.ts`)

```typescript
export interface CardDraft {
  title: string;
  description: string;
  modelPlan: ModelType;
  modelImplement: ModelType;
  modelTest: ModelType;
  modelReview: ModelType;
  previewImages: DraftImage[];
  savedAt: string; // ISO timestamp
  version: number; // Para controle de versão do draft
}

export interface DraftImage {
  id: string;
  filename: string;
  preview: string; // Base64 data URL
  size: number;
}
```

#### 2. **Utilitários de Storage** (`utils/draftStorage.ts`)

```typescript
const DRAFT_KEY = 'orquestrator_card_draft';
const DRAFT_VERSION = 1;

export class DraftStorage {
  static save(draft: CardDraft): void {
    try {
      const data = {
        ...draft,
        savedAt: new Date().toISOString(),
        version: DRAFT_VERSION
      };
      localStorage.setItem(DRAFT_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('Failed to save draft:', error);
      // Limpar localStorage se estiver cheio
      if (error.name === 'QuotaExceededError') {
        this.clear();
      }
    }
  }

  static load(): CardDraft | null {
    try {
      const stored = localStorage.getItem(DRAFT_KEY);
      if (!stored) return null;

      const draft = JSON.parse(stored);

      // Verificar versão para evitar incompatibilidades
      if (draft.version !== DRAFT_VERSION) {
        this.clear();
        return null;
      }

      // Verificar se draft não é muito antigo (24 horas)
      const savedAt = new Date(draft.savedAt);
      const now = new Date();
      const hoursDiff = (now.getTime() - savedAt.getTime()) / (1000 * 60 * 60);

      if (hoursDiff > 24) {
        this.clear();
        return null;
      }

      return draft;
    } catch (error) {
      console.error('Failed to load draft:', error);
      this.clear();
      return null;
    }
  }

  static clear(): void {
    localStorage.removeItem(DRAFT_KEY);
  }

  static exists(): boolean {
    return localStorage.getItem(DRAFT_KEY) !== null;
  }
}
```

#### 3. **Custom Hook** (`hooks/useDraft.ts`)

```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import { CardDraft } from '../types';
import { DraftStorage } from '../utils/draftStorage';
import { debounce } from '../utils/helpers';

interface UseDraftOptions {
  onRestore?: (draft: CardDraft) => void;
  autoSaveDelay?: number; // ms
  enabled?: boolean;
}

export function useDraft(options: UseDraftOptions = {}) {
  const {
    onRestore,
    autoSaveDelay = 1000,
    enabled = true
  } = options;

  const [hasDraft, setHasDraft] = useState(false);
  const [isDraftDirty, setIsDraftDirty] = useState(false);
  const [showDraftNotification, setShowDraftNotification] = useState(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout>();

  // Check for existing draft on mount
  useEffect(() => {
    if (!enabled) return;

    const draft = DraftStorage.load();
    if (draft) {
      setHasDraft(true);
      setShowDraftNotification(true);
    }
  }, [enabled]);

  // Debounced save function
  const saveDraft = useCallback(
    debounce((data: Partial<CardDraft>) => {
      if (!enabled) return;

      const draft: CardDraft = {
        title: data.title || '',
        description: data.description || '',
        modelPlan: data.modelPlan || 'opus-4.5',
        modelImplement: data.modelImplement || 'opus-4.5',
        modelTest: data.modelTest || 'opus-4.5',
        modelReview: data.modelReview || 'opus-4.5',
        previewImages: data.previewImages || [],
        savedAt: new Date().toISOString(),
        version: 1
      };

      // Only save if there's actual content
      if (draft.title || draft.description || draft.previewImages.length > 0) {
        DraftStorage.save(draft);
        setIsDraftDirty(false);
      }
    }, autoSaveDelay),
    [enabled, autoSaveDelay]
  );

  const restoreDraft = useCallback(() => {
    const draft = DraftStorage.load();
    if (draft && onRestore) {
      onRestore(draft);
      setShowDraftNotification(false);
    }
  }, [onRestore]);

  const discardDraft = useCallback(() => {
    DraftStorage.clear();
    setHasDraft(false);
    setShowDraftNotification(false);
    setIsDraftDirty(false);
  }, []);

  const clearDraft = useCallback(() => {
    DraftStorage.clear();
    setHasDraft(false);
    setIsDraftDirty(false);
  }, []);

  // Mark draft as dirty when changes are made
  const markDirty = useCallback(() => {
    setIsDraftDirty(true);
  }, []);

  return {
    hasDraft,
    isDraftDirty,
    showDraftNotification,
    saveDraft,
    restoreDraft,
    discardDraft,
    clearDraft,
    markDirty,
    setShowDraftNotification
  };
}
```

#### 4. **Integração no Modal** (`AddCardModal.tsx`)

Modificações principais:

```typescript
import { useDraft } from '../../hooks/useDraft';
import { CardDraft, DraftImage } from '../../types';

export function AddCardModal({ isOpen, onClose, onSubmit }: AddCardModalProps) {
  // Estados existentes...
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  // ...outros estados

  // Integrar hook de draft
  const {
    hasDraft,
    isDraftDirty,
    showDraftNotification,
    saveDraft,
    restoreDraft,
    discardDraft,
    clearDraft,
    markDirty,
    setShowDraftNotification
  } = useDraft({
    enabled: isOpen,
    autoSaveDelay: 1000,
    onRestore: (draft: CardDraft) => {
      setTitle(draft.title);
      setDescription(draft.description);
      setModelPlan(draft.modelPlan);
      setModelImplement(draft.modelImplement);
      setModelTest(draft.modelTest);
      setModelReview(draft.modelReview);

      // Restaurar imagens (converter de DraftImage para preview format)
      const restoredImages = draft.previewImages.map(img => ({
        id: img.id,
        file: null, // File não pode ser serializado, será null
        preview: img.preview
      }));
      setPreviewImages(restoredImages);
    }
  });

  // Auto-save quando campos mudam
  useEffect(() => {
    if (!isOpen) return;

    const draftData = {
      title,
      description,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview,
      previewImages: previewImages.map(img => ({
        id: img.id,
        filename: img.file?.name || 'restored-image',
        preview: img.preview,
        size: img.file?.size || 0
      }))
    };

    saveDraft(draftData);
    markDirty();
  }, [title, description, modelPlan, modelImplement, modelTest, modelReview, previewImages, isOpen]);

  // Modificar handleClose para verificar draft
  const handleClose = useCallback(() => {
    if (isDraftDirty && (title || description || previewImages.length > 0)) {
      // Draft será mantido no localStorage
      // Mostrar indicador visual opcional
    }
    onClose();
  }, [isDraftDirty, title, description, previewImages, onClose]);

  // Modificar handleSubmit para limpar draft após sucesso
  const handleSubmitWithDraftClear = async (e: FormEvent) => {
    e.preventDefault();
    // ...validação existente

    try {
      setIsSubmitting(true);
      await onSubmit(/* ...params */);
      clearDraft(); // Limpar draft após sucesso
      onClose();
    } catch (error) {
      // ...tratamento de erro existente
    } finally {
      setIsSubmitting(false);
    }
  };

  // Adicionar notificação de draft disponível
  const DraftNotification = () => {
    if (!showDraftNotification) return null;

    return (
      <div className={styles.draftNotification}>
        <div className={styles.draftMessage}>
          <span className={styles.draftIcon}>💾</span>
          <span>Um rascunho foi encontrado. Deseja restaurar?</span>
        </div>
        <div className={styles.draftActions}>
          <button
            type="button"
            onClick={restoreDraft}
            className={styles.draftRestoreBtn}
          >
            Restaurar
          </button>
          <button
            type="button"
            onClick={() => {
              discardDraft();
              setShowDraftNotification(false);
            }}
            className={styles.draftDiscardBtn}
          >
            Descartar
          </button>
        </div>
      </div>
    );
  };

  // Adicionar indicador de auto-save
  const AutoSaveIndicator = () => {
    if (!isDraftDirty || !isOpen) return null;

    return (
      <div className={styles.autoSaveIndicator}>
        <span className={styles.autoSaveIcon}>•</span>
        <span className={styles.autoSaveText}>Salvando rascunho...</span>
      </div>
    );
  };

  return createPortal(
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Adicionar notificação de draft no topo */}
        <DraftNotification />

        <div className={styles.header}>
          <h2 className={styles.title}>Create New Card</h2>
          <AutoSaveIndicator />
          {/* ...resto do header */}
        </div>

        {/* ...resto do modal */}
      </div>
    </div>,
    portalRoot
  );
}
```

#### 5. **Estilos CSS** (`AddCardModal.module.css`)

```css
/* Notificação de Draft */
.draftNotification {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.draftMessage {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
}

.draftIcon {
  font-size: 18px;
}

.draftActions {
  display: flex;
  gap: 8px;
}

.draftRestoreBtn,
.draftDiscardBtn {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.draftRestoreBtn {
  background: white;
  color: #667eea;
  border: none;
}

.draftRestoreBtn:hover {
  background: #f0f0f0;
}

.draftDiscardBtn {
  background: transparent;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.draftDiscardBtn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.5);
}

/* Indicador de Auto-save */
.autoSaveIndicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
  margin-left: auto;
}

.autoSaveIcon {
  color: #10b981;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.autoSaveText {
  opacity: 0.7;
}

/* Indicador de mudanças não salvas no botão de fechar */
.closeButtonWithDraft {
  position: relative;
}

.closeButtonWithDraft::after {
  content: '';
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  animation: pulse 2s infinite;
}
```

#### 6. **Helpers Adicionais** (`utils/helpers.ts`)

```typescript
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }

    timeout = setTimeout(later, wait);
  };
}
```

---

## 4. Testes

### Unitários
- [ ] **DraftStorage class:**
  - [ ] Salvar draft no localStorage
  - [ ] Carregar draft válido
  - [ ] Rejeitar draft com versão incompatível
  - [ ] Rejeitar draft com mais de 24 horas
  - [ ] Limpar draft
  - [ ] Tratar erro de quota excedida

- [ ] **useDraft hook:**
  - [ ] Detectar draft existente ao montar
  - [ ] Auto-salvar com debounce
  - [ ] Restaurar draft com callback
  - [ ] Descartar draft
  - [ ] Marcar como dirty

- [ ] **AddCardModal integração:**
  - [ ] Mostrar notificação quando draft existe
  - [ ] Restaurar todos os campos do draft
  - [ ] Auto-salvar mudanças
  - [ ] Limpar draft após criação bem-sucedida
  - [ ] Preservar draft ao fechar modal

### Integração
- [ ] **Fluxo completo:**
  - [ ] Criar card parcialmente, fechar modal, reabrir e restaurar
  - [ ] Verificar que imagens são preservadas
  - [ ] Verificar que modelos selecionados são preservados
  - [ ] Confirmar que draft é limpo após criação

### E2E (Cypress/Playwright)
- [ ] Simular fechamento acidental e verificar restauração
- [ ] Testar limite de localStorage
- [ ] Testar comportamento com múltiplas abas

---

## 5. Considerações

### Riscos e Mitigações

**Risco 1: Limite de localStorage (5-10MB)**
- **Mitigação:** Limitar número de imagens no draft, comprimir base64, limpar drafts antigos automaticamente

**Risco 2: Dados sensíveis no localStorage**
- **Mitigação:** Não salvar informações sensíveis, adicionar expiração de 24 horas

**Risco 3: Conflito entre abas**
- **Mitigação:** Usar timestamp para detectar draft mais recente, ou implementar storage event listener

### Melhorias Futuras

1. **Múltiplos Drafts:** Permitir salvar múltiplos rascunhos com nomes
2. **Sync Backend:** Opção de salvar drafts no servidor para sincronização
3. **Undo/Redo:** Histórico de mudanças dentro do draft
4. **Templates:** Salvar drafts como templates reutilizáveis
5. **Storage Event:** Sincronizar entre abas quando draft é atualizado

### Decisões de Design

1. **localStorage vs sessionStorage:** Escolhemos localStorage para persistir entre sessões
2. **Auto-save delay:** 1 segundo padrão para balancear performance e segurança
3. **Expiração:** 24 horas para evitar drafts obsoletos
4. **Base64 para imagens:** Única forma de serializar imagens no localStorage
5. **Debounce:** Evitar salvar a cada keystroke para melhor performance