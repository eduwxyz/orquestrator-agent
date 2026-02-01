import { useState, useCallback, useEffect } from 'react';
import { VotingState, VotingOption } from '../../../types/live';
import { API_ENDPOINTS } from '../../../api/config';
import styles from './VotingModal.module.css';

interface VotingModalProps {
  voting: VotingState;
  sessionId: string;
  onClose?: () => void;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function VotingModal({ voting, sessionId }: VotingModalProps) {
  const [votedFor, setVotedFor] = useState<string | null>(null);
  const [isVoting, setIsVoting] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [winner, setWinner] = useState<VotingOption | null>(null);

  // Reset state when voting becomes active again
  useEffect(() => {
    if (voting.isActive) {
      setVotedFor(null);
      setShowResults(false);
      setWinner(null);
    }
  }, [voting.roundId]);

  // Show results when voting ends
  useEffect(() => {
    if (!voting.isActive && voting.options.length > 0 && !showResults) {
      // Find winner (highest votes)
      const sorted = [...voting.options].sort((a, b) => b.voteCount - a.voteCount);
      if (sorted.length > 0) {
        setWinner(sorted[0]);
        setShowResults(true);

        // Hide after 5 seconds
        setTimeout(() => {
          setShowResults(false);
        }, 5000);
      }
    }
  }, [voting.isActive, voting.options, showResults]);

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

  // Calculate timer progress (60 seconds total)
  const timeRemaining = voting.timeRemainingSeconds || 0;
  const progress = (timeRemaining / 60) * 100;
  const totalVotes = voting.options.reduce((sum, opt) => sum + opt.voteCount, 0);

  // Don't render if voting is not active and not showing results
  if (!voting.isActive && !showResults) {
    return null;
  }

  // Show results modal
  if (showResults && winner) {
    return (
      <div className={styles.overlay}>
        <div className={styles.modal}>
          <div className={styles.resultsContent}>
            <div className={styles.winnerBadge}>🏆</div>
            <h2 className={styles.resultsTitle}>Votação Encerrada!</h2>
            <div className={styles.winnerCard}>
              <span className={styles.winnerTitle}>{winner.title}</span>
              <span className={styles.winnerVotes}>
                {winner.voteCount} {winner.voteCount === 1 ? 'voto' : 'votos'}
              </span>
            </div>
            <p className={styles.nextText}>Começando o projeto em breve...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* Header with timer */}
        <div className={styles.header}>
          <h2 className={styles.title}>🗳️ Vote no Próximo Projeto!</h2>
          <div className={styles.timerContainer}>
            <svg className={styles.timerSvg} viewBox="0 0 100 100">
              <circle
                className={styles.timerBg}
                cx="50"
                cy="50"
                r="45"
              />
              <circle
                className={styles.timerProgress}
                cx="50"
                cy="50"
                r="45"
                strokeDasharray={`${2 * Math.PI * 45}`}
                strokeDashoffset={`${2 * Math.PI * 45 * (1 - progress / 100)}`}
              />
            </svg>
            <span className={styles.timerText}>{formatTime(timeRemaining)}</span>
          </div>
        </div>

        {/* Voting options */}
        <div className={styles.options}>
          {voting.options.map((option) => {
            const percentage = totalVotes > 0
              ? Math.round((option.voteCount / totalVotes) * 100)
              : 0;
            const isVoted = votedFor === option.id;

            return (
              <button
                key={option.id}
                className={`${styles.option} ${isVoted ? styles.voted : ''} ${votedFor && !isVoted ? styles.notVoted : ''}`}
                onClick={() => handleVote(option.id)}
                disabled={!!votedFor || isVoting}
              >
                <div className={styles.optionHeader}>
                  <span className={styles.optionTitle}>{option.title}</span>
                  <span className={styles.optionVotes}>
                    {option.voteCount} {option.voteCount === 1 ? 'voto' : 'votos'}
                  </span>
                </div>
                {option.description && (
                  <span className={styles.optionDescription}>{option.description}</span>
                )}
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                {isVoted && <span className={styles.checkmark}>✓</span>}
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          {votedFor ? (
            <span className={styles.votedMessage}>✓ Seu voto foi registrado!</span>
          ) : (
            <span className={styles.helpText}>Clique em uma opção para votar</span>
          )}
          <span className={styles.totalVotes}>{totalVotes} votos no total</span>
        </div>
      </div>
    </div>
  );
}
