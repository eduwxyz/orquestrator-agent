import { useDroppable } from '@dnd-kit/core';
import { Card as CardType, Column as ColumnType, ColumnId, ExecutionStatus, WorkflowStatus } from '../../types';
import { Card } from '../Card/Card';
import { AddCard } from '../AddCard/AddCard';
import styles from './Column.module.css';

interface ColumnProps {
  column: ColumnType;
  cards: CardType[];
  onAddCard: (title: string, description: string, columnId: ColumnId) => void;
  onRemoveCard: (cardId: string) => void;
  getExecutionStatus?: (cardId: string) => ExecutionStatus | undefined;
  getWorkflowStatus?: (cardId: string) => WorkflowStatus | undefined;
  onRunWorkflow?: (card: CardType) => void;
  showArchived?: boolean;
  onToggleShowArchived?: () => void;
  onArchiveCard?: (cardId: string, archived: boolean) => void;
}

export function Column({ column, cards, onAddCard, onRemoveCard, getExecutionStatus, getWorkflowStatus, onRunWorkflow, showArchived, onToggleShowArchived, onArchiveCard }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  const isDoneColumn = column.id === 'done';
  const archivedCards = cards.filter(c => c.archived);
  const activeCards = cards.filter(c => !c.archived);
  const displayCards = showArchived ? cards : activeCards;

  return (
    <div
      ref={setNodeRef}
      className={`${styles.column} ${styles[`column_${column.id}`]} ${isOver ? styles.columnOver : ''}`}
    >
      <div className={styles.header}>
        <h2 className={styles.title}>{column.title}</h2>
        <span className={styles.count}>
          {activeCards.length}
          {archivedCards.length > 0 && ` (+${archivedCards.length})`}
        </span>
        {isDoneColumn && archivedCards.length > 0 && (
          <button
            className={styles.toggleArchived}
            onClick={onToggleShowArchived}
            title={showArchived ? 'Hide archived cards' : 'Show archived cards'}
          >
            {showArchived ? '📦 Hide Archived' : '📦 Show Archived'}
          </button>
        )}
      </div>
      <div className={styles.cards}>
        {displayCards.map(card => (
          <Card
            key={card.id}
            card={card}
            onRemove={() => onRemoveCard(card.id)}
            executionStatus={getExecutionStatus?.(card.id)}
            workflowStatus={getWorkflowStatus?.(card.id)}
            onRunWorkflow={onRunWorkflow}
            onArchive={isDoneColumn ? (archived) => onArchiveCard?.(card.id, archived) : undefined}
          />
        ))}
      </div>
      {column.id === 'backlog' && (
        <AddCard columnId={column.id} onAdd={onAddCard} />
      )}
    </div>
  );
}
