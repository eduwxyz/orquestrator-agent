import { useDroppable } from '@dnd-kit/core';
import { Card as CardType, Column as ColumnType, ColumnId, ExecutionStatus } from '../../types';
import { Card } from '../Card/Card';
import { AddCard } from '../AddCard/AddCard';
import styles from './Column.module.css';

interface ColumnProps {
  column: ColumnType;
  cards: CardType[];
  onAddCard: (title: string, description: string, columnId: ColumnId) => void;
  onRemoveCard: (cardId: string) => void;
  getExecutionStatus?: (cardId: string) => ExecutionStatus | undefined;
}

export function Column({ column, cards, onAddCard, onRemoveCard, getExecutionStatus }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  return (
    <div
      ref={setNodeRef}
      className={`${styles.column} ${isOver ? styles.columnOver : ''}`}
    >
      <div className={styles.header}>
        <h2 className={styles.title}>{column.title}</h2>
        <span className={styles.count}>{cards.length}</span>
      </div>
      <div className={styles.cards}>
        {cards.map(card => (
          <Card
            key={card.id}
            card={card}
            onRemove={() => onRemoveCard(card.id)}
            executionStatus={getExecutionStatus?.(card.id)}
          />
        ))}
      </div>
      {column.id === 'backlog' && (
        <AddCard columnId={column.id} onAdd={onAddCard} />
      )}
    </div>
  );
}
