import { API_ENDPOINTS, API_CONFIG } from './config';
import { Project } from '../types';

export async function loadProject(projectPath: string): Promise<void> {
  try {
    const response = await fetch(API_ENDPOINTS.projects.load, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ path: projectPath }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail ||
        `Falha ao carregar projeto (HTTP ${response.status})`
      );
    }
  } catch (error) {
    // Melhor tratamento de erro de conexão
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error(
        `Não foi possível conectar ao servidor em ${API_CONFIG.BASE_URL}. ` +
        'Verifique se o backend está rodando (make backend).'
      );
    }
    throw error;
  }
}

export async function getCurrentProject(): Promise<Project | null> {
  try {
    const response = await fetch(API_ENDPOINTS.projects.current);

    if (!response.ok) {
      if (response.status === 404) {
        return null; // Nenhum projeto carregado
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      console.error(
        `[getCurrentProject] Backend não está acessível em ${API_CONFIG.BASE_URL}`
      );
      throw new Error('Backend não está rodando. Execute "make backend" no terminal.');
    }
    throw error;
  }
}

export async function getRecentProjects(filterType: 'recent' | 'favorites' = 'recent', limit: number = 10): Promise<Project[]> {
  try {
    const url = `${API_ENDPOINTS.projects.recent}?filter_type=${filterType}&limit=${limit}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data.projects || [];
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      console.error(
        `[getRecentProjects] Backend não está acessível em ${API_CONFIG.BASE_URL}`
      );
      return []; // Retornar lista vazia se backend não estiver disponível
    }
    throw error;
  }
}

export async function toggleFavorite(projectId: string): Promise<{ success: boolean; isFavorite: boolean }> {
  try {
    const response = await fetch(`${API_CONFIG.BASE_URL}/api/projects/${projectId}/favorite`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error('Backend não está rodando. Execute "make backend" no terminal.');
    }
    throw error;
  }
}

export async function quickSwitchProject(projectPath: string): Promise<Project> {
  try {
    const response = await fetch(`${API_CONFIG.BASE_URL}/api/projects/quick-switch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ path: projectPath }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Falha ao trocar projeto (HTTP ${response.status})`
      );
    }

    const data = await response.json();
    return data.project;
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error(
        `Não foi possível conectar ao servidor em ${API_CONFIG.BASE_URL}. ` +
        'Verifique se o backend está rodando (make backend).'
      );
    }
    throw error;
  }
}