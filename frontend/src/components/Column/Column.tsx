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
  onUpdateCard?: (card: CardType) => void;
  getExecutionStatus?: (cardId: string) => ExecutionStatus | undefined;
  getWorkflowStatus?: (cardId: string) => WorkflowStatus | undefined;
  onRunWorkflow?: (card: CardType) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Column({ column, cards, onAddCard, onRemoveCard, onUpdateCard, getExecutionStatus, getWorkflowStatus, onRunWorkflow, isCollapsed, onToggleCollapse }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  const isArchivedColumn = column.id === 'archived';
  const isCanceladoColumn = column.id === 'cancelado';
  const isCollapsible = isArchivedColumn || isCanceladoColumn;

  return (
    <div
      ref={setNodeRef}
      className={`${styles.column} ${styles[`column_${column.id}`]} ${isOver ? styles.columnOver : ''} ${isCollapsed ? styles.collapsed : ''}`}
    >
      <div
        className={`${styles.header} ${isCollapsible ? styles.clickableHeader : ''}`}
        onClick={isCollapsible ? onToggleCollapse : undefined}
        style={isCollapsible ? { cursor: 'pointer' } : undefined}
      >
        <h2 className={styles.title}>{column.title}</h2>
        <span className={styles.count}>{cards.length}</span>
        {isCollapsible && (
          <span className={styles.collapseIndicator}>
            {isCollapsed ? '▶' : '▼'}
          </span>
        )}
      </div>

      {!isCollapsed && (
        <div className={styles.cards}>
          {cards.map(card => (
            <Card
              key={card.id}
              card={card}
              onRemove={() => onRemoveCard(card.id)}
              onUpdateCard={onUpdateCard}
              executionStatus={getExecutionStatus?.(card.id)}
              workflowStatus={getWorkflowStatus?.(card.id)}
              onRunWorkflow={onRunWorkflow}
            />
          ))}
        </div>
      )}

      {column.id === 'backlog' && !isCollapsed && (
        <AddCard columnId={column.id} onAdd={onAddCard} />
      )}
    </div>
  );
}
