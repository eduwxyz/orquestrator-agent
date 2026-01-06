/**
 * Git API client for branch operations
 */
import { API_CONFIG } from './config';

export interface GitBranch {
  name: string;
  type: 'local' | 'remote';
}

export interface BranchesResponse {
  success: boolean;
  branches: GitBranch[];
  defaultBranch: string;
}

export async function fetchGitBranches(): Promise<BranchesResponse> {
  const response = await fetch(`${API_CONFIG.BASE_URL}/api/git/branches`);

  if (!response.ok) {
    throw new Error(`Failed to fetch branches: ${response.statusText}`);
  }

  return response.json();
}
