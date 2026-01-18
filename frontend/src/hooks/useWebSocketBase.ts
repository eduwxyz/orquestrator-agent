import { useEffect, useRef, useCallback, useState } from 'react';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketBaseOptions {
  /** URL do WebSocket */
  url: string;
  /** Habilitar conexão (default: true) */
  enabled?: boolean;
  /** Callback quando conectado */
  onOpen?: () => void;
  /** Callback quando desconectado */
  onClose?: () => void;
  /** Callback quando erro */
  onError?: (error: Event) => void;
  /** Callback quando recebe mensagem */
  onMessage?: (data: unknown) => void;
  /** Máximo de tentativas de reconexão (default: 10) */
  maxReconnectAttempts?: number;
  /** Delay base para reconexão em ms (default: 1000) */
  baseReconnectDelay?: number;
  /** Delay máximo para reconexão em ms (default: 30000) */
  maxReconnectDelay?: number;
  /** Intervalo de heartbeat em ms (default: 30000, 0 para desabilitar) */
  heartbeatInterval?: number;
  /** Timeout para pong em ms (default: 10000) */
  pongTimeout?: number;
  /** Nome para logs (default: 'WS') */
  name?: string;
}

interface UseWebSocketBaseReturn {
  status: WebSocketStatus;
  isConnected: boolean;
  send: (data: unknown) => boolean;
  reconnect: () => void;
  disconnect: () => void;
}

/**
 * Hook base para WebSocket com reconexão robusta
 *
 * Features:
 * - Exponential backoff com jitter
 * - Heartbeat automático (ping/pong)
 * - Fila de mensagens durante reconexão
 * - Estados claros: connecting | connected | disconnected | error
 */
export function useWebSocketBase(options: WebSocketBaseOptions): UseWebSocketBaseReturn {
  const {
    url,
    enabled = true,
    onOpen,
    onClose,
    onError,
    onMessage,
    maxReconnectAttempts = 10,
    baseReconnectDelay = 1000,
    maxReconnectDelay = 30000,
    heartbeatInterval = 30000,
    pongTimeout = 10000,
    name = 'WS',
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>('disconnected');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pongTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<unknown[]>([]);
  const isUnmountedRef = useRef(false);
  const lastPongRef = useRef<number>(Date.now());

  // Callbacks refs para evitar reconexões desnecessárias
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
    onMessageRef.current = onMessage;
  }, [onOpen, onClose, onError, onMessage]);

  // Calcular delay com exponential backoff + jitter
  const getReconnectDelay = useCallback(() => {
    const exponentialDelay = baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
    const cappedDelay = Math.min(exponentialDelay, maxReconnectDelay);
    // Adicionar jitter de ±25% para evitar thundering herd
    const jitter = cappedDelay * 0.25 * (Math.random() * 2 - 1);
    return Math.floor(cappedDelay + jitter);
  }, [baseReconnectDelay, maxReconnectDelay]);

  // Limpar timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }
  }, []);

  // Iniciar heartbeat
  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval <= 0) return;

    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        // Verificar se recebemos pong recentemente
        const timeSinceLastPong = Date.now() - lastPongRef.current;
        if (timeSinceLastPong > heartbeatInterval + pongTimeout) {
          console.warn(`[${name}] Pong timeout - connection may be stale, reconnecting...`);
          wsRef.current?.close();
          return;
        }

        // Enviar ping
        try {
          wsRef.current.send(JSON.stringify({ type: 'ping' }));

          // Timeout para pong
          pongTimeoutRef.current = setTimeout(() => {
            const elapsed = Date.now() - lastPongRef.current;
            if (elapsed > heartbeatInterval) {
              console.warn(`[${name}] No pong received, connection may be dead`);
            }
          }, pongTimeout);
        } catch {
          console.error(`[${name}] Failed to send ping`);
        }
      }
    }, heartbeatInterval);
  }, [heartbeatInterval, pongTimeout, name]);

  // Processar fila de mensagens
  const flushMessageQueue = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;

    while (messageQueueRef.current.length > 0) {
      const message = messageQueueRef.current.shift();
      try {
        wsRef.current.send(JSON.stringify(message));
        console.log(`[${name}] Flushed queued message`);
      } catch (error) {
        console.error(`[${name}] Failed to flush queued message:`, error);
        // Re-adicionar à fila se falhar
        messageQueueRef.current.unshift(message);
        break;
      }
    }
  }, [name]);

  // Conectar
  const connect = useCallback(() => {
    if (!enabled || isUnmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    clearTimers();
    setStatus('connecting');
    console.log(`[${name}] Connecting to ${url}...`);

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close();
          return;
        }

        setStatus('connected');
        reconnectAttemptsRef.current = 0;
        lastPongRef.current = Date.now();
        console.log(`[${name}] Connected successfully`);

        startHeartbeat();
        flushMessageQueue();
        onOpenRef.current?.();
      };

      ws.onclose = (event) => {
        if (isUnmountedRef.current) return;

        clearTimers();
        setStatus('disconnected');
        console.log(`[${name}] Disconnected (code: ${event.code}, reason: ${event.reason || 'none'})`);
        onCloseRef.current?.();

        // Reconectar se ainda habilitado e não excedeu tentativas
        if (enabled && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = getReconnectDelay();
          reconnectAttemptsRef.current++;
          console.log(`[${name}] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error(`[${name}] Max reconnect attempts reached`);
          setStatus('error');
        }
      };

      ws.onerror = (error) => {
        console.error(`[${name}] WebSocket error:`, error);
        onErrorRef.current?.(error);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Tratar pong
          if (data.type === 'pong') {
            lastPongRef.current = Date.now();
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current);
              pongTimeoutRef.current = null;
            }
            return;
          }

          onMessageRef.current?.(data);
        } catch {
          // Se não for JSON, passar como string
          onMessageRef.current?.(event.data);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error(`[${name}] Failed to create WebSocket:`, error);
      setStatus('error');
    }
  }, [url, enabled, maxReconnectAttempts, name, clearTimers, getReconnectDelay, startHeartbeat, flushMessageQueue]);

  // Desconectar
  const disconnect = useCallback(() => {
    clearTimers();
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevenir reconexão

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setStatus('disconnected');
    messageQueueRef.current = [];
  }, [clearTimers, maxReconnectAttempts]);

  // Reconectar manualmente
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(() => connect(), 100);
  }, [disconnect, connect]);

  // Enviar mensagem
  const send = useCallback((data: unknown): boolean => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(data));
        return true;
      } catch (error) {
        console.error(`[${name}] Failed to send message:`, error);
        messageQueueRef.current.push(data);
        return false;
      }
    } else {
      // Adicionar à fila se não conectado
      console.log(`[${name}] Queuing message (not connected)`);
      messageQueueRef.current.push(data);
      return false;
    }
  }, [name]);

  // Effect para conectar/desconectar
  useEffect(() => {
    isUnmountedRef.current = false;

    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      isUnmountedRef.current = true;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount');
        wsRef.current = null;
      }
    };
  }, [enabled, url]); // Reconectar se URL mudar

  return {
    status,
    isConnected: status === 'connected',
    send,
    reconnect,
    disconnect,
  };
}
