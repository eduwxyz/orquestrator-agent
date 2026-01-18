import { useCallback, useMemo } from 'react';
import { useWebSocketBase } from './useWebSocketBase';
import { WS_ENDPOINTS } from '../api/config';

interface ExecutionCompleteMessage {
  type: 'execution_complete';
  cardId: string;
  status: 'success' | 'error';
  command: string;
  tokenStats?: { inputTokens: number; outputTokens: number; totalTokens: number };
  costStats?: { totalCost: number; planCost: number; implementCost: number; testCost: number; reviewCost: number };
  error?: string;
  timestamp: string;
}

interface LogMessage {
  type: 'log';
  cardId: string;
  logType: string;
  content: string;
  timestamp: string;
}

type WebSocketMessage = ExecutionCompleteMessage | LogMessage;

export function useExecutionWebSocket(
  cardId: string | null,
  onComplete?: (msg: ExecutionCompleteMessage) => void,
  onLog?: (msg: LogMessage) => void
) {
  const handleMessage = useCallback((data: unknown) => {
    const msg = data as WebSocketMessage;

    if (msg.type === 'execution_complete' && onComplete) {
      onComplete(msg as ExecutionCompleteMessage);
    } else if (msg.type === 'log' && onLog) {
      onLog(msg as LogMessage);
    }
  }, [onComplete, onLog]);

  const { isConnected, status, reconnect } = useWebSocketBase({
    url: cardId ? WS_ENDPOINTS.execution(cardId) : '',
    enabled: !!cardId,
    onMessage: handleMessage,
    name: `ExecWS:${cardId?.slice(0, 8) || 'none'}`,
    maxReconnectAttempts: 10,
    heartbeatInterval: 30000,
  });

  return useMemo(() => ({
    isConnected,
    status,
    reconnect,
  }), [isConnected, status, reconnect]);
}
