# Plano de Implementação: Correção de Conexão do Project Loader

**Tipo:** Bug Fix
**Prioridade:** Alta
**Criado em:** 2025-01-03

## 1. Resumo

Corrigir erro de conexão `ERR_CONNECTION_REFUSED` no componente Project Loader do frontend, que está tentando conectar na porta 8000 enquanto o backend está rodando apenas na porta 3001. O problema impede o carregamento de projetos através da interface.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Alinhar as portas de conexão entre frontend e backend para o módulo de projects
- [x] Garantir que todas as funcionalidades de projetos funcionem corretamente
- [x] Padronizar a configuração de API URLs no frontend
- [x] Adicionar tratamento de erros mais informativo para problemas de conexão

### Fora do Escopo
- Refatoração completa da arquitetura de comunicação frontend-backend
- Criação de múltiplas instâncias de backend
- Alteração da estrutura de rotas existentes

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/api/projects.ts` | Modificar | Corrigir porta de 8000 para 3001 |
| `frontend/.env.example` | Criar | Adicionar variável de ambiente padrão |
| `frontend/.env` | Criar | Configurar variável de ambiente local |
| `frontend/src/api/config.ts` | Criar | Centralizar configuração de API |
| `frontend/src/components/ProjectLoader/ProjectLoader.tsx` | Modificar | Melhorar tratamento de erros |
| `frontend/src/App.tsx` | Modificar | Melhorar mensagens de erro |

### Detalhes Técnicos

#### 1. **Correção Imediata da Porta (frontend/src/api/projects.ts)**

```typescript
// ANTES (linha 3)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// DEPOIS
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';
```

#### 2. **Criação de Configuração Centralizada (frontend/src/api/config.ts)**

```typescript
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
} as const;
```

#### 3. **Atualização dos Imports de API (frontend/src/api/projects.ts)**

```typescript
import { API_ENDPOINTS, API_CONFIG } from './config';

export interface Project {
  name: string;
  path: string;
  timestamp?: string;
}

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

export async function getRecentProjects(): Promise<Project[]> {
  try {
    const response = await fetch(API_ENDPOINTS.projects.recent);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
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
```

#### 4. **Melhoria no Tratamento de Erros (frontend/src/components/ProjectLoader/ProjectLoader.tsx)**

```typescript
// Adicionar ao handleLoadProject (linha 31)
const handleLoadProject = async () => {
  if (!projectPath.trim()) {
    setError('Por favor, insira o caminho do projeto');
    return;
  }

  setIsLoading(true);
  setError(null);

  try {
    await loadProject(projectPath);
    onProjectLoaded();
    onClose();
  } catch (err) {
    console.error('Erro ao carregar projeto:', err);

    // Mensagens de erro mais específicas
    if (err instanceof Error) {
      if (err.message.includes('Backend não está rodando')) {
        setError(
          'Servidor não está rodando. ' +
          'Por favor, execute "make backend" em outro terminal.'
        );
      } else if (err.message.includes('não foi possível conectar')) {
        setError(
          'Não foi possível conectar ao servidor. ' +
          'Verifique se o backend está rodando na porta 3001.'
        );
      } else {
        setError(err.message);
      }
    } else {
      setError('Erro desconhecido ao carregar projeto');
    }
  } finally {
    setIsLoading(false);
  }
};
```

#### 5. **Configuração de Variáveis de Ambiente (frontend/.env.example)**

```env
# URL base da API do backend
# Por padrão usa localhost:3001
# Sobrescreva se o backend estiver em outra porta/host
VITE_API_URL=http://localhost:3001

# Outras configurações opcionais
VITE_APP_TITLE=Orquestrator Agent
VITE_DEBUG=false
```

#### 6. **Atualização do arquivo cards.ts para usar config centralizada**

```typescript
// frontend/src/api/cards.ts
import { API_ENDPOINTS } from './config';

// Remover a linha antiga:
// const API_BASE = 'http://localhost:3001/api';

// Atualizar todas as referências para usar API_ENDPOINTS.cards
export async function fetchCards(tag?: string): Promise<Card[]> {
  const url = tag
    ? `${API_ENDPOINTS.cards}?tag=${encodeURIComponent(tag)}`
    : API_ENDPOINTS.cards;

  const response = await fetch(url);
  // ... resto do código
}
```

---

## 4. Testes

### Manuais
- [x] Verificar que o backend está rodando com `make backend`
- [x] Testar carregamento de projeto com caminho válido
- [x] Testar carregamento de projeto com caminho inválido
- [x] Verificar mensagem de erro quando backend está offline
- [x] Testar funcionalidade de projetos recentes
- [x] Testar obtenção de projeto atual

### Unitários
- [ ] Teste para `loadProject()` com sucesso
- [ ] Teste para `loadProject()` com erro de conexão
- [ ] Teste para `getCurrentProject()` com projeto existente
- [ ] Teste para `getCurrentProject()` sem projeto
- [ ] Teste para `getRecentProjects()` com lista vazia

### Integração
- [ ] Teste E2E do fluxo completo de carregamento de projeto
- [ ] Teste de fallback quando variável de ambiente não está definida
- [ ] Teste de conexão com diferentes configurações de porta

---

## 5. Considerações

### Riscos
- **Compatibilidade**: Usuários com configurações antigas podem ter problemas
  - **Mitigação**: Documentar claramente a mudança no README

- **Variáveis de Ambiente**: Conflitos com configurações existentes
  - **Mitigação**: Usar `.env.example` e documentar no README

### Dependências
- Nenhuma dependência externa adicional
- Backend deve estar rodando na porta 3001 (configuração padrão)

### Documentação Necessária
- [x] Atualizar README com instruções de configuração
- [x] Adicionar seção de troubleshooting para erros de conexão
- [x] Documentar variáveis de ambiente disponíveis

### Melhorias Futuras
- Implementar reconexão automática quando backend volta online
- Adicionar indicador visual de status de conexão com backend
- Implementar cache local de projetos recentes
- Adicionar health check endpoint no backend