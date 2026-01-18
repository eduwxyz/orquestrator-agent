import { useState, useRef, useCallback, useEffect } from 'react';
import { ChatState, Message } from '../types/chat';
import { v4 as uuidv4 } from 'uuid';
import { useWebSocketBase } from './useWebSocketBase';
import { WS_ENDPOINTS } from '../api/config';

interface ChatWebSocketMessage {
  type: 'chunk' | 'end' | 'error';
  content?: string;
  messageId?: string;
  message?: string;
}

export function useChat() {
  const [state, setState] = useState<ChatState>({
    isOpen: false,
    session: null,
    isLoading: false,
    error: null,
    selectedModel: 'sonnet-4.5',
    unreadCount: 0,
  });

  const sessionId = useRef<string>(uuidv4());
  const currentMessageId = useRef<string | null>(null);
  const pendingMessage = useRef<string | null>(null);

  // Initialize session
  useEffect(() => {
    setState((prev) => ({
      ...prev,
      session: {
        id: sessionId.current,
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    }));
  }, []);

  // Keyboard shortcut (Cmd+K or Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleChat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleMessage = useCallback((data: unknown) => {
    const chatData = data as ChatWebSocketMessage;

    if (chatData.type === 'chunk') {
      // Update streaming message
      setState((prev) => {
        if (!prev.session) return prev;

        const messages = [...prev.session.messages];
        const lastMessage = messages[messages.length - 1];

        if (lastMessage && lastMessage.id === currentMessageId.current) {
          lastMessage.content += chatData.content || '';
          lastMessage.isStreaming = true;
        } else {
          // Start new assistant message
          const newMessage: Message = {
            id: chatData.messageId || uuidv4(),
            role: 'assistant',
            content: chatData.content || '',
            timestamp: new Date().toISOString(),
            isStreaming: true,
          };
          currentMessageId.current = newMessage.id;
          messages.push(newMessage);
        }

        return {
          ...prev,
          session: {
            ...prev.session,
            messages,
            updatedAt: new Date().toISOString(),
          },
        };
      });
    } else if (chatData.type === 'end') {
      // Mark streaming as complete
      setState((prev) => {
        if (!prev.session) return prev;

        const messages = prev.session.messages.map((msg) =>
          msg.id === currentMessageId.current
            ? { ...msg, isStreaming: false }
            : msg
        );

        currentMessageId.current = null;

        return {
          ...prev,
          session: {
            ...prev.session,
            messages,
            updatedAt: new Date().toISOString(),
          },
          isLoading: false,
        };
      });
    } else if (chatData.type === 'error') {
      setState((prev) => ({
        ...prev,
        error: chatData.message || 'An error occurred',
        isLoading: false,
      }));
      currentMessageId.current = null;
    }
  }, []);

  const handleOpen = useCallback(() => {
    console.log('[ChatWS] Connected');
    setState((prev) => ({ ...prev, error: null }));

    // Clear pending message flag on connect
    pendingMessage.current = null;
  }, []);

  const handleClose = useCallback(() => {
    console.log('[ChatWS] Disconnected');
  }, []);

  const handleError = useCallback(() => {
    setState((prev) => ({
      ...prev,
      error: 'Connection error. Please try again.',
      isLoading: false,
    }));
  }, []);

  const { isConnected, send, reconnect } = useWebSocketBase({
    url: WS_ENDPOINTS.chat(sessionId.current),
    enabled: state.isOpen, // Only connect when chat is open
    onMessage: handleMessage,
    onOpen: handleOpen,
    onClose: handleClose,
    onError: handleError,
    name: 'ChatWS',
    maxReconnectAttempts: 10,
    heartbeatInterval: 30000,
  });

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || state.isLoading) return;

      // Add user message
      const userMessage: Message = {
        id: uuidv4(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString(),
      };

      setState((prev) => {
        if (!prev.session) return prev;

        return {
          ...prev,
          session: {
            ...prev.session,
            messages: [...prev.session.messages, userMessage],
            updatedAt: new Date().toISOString(),
          },
          isLoading: true,
          error: null,
        };
      });

      // Send message (useWebSocketBase handles queuing if not connected)
      const sent = send({
        type: 'message',
        content: content.trim(),
        model: state.selectedModel,
      });

      if (!sent) {
        // Message was queued, it will be sent when connected
        console.log('[ChatWS] Message queued for sending');
      }
    },
    [state.isLoading, state.selectedModel, send]
  );

  const toggleChat = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isOpen: !prev.isOpen,
    }));
  }, []);

  const closeChat = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isOpen: false,
    }));
  }, []);

  const handleModelChange = useCallback((model: string) => {
    // Reset session when model changes
    const newSessionId = uuidv4();
    sessionId.current = newSessionId;

    setState((prev) => ({
      ...prev,
      selectedModel: model,
      session: {
        id: newSessionId,
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        model,
      },
    }));

    currentMessageId.current = null;
  }, []);

  const createNewSession = useCallback(() => {
    // Create new session ID
    const newSessionId = uuidv4();
    sessionId.current = newSessionId;

    // Reset session state
    setState((prev) => ({
      ...prev,
      session: {
        id: newSessionId,
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        model: prev.selectedModel,
      },
      isLoading: false,
      error: null,
    }));

    currentMessageId.current = null;

    // Reconnect with new session ID
    reconnect();
  }, [reconnect]);

  return {
    state,
    sendMessage,
    toggleChat,
    closeChat,
    handleModelChange,
    createNewSession,
    isConnected,
  };
}
