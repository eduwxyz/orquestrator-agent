import { useEffect, useState } from 'react';
import { fetchRecentActivities, Activity } from '../../api/activities';
import styles from './ActivityFeed.module.css';

interface ActivityFeedProps {
  maxItems?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

type ActivityType = 'created' | 'moved' | 'completed' | 'archived' | 'updated' | 'executed' | 'commented';

// Ícones SVG inline para cada tipo de atividade
const ActivityIcon = ({ type }: { type: ActivityType }) => {
  switch (type) {
    case 'created':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    case 'moved':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    case 'completed':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 8L6.5 11.5L13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    case 'archived':
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M2 5H14M3 5V13C3 13.5523 3.44772 14 4 14H12C12.5523 14 13 13.5523 13 13V5M5.5 8H10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M5 5V3C5 2.44772 5.44772 2 6 2H10C10.5523 2 11 2.44772 11 3V5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
  }
};

const ActivityFeed = ({
  maxItems = 10,
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
}: ActivityFeedProps) => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadActivities = async () => {
    try {
      const data = await fetchRecentActivities(maxItems);
      setActivities(data);
      setError(null);
    } catch (err) {
      setError('Falha ao carregar atividades');
      console.error('Error loading activities:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();

    // Auto-refresh if enabled
    if (autoRefresh) {
      const interval = setInterval(loadActivities, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [maxItems, autoRefresh, refreshInterval]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'agora mesmo';
    if (diffMins < 60) return `há ${diffMins} min`;
    if (diffHours < 24) return `há ${diffHours}h`;
    if (diffDays < 7) return `há ${diffDays}d`;

    return date.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' });
  };

  const getActivityColor = (type: ActivityType) => {
    switch (type) {
      case 'created': return 'blue';
      case 'moved': return 'amber';
      case 'completed': return 'green';
      case 'archived': return 'purple';
      default: return 'cyan';
    }
  };

  const getActivityText = (activity: Activity) => {
    switch (activity.type) {
      case 'created':
        return 'foi criado';
      case 'moved':
        return `foi movido para ${activity.toColumn}`;
      case 'completed':
        return 'foi concluído';
      case 'archived':
        return 'foi arquivado';
      case 'updated':
        return 'foi atualizado';
      case 'executed':
        return 'foi executado';
      case 'commented':
        return 'recebeu comentário';
      default:
        return 'foi modificado';
    }
  };

  if (isLoading) {
    return (
      <div className={styles.activityFeed}>
        <div className={styles.header}>
          <h3 className={styles.title}>Atividade Recente</h3>
        </div>
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>Carregando atividades...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.activityFeed}>
        <div className={styles.header}>
          <h3 className={styles.title}>Atividade Recente</h3>
        </div>
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>{error}</p>
        </div>
      </div>
    );
  }

  if (activities.length === 0) {
    return (
      <div className={styles.activityFeed}>
        <div className={styles.header}>
          <h3 className={styles.title}>Atividade Recente</h3>
        </div>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 8V12L15 15M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p className={styles.emptyText}>Nenhuma atividade recente</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.activityFeed}>
      <div className={styles.header}>
        <h3 className={styles.title}>Atividade Recente</h3>
        <span className={styles.badge}>{activities.length}</span>
      </div>

      <div className={styles.timeline}>
        {activities.map((activity, index) => (
          <div
            key={activity.id}
            className={styles.activityItem}
            style={{
              animationDelay: `${index * 50}ms`,
            }}
          >
            <div className={`${styles.iconContainer} ${styles[`color-${getActivityColor(activity.type)}`]}`}>
              <ActivityIcon type={activity.type} />
            </div>

            <div className={styles.content}>
              <div className={styles.activityText}>
                <span className={styles.cardName}>{activity.cardTitle}</span>
                {' '}
                <span className={styles.actionText}>{getActivityText(activity)}</span>
              </div>
              <time className={styles.timestamp}>{formatTimestamp(activity.timestamp)}</time>
            </div>

            {index < activities.length - 1 && <div className={styles.connector} />}
          </div>
        ))}
      </div>

      <button className={styles.viewAllButton}>
        <span>Ver todo histórico</span>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
    </div>
  );
};

export default ActivityFeed;
