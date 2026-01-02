import { useCallback, useEffect, useRef, useState } from 'react';
import { CardDraft } from '../types';
import { DraftStorage } from '../utils/draftStorage';

// Função debounce inline
function debounce<TArgs extends unknown[]>(
  func: (...args: TArgs) => void,
  wait: number
): (...args: TArgs) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function executedFunction(...args: TArgs) {
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

interface UseDraftOptions {
  onRestore?: (draft: CardDraft) => void;
  autoSaveDelay?: number;
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
  const initialCheckDone = useRef(false);

  // Check for existing draft on mount
  useEffect(() => {
    if (!enabled || initialCheckDone.current) return;

    const draft = DraftStorage.load();
    if (draft) {
      setHasDraft(true);
      setShowDraftNotification(true);
    }
    initialCheckDone.current = true;
  }, [enabled]);

  // Reset initial check when modal closes
  useEffect(() => {
    if (!enabled) {
      initialCheckDone.current = false;
    }
  }, [enabled]);

  // Debounced save function
  const debouncedSave = useRef(
    debounce((data: Partial<CardDraft>) => {
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
        setHasDraft(true);
        setIsDraftDirty(false);
      }
    }, autoSaveDelay)
  ).current;

  const saveDraft = useCallback((data: Partial<CardDraft>) => {
    if (!enabled) return;
    setIsDraftDirty(true);
    debouncedSave(data);
  }, [enabled, debouncedSave]);

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

  return {
    hasDraft,
    isDraftDirty,
    showDraftNotification,
    saveDraft,
    restoreDraft,
    discardDraft,
    clearDraft,
    setShowDraftNotification
  };
}
