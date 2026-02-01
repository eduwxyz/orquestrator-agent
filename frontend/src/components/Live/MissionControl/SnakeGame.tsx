import { useRef, useEffect, useState, useCallback } from 'react';
import styles from './SnakeGame.module.css';

interface SnakeGameProps {
  onGameOver: (score: number) => void;
  onScoreChange?: (score: number) => void;
  playerName?: string;
  onChangeName?: () => void;
  lastSaveResult?: { success: boolean; rank?: number; message?: string } | null;
}

interface Point {
  x: number;
  y: number;
}

type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT';

const GRID_SIZE = 20;
const CELL_SIZE = 15;
const INITIAL_SPEED = 150;
const SPEED_INCREMENT = 5;
const MIN_SPEED = 50;

export function SnakeGame({ onGameOver, onScoreChange, playerName, onChangeName, lastSaveResult }: SnakeGameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'paused' | 'gameover'>('idle');
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() => {
    const saved = localStorage.getItem('snake_high_score');
    return saved ? parseInt(saved, 10) : 0;
  });

  // Game state refs (to avoid stale closures in game loop)
  const snakeRef = useRef<Point[]>([{ x: 10, y: 10 }]);
  const directionRef = useRef<Direction>('RIGHT');
  const nextDirectionRef = useRef<Direction>('RIGHT');
  const foodRef = useRef<Point>({ x: 15, y: 10 });
  const speedRef = useRef(INITIAL_SPEED);
  const gameLoopRef = useRef<number | null>(null);
  const lastUpdateRef = useRef(0);

  const generateFood = useCallback((): Point => {
    const snake = snakeRef.current;
    let newFood: Point;
    do {
      newFood = {
        x: Math.floor(Math.random() * GRID_SIZE),
        y: Math.floor(Math.random() * GRID_SIZE),
      };
    } while (snake.some(segment => segment.x === newFood.x && segment.y === newFood.y));
    return newFood;
  }, []);

  const resetGame = useCallback(() => {
    snakeRef.current = [{ x: 10, y: 10 }];
    directionRef.current = 'RIGHT';
    nextDirectionRef.current = 'RIGHT';
    foodRef.current = generateFood();
    speedRef.current = INITIAL_SPEED;
    setScore(0);
  }, [generateFood]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const snake = snakeRef.current;
    const food = foodRef.current;

    // Clear canvas
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid (subtle)
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= GRID_SIZE; i++) {
      ctx.beginPath();
      ctx.moveTo(i * CELL_SIZE, 0);
      ctx.lineTo(i * CELL_SIZE, GRID_SIZE * CELL_SIZE);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * CELL_SIZE);
      ctx.lineTo(GRID_SIZE * CELL_SIZE, i * CELL_SIZE);
      ctx.stroke();
    }

    // Draw food
    ctx.fillStyle = '#ef4444';
    ctx.shadowColor = '#ef4444';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(
      food.x * CELL_SIZE + CELL_SIZE / 2,
      food.y * CELL_SIZE + CELL_SIZE / 2,
      CELL_SIZE / 2 - 2,
      0,
      Math.PI * 2
    );
    ctx.fill();
    ctx.shadowBlur = 0;

    // Draw snake
    snake.forEach((segment, index) => {
      const isHead = index === 0;
      const gradient = ctx.createLinearGradient(
        segment.x * CELL_SIZE,
        segment.y * CELL_SIZE,
        (segment.x + 1) * CELL_SIZE,
        (segment.y + 1) * CELL_SIZE
      );

      if (isHead) {
        gradient.addColorStop(0, '#22c55e');
        gradient.addColorStop(1, '#22d3ee');
        ctx.shadowColor = '#22c55e';
        ctx.shadowBlur = 8;
      } else {
        const alpha = 1 - (index / snake.length) * 0.5;
        ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
        ctx.shadowBlur = 0;
      }

      ctx.fillStyle = isHead ? gradient : ctx.fillStyle;
      ctx.fillRect(
        segment.x * CELL_SIZE + 1,
        segment.y * CELL_SIZE + 1,
        CELL_SIZE - 2,
        CELL_SIZE - 2
      );

      // Draw eyes on head
      if (isHead) {
        ctx.shadowBlur = 0;
        ctx.fillStyle = '#0d1117';
        const eyeSize = 3;
        const eyeOffset = 4;

        let eye1X = segment.x * CELL_SIZE + eyeOffset;
        let eye1Y = segment.y * CELL_SIZE + eyeOffset;
        let eye2X = segment.x * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
        let eye2Y = segment.y * CELL_SIZE + eyeOffset;

        if (directionRef.current === 'DOWN') {
          eye1Y = segment.y * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
          eye2Y = segment.y * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
        } else if (directionRef.current === 'LEFT') {
          eye1X = segment.x * CELL_SIZE + eyeOffset;
          eye2X = segment.x * CELL_SIZE + eyeOffset;
          eye1Y = segment.y * CELL_SIZE + eyeOffset;
          eye2Y = segment.y * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
        } else if (directionRef.current === 'RIGHT') {
          eye1X = segment.x * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
          eye2X = segment.x * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
          eye1Y = segment.y * CELL_SIZE + eyeOffset;
          eye2Y = segment.y * CELL_SIZE + CELL_SIZE - eyeOffset - eyeSize;
        }

        ctx.fillRect(eye1X, eye1Y, eyeSize, eyeSize);
        ctx.fillRect(eye2X, eye2Y, eyeSize, eyeSize);
      }
    });

    ctx.shadowBlur = 0;
  }, []);

  const update = useCallback(() => {
    const snake = snakeRef.current;
    const food = foodRef.current;

    // Update direction
    directionRef.current = nextDirectionRef.current;

    // Calculate new head position
    const head = { ...snake[0] };
    switch (directionRef.current) {
      case 'UP':
        head.y -= 1;
        break;
      case 'DOWN':
        head.y += 1;
        break;
      case 'LEFT':
        head.x -= 1;
        break;
      case 'RIGHT':
        head.x += 1;
        break;
    }

    // Check wall collision
    if (head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE) {
      return false;
    }

    // Check self collision
    if (snake.some(segment => segment.x === head.x && segment.y === head.y)) {
      return false;
    }

    // Move snake
    snake.unshift(head);

    // Check food collision
    if (head.x === food.x && head.y === food.y) {
      const newScore = score + 10;
      setScore(newScore);
      onScoreChange?.(newScore);
      foodRef.current = generateFood();

      // Increase speed
      if (speedRef.current > MIN_SPEED) {
        speedRef.current = Math.max(MIN_SPEED, speedRef.current - SPEED_INCREMENT);
      }
    } else {
      snake.pop();
    }

    return true;
  }, [score, generateFood, onScoreChange]);

  const gameLoop = useCallback((timestamp: number) => {
    if (gameState !== 'playing') return;

    const elapsed = timestamp - lastUpdateRef.current;

    if (elapsed >= speedRef.current) {
      lastUpdateRef.current = timestamp;

      const isAlive = update();
      if (!isAlive) {
        setGameState('gameover');

        // Update high score
        if (score > highScore) {
          setHighScore(score);
          localStorage.setItem('snake_high_score', score.toString());
        }

        onGameOver(score);
        return;
      }
    }

    draw();
    gameLoopRef.current = requestAnimationFrame(gameLoop);
  }, [gameState, update, draw, score, highScore, onGameOver]);

  const startGame = useCallback(() => {
    resetGame();
    setGameState('playing');
    lastUpdateRef.current = performance.now();
  }, [resetGame]);

  const togglePause = useCallback(() => {
    if (gameState === 'playing') {
      setGameState('paused');
    } else if (gameState === 'paused') {
      setGameState('playing');
      lastUpdateRef.current = performance.now();
    }
  }, [gameState]);

  // Handle keyboard input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Prevent scrolling
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
        e.preventDefault();
      }

      if (gameState === 'idle' || gameState === 'gameover') {
        if (e.key === ' ' || e.key === 'Enter') {
          startGame();
        }
        return;
      }

      if (e.key === ' ' || e.key === 'Escape') {
        togglePause();
        return;
      }

      if (gameState !== 'playing') return;

      const currentDir = directionRef.current;

      switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
          if (currentDir !== 'DOWN') nextDirectionRef.current = 'UP';
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          if (currentDir !== 'UP') nextDirectionRef.current = 'DOWN';
          break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
          if (currentDir !== 'RIGHT') nextDirectionRef.current = 'LEFT';
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          if (currentDir !== 'LEFT') nextDirectionRef.current = 'RIGHT';
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameState, startGame, togglePause]);

  // Game loop effect
  useEffect(() => {
    if (gameState === 'playing') {
      gameLoopRef.current = requestAnimationFrame(gameLoop);
    }

    return () => {
      if (gameLoopRef.current) {
        cancelAnimationFrame(gameLoopRef.current);
      }
    };
  }, [gameState, gameLoop]);

  // Initial draw
  useEffect(() => {
    draw();
  }, [draw]);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.scoreContainer}>
          <span className={styles.scoreLabel}>SCORE</span>
          <span className={styles.scoreValue}>{score}</span>
        </div>
        <div className={styles.playerContainer}>
          {playerName ? (
            <button className={styles.playerName} onClick={onChangeName} title="Clique para trocar">
              {playerName}
            </button>
          ) : (
            <span className={styles.noPlayer}>Sem nome</span>
          )}
        </div>
        <div className={styles.highScoreContainer}>
          <span className={styles.highScoreLabel}>BEST</span>
          <span className={styles.highScoreValue}>{highScore}</span>
        </div>
      </div>

      {/* Toast de feedback */}
      {lastSaveResult && (
        <div className={`${styles.toast} ${lastSaveResult.success ? styles.toastSuccess : styles.toastError}`}>
          {lastSaveResult.success
            ? `Salvo! Rank #${lastSaveResult.rank}`
            : lastSaveResult.message || 'Erro ao salvar'}
        </div>
      )}

      <div className={styles.gameArea}>
        <canvas
          ref={canvasRef}
          width={GRID_SIZE * CELL_SIZE}
          height={GRID_SIZE * CELL_SIZE}
          className={styles.canvas}
        />

        {gameState === 'idle' && (
          <div className={styles.overlay}>
            <div className={styles.overlayContent}>
              <span className={styles.snakeEmoji}>🐍</span>
              <span className={styles.overlayTitle}>SNAKE</span>
              <span className={styles.overlayHint}>Press SPACE to start</span>
              <span className={styles.overlayControls}>Arrow keys or WASD to move</span>
            </div>
          </div>
        )}

        {gameState === 'paused' && (
          <div className={styles.overlay}>
            <div className={styles.overlayContent}>
              <span className={styles.overlayTitle}>PAUSED</span>
              <span className={styles.overlayHint}>Press SPACE to continue</span>
            </div>
          </div>
        )}

        {gameState === 'gameover' && (
          <div className={styles.overlay}>
            <div className={styles.overlayContent}>
              <span className={styles.overlayTitle}>GAME OVER</span>
              <span className={styles.finalScore}>Score: {score}</span>
              {score > 0 && score >= highScore && (
                <span className={styles.newRecord}>NEW RECORD!</span>
              )}
              <span className={styles.overlayHint}>Press SPACE to play again</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
