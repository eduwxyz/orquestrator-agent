import { ModuleType } from '../../layouts/WorkspaceLayout';
import styles from './TopNav.module.css';

interface TopNavProps {
  currentModule: ModuleType;
  onNavigate: (module: ModuleType) => void;
}

const navItems: { id: ModuleType; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'kanban', label: 'Workflow' },
  { id: 'chat', label: 'Chat' },
  { id: 'settings', label: 'Settings' },
];

const TopNav = ({ currentModule, onNavigate }: TopNavProps) => {
  return (
    <nav className={styles.topnav}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
          </svg>
        </div>
        <span className={styles.logoText}>Zenflow</span>
      </div>

      <div className={styles.navCenter}>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`${styles.navLink} ${currentModule === item.id ? styles.active : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className={styles.navRight}>
        <button className={styles.iconBtn} title="Search — ⌘K">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </button>
        <button className={styles.iconBtn} title="Notifications">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span className={styles.notifDot}></span>
        </button>
        <div className={styles.avatar}>E</div>
      </div>
    </nav>
  );
};

export default TopNav;
