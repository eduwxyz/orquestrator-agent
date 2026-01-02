/**
 * Configuração centralizada de APIs
 */
export const API_CONFIG = {
  // URL base do backend - usar variável de ambiente ou padrão
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:3001',

  // Timeouts padrão
  TIMEOUT: 30000,

  // Retry configuration
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
} as const;

// Endpoints específicos
export const API_ENDPOINTS = {
  // Cards
  cards: `${API_CONFIG.BASE_URL}/api/cards`,

  // Projects
  projects: {
    load: `${API_CONFIG.BASE_URL}/api/projects/load`,
    current: `${API_CONFIG.BASE_URL}/api/projects/current`,
    recent: `${API_CONFIG.BASE_URL}/api/projects/recent`,
  },

  // Images
  images: `${API_CONFIG.BASE_URL}/api/images`,

  // Agent
  agent: {
    stream: `${API_CONFIG.BASE_URL}/api/cards`,
  },

  // Logs
  logs: `${API_CONFIG.BASE_URL}/api/logs`,

  // Execution endpoints
  execution: {
    plan: `${API_CONFIG.BASE_URL}/api/execute-plan`,
    implement: `${API_CONFIG.BASE_URL}/api/execute-implement`,
    test: `${API_CONFIG.BASE_URL}/api/execute-test`,
    review: `${API_CONFIG.BASE_URL}/api/execute-review`,
  },
} as const;