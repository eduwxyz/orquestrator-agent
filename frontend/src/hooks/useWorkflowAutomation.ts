import { useState, useCallback } from 'react';
import { Card, ColumnId, WorkflowStatus, WorkflowStage } from '../types';
import * as cardsApi from '../api/cards';
import { updateWorkflowState } from '../api/cards';

interface UseWorkflowAutomationProps {
  executePlan: (card: Card) => Promise<{ success: boolean; specPath?: string; error?: string }>;
  executeImplement: (card: Card) => Promise<{ success: boolean; error?: string }>;
  executeTest: (card: Card) => Promise<{ success: boolean; error?: string }>;
  executeReview: (card: Card) => Promise<{ success: boolean; error?: string }>;
  onCardMove: (cardId: string, columnId: ColumnId) => void;
  onSpecPathUpdate: (cardId: string, specPath: string) => void;
  initialStatuses?: Map<string, WorkflowStatus>; // Para restaurar estados
}

export function useWorkflowAutomation({
  executePlan,
  executeImplement,
  executeTest,
  executeReview,
  onCardMove,
  onSpecPathUpdate,
  initialStatuses,
}: UseWorkflowAutomationProps) {
  const [workflowStatuses, setWorkflowStatuses] = useState<Map<string, WorkflowStatus>>(
    initialStatuses || new Map()
  );

  const runWorkflow = useCallback(async (card: Card) => {
    // Validar que o card está em backlog
    if (card.columnId !== 'backlog') {
      console.warn('Workflow só pode ser iniciado de cards em backlog');
      return;
    }

    const updateStatus = async (stage: WorkflowStage, currentColumn: ColumnId, error?: string) => {
      setWorkflowStatuses(prev => {
        const next = new Map(prev);
        next.set(card.id, { cardId: card.id, stage, currentColumn, error });
        return next;
      });

      // Persistir no backend
      try {
        await updateWorkflowState(card.id, { stage, error });
      } catch (err) {
        console.error('[WorkflowAutomation] Failed to persist workflow state:', err);
      }
    };

    try {
      // Etapa 1: Plan (backlog → plan)
      await cardsApi.moveCard(card.id, 'plan');
      onCardMove(card.id, 'plan');
      await updateStatus('planning', 'plan');

      const planResult = await executePlan(card);
      if (!planResult.success) {
        // Rollback: voltar para backlog
        await cardsApi.moveCard(card.id, 'backlog');
        onCardMove(card.id, 'backlog');
        await updateStatus('error', 'backlog', planResult.error);
        return;
      }

      // Persistir specPath
      if (planResult.specPath) {
        await cardsApi.updateSpecPath(card.id, planResult.specPath);
        onSpecPathUpdate(card.id, planResult.specPath);
        card.specPath = planResult.specPath;
      }

      // Etapa 2: Implement (plan → in-progress)
      await cardsApi.moveCard(card.id, 'in-progress');
      onCardMove(card.id, 'in-progress');
      await updateStatus('implementing', 'in-progress');

      const implementResult = await executeImplement(card);
      if (!implementResult.success) {
        // Rollback: voltar para plan
        await cardsApi.moveCard(card.id, 'plan');
        onCardMove(card.id, 'plan');
        await updateStatus('error', 'plan', implementResult.error);
        return;
      }

      // Etapa 3: Test (in-progress → test)
      await cardsApi.moveCard(card.id, 'test');
      onCardMove(card.id, 'test');
      await updateStatus('testing', 'test');

      const testResult = await executeTest(card);
      if (!testResult.success) {
        // Rollback: voltar para in-progress
        await cardsApi.moveCard(card.id, 'in-progress');
        onCardMove(card.id, 'in-progress');
        await updateStatus('error', 'in-progress', testResult.error);
        return;
      }

      // Etapa 4: Review (test → review)
      await cardsApi.moveCard(card.id, 'review');
      onCardMove(card.id, 'review');
      await updateStatus('reviewing', 'review');

      const reviewResult = await executeReview(card);
      if (!reviewResult.success) {
        // Rollback: voltar para test
        await cardsApi.moveCard(card.id, 'test');
        onCardMove(card.id, 'test');
        await updateStatus('error', 'test', reviewResult.error);
        return;
      }

      // Finalizar (review → done)
      await cardsApi.moveCard(card.id, 'done');
      onCardMove(card.id, 'done');
      await updateStatus('completed', 'done');

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      await updateStatus('error', card.columnId, errorMsg);
      console.error('[useWorkflowAutomation] Workflow failed:', errorMsg);
    }
  }, [executePlan, executeImplement, executeTest, executeReview, onCardMove, onSpecPathUpdate]);

  const getWorkflowStatus = useCallback((cardId: string) => {
    return workflowStatuses.get(cardId);
  }, [workflowStatuses]);

  const clearWorkflowStatus = useCallback((cardId: string) => {
    setWorkflowStatuses(prev => {
      const next = new Map(prev);
      next.delete(cardId);
      return next;
    });
  }, []);

  return {
    runWorkflow,
    getWorkflowStatus,
    clearWorkflowStatus,
  };
}
