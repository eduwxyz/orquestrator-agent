export type ColumnId = 'backlog' | 'plan' | 'implement' | 'test' | 'review' | 'done' | 'archived' | 'cancelado';
export type ModelType =
  | 'opus-4.5' | 'sonnet-4.5' | 'haiku-4.5'  // Claude models
  | 'gemini-3-pro' | 'gemini-3-flash';  // Gemini models

// Status de merge - IA resolve conflitos automaticamente
export type MergeStatus = 'none' | 'merging' | 'resolving' | 'merged' | 'failed';

// Provider info para UI
export type ModelProvider = 'anthropic' | 'google';

export interface ModelInfo {
  value: ModelType;
  label: string;
  provider: ModelProvider;
  tagline: string;
  performance: string;
  icon: string;
  accent: string;
}

export interface CardImage {
  id: string;
  filename: string;
  path: string; // Caminho no servidor /tmp/xxx
  uploadedAt: string;
}

export interface DiffStats {
  filesAdded: string[];
  filesModified: string[];
  filesRemoved: string[];
  linesAdded: number;
  linesRemoved: number;
  totalChanges: number;
  capturedAt?: string;
  branchName?: string;
}

export interface ActiveExecution {
  id: string;
  status: 'idle' | 'running' | 'success' | 'error';
  command?: string;
  startedAt?: string;
  completedAt?: string;
  workflowStage?: string; // Stage do workflow (plan, implement, test, review)
  workflowError?: string; // Erro do workflow se houver
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
  activeExecution?: ActiveExecution; // Execucao ativa persistida no banco
  parentCardId?: string; // ID do card pai (quando for um card de correcao)
  isFixCard?: boolean; // Indica se eh um card de correcao
  testErrorContext?: string; // Contexto do erro que gerou o card de correcao
  // Campos para worktree isolation
  branchName?: string;
  worktreePath?: string;
  // Campos para diff visualization
  diffStats?: DiffStats;
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
  // Fix card fields
  fixCardCreated?: boolean; // Indica se um card de correção foi criado
  fixCardId?: string; // ID do card de correção criado
  // Workflow recovery fields
  workflowStage?: string; // Stage do workflow (plan, implement, test, review)
}

export const COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'plan', title: 'Plan' },
  { id: 'implement', title: 'Implement' },
  { id: 'test', title: 'Test' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' },
  { id: 'archived', title: 'Archived' },
  { id: 'cancelado', title: 'Cancelado' },
];

// Transições permitidas no fluxo SDLC
export const ALLOWED_TRANSITIONS: Record<ColumnId, ColumnId[]> = {
  'backlog': ['plan', 'cancelado'],
  'plan': ['implement', 'cancelado'],
  'implement': ['test', 'cancelado'],
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

// Adicionar após a função isValidTransition
export function isCardFinalized(columnId: ColumnId): boolean {
  return columnId === 'done' || columnId === 'archived' || columnId === 'cancelado';
}

export type WorkflowStage = 'idle' | 'planning' | 'implementing' | 'testing' | 'reviewing' | 'completed' | 'error';

export interface WorkflowStatus {
  cardId: string;
  stage: WorkflowStage;
  currentColumn: ColumnId;
  error?: string;
}

// Tipos para gerenciamento de projetos
export interface Project {
  id: string;
  path: string;
  name: string;
  hasClaudeConfig: boolean;
  loadedAt: string;
  claudeConfigPath?: string;
  isFavorite?: boolean;
  accessCount?: number;
}

// Tipos para sistema de draft
export interface DraftImage {
  id: string;
  filename: string;
  preview: string; // Base64 data URL
  size: number;
}

export interface CardDraft {
  title: string;
  description: string;
  modelPlan: ModelType;
  modelImplement: ModelType;
  modelTest: ModelType;
  modelReview: ModelType;
  previewImages: DraftImage[];
  savedAt: string; // ISO timestamp
  version: number; // Para controle de versão do draft
}

// Tipos para histórico de execuções
export interface ExecutionHistory {
  executionId: string;
  command: string;
  title: string;
  status: 'idle' | 'running' | 'success' | 'error';
  workflowStage?: string;
  startedAt: string;
  completedAt?: string;
  logs: ExecutionLog[];
}

export interface CardExecutionHistory {
  cardId: string;
  history: ExecutionHistory[];
}

// Interface para branches ativos
export interface ActiveBranch {
  branch: string;
  path: string;
  cardId: string;
  cardTitle: string;
  cardColumn: string;
}
