import { useState, useRef, useCallback, useEffect } from 'react';
import { ChatState, Message } from '../types/chat';
import { v4 as uuidv4 } from 'uuid';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:3001';

export function useChat() {
  const [state, setState] = useState<ChatState>({
    isOpen: false,
    session: null,
    isLoading: false,
    error: null,
    selectedModel: 'sonnet-4.5',
    unreadCount: 0,
  });

  const ws = useRef<WebSocket | null>(null);
  const sessionId = useRef<string>(uuidv4());
  const currentMessageId = useRef<string | null>(null);

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

  const connectWebSocket = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const websocket = new WebSocket(`${WS_URL}/api/chat/ws/${sessionId.current}`);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setState((prev) => ({ ...prev, error: null }));
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'chunk') {
          // Update streaming message
          setState((prev) => {
            if (!prev.session) return prev;

            const messages = [...prev.session.messages];
            const lastMessage = messages[messages.length - 1];

            if (lastMessage && lastMessage.id === currentMessageId.current) {
              lastMessage.content += data.content;
              lastMessage.isStreaming = true;
            } else {
              // Start new assistant message
              const newMessage: Message = {
                id: data.messageId || uuidv4(),
                role: 'assistant',
                content: data.content,
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
        } else if (data.type === 'end') {
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
        } else if (data.type === 'error') {
          setState((prev) => ({
            ...prev,
            error: data.message || 'An error occurred',
            isLoading: false,
          }));
          currentMessageId.current = null;
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setState((prev) => ({
        ...prev,
        error: 'Connection error. Please try again.',
        isLoading: false,
      }));
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      ws.current = null;
    };

    ws.current = websocket;
  }, []);

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

      // Connect WebSocket if not connected
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        connectWebSocket();
        // Wait for connection
        await new Promise((resolve) => {
          const checkConnection = setInterval(() => {
            if (ws.current?.readyState === WebSocket.OPEN) {
              clearInterval(checkConnection);
              resolve(true);
            }
          }, 100);
        });
      }

      // Send message through WebSocket
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(
          JSON.stringify({
            type: 'message',
            content: content.trim(),
            model: state.selectedModel,
          })
        );
      }
    },
    [state.isLoading, state.selectedModel, connectWebSocket]
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
    setState((prev) => ({
      ...prev,
      selectedModel: model,
      session: {
        id: uuidv4(),
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        model,
      },
    }));

    // Close existing WebSocket connection
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    // Update session ID for new WebSocket connection
    sessionId.current = uuidv4();
  }, []);

  const createNewSession = useCallback(() => {
    // Close existing WebSocket connection
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

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
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  return {
    state,
    sendMessage,
    toggleChat,
    closeChat,
    handleModelChange,
    createNewSession,
  };
}
