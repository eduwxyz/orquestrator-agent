import { useEffect } from 'react';
import { useLiveWebSocket } from '../hooks/useLiveWebSocket';
import { MissionControl } from '../components/Live/MissionControl';

export function LivePage() {
  // Connect to live WebSocket
  const { state, isConnected } = useLiveWebSocket();

  // Update page title with spectator count
  useEffect(() => {
    document.title = `AI Live Studio (${state.status.spectatorCount} watching)`;
    return () => {
      document.title = 'AI Live Studio';
    };
  }, [state.status.spectatorCount]);

  return <MissionControl state={state} isConnected={isConnected} />;
}
