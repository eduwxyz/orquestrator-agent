import { useEffect, useRef, useMemo } from 'react';
import { ExecutionLog } from '../../types';
import styles from './LogsModal.module.css';

interface LogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  status: 'idle' | 'running' | 'success' | 'error';
  logs: ExecutionLog[];
  startedAt?: string;
  completedAt?: string;
}

export function LogsModal({
  isOpen,
  onClose,
  title,
  status,
  logs,
  startedAt,
  completedAt
}: LogsModalProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const scrollPositionRef = useRef(0);

  // Scroll to bottom when new logs arrive
  useEffect(() => {
    if (isOpen) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isOpen, logs]);

  // Preserve scroll position and handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      // Save current scroll position
      scrollPositionRef.current = window.scrollY;

      // Prevent body scroll
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.top = `-${scrollPositionRef.current}px`;
      document.body.style.width = '100%';

      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);

      // Restore scroll
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      window.scrollTo(0, scrollPositionRef.current);
    };
  }, [isOpen, onClose]);

  // Calculate duration
  const duration = useMemo(() => {
    if (!startedAt) return undefined;

    const start = new Date(startedAt).getTime();
    const end = completedAt ? new Date(completedAt).getTime() : Date.now();

    return end - start;
  }, [startedAt, completedAt]);

  if (!isOpen) return null;

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'medium'
    });
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    return `${mins}m ${secs}s`;
  };

  const formatLogContent = (content: string): React.ReactNode => {
    // Detect JSON and format
    if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
      try {
        const parsed = JSON.parse(content);
        return <pre className={styles.jsonContent}>{JSON.stringify(parsed, null, 2)}</pre>;
      } catch {
        // Not valid JSON, continue with normal formatting
      }
    }

    // Detect file paths and highlight
    const withHighlightedPaths = content.replace(
      /([\w\/\-\.]+\.(ts|tsx|js|jsx|py|md|json|css|html))/g,
      '<span class="file-path">$1</span>'
    );

    return <span dangerouslySetInnerHTML={{ __html: withHighlightedPaths }} />;
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
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}> {/* Prevent closing modal when clicking inside */}
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <h2 className={styles.title}>Logs de Execução</h2>
            <span className={styles.cardTitle}>{title}</span>
          </div>
          <div className={styles.controls}>
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

        {/* Metadata Panel */}
        <div className={styles.metadataPanel}>
          <div className={styles.metadata}>
            {/* Started At */}
            <div className={styles.metadataItem}>
              <div className={styles.metadataIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
              </div>
              <div className={styles.metadataContent}>
                <div className={styles.metadataLabel}>Iniciado em</div>
                <div className={styles.metadataValue}>
                  {startedAt ? formatDateTime(startedAt) : '-'}
                </div>
              </div>
            </div>

            {/* Completed At */}
            {completedAt && (
              <div className={styles.metadataItem}>
                <div className={styles.metadataIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                  </svg>
                </div>
                <div className={styles.metadataContent}>
                  <div className={styles.metadataLabel}>Concluído em</div>
                  <div className={styles.metadataValue}>
                    {formatDateTime(completedAt)}
                  </div>
                </div>
              </div>
            )}

            {/* Duration */}
            {duration !== undefined && (
              <div className={`${styles.metadataItem} ${styles.highlight}`}>
                <div className={styles.metadataIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="2" x2="12" y2="6"/>
                    <line x1="12" y1="18" x2="12" y2="22"/>
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/>
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
                    <line x1="2" y1="12" x2="6" y2="12"/>
                    <line x1="18" y1="12" x2="22" y2="12"/>
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/>
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
                  </svg>
                </div>
                <div className={styles.metadataContent}>
                  <div className={styles.metadataLabel}>Duração</div>
                  <div className={styles.metadataValue}>
                    {formatDuration(duration)}
                  </div>
                </div>
              </div>
            )}

            {/* Status */}
            <div className={styles.metadataItem}>
              <div className={styles.metadataIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <circle cx="12" cy="12" r="3" fill="currentColor"/>
                </svg>
              </div>
              <div className={styles.metadataContent}>
                <div className={styles.metadataLabel}>Status</div>
                <div className={styles.metadataValue}>
                  {getStatusText()}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Logs Container */}
        <div className={styles.logsContainer}>
          {logs.length === 0 ? (
            <div className={styles.emptyState}>
              {status === 'running' ? 'Aguardando logs...' : 'Nenhum log disponível ainda...'}
            </div>
          ) : (
            <div className={styles.logGroups}>
              {logs.map((log, idx) => (
                <div key={idx} className={`${styles.logEntry} ${getLogTypeClass(log.type)}`}>
                  <div className={styles.logEntryHeader}>
                    <span className={styles.timestamp}>{formatTimestamp(log.timestamp)}</span>
                    <span className={`${styles.logType} ${getLogTypeClass(log.type)}`}>
                      {log.type.toUpperCase()}
                    </span>
                  </div>
                  <div className={styles.logContent}>
                    {formatLogContent(log.content)}
                  </div>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
