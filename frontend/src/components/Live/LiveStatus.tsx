import { LiveStatus as LiveStatusType } from '../../types/live';
import styles from './Live.module.css';

interface LiveStatusProps {
  status: LiveStatusType;
}

const STAGE_LABELS: Record<string, string> = {
  planning: 'Planning',
  implementing: 'Implementing',
  testing: 'Testing',
  review: 'Reviewing',
};

const STAGE_ICONS: Record<string, string> = {
  planning: '📝',
  implementing: '🔨',
  testing: '🧪',
  review: '🔍',
};

export function LiveStatusPanel({ status }: LiveStatusProps) {
  const { isWorking, currentStage, currentCard, progress } = status;

  return (
    <div className={styles.statusPanel}>
      <h3 className={styles.sectionTitle}>Current Status</h3>

      {isWorking && currentStage ? (
        <div className={styles.statusContent}>
          <div className={styles.statusStage}>
            <span className={styles.stageIcon}>{STAGE_ICONS[currentStage] || '⚙️'}</span>
            <span className={styles.stageLabel}>{STAGE_LABELS[currentStage] || currentStage}</span>
          </div>

          {currentCard && (
            <div className={styles.currentCard}>
              <span className={styles.cardTitle}>{currentCard.title}</span>
              {currentCard.description && (
                <span className={styles.cardDesc}>
                  {currentCard.description.slice(0, 100)}
                  {currentCard.description.length > 100 ? '...' : ''}
                </span>
              )}
            </div>
          )}

          {progress !== null && (
            <div className={styles.progressContainer}>
              <div
                className={styles.progressBar}
                style={{ width: `${progress}%` }}
              />
              <span className={styles.progressText}>{progress}%</span>
            </div>
          )}
        </div>
      ) : (
        <div className={styles.statusIdle}>
          <span className={styles.idleIcon}>💤</span>
          <span className={styles.idleText}>AI is idle</span>
          <span className={styles.idleSubtext}>Waiting for next task</span>
        </div>
      )}
    </div>
  );
}
