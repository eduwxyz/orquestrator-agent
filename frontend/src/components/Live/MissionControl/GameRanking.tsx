import { useEffect, useState } from 'react';
import styles from './GameRanking.module.css';

export interface RankingEntry {
  id: string;
  playerName: string;
  score: number;
  gameType: string;
  createdAt: string;
  isNew?: boolean;
}

interface GameRankingProps {
  ranking: RankingEntry[];
  currentPlayerName?: string;
  highlightScore?: number;
}

export function GameRanking({ ranking, currentPlayerName, highlightScore }: GameRankingProps) {
  const [animatedEntries, setAnimatedEntries] = useState<Set<string>>(new Set());

  // Animate new entries
  useEffect(() => {
    const newEntries = ranking.filter(entry => entry.isNew).map(entry => entry.id);
    if (newEntries.length > 0) {
      setAnimatedEntries(new Set(newEntries));
      // Remove animation flag after animation completes
      const timer = setTimeout(() => {
        setAnimatedEntries(new Set());
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [ranking]);

  const getMedalEmoji = (position: number): string => {
    switch (position) {
      case 1:
        return '🥇';
      case 2:
        return '🥈';
      case 3:
        return '🥉';
      default:
        return '';
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'agora';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.headerIcon}>🏆</span>
        <span className={styles.headerTitle}>RANKING</span>
      </div>

      <div className={styles.list}>
        {ranking.length === 0 ? (
          <div className={styles.emptyState}>
            <span className={styles.emptyIcon}>🎮</span>
            <span className={styles.emptyText}>Seja o primeiro!</span>
          </div>
        ) : (
          ranking.slice(0, 10).map((entry, index) => {
            const position = index + 1;
            const isCurrentPlayer = entry.playerName === currentPlayerName;
            const isHighlighted = highlightScore !== undefined && entry.score === highlightScore && isCurrentPlayer;
            const isAnimated = animatedEntries.has(entry.id);

            return (
              <div
                key={entry.id}
                className={`
                  ${styles.entry}
                  ${position <= 3 ? styles.topThree : ''}
                  ${isCurrentPlayer ? styles.currentPlayer : ''}
                  ${isHighlighted ? styles.highlighted : ''}
                  ${isAnimated ? styles.newEntry : ''}
                `}
              >
                <div className={styles.position}>
                  {position <= 3 ? (
                    <span className={styles.medal}>{getMedalEmoji(position)}</span>
                  ) : (
                    <span className={styles.positionNumber}>{position}</span>
                  )}
                </div>

                <div className={styles.playerInfo}>
                  <span className={styles.playerName}>
                    {entry.playerName}
                    {isCurrentPlayer && <span className={styles.youBadge}>you</span>}
                  </span>
                  <span className={styles.timestamp}>{formatDate(entry.createdAt)}</span>
                </div>

                <div className={styles.score}>
                  {entry.score}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
