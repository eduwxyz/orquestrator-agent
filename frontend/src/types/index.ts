export type ColumnId = 'backlog' | 'plan' | 'in-progress' | 'test' | 'review' | 'done';

export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
  specPath?: string; // Caminho do arquivo de spec gerado na etapa de planejamento
  archived?: boolean; // Se o card está arquivado (apenas para coluna Done)
}

export interface Column {
  id: ColumnId;
  title: string;
}

export interface ExecutionLog {
  timestamp: string;
  type: 'info' | 'tool' | 'text' | 'error' | 'result';
  content: string;
}

export interface ExecutionStatus {
  cardId: string;
  status: 'idle' | 'running' | 'success' | 'error';
  result?: string;
  logs: ExecutionLog[];
}

export const COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'plan', title: 'Plan' },
  { id: 'in-progress', title: 'In Progress' },
  { id: 'test', title: 'Test' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' },
];

// Transições permitidas no fluxo SDLC
export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'backlog': ['plan'],
  'plan': ['in-progress'],
  'in-progress': ['test'],
  'test': ['review'],
  'review': ['done'],
  'done': [],
};

export function isValidTransition(from: ColumnId, to: ColumnId): boolean {
  if (from === to) return true; // Mesma coluna é sempre válido
  return ALLOWED_TRANSITIONS[from]?.includes(to) ?? false;
}

export type WorkflowStage = 'idle' | 'planning' | 'implementing' | 'testing' | 'reviewing' | 'completed' | 'error';

export interface WorkflowStatus {
  cardId: string;
  stage: WorkflowStage;
  currentColumn: ColumnId;
  error?: string;
}
