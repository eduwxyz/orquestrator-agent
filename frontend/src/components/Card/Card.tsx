import { useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { Card as CardType, ExecutionStatus, WorkflowStatus } from '../../types';
import { LogsModal } from '../LogsModal';
import { CardEditModal } from '../CardEditModal';
import { removeImage } from '../../utils/imageHandler';
import { API_ENDPOINTS } from '../../api/config';
import styles from './Card.module.css';

interface CardProps {
  card: CardType;
  onRemove: () => void;
  onUpdateCard?: (card: CardType) => void;
  isDragging?: boolean;
  executionStatus?: ExecutionStatus;
  workflowStatus?: WorkflowStatus;
  onRunWorkflow?: (card: CardType) => void;
}

export function Card({ card, onRemove, onUpdateCard, isDragging = false, executionStatus, workflowStatus, onRunWorkflow }: CardProps) {
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [removingImageId, setRemovingImageId] = useState<string | null>(null);

  const isRunning = workflowStatus && workflowStatus.stage !== 'idle' && workflowStatus.stage !== 'completed';

  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: card.id,
    disabled: isRunning // Apenas desabilitar drag durante execução do workflow
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

  const handleRemoveImage = async (imageId: string) => {
    try {
      setRemovingImageId(imageId);
      await removeImage(imageId);

      // Atualizar o card removendo a imagem
      if (onUpdateCard && card.images) {
        const updatedCard = {
          ...card,
          images: card.images.filter(img => img.id !== imageId)
        };
        onUpdateCard(updatedCard);
      }
    } catch (error) {
      console.error('Failed to remove image:', error);
    } finally {
      setRemovingImageId(null);
    }
  };

  // Função helper para determinar a mensagem de execução
  const getExecutionMessage = () => {
    if (!executionStatus || executionStatus.status === 'idle') return null;

    const { status } = executionStatus;
    const stage = workflowStatus?.stage;

    // Mapear stage para comando
    const stageToCommand: Record<string, { running: string; success: string; error: string }> = {
      planning: {
        running: 'Executing /plan...',
        success: 'Plan completed',
        error: 'Plan failed',
      },
      implementing: {
        running: 'Executing /implement...',
        success: 'Implementation completed',
        error: 'Implementation failed',
      },
      testing: {
        running: 'Executing /test-implementation...',
        success: 'Tests completed',
        error: 'Tests failed',
      },
      reviewing: {
        running: 'Executing /review...',
        success: 'Review completed',
        error: 'Review failed',
      },
    };

    // Se temos workflowStatus.stage, usar ele para determinar a mensagem
    if (stage && stage in stageToCommand) {
      return stageToCommand[stage][status];
    }

    // Fallback: determinar com base na coluna do card (para execuções manuais)
    const columnToCommand: Record<string, { running: string; success: string; error: string }> = {
      plan: {
        running: 'Executing /plan...',
        success: 'Plan completed',
        error: 'Plan failed',
      },
      'in-progress': {
        running: 'Executing /implement...',
        success: 'Implementation completed',
        error: 'Implementation failed',
      },
      test: {
        running: 'Executing /test-implementation...',
        success: 'Tests completed',
        error: 'Tests failed',
      },
      review: {
        running: 'Executing /review...',
        success: 'Review completed',
        error: 'Review failed',
      },
    };

    if (card.columnId in columnToCommand) {
      return columnToCommand[card.columnId][status];
    }

    // Fallback genérico
    const genericMessages: Record<string, string> = {
      running: 'Executing...',
      success: 'Execution completed',
      error: 'Execution failed',
    };

    return genericMessages[status];
  };

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={`${styles.card} ${isDragging ? styles.dragging : ''} ${getStatusClass()} ${card.isFixCard ? styles.fixCard : ''}`}
        {...listeners}
        {...attributes}
      >
        {card.isFixCard && (
          <div className={styles.fixBadge}>
            🔧 Correção
          </div>
        )}
        <div className={styles.content}>
          <h3 className={styles.title}>{card.title}</h3>
          {card.description && (
            <p className={styles.description}>{card.description}</p>
          )}
          {card.images && card.images.length > 0 && (
            <div className={styles.imagePreview}>
              {card.images.map(image => (
                <div key={image.id} className={styles.imageThumb}>
                  <img
                    src={`${API_ENDPOINTS.images}/${image.id}`}
                    alt={image.filename}
                    title={image.filename}
                  />
                  <button
                    className={styles.removeImageButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveImage(image.id);
                    }}
                    disabled={removingImageId === image.id}
                    aria-label={`Remove ${image.filename}`}
                  >
                    {removingImageId === image.id ? '...' : '✕'}
                  </button>
                </div>
              ))}
            </div>
          )}
          {executionStatus && executionStatus.status !== 'idle' && (
            <div className={styles.executionStatus}>
              {(() => {
                const message = getExecutionMessage();
                if (!message) return null;

                return (
                  <>
                    {executionStatus.status === 'running' && (
                      <span className={styles.statusBadge}>
                        <span className={styles.spinner} />
                        {message}
                      </span>
                    )}
                    {executionStatus.status === 'success' && (
                      <span className={styles.statusBadge}>
                        <span className={styles.checkIcon}>✓</span>
                        {message}
                      </span>
                    )}
                    {executionStatus.status === 'error' && (
                      <span className={styles.statusBadge}>
                        <span className={styles.errorIcon}>✗</span>
                        {message}
                      </span>
                    )}
                    {hasLogs && (
                      <button
                        className={styles.viewLogsButton}
                        onClick={(e) => {
                          e.stopPropagation();
                          setIsLogsOpen(true);
                        }}
                        aria-label="View execution logs"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                          <polyline points="14 2 14 8 20 8"/>
                          <line x1="16" y1="13" x2="8" y2="13"/>
                          <line x1="16" y1="17" x2="8" y2="17"/>
                          <line x1="10" y1="9" x2="8" y2="9"/>
                        </svg>
                        View Logs
                      </button>
                    )}
                  </>
                );
              })()}
            </div>
          )}
        </div>
        {card.columnId === 'backlog' && !isRunning && (
          <button
            className={styles.runButton}
            onClick={(e) => {
              e.stopPropagation();
              onRunWorkflow?.(card);
            }}
            aria-label="Run workflow"
            title="Executar workflow completo automaticamente"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M4 2l10 6-10 6V2z" />
            </svg>
            Run
          </button>
        )}
        {card.columnId === 'done' && (
          <button
            className={styles.createPrButton}
            onClick={(e) => {
              e.stopPropagation();
              // Placeholder: funcionalidade será implementada futuramente
            }}
            aria-label="Create Pull Request"
            title="Criar Pull Request para esta feature"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13 3a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm0-1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM3 13a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm0-1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0-10a1 1 0 1 1 0 2 1 1 0 0 1 0-2zM3 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm9.5 4.5V8h-1V5.5h1zM4 4.5v7h-1v-7h1zm8.5 8V10h1v2.5a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 0-1.5 1.5v.5h-1v-.5A2.5 2.5 0 0 1 5 13h7a.5.5 0 0 0 .5-.5z"/>
            </svg>
            Create PR
          </button>
        )}
        {workflowStatus && workflowStatus.stage !== 'idle' && (
          <div className={styles.workflowProgress}>
            <span className={styles.progressBadge}>
              {workflowStatus.stage === 'planning' && '📋 Planning...'}
              {workflowStatus.stage === 'implementing' && '⚙️ Implementing...'}
              {workflowStatus.stage === 'testing' && '🧪 Testing...'}
              {workflowStatus.stage === 'reviewing' && '👁️ Reviewing...'}
              {workflowStatus.stage === 'completed' && '✅ Completed'}
              {workflowStatus.stage === 'error' && '❌ Failed'}
            </span>
          </div>
        )}
        <button
          className={styles.editButton}
          onClick={(e) => {
            e.stopPropagation();
            setIsEditOpen(true);
          }}
          aria-label="Edit card"
          title="Edit card (add images)"
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
            <path d="M10.5 1.5l2 2-8 8H2.5v-2l8-8z" />
          </svg>
        </button>
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
          startedAt={executionStatus.startedAt}
          completedAt={executionStatus.completedAt}
        />
      )}
      {onUpdateCard && (
        <CardEditModal
          isOpen={isEditOpen}
          onClose={() => setIsEditOpen(false)}
          card={card}
          onUpdateCard={onUpdateCard}
        />
      )}
    </>
  );
}
