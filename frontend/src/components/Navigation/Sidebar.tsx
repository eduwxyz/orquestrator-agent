import { ModuleType } from '../../layouts/WorkspaceLayout';
import { ThemeToggle } from '../ThemeToggle/ThemeToggle';
import styles from './Sidebar.module.css';

interface NavigationItem {
  id: ModuleType;
  label: string;
  icon: string;
  description: string;
}

const navigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: 'fa-solid fa-chart-line',
    description: 'Visão geral do projeto',
  },
  {
    id: 'kanban',
    label: 'Kanban Board',
    icon: 'fa-solid fa-table-columns',
    description: 'Gerenciar tarefas e workflow',
  },
  {
    id: 'chat',
    label: 'AI Assistant',
    icon: 'fa-solid fa-comments',
    description: 'Chat com assistente AI',
  },
  {
    id: 'metrics',
    label: 'Métricas',
    icon: 'fa-solid fa-chart-bar',
    description: 'Analytics e performance',
  },
  {
    id: 'settings',
    label: 'Configurações',
    icon: 'fa-solid fa-gear',
    description: 'Preferências do projeto',
  },
];

interface SidebarProps {
  currentModule: ModuleType;
  onNavigate: (module: ModuleType) => void;
}

const Sidebar = ({ currentModule, onNavigate }: SidebarProps) => {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>
            <i className="fa-solid fa-rocket"></i>
          </span>
          <h2 className={styles.logoText}>Workspace</h2>
        </div>
      </div>

      <nav className={styles.nav}>
        <ul className={styles.navList}>
          {navigationItems.map((item) => (
            <li key={item.id}>
              <button
                className={`${styles.navItem} ${
                  currentModule === item.id ? styles.navItemActive : ''
                }`}
                onClick={() => onNavigate(item.id)}
                aria-current={currentModule === item.id ? 'page' : undefined}
              >
                <span className={styles.navIcon}>
                  <i className={item.icon}></i>
                </span>
                <div className={styles.navContent}>
                  <span className={styles.navLabel}>{item.label}</span>
                  <span className={styles.navDescription}>{item.description}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className={styles.footer}>
        <ThemeToggle />
        <div className={styles.footerInfo}>
          <span className={styles.footerLabel}>Orquestrator Agent</span>
          <span className={styles.footerVersion}>v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
