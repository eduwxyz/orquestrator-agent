import { API_CONFIG } from './config';

export interface AutoCleanupSettings {
  enabled: boolean;
  cleanup_after_days: number;
}

export interface AutoCleanupResponse {
  success: boolean;
  settings: AutoCleanupSettings;
}

export interface UpdateAutoCleanupRequest {
  enabled?: boolean;
  cleanup_after_days?: number;
}

const SETTINGS_BASE_URL = `${API_CONFIG.BASE_URL}/api/settings`;

export async function getAutoCleanupSettings(): Promise<AutoCleanupSettings> {
  try {
    const response = await fetch(`${SETTINGS_BASE_URL}/auto-cleanup`);

    if (!response.ok) {
      throw new Error(`Failed to fetch auto-cleanup settings (HTTP ${response.status})`);
    }

    const data: AutoCleanupResponse = await response.json();
    return data.settings;
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error(
        `Não foi possível conectar ao servidor em ${API_CONFIG.BASE_URL}. ` +
        'Verifique se o backend está rodando.'
      );
    }
    throw error;
  }
}

export async function updateAutoCleanupSettings(
  settings: UpdateAutoCleanupRequest
): Promise<AutoCleanupSettings> {
  try {
    const response = await fetch(`${SETTINGS_BASE_URL}/auto-cleanup`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Failed to update auto-cleanup settings (HTTP ${response.status})`
      );
    }

    const data: AutoCleanupResponse = await response.json();
    return data.settings;
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error(
        `Não foi possível conectar ao servidor em ${API_CONFIG.BASE_URL}. ` +
        'Verifique se o backend está rodando.'
      );
    }
    throw error;
  }
}
