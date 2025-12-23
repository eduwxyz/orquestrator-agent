import { useState, useRef } from 'react';
import { DndContext, DragEndEvent, DragOverEvent, DragStartEvent, DragOverlay, closestCorners, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { Card as CardType, ColumnId, COLUMNS } from './types';
import { Board } from './components/Board/Board';
import { Card } from './components/Card/Card';
import { useAgentExecution } from './hooks/useAgentExecution';
import styles from './App.module.css';

function App() {
  const [cards, setCards] = useState<CardType[]>([]);
  const [activeCard, setActiveCard] = useState<CardType | null>(null);
  const dragStartColumnRef = useRef<ColumnId | null>(null);
  const { executePlan, getExecutionStatus } = useAgentExecution();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const addCard = (title: string, description: string, columnId: ColumnId) => {
    if (columnId !== 'backlog') {
      console.warn('Cards só podem ser criados na raia backlog');
      return;
    }

    const newCard: CardType = {
      id: crypto.randomUUID(),
      title,
      description,
      columnId,
    };
    setCards(prev => [...prev, newCard]);
  };

  const removeCard = (cardId: string) => {
    setCards(prev => prev.filter(card => card.id !== cardId));
  };

  const moveCard = (cardId: string, newColumnId: ColumnId) => {
    setCards(prev =>
      prev.map(card =>
        card.id === cardId ? { ...card, columnId: newColumnId } : card
      )
    );
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const card = cards.find(c => c.id === active.id);
    if (card) {
      setActiveCard(card);
      dragStartColumnRef.current = card.columnId;
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    const activeCard = cards.find(c => c.id === activeId);
    if (!activeCard) return;

    // Check if we're over a column
    const isOverColumn = COLUMNS.some(col => col.id === overId);
    if (isOverColumn) {
      const newColumnId = overId as ColumnId;
      if (activeCard.columnId !== newColumnId) {
        moveCard(activeId, newColumnId);
      }
      return;
    }

    // Check if we're over another card
    const overCard = cards.find(c => c.id === overId);
    if (overCard && activeCard.columnId !== overCard.columnId) {
      moveCard(activeId, overCard.columnId);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    const startColumn = dragStartColumnRef.current;
    setActiveCard(null);
    dragStartColumnRef.current = null;

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Get the card and determine final column
    const card = cards.find(c => c.id === activeId);
    let finalColumnId: ColumnId | null = null;

    // Check if dropped on a column
    const isOverColumn = COLUMNS.some(col => col.id === overId);
    if (isOverColumn) {
      finalColumnId = overId as ColumnId;
      moveCard(activeId, finalColumnId);
    } else {
      // Dropped on another card - get that card's column
      const overCard = cards.find(c => c.id === overId);
      if (overCard) {
        finalColumnId = overCard.columnId;
      }
    }

    // Detect backlog → plan transition and trigger /plan execution
    if (card && startColumn === 'backlog' && finalColumnId === 'plan') {
      console.log(`[App] Card moved from backlog to plan: ${card.title}`);
      executePlan(card);
    }
  };

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1 className={styles.title}>Kanban Board</h1>
      </header>
      <main className={styles.main}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <Board
            columns={COLUMNS}
            cards={cards}
            onAddCard={addCard}
            onRemoveCard={removeCard}
            getExecutionStatus={getExecutionStatus}
          />
          <DragOverlay>
            {activeCard ? (
              <Card
                card={activeCard}
                onRemove={() => {}}
                isDragging
              />
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
}

export default App;
