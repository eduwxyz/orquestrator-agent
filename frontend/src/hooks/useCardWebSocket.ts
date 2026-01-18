import { useCallback, useMemo } from 'react';
import { Card, ColumnId } from '../types';
import { useWebSocketBase } from './useWebSocketBase';
import { WS_ENDPOINTS } from '../api/config';

export interface CardMovedMessage {
  type: 'card_moved';
  cardId: string;
  fromColumn: ColumnId;
  toColumn: ColumnId;
  card: Card;
  timestamp: string;
}

export interface CardUpdatedMessage {
  type: 'card_updated';
  cardId: string;
  card: Card;
  timestamp: string;
}

export interface CardCreatedMessage {
  type: 'card_created';
  cardId: string;
  card: Card;
  timestamp: string;
}

type WebSocketMessage = CardMovedMessage | CardUpdatedMessage | CardCreatedMessage;

interface UseCardWebSocketProps {
  onCardMoved?: (message: CardMovedMessage) => void;
  onCardUpdated?: (message: CardUpdatedMessage) => void;
  onCardCreated?: (message: CardCreatedMessage) => void;
  enabled?: boolean;
}

export function useCardWebSocket({
  onCardMoved,
  onCardUpdated,
  onCardCreated,
  enabled = true
}: UseCardWebSocketProps) {
  const handleMessage = useCallback((data: unknown) => {
    const message = data as WebSocketMessage;

    switch (message.type) {
      case 'card_moved':
        console.log(`[CardWS] Card ${message.cardId} moved from ${message.fromColumn} to ${message.toColumn}`);
        onCardMoved?.(message);
        break;
      case 'card_updated':
        console.log(`[CardWS] Card ${message.cardId} updated`);
        onCardUpdated?.(message);
        break;
      case 'card_created':
        console.log(`[CardWS] Card ${message.cardId} created`);
        onCardCreated?.(message);
        break;
    }
  }, [onCardMoved, onCardUpdated, onCardCreated]);

  const { isConnected, status, reconnect } = useWebSocketBase({
    url: WS_ENDPOINTS.cards,
    enabled,
    onMessage: handleMessage,
    name: 'CardWS',
    maxReconnectAttempts: 10,
    heartbeatInterval: 30000,
  });

  return useMemo(() => ({
    isConnected,
    status,
    reconnect,
  }), [isConnected, status, reconnect]);
}
