import { useEffect, useRef } from 'react';
import { ExecutionLog } from '../../types';
import styles from './LogsModal.module.css';

interface LogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  status: 'idle' | 'running' | 'success' | 'error';
  logs: ExecutionLog[];
}

export function LogsModal({ isOpen, onClose, title, status, logs }: LogsModalProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isOpen, logs]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getLogTypeClass = (type: ExecutionLog['type']) => {
    switch (type) {
      case 'info': return styles.logInfo;
      case 'tool': return styles.logTool;
      case 'text': return styles.logText;
      case 'error': return styles.logError;
      case 'result': return styles.logResult;
      default: return '';
    }
  };

  const getStatusClass = () => {
    switch (status) {
      case 'running': return styles.statusRunning;
      case 'success': return styles.statusSuccess;
      case 'error': return styles.statusError;
      default: return '';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'running': return 'Executando...';
      case 'success': return 'Concluído';
      case 'error': return 'Erro';
      default: return 'Aguardando';
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <h2 className={styles.title}>Logs de Execução</h2>
            <span className={styles.cardTitle}>{title}</span>
          </div>
          <div className={styles.headerRight}>
            <span className={`${styles.statusBadge} ${getStatusClass()}`}>
              {status === 'running' && <span className={styles.spinner} />}
              {getStatusText()}
            </span>
            <button className={styles.closeButton} onClick={onClose}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M4 4l12 12M16 4L4 16" />
              </svg>
            </button>
          </div>
        </div>
        <div className={styles.logsContainer}>
          {logs.length === 0 ? (
            <div className={styles.emptyState}>
              Nenhum log disponível ainda...
            </div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className={`${styles.logEntry} ${getLogTypeClass(log.type)}`}>
                <span className={styles.timestamp}>{formatTimestamp(log.timestamp)}</span>
                <span className={styles.logType}>[{log.type.toUpperCase()}]</span>
                <span className={styles.logContent}>{log.content}</span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
