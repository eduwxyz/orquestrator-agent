import { useState, useEffect, useCallback } from 'react';
import styles from './AutoReactions.module.css';

interface Reaction {
  id: string;
  emoji: string;
  x: number;
  y: number;
}

interface AutoReactionsProps {
  trigger: 'success' | 'error' | 'start' | 'idle' | null;
}

const REACTION_SETS = {
  success: ['🔥', '✨', '🚀', '⭐', '💪', '🎉', '✅', '💯'],
  error: ['💀', '😱', '⚠️', '💥', '🔴', '❌', '😵', '🆘'],
  start: ['🚀', '⚡', '🎯', '🔥', '💫', '🌟', '🎬', '▶️'],
  idle: ['💤', '⏳', '🌙', '☕', '🔄'],
};

export function AutoReactions({ trigger }: AutoReactionsProps) {
  const [reactions, setReactions] = useState<Reaction[]>([]);

  const spawnReactions = useCallback((type: 'success' | 'error' | 'start' | 'idle') => {
    const emojis = REACTION_SETS[type];
    const count = type === 'idle' ? 3 : type === 'error' ? 8 : 12;

    const newReactions: Reaction[] = [];

    for (let i = 0; i < count; i++) {
      const emoji = emojis[Math.floor(Math.random() * emojis.length)];
      newReactions.push({
        id: `${Date.now()}-${i}`,
        emoji,
        x: 10 + Math.random() * 80, // 10-90% da tela
        y: 60 + Math.random() * 30, // Começa na parte inferior
      });
    }

    setReactions(prev => [...prev, ...newReactions]);

    // Remove após animação
    setTimeout(() => {
      setReactions(prev => prev.filter(r => !newReactions.find(nr => nr.id === r.id)));
    }, 3000);
  }, []);

  // Trigger reactions based on prop
  useEffect(() => {
    if (trigger) {
      spawnReactions(trigger);
    }
  }, [trigger, spawnReactions]);

  return (
    <div className={styles.container}>
      {reactions.map(reaction => (
        <div
          key={reaction.id}
          className={styles.reaction}
          style={{
            left: `${reaction.x}%`,
            bottom: `${reaction.y}%`,
          }}
        >
          {reaction.emoji}
        </div>
      ))}
    </div>
  );
}
