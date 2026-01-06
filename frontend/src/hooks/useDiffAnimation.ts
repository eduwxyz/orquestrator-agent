import { useState, useEffect, useCallback } from 'react';
import type { DiffStats } from '../types';

export type AnimationState = 'idle' | 'playing' | 'paused' | 'completed';
export type AnimationFrame = 'init' | 'files_added' | 'files_modified' | 'files_removed' | 'line_stats' | 'complete';

interface UseDiffAnimationReturn {
  animationState: AnimationState;
  currentFrame: AnimationFrame;
  frameIndex: number;
  play: () => void;
  pause: () => void;
  reset: () => void;
  isFrameVisible: (frame: AnimationFrame) => boolean;
}

const FRAME_SEQUENCE: AnimationFrame[] = [
  'init',
  'files_added',
  'files_modified',
  'files_removed',
  'line_stats',
  'complete'
];

const FRAME_DURATION = 800; // milliseconds per frame

export function useDiffAnimation(diffStats: DiffStats | null | undefined): UseDiffAnimationReturn {
  const [animationState, setAnimationState] = useState<AnimationState>('idle');
  const [frameIndex, setFrameIndex] = useState<number>(0);
  const [currentFrame, setCurrentFrame] = useState<AnimationFrame>('init');

  const play = useCallback(() => {
    if (!diffStats) return;

    if (animationState === 'idle' || animationState === 'completed') {
      setFrameIndex(0);
      setCurrentFrame('init');
    }
    setAnimationState('playing');
  }, [diffStats, animationState]);

  const pause = useCallback(() => {
    setAnimationState('paused');
  }, []);

  const reset = useCallback(() => {
    setAnimationState('idle');
    setFrameIndex(0);
    setCurrentFrame('init');
  }, []);

  const isFrameVisible = useCallback((frame: AnimationFrame): boolean => {
    const targetIndex = FRAME_SEQUENCE.indexOf(frame);
    return frameIndex >= targetIndex;
  }, [frameIndex]);

  // Auto-play animation when diff stats are available
  useEffect(() => {
    if (diffStats && animationState === 'idle') {
      // Small delay before starting
      const timer = setTimeout(() => {
        play();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [diffStats, animationState, play]);

  // Animation frame progression
  useEffect(() => {
    if (animationState !== 'playing') return;

    const timer = setTimeout(() => {
      const nextIndex = frameIndex + 1;

      if (nextIndex >= FRAME_SEQUENCE.length) {
        setAnimationState('completed');
        return;
      }

      setFrameIndex(nextIndex);
      setCurrentFrame(FRAME_SEQUENCE[nextIndex]);
    }, FRAME_DURATION);

    return () => clearTimeout(timer);
  }, [animationState, frameIndex]);

  return {
    animationState,
    currentFrame,
    frameIndex,
    play,
    pause,
    reset,
    isFrameVisible,
  };
}
