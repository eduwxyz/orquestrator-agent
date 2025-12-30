/**
 * API client for cards endpoints.
 */

import type { Card, CardImage, ColumnId, ModelType, ActiveExecution, ExecutionLog } from '../types';

const API_BASE = 'http://localhost:3001/api';

interface CardResponse {
  id: string;
  title: string;
  description: string | null;
  columnId: ColumnId;
  specPath: string | null;
  modelPlan: ModelType;
  modelImplement: ModelType;
  modelTest: ModelType;
  modelReview: ModelType;
  images?: CardImage[];
  createdAt: string;
  updatedAt: string;
  activeExecution?: ActiveExecution;
}

interface CardsListResponse {
  success: boolean;
  cards: CardResponse[];
}

interface CardSingleResponse {
  success: boolean;
  card: CardResponse;
}

function mapCardResponseToCard(response: CardResponse): Card {
  return {
    id: response.id,
    title: response.title,
    description: response.description || '',
    columnId: response.columnId,
    specPath: response.specPath || undefined,
    modelPlan: response.modelPlan,
    modelImplement: response.modelImplement,
    modelTest: response.modelTest,
    modelReview: response.modelReview,
    images: response.images,
    activeExecution: response.activeExecution,
  };
}

/**
 * Fetch all cards from the API.
 */
export async function fetchCards(): Promise<Card[]> {
  const url = `${API_BASE}/cards`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch cards: ${response.statusText}`);
  }

  const data: CardsListResponse = await response.json();
  return data.cards.map(mapCardResponseToCard);
}

/**
 * Create a new card (always in backlog).
 */
export async function createCard(
  title: string,
  description: string,
  modelPlan: ModelType,
  modelImplement: ModelType,
  modelTest: ModelType,
  modelReview: ModelType
): Promise<Card> {
  const response = await fetch(`${API_BASE}/cards`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title,
      description: description || null,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create card: ${response.statusText}`);
  }

  const data: CardSingleResponse = await response.json();
  return mapCardResponseToCard(data.card);
}

/**
 * Update an existing card.
 */
export async function updateCard(
  cardId: string,
  updates: Partial<Pick<Card, 'title' | 'description' | 'columnId' | 'specPath'>>
): Promise<Card> {
  const response = await fetch(`${API_BASE}/cards/${cardId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: updates.title,
      description: updates.description,
      columnId: updates.columnId,
      specPath: updates.specPath,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update card: ${response.statusText}`);
  }

  const data: CardSingleResponse = await response.json();
  return mapCardResponseToCard(data.card);
}

/**
 * Delete a card.
 */
export async function deleteCard(cardId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/cards/${cardId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete card: ${response.statusText}`);
  }
}

/**
 * Move a card to another column (with SDLC validation on backend).
 */
export async function moveCard(cardId: string, columnId: ColumnId): Promise<Card> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/move`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ columnId }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to move card: ${response.statusText}`);
  }

  const data: CardSingleResponse = await response.json();
  return mapCardResponseToCard(data.card);
}

/**
 * Update the spec path for a card.
 */
export async function updateSpecPath(cardId: string, specPath: string): Promise<Card> {
  const response = await fetch(`${API_BASE}/cards/${cardId}/spec-path?spec_path=${encodeURIComponent(specPath)}`, {
    method: 'PATCH',
  });

  if (!response.ok) {
    throw new Error(`Failed to update spec path: ${response.statusText}`);
  }

  const data: CardSingleResponse = await response.json();
  return mapCardResponseToCard(data.card);
}

interface LogsResponse {
  cardId: string;
  status: 'idle' | 'running' | 'success' | 'error';
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  result?: string;
  logs: ExecutionLog[];
}

/**
 * Fetch execution logs for a card.
 */
export async function fetchLogs(cardId: string): Promise<LogsResponse> {
  const response = await fetch(`${API_BASE}/logs/${cardId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch logs: ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}

