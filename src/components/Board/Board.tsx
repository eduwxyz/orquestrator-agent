import { Card as CardType, Column as ColumnType, ColumnId, ExecutionStatus } from '../../types';
import { Column } from '../Column/Column';
import styles from './Board.module.css';

interface BoardProps {
  columns: ColumnType[];
  cards: CardType[];
  onAddCard: (title: string, description: string, columnId: ColumnId) => void;
  onRemoveCard: (cardId: string) => void;
  getExecutionStatus?: (cardId: string) => ExecutionStatus | undefined;
}

export function Board({ columns, cards, onAddCard, onRemoveCard, getExecutionStatus }: BoardProps) {
  return (
    <div className={styles.board}>
      {columns.map(column => (
        <Column
          key={column.id}
          column={column}
          cards={cards.filter(card => card.columnId === column.id)}
          onAddCard={onAddCard}
          onRemoveCard={onRemoveCard}
          getExecutionStatus={getExecutionStatus}
        />
      ))}
    </div>
  );
}
