import { useState, useCallback } from 'react';
import { VotingState } from '../../types/live';
import { API_ENDPOINTS } from '../../api/config';
import styles from './Live.module.css';

interface VotingPanelProps {
  voting: VotingState;
  sessionId: string;
}

const CATEGORY_ICONS: Record<string, string> = {
  game: '🎮',
  app: '📱',
  site: '🌐',
  tool: '🔧',
};

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function VotingPanel({ voting, sessionId }: VotingPanelProps) {
  const [votedFor, setVotedFor] = useState<string | null>(null);
  const [isVoting, setIsVoting] = useState(false);

  const handleVote = useCallback(async (optionId: string) => {
    if (votedFor || isVoting) return;

    setIsVoting(true);
    try {
      const response = await fetch(API_ENDPOINTS.live.vote, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          option_id: optionId,
          session_id: sessionId,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setVotedFor(optionId);
      }
    } catch (error) {
      console.error('Failed to vote:', error);
    } finally {
      setIsVoting(false);
    }
  }, [votedFor, isVoting, sessionId]);

  if (!voting.isActive) {
    return (
      <div className={styles.votingPanel}>
        <h3 className={styles.sectionTitle}>
          <span className={styles.votingIcon}>🗳</span>
          Voting
        </h3>
        <div className={styles.votingInactive}>
          <span className={styles.votingInactiveIcon}>⏳</span>
          <span>Voting will start when AI finishes current project</span>
        </div>
      </div>
    );
  }

  const totalVotes = voting.options.reduce((sum, opt) => sum + opt.voteCount, 0);

  return (
    <div className={styles.votingPanel}>
      <div className={styles.votingHeader}>
        <h3 className={styles.sectionTitle}>
          <span className={styles.votingIcon}>🗳</span>
          Vote for Next Project
        </h3>
        <div className={styles.votingTimer}>
          <span className={styles.timerIcon}>⏱</span>
          <span className={styles.timerText}>
            {formatTime(voting.timeRemainingSeconds || 0)}
          </span>
        </div>
      </div>

      <div className={styles.votingOptions}>
        {voting.options.map(option => {
          const percentage = totalVotes > 0
            ? Math.round((option.voteCount / totalVotes) * 100)
            : 0;
          const isVoted = votedFor === option.id;

          return (
            <button
              key={option.id}
              className={`${styles.votingOption} ${isVoted ? styles.voted : ''} ${votedFor && !isVoted ? styles.notVoted : ''}`}
              onClick={() => handleVote(option.id)}
              disabled={!!votedFor || isVoting}
            >
              <div className={styles.optionContent}>
                <span className={styles.optionIcon}>
                  {CATEGORY_ICONS[option.category || ''] || '📦'}
                </span>
                <span className={styles.optionTitle}>{option.title}</span>
                <span className={styles.optionVotes}>{option.voteCount}</span>
              </div>
              <div
                className={styles.optionBar}
                style={{ width: `${percentage}%` }}
              />
            </button>
          );
        })}
      </div>

      {votedFor && (
        <div className={styles.votedMessage}>
          ✓ You voted! Waiting for results...
        </div>
      )}
    </div>
  );
}
