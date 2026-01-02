import { CardDraft } from '../types';

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
      if (error instanceof Error && error.name === 'QuotaExceededError') {
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
