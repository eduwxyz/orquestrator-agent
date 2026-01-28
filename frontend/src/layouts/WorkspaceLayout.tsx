import { ReactNode } from 'react';
import TopNav from '../components/Navigation/TopNav';
import styles from './WorkspaceLayout.module.css';

export type ModuleType = 'dashboard' | 'kanban' | 'chat' | 'settings';

interface WorkspaceLayoutProps {
  children: ReactNode;
  currentModule: ModuleType;
  onNavigate: (module: ModuleType) => void;
}

const WorkspaceLayout = ({ children, currentModule, onNavigate }: WorkspaceLayoutProps) => {
  return (
    <div className={styles.workspace}>
      <TopNav currentModule={currentModule} onNavigate={onNavigate} />
      <main className={styles.content}>
        {children}
      </main>
    </div>
  );
};

export default WorkspaceLayout;
