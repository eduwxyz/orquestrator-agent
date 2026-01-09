/**
 * API client for activity logs
 */
import { API_CONFIG } from './config';

export interface Activity {
  id: string;
  cardId: string;
  cardTitle: string;
  cardDescription?: string;
  type: 'created' | 'moved' | 'completed' | 'archived' | 'updated' | 'executed' | 'commented';
  timestamp: string;
  fromColumn?: string;
  toColumn?: string;
  oldValue?: string;
  newValue?: string;
  userId?: string;
  description?: string;
}

/**
 * Fetch recent activities from the API
 */
export const fetchRecentActivities = async (
  limit: number = 10,
  offset: number = 0
): Promise<Activity[]> => {
  const response = await fetch(
    `${API_CONFIG.BASE_URL}/api/activities/recent?limit=${limit}&offset=${offset}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch activities: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Fetch activities for a specific card
 */
export const fetchCardActivities = async (cardId: string): Promise<Activity[]> => {
  const response = await fetch(
    `${API_CONFIG.BASE_URL}/api/activities/card/${cardId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch card activities: ${response.statusText}`);
  }

  return response.json();
};
