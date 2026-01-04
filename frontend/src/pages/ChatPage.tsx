import { useEffect, useRef } from 'react';
import { Message } from '../types/chat';
import ChatMessage from '../components/Chat/ChatMessage';
import ChatInput from '../components/Chat/ChatInput';
import { ModelSelector } from '../components/Chat/ModelSelector';
import { MessageSquarePlus } from 'lucide-react';
import styles from './ChatPage.module.css';

interface ChatPageProps {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
  onNewChat?: () => void;
}

const ChatPage = ({
  messages,
  isLoading,
  error,
  onSendMessage,
  selectedModel,
  onModelChange,
  onNewChat,
}: ChatPageProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className={styles.chatPage}>
      <div className={styles.chatHeader}>
        <div className={styles.chatInfo}>
          <h1 className={styles.chatTitle}>AI Assistant</h1>
          <p className={styles.chatSubtitle}>
            Converse com o assistente inteligente do projeto
          </p>
        </div>
        <div className={styles.chatActions}>
          {onNewChat && (
            <button
              className={styles.newChatButton}
              onClick={onNewChat}
              title="Start new chat session"
              disabled={isLoading}
            >
              <MessageSquarePlus size={18} />
              <span>New Chat</span>
            </button>
          )}
          <ModelSelector
            selectedModel={selectedModel}
            onModelChange={onModelChange}
            disabled={isLoading}
          />
          <div className={styles.chatStatus}>
            <div className={styles.statusIndicator}></div>
            <span className={styles.statusText}>Online</span>
          </div>
        </div>
      </div>

      <div className={styles.chatContainer}>
        <div className={styles.messagesArea}>
          <div className={styles.messagesContainer}>
            {messages.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>💬</div>
                <h2 className={styles.emptyTitle}>Bem-vindo ao AI Assistant</h2>
                <p className={styles.emptyText}>
                  Inicie uma conversa com seu assistente de IA
                </p>
                <p className={styles.emptySubtext}>
                  Faça perguntas sobre seu projeto, peça ajuda com código, ou explore ideias!
                </p>
                <div className={styles.suggestions}>
                  <h3 className={styles.suggestionsTitle}>Sugestões:</h3>
                  <button
                    className={styles.suggestionButton}
                    onClick={() => onSendMessage("Como posso melhorar meu código?")}
                  >
                    Como posso melhorar meu código?
                  </button>
                  <button
                    className={styles.suggestionButton}
                    onClick={() => onSendMessage("Explique o padrão SDLC")}
                  >
                    Explique o padrão SDLC
                  </button>
                  <button
                    className={styles.suggestionButton}
                    onClick={() => onSendMessage("Ajude-me a organizar minhas tarefas")}
                  >
                    Ajude-me a organizar minhas tarefas
                  </button>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))
            )}
            {isLoading && (
              <div className={styles.typingIndicator}>
                <span></span>
                <span></span>
                <span></span>
              </div>
            )}
            {error && (
              <div className={styles.errorMessage}>
                <span className={styles.errorIcon}>⚠️</span>
                {error}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className={styles.inputArea}>
          <ChatInput onSend={onSendMessage} disabled={isLoading} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
