export type ColumnId = 'backlog' | 'plan' | 'in-progress' | 'test' | 'review' | 'done';

export interface Card {
  id: string;
  title: string;
  description: string;
  columnId: ColumnId;
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
