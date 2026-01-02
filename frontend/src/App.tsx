import { useState, useRef, useEffect } from 'react';
import { DndContext, DragEndEvent, DragOverEvent, DragStartEvent, DragOverlay, closestCorners, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { Card as CardType, ColumnId, COLUMNS, isValidTransition, ExecutionStatus, Project, WorkflowStatus, WorkflowStage } from './types';
import { Board } from './components/Board/Board';
import { Card } from './components/Card/Card';
import { ProjectLoader } from './components/ProjectLoader/ProjectLoader';
import { ProjectSwitcher } from './components/ProjectSwitcher';
import { useAgentExecution } from './hooks/useAgentExecution';
import { useWorkflowAutomation } from './hooks/useWorkflowAutomation';
import * as cardsApi from './api/cards';
import { getCurrentProject } from './api/projects';
import styles from './App.module.css';

function App() {
  const [cards, setCards] = useState<CardType[]>([]);
  const [activeCard, setActiveCard] = useState<CardType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isArchivedCollapsed, setIsArchivedCollapsed] = useState(false);
  const [isCanceladoCollapsed, setIsCanceladoCollapsed] = useState(false);
  const [initialExecutions, setInitialExecutions] = useState<Map<string, ExecutionStatus> | undefined>();
  const [initialWorkflowStatuses, setInitialWorkflowStatuses] = useState<Map<string, WorkflowStatus> | undefined>();
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const dragStartColumnRef = useRef<ColumnId | null>(null);
  const { executePlan, executeImplement, executeTest, executeReview, getExecutionStatus } = useAgentExecution(initialExecutions);

  // Define moveCard and updateCardSpecPath BEFORE useWorkflowAutomation
  const moveCard = (cardId: string, newColumnId: ColumnId) => {
    setCards(prev =>
      prev.map(card =>
        card.id === cardId ? { ...card, columnId: newColumnId } : card
      )
    );
  };

  const updateCardSpecPath = (cardId: string, specPath: string) => {
    setCards(prev =>
      prev.map(card =>
        card.id === cardId ? { ...card, specPath } : card
      )
    );
  };

  const {
    runWorkflow,
    getWorkflowStatus,
    // clearWorkflowStatus, // Não está sendo usado no momento
  } = useWorkflowAutomation({
    executePlan,
    executeImplement,
    executeTest,
    executeReview,
    onCardMove: moveCard,
    onSpecPathUpdate: updateCardSpecPath,
    initialStatuses: initialWorkflowStatuses,
  });

  // Load cards, active executions, and current project from API on mount
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // Load cards
        const loadedCards = await cardsApi.fetchCards();
        setCards(loadedCards);

        // Load current project
        try {
          const project = await getCurrentProject();
          if (project) {
            setCurrentProject(project);
          }
        } catch (error) {
          console.warn('[App] Failed to load current project:', error);
          // Ignorar erro se o backend não estiver disponível
          if (error instanceof Error && error.message.includes('Backend não está rodando')) {
            console.info('[App] Backend não disponível - funcionalidade de projetos desabilitada');
          }
        }

        // Construir mapa de execuções ativas e workflow statuses
        const executionsMap = new Map<string, ExecutionStatus>();
        const workflowMap = new Map<string, WorkflowStatus>();

        for (const card of loadedCards) {
          if (card.activeExecution) {
            // Buscar logs completos da execução se estiver em andamento
            if (card.activeExecution.status === 'running') {
              try {
                const logsData = await cardsApi.fetchLogs(card.id);
                executionsMap.set(card.id, {
                  cardId: card.id,
                  status: logsData.status,
                  startedAt: logsData.startedAt,
                  completedAt: logsData.completedAt,
                  logs: logsData.logs || [],
                  result: logsData.result,
                });
              } catch (error) {
                console.warn(`[App] Failed to fetch logs for card ${card.id}:`, error);
                // Usar informações básicas da execução ativa
                executionsMap.set(card.id, {
                  cardId: card.id,
                  status: card.activeExecution.status,
                  startedAt: card.activeExecution.startedAt,
                  completedAt: card.activeExecution.completedAt,
                  logs: [],
                });
              }
            } else {
              // Para execuções completas, apenas usar as informações básicas
              executionsMap.set(card.id, {
                cardId: card.id,
                status: card.activeExecution.status,
                startedAt: card.activeExecution.startedAt,
                completedAt: card.activeExecution.completedAt,
                logs: [],
              });
            }

            // Restaurar workflow state se existir
            const activeExecWithWorkflow = card.activeExecution as any;
            if (activeExecWithWorkflow.workflowStage) {
              workflowMap.set(card.id, {
                cardId: card.id,
                stage: activeExecWithWorkflow.workflowStage as WorkflowStage,
                currentColumn: card.columnId,
                error: activeExecWithWorkflow.workflowError,
              });
            }
          }
        }

        if (executionsMap.size > 0) {
          setInitialExecutions(executionsMap);
        }

        if (workflowMap.size > 0) {
          setInitialWorkflowStatuses(workflowMap);
        }
      } catch (error) {
        console.error('[App] Failed to load cards:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadInitialData();
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const addCard = async (
    _title: string,
    _description: string,
    columnId: ColumnId
  ) => {
    // Nota: Esta função agora é apenas para compatibilidade
    // O AddCard.tsx cria o card diretamente via API e faz reload da página
    if (columnId !== 'backlog') {
      console.warn('Cards só podem ser criados na raia backlog');
      return;
    }
    // O AddCard já gerencia tudo internamente
  };

  const removeCard = async (cardId: string) => {
    try {
      await cardsApi.deleteCard(cardId);
      setCards(prev => prev.filter(card => card.id !== cardId));
    } catch (error) {
      console.error('[App] Failed to delete card:', error);
      alert('Falha ao remover card.');
    }
  };

  const updateCard = (updatedCard: CardType) => {
    setCards(prev =>
      prev.map(card =>
        card.id === updatedCard.id ? updatedCard : card
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
    const startColumn = dragStartColumnRef.current;

    const activeCardData = cards.find(c => c.id === activeId);
    if (!activeCardData || !startColumn) return;

    // Check if we're over a column
    const isOverColumn = COLUMNS.some(col => col.id === overId);
    if (isOverColumn) {
      const newColumnId = overId as ColumnId;
      // Só move visualmente se for uma transição válida ou mesma coluna
      if (activeCardData.columnId !== newColumnId) {
        if (isValidTransition(startColumn, newColumnId)) {
          moveCard(activeId, newColumnId);
        }
      }
      return;
    }

    // Check if we're over another card
    const overCard = cards.find(c => c.id === overId);
    if (overCard && activeCardData.columnId !== overCard.columnId) {
      if (isValidTransition(startColumn, overCard.columnId)) {
        moveCard(activeId, overCard.columnId);
      }
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    const startColumn = dragStartColumnRef.current;
    setActiveCard(null);
    dragStartColumnRef.current = null;

    if (!over || !startColumn) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Get the card and determine final column
    const card = cards.find(c => c.id === activeId);
    if (!card) return;

    let finalColumnId: ColumnId | null = null;

    // Check if dropped on a column
    const isOverColumn = COLUMNS.some(col => col.id === overId);
    if (isOverColumn) {
      finalColumnId = overId as ColumnId;
    } else {
      // Dropped on another card - get that card's column
      const overCard = cards.find(c => c.id === overId);
      if (overCard) {
        finalColumnId = overCard.columnId;
      }
    }

    if (!finalColumnId || finalColumnId === startColumn) return;

    // Validar transição SDLC
    if (!isValidTransition(startColumn, finalColumnId)) {
      // Reverter para coluna original
      moveCard(activeId, startColumn);
      alert(`Transição inválida: ${startColumn} → ${finalColumnId}.\nSiga o fluxo SDLC: backlog → plan → in-progress → test → review → done`);
      return;
    }

    // Mover card para a coluna final (visual update)
    moveCard(activeId, finalColumnId);

    // Persist move to API
    try {
      await cardsApi.moveCard(activeId, finalColumnId);
    } catch (error) {
      console.error('[App] Failed to persist move:', error);
      moveCard(activeId, startColumn);
      alert('Falha ao mover card. Verifique se o servidor está rodando.');
      return;
    }

    // Triggers baseados na transição
    if (startColumn === 'backlog' && finalColumnId === 'plan') {
      console.log(`[App] Card moved from backlog to plan: ${card.title}`);
      const result = await executePlan(card);
      if (result.success && result.specPath) {
        updateCardSpecPath(card.id, result.specPath);
        console.log(`[App] Spec path saved: ${result.specPath}`);
      }
    } else if (startColumn === 'plan' && finalColumnId === 'in-progress') {
      // Buscar o card atualizado (pode ter specPath agora)
      const updatedCard = cards.find(c => c.id === activeId);
      if (updatedCard?.specPath) {
        console.log(`[App] Card moved from plan to in-progress: ${updatedCard.title}`);
        console.log(`[App] Executing /implement with spec: ${updatedCard.specPath}`);
        executeImplement(updatedCard);
      } else {
        alert('Este card não possui um plano associado. Execute primeiro a etapa de planejamento.');
        moveCard(activeId, startColumn);
      }
    } else if (startColumn === 'in-progress' && finalColumnId === 'test') {
      // Trigger: in-progress → test - Executar /test-implementation
      const updatedCard = cards.find(c => c.id === activeId);
      if (updatedCard?.specPath) {
        console.log(`[App] Card moved from in-progress to test: ${updatedCard.title}`);
        console.log(`[App] Executing /test-implementation with spec: ${updatedCard.specPath}`);
        executeTest(updatedCard);
      } else {
        alert('Este card não possui um plano associado. Execute primeiro a etapa de planejamento.');
        moveCard(activeId, startColumn);
      }
    } else if (startColumn === 'test' && finalColumnId === 'review') {
      // Trigger: test → review - Executar /review
      const updatedCard = cards.find(c => c.id === activeId);
      if (updatedCard?.specPath) {
        console.log(`[App] Card moved from test to review: ${updatedCard.title}`);
        console.log(`[App] Executing /review with spec: ${updatedCard.specPath}`);
        executeReview(updatedCard);
      } else {
        alert('Este card não possui um plano associado. Execute primeiro a etapa de planejamento.');
        moveCard(activeId, startColumn);
      }
    }
  };

  if (isLoading) {
    return (
      <div className={styles.app}>
        <header className={styles.header}>
          <h1 className={styles.title}>Board Kanban</h1>
        </header>
        <main className={styles.main}>
          <p>Carregando cards...</p>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1 className={styles.title}>Board Kanban</h1>
        <div className={styles.projectActions}>
          <ProjectSwitcher
            currentProject={currentProject}
            onProjectSwitch={setCurrentProject}
          />
          <ProjectLoader
            currentProject={currentProject}
            onProjectLoad={setCurrentProject}
          />
        </div>
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
            onUpdateCard={updateCard}
            getExecutionStatus={getExecutionStatus}
            getWorkflowStatus={getWorkflowStatus}
            onRunWorkflow={runWorkflow}
            isArchivedCollapsed={isArchivedCollapsed}
            onToggleArchivedCollapse={() => setIsArchivedCollapsed(!isArchivedCollapsed)}
            isCanceladoCollapsed={isCanceladoCollapsed}
            onToggleCanceladoCollapse={() => setIsCanceladoCollapsed(!isCanceladoCollapsed)}
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
      <div id="modal-root" />
    </div>
  );
}

export default App;
