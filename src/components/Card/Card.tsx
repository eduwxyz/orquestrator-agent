import { useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { Card as CardType, ExecutionStatus } from '../../types';
import { LogsModal } from '../LogsModal';
import styles from './Card.module.css';

interface CardProps {
  card: CardType;
  onRemove: () => void;
  isDragging?: boolean;
  executionStatus?: ExecutionStatus;
}

export function Card({ card, onRemove, isDragging = false, executionStatus }: CardProps) {
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: card.id,
  });

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
      }
    : undefined;

  const getStatusClass = () => {
    if (!executionStatus) return '';
    switch (executionStatus.status) {
      case 'running': return styles.statusRunning;
      case 'success': return styles.statusSuccess;
      case 'error': return styles.statusError;
      default: return '';
    }
  };

  const hasLogs = executionStatus && executionStatus.logs && executionStatus.logs.length > 0;

  const handleCardClick = (e: React.MouseEvent) => {
    // Only open logs if we have execution data
    if (executionStatus && executionStatus.status !== 'idle') {
      e.stopPropagation();
      setIsLogsOpen(true);
    }
  };

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={`${styles.card} ${isDragging ? styles.dragging : ''} ${getStatusClass()} ${hasLogs ? styles.clickable : ''}`}
        {...listeners}
        {...attributes}
        onClick={handleCardClick}
      >
        <div className={styles.content}>
          <h3 className={styles.title}>{card.title}</h3>
          {card.description && (
            <p className={styles.description}>{card.description}</p>
          )}
          {executionStatus && executionStatus.status !== 'idle' && (
            <div className={styles.executionStatus}>
              {executionStatus.status === 'running' && (
                <span className={styles.statusBadge}>
                  <span className={styles.spinner} />
                  Executing /plan...
                </span>
              )}
              {executionStatus.status === 'success' && (
                <span className={styles.statusBadge}>
                  <span className={styles.checkIcon}>✓</span>
                  Plan completed
                </span>
              )}
              {executionStatus.status === 'error' && (
                <span className={styles.statusBadge}>
                  <span className={styles.errorIcon}>✗</span>
                  Plan failed
                </span>
              )}
              {hasLogs && (
                <span className={styles.logsHint}>Click to view logs</span>
              )}
            </div>
          )}
        </div>
        <button
          className={styles.removeButton}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          aria-label="Remove card"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M1 1l12 12M13 1L1 13" />
          </svg>
        </button>
      </div>
      {executionStatus && (
        <LogsModal
          isOpen={isLogsOpen}
          onClose={() => setIsLogsOpen(false)}
          title={card.title}
          status={executionStatus.status}
          logs={executionStatus.logs || []}
        />
      )}
    </>
  );
}
