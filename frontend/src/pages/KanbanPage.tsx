import { DndContext, DragOverlay, closestCorners } from '@dnd-kit/core';
import { Card as CardType, Column, ColumnId, ExecutionStatus, WorkflowStatus } from '../types';
import { Board } from '../components/Board/Board';
import { Card } from '../components/Card/Card';
import { Project } from '../types';
import { ProjectLoader } from '../components/ProjectLoader/ProjectLoader';
import { ProjectSwitcher } from '../components/ProjectSwitcher';
import { AddCard } from '../components/AddCard/AddCard';
import styles from './KanbanPage.module.css';

interface KanbanPageProps {
  columns: Column[];
  cards: CardType[];
  activeCard: CardType | null;
  sensors: any;
  onDragStart: (event: any) => void;
  onDragOver: (event: any) => void;
  onDragEnd: (event: any) => void;
  onAddCard: (title: string, description: string, columnId: ColumnId) => void;
  onRemoveCard: (cardId: string) => void;
  onUpdateCard: (card: CardType) => void;
  getExecutionStatus: (cardId: string) => ExecutionStatus | undefined;
  getWorkflowStatus: (cardId: string) => WorkflowStatus | undefined;
  onRunWorkflow: (card: CardType) => void;
  isArchivedCollapsed: boolean;
  onToggleArchivedCollapse: () => void;
  isCanceladoCollapsed: boolean;
  onToggleCanceladoCollapse: () => void;
  currentProject: Project | null;
  onProjectSwitch: (project: Project | null) => void;
  onProjectLoad: (project: Project | null) => void;
  fetchLogsHistory?: (cardId: string) => Promise<{ cardId: string; history: any[] } | null>;
  loadingExpertsCardId?: string | null;
}

const KanbanPage = ({
  columns,
  cards,
  activeCard,
  sensors,
  onDragStart,
  onDragOver,
  onDragEnd,
  onAddCard,
  onRemoveCard,
  onUpdateCard,
  getExecutionStatus,
  getWorkflowStatus,
  onRunWorkflow,
  isArchivedCollapsed,
  onToggleArchivedCollapse,
  isCanceladoCollapsed,
  onToggleCanceladoCollapse,
  currentProject,
  onProjectSwitch,
  onProjectLoad,
  fetchLogsHistory,
  loadingExpertsCardId,
}: KanbanPageProps) => {
  return (
    <div className={styles.kanbanPage}>
      <div className={styles.kanbanHeader}>
        <div className={styles.kanbanInfo}>
          <h1 className={styles.kanbanTitle}>Workflow Board</h1>
          <p className={styles.kanbanSubtitle}>
            Gerencie seu workflow com automação SDLC
          </p>
        </div>
        <div className={styles.projectActions}>
          <AddCard columnId="backlog" onAdd={onAddCard} />
          <ProjectSwitcher
            currentProject={currentProject}
            onProjectSwitch={onProjectSwitch}
          />
          <ProjectLoader
            currentProject={currentProject}
            onProjectLoad={onProjectLoad}
          />
        </div>
      </div>

      <div className={styles.kanbanContent}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragOver={onDragOver}
          onDragEnd={onDragEnd}
        >
          <Board
            columns={columns}
            cards={cards}
            onAddCard={onAddCard}
            onRemoveCard={onRemoveCard}
            onUpdateCard={onUpdateCard}
            getExecutionStatus={getExecutionStatus}
            getWorkflowStatus={getWorkflowStatus}
            onRunWorkflow={onRunWorkflow}
            isArchivedCollapsed={isArchivedCollapsed}
            onToggleArchivedCollapse={onToggleArchivedCollapse}
            isCanceladoCollapsed={isCanceladoCollapsed}
            onToggleCanceladoCollapse={onToggleCanceladoCollapse}
            fetchLogsHistory={fetchLogsHistory}
            loadingExpertsCardId={loadingExpertsCardId}
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
      </div>
    </div>
  );
};

export default KanbanPage;
