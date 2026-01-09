import { ReactNode } from 'react';
import Sidebar from '../components/Navigation/Sidebar';
import styles from './WorkspaceLayout.module.css';

export type ModuleType = 'dashboard' | 'kanban' | 'chat' | 'metrics' | 'settings';

interface WorkspaceLayoutProps {
  children: ReactNode;
  currentModule: ModuleType;
  onNavigate: (module: ModuleType) => void;
}

const moduleLabels: Record<ModuleType, string> = {
  dashboard: 'Dashboard',
  kanban: 'Kanban Board',
  chat: 'AI Assistant',
  metrics: 'Métricas',
  settings: 'Configurações',
};

const WorkspaceLayout = ({ children, currentModule, onNavigate }: WorkspaceLayoutProps) => {
  return (
    <div className={styles.workspace}>
      <Sidebar currentModule={currentModule} onNavigate={onNavigate} />
      <div className={styles.mainContent}>
        <header className={styles.header}>
          <div className={styles.breadcrumb}>
            <span className={styles.breadcrumbItem}>Workspace</span>
            <span className={styles.breadcrumbSeparator}>/</span>
            <span className={styles.breadcrumbItemActive}>{moduleLabels[currentModule]}</span>
          </div>
        </header>
        <main className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
};

export default WorkspaceLayout;
