export type ColumnId = 'backlog' | 'plan' | 'in-progress' | 'test' | 'review' | 'done' | 'archived' | 'cancelado';
export type ModelType = 'opus-4.5' | 'sonnet-4.5' | 'haiku-4.5';

export interface CardImage {
  id: string;
  filename: string;
  path: string; // Caminho no servidor /tmp/xxx
  uploadedAt: string;
}

export interface ActiveExecution {
  id: string;
  status: 'idle' | 'running' | 'success' | 'error';
  command?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
  specPath?: string; // Caminho do arquivo de spec gerado na etapa de planejamento
  modelPlan: ModelType;
  modelImplement: ModelType;
  modelTest: ModelType;
  modelReview: ModelType;
  images?: CardImage[];
  activeExecution?: ActiveExecution; // Execução ativa persistida no banco
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
  // Metadata fields
  startedAt?: string; // ISO timestamp
  completedAt?: string; // ISO timestamp
  duration?: number; // milliseconds
}

export const COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'plan', title: 'Plan' },
  { id: 'in-progress', title: 'In Progress' },
  { id: 'test', title: 'Test' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' },
  { id: 'archived', title: 'Archived' },
  { id: 'cancelado', title: 'Cancelado' },
];

// Transições permitidas no fluxo SDLC
export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'backlog': ['plan', 'cancelado'],
  'plan': ['in-progress', 'cancelado'],
  'in-progress': ['test', 'cancelado'],
  'test': ['review', 'cancelado'],
  'review': ['done', 'cancelado'],
  'done': ['archived', 'cancelado'],
  'archived': ['done'],
  'cancelado': [], // Não permite sair de cancelado
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
