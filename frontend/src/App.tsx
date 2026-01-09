import { useState, useRef, useEffect } from 'react';
import { DragEndEvent, DragOverEvent, DragStartEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { Card as CardType, ColumnId, COLUMNS, isValidTransition, ExecutionStatus, Project, WorkflowStatus, WorkflowStage } from './types';
import { useAgentExecution } from './hooks/useAgentExecution';
import { useWorkflowAutomation } from './hooks/useWorkflowAutomation';
import { useChat } from './hooks/useChat';
import { useViewPersistence } from './hooks/useViewPersistence';
import * as cardsApi from './api/cards';
import { getCurrentProject } from './api/projects';
import WorkspaceLayout, { ModuleType } from './layouts/WorkspaceLayout';
import HomePage from './pages/HomePage';
import KanbanPage from './pages/KanbanPage';
import ChatPage from './pages/ChatPage';
import MetricsPage from './pages/MetricsPage';
import SettingsPage from './pages/SettingsPage';
import styles from './App.module.css';

function App() {
  const { getSavedView, saveView } = useViewPersistence();

  // Inicializar com view salva
  const [currentView, setCurrentView] = useState<ModuleType>(() => {
    return getSavedView();
  });
  const [cards, setCards] = useState<CardType[]>([]);
  const [activeCard, setActiveCard] = useState<CardType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isArchivedCollapsed, setIsArchivedCollapsed] = useState(false);
  const [isCanceladoCollapsed, setIsCanceladoCollapsed] = useState(false);
  const [initialExecutions, setInitialExecutions] = useState<Map<string, ExecutionStatus> | undefined>();
  const [initialWorkflowStatuses, setInitialWorkflowStatuses] = useState<Map<string, WorkflowStatus> | undefined>();
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const dragStartColumnRef = useRef<ColumnId | null>(null);

  // Callback para atualizar cards quando uma execução completar
  const handleExecutionComplete = async (cardId: string, status: ExecutionStatus) => {
    if (status.status === 'success') {
      try {
        const updatedCard = await cardsApi.fetchCard(cardId);
        setCards(prev => prev.map(card =>
          card.id === cardId ? updatedCard : card
        ));
      } catch (error) {
        console.error('[App] Failed to fetch updated card:', error);
      }
    }
  };

  const { executePlan, executeImplement, executeTest, executeReview, getExecutionStatus, registerCompletionCallback, executions, fetchLogsHistory } = useAgentExecution({
    initialExecutions,
    onExecutionComplete: handleExecutionComplete,
  });
  const { state: chatState, sendMessage, handleModelChange, createNewSession } = useChat();

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
    handleCompletedReview,
    // clearWorkflowStatus, // Não está sendo usado no momento
  } = useWorkflowAutomation({
    executePlan,
    executeImplement,
    executeTest,
    executeReview,
    onCardMove: moveCard,
    onSpecPathUpdate: updateCardSpecPath,
    initialStatuses: initialWorkflowStatuses,
    cards,
    registerCompletionCallback,
    executions,
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
        // IMPORTANTE: Incluir cards em "done" para manter histórico de logs acessível
        const executionsMap = new Map<string, ExecutionStatus>();
        const workflowMap = new Map<string, WorkflowStatus>();

        for (const card of loadedCards) {
          // Carregar execução para TODOS os cards com activeExecution, incluindo os em "done"
          if (card.activeExecution) {
            console.log(`[App] Found card ${card.id} with activeExecution:`, card.activeExecution);

            // Buscar logs completos da execução se estiver em andamento
            if (card.activeExecution.status === 'running') {
              console.log(`[App] Card ${card.id} is running, fetching logs...`);
              try {
                const logsData = await cardsApi.fetchLogs(card.id);
                console.log(`[App] Fetched logs for card ${card.id}:`, logsData);
                executionsMap.set(card.id, {
                  cardId: card.id,
                  status: logsData.status,
                  startedAt: logsData.startedAt,
                  completedAt: logsData.completedAt,
                  logs: logsData.logs || [],
                  result: logsData.result,
                  workflowStage: logsData.workflowStage, // Incluir workflow stage
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
                  workflowStage: card.activeExecution.workflowStage, // Incluir workflow stage
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
                workflowStage: card.activeExecution.workflowStage, // Incluir workflow stage
              });
            }

            // Restaurar workflow state se existir
            const activeExecWithWorkflow = card.activeExecution as any;
            if (activeExecWithWorkflow.workflowStage) {
              // Mapear valores antigos para os novos (compatibilidade)
              const stageMap: Record<string, WorkflowStage> = {
                'plan': 'planning',
                'implement': 'implementing',
                'test': 'testing',
                'test-implementation': 'testing',
                'review': 'reviewing',
                // Valores já corretos
                'planning': 'planning',
                'implementing': 'implementing',
                'testing': 'testing',
                'reviewing': 'reviewing',
                'completed': 'completed',
                'error': 'error',
                'idle': 'idle',
              };
              const mappedStage = stageMap[activeExecWithWorkflow.workflowStage] || 'planning';

              workflowMap.set(card.id, {
                cardId: card.id,
                stage: mappedStage,
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

  // Polling para atualizar token stats em tempo real (a cada 2 segundos)
  const hasActiveExecutions = cards.some(c => c.activeExecution?.status === 'running');

  useEffect(() => {
    if (!hasActiveExecutions) {
      return; // Não faz polling se não há execuções ativas
    }

    console.log('[App] Starting token stats polling (active executions detected)');

    const pollTokenStats = async () => {
      try {
        const updatedCards = await cardsApi.fetchCards();

        setCards(prev => {
          // Só atualizar se houver mudanças reais
          const hasChanges = prev.some(card => {
            const updated = updatedCards.find(c => c.id === card.id);
            if (!updated) return false;

            return (
              JSON.stringify(card.tokenStats) !== JSON.stringify(updated.tokenStats) ||
              JSON.stringify(card.activeExecution) !== JSON.stringify(updated.activeExecution) ||
              JSON.stringify(card.diffStats) !== JSON.stringify(updated.diffStats)
            );
          });

          if (!hasChanges) return prev;

          return prev.map(card => {
            const updated = updatedCards.find(c => c.id === card.id);
            return updated ? {
              ...card,
              tokenStats: updated.tokenStats,
              activeExecution: updated.activeExecution,
              diffStats: updated.diffStats,
            } : card;
          });
        });
      } catch (error) {
        console.error('[App] Error polling token stats:', error);
      }
    };

    // Primeira execução imediata
    pollTokenStats();

    const interval = setInterval(pollTokenStats, 2000);
    return () => {
      console.log('[App] Stopping token stats polling');
      clearInterval(interval);
    };
  }, [hasActiveExecutions]); // Dependência mais estável

  // Polling para monitorar merge automático em background
  const mergingCardsRef = useRef<CardType[]>([]);

  useEffect(() => {
    // Atualizar ref
    mergingCardsRef.current = cards.filter(c =>
      c.mergeStatus === 'resolving' || c.mergeStatus === 'merging'
    );

    if (mergingCardsRef.current.length === 0) {
      return; // Nada para monitorar
    }

    console.log(`[App] Monitoring ${mergingCardsRef.current.length} card(s) with merges in progress`);

    const pollMergeStatus = async () => {
      try {
        const updatedCards = await cardsApi.fetchCards();
        const currentMergingCards = mergingCardsRef.current;

        for (const oldCard of currentMergingCards) {
          const updatedCard = updatedCards.find(c => c.id === oldCard.id);

          if (!updatedCard) continue;

          // Se o merge foi completado com sucesso
          if (updatedCard.mergeStatus === 'merged' && updatedCard.columnId === 'review') {
            console.log(`[App] Merge completed for card ${updatedCard.id}, moving to Done`);

            // Mover para done
            await cardsApi.moveCard(updatedCard.id, 'done');

            // Atualizar estado local
            setCards(prev => prev.map(c =>
              c.id === updatedCard.id
                ? { ...updatedCard, columnId: 'done', mergeStatus: 'merged' }
                : c
            ));
          }
          // Se o merge falhou
          else if (updatedCard.mergeStatus === 'failed') {
            console.error(`[App] Merge failed for card ${updatedCard.id}`);

            // Atualizar estado local com o status de falha
            setCards(prev => prev.map(c =>
              c.id === updatedCard.id
                ? { ...updatedCard }
                : c
            ));
          }
          // Se ainda está resolvendo, atualizar o card
          else if (updatedCard.mergeStatus === 'resolving') {
            setCards(prev => prev.map(c =>
              c.id === updatedCard.id
                ? { ...updatedCard }
                : c
            ));
          }
        }
      } catch (error) {
        console.error('[App] Error polling merge status:', error);
      }
    };

    const interval = setInterval(pollMergeStatus, 5000);
    return () => clearInterval(interval);
  }, [cards.filter(c => c.mergeStatus === 'resolving' || c.mergeStatus === 'merging').length]); // Dependência mais específica

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

  // Função para navegar entre views com persistência
  const handleNavigate = (module: ModuleType) => {
    setCurrentView(module);
    saveView(module);
  };

  // Callback para atualização reativa quando um card é criado
  const handleCardCreated = (newCard: CardType) => {
    // Adicionar o novo card à lista
    setCards(prev => [...prev, newCard]);
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
      alert(`Transição inválida: ${startColumn} → ${finalColumnId}.\nSiga o fluxo SDLC: backlog → plan → implement → test → review → done`);
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
    } else if (startColumn === 'plan' && finalColumnId === 'implement') {
      // Buscar o card atualizado (pode ter specPath agora)
      const updatedCard = cards.find(c => c.id === activeId);
      if (updatedCard?.specPath) {
        console.log(`[App] Card moved from plan to implement: ${updatedCard.title}`);
        console.log(`[App] Executing /implement with spec: ${updatedCard.specPath}`);
        executeImplement(updatedCard);
      } else {
        alert('Este card não possui um plano associado. Execute primeiro a etapa de planejamento.');
        moveCard(activeId, startColumn);
      }
    } else if (startColumn === 'implement' && finalColumnId === 'test') {
      // Trigger: implement → test - Executar /test-implementation
      const updatedCard = cards.find(c => c.id === activeId);
      if (updatedCard?.specPath) {
        console.log(`[App] Card moved from implement to test: ${updatedCard.title}`);
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
    } else if (startColumn === 'review' && finalColumnId === 'done') {
      // Trigger: review → done - Fazer merge automático
      const updatedCard = cards.find(c => c.id === activeId);
      if (updatedCard?.branchName) {
        console.log(`[App] Card moved from review to done: ${updatedCard.title}`);
        console.log(`[App] Starting automatic merge for branch: ${updatedCard.branchName}`);

        // Tentar fazer merge
        const mergeResult = await handleCompletedReview(updatedCard.id);

        if (mergeResult.success) {
          console.log(`[App] Merge successful for card: ${updatedCard.title}`);
        } else if (mergeResult.status === 'resolving') {
          console.log(`[App] Merge has conflicts, AI is resolving automatically`);
          // Card já está em done, merge será completado em background
        } else {
          console.error(`[App] Merge failed: ${mergeResult.error}`);
          alert(`Falha ao fazer merge: ${mergeResult.error}\nO card foi movido para Done, mas o merge precisa ser feito manualmente.`);
        }
      } else {
        console.log(`[App] Card has no branch, skipping merge`);
      }
    }
  };

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <HomePage cards={cards} onNavigate={handleNavigate} />;

      case 'kanban':
        return (
          <KanbanPage
            columns={COLUMNS}
            cards={cards}
            activeCard={activeCard}
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
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
            currentProject={currentProject}
            onProjectSwitch={setCurrentProject}
            onProjectLoad={setCurrentProject}
            fetchLogsHistory={fetchLogsHistory}
            onCardCreated={handleCardCreated}
          />
        );

      case 'chat':
        return (
          <ChatPage
            messages={chatState.session?.messages || []}
            isLoading={chatState.isLoading}
            error={chatState.error}
            onSendMessage={sendMessage}
            selectedModel={chatState.selectedModel}
            onModelChange={handleModelChange}
            onNewChat={createNewSession}
          />
        );

      case 'metrics':
        return <MetricsPage projectId={currentProject?.id || 'default'} />;

      case 'settings':
        return <SettingsPage />;

      default:
        return <HomePage cards={cards} onNavigate={setCurrentView} />;
    }
  };

  if (isLoading) {
    return (
      <div className={styles.app}>
        <div className={styles.loader}>
          <div className={styles.loaderSpinner}></div>
          <p>Carregando workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <WorkspaceLayout currentModule={currentView} onNavigate={handleNavigate}>
      {renderView()}
      <div id="modal-root" />
    </WorkspaceLayout>
  );
}

export default App;
