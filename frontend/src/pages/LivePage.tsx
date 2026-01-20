import { useEffect, useState, useCallback } from 'react';
import { useLiveWebSocket } from '../hooks/useLiveWebSocket';
import { MissionControl } from '../components/Live/MissionControl';
import { RankingEntry } from '../components/Live/MissionControl/GameRanking';

export function LivePage() {
  // State for real-time ranking updates
  const [rankingUpdate, setRankingUpdate] = useState<{ entry: RankingEntry; rank: number } | null>(null);

  // Handle ranking update from WebSocket
  const handleGameRankingUpdate = useCallback((entry: RankingEntry, rank: number) => {
    setRankingUpdate({ entry, rank });
    // Clear after animation
    setTimeout(() => setRankingUpdate(null), 5000);
  }, []);

  // Connect to live WebSocket with ranking callback
  const { state, isConnected } = useLiveWebSocket({
    onGameRankingUpdate: handleGameRankingUpdate,
  });

  // Update page title with spectator count
  useEffect(() => {
    document.title = `AI Live Studio (${state.status.spectatorCount} watching)`;
    return () => {
      document.title = 'AI Live Studio';
    };
  }, [state.status.spectatorCount]);

  return (
    <MissionControl
      state={state}
      isConnected={isConnected}
      rankingUpdate={rankingUpdate}
    />
  );
}
