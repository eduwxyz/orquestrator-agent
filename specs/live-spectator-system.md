# Plano: Sistema de Espectadores /live

## Resumo

Criar página pública `/live` para espectadores acompanharem a IA trabalhando em tempo real, com sistema de votação e galeria de projetos.

---

## Contexto do Projeto

### O que é o Orquestrador

Este projeto é um **Orquestrador de Agentes de IA** - uma aplicação que permite à IA trabalhar de forma autônoma em projetos de software. O sistema funciona como um desenvolvedor virtual que:

1. **Recebe um objetivo** (ex: "Criar um jogo de Snake em Python")
2. **Decompõe em tarefas** usando IA (Claude) para criar cards no Kanban
3. **Executa cada tarefa** de forma autônoma, passando pelo ciclo SDLC completo
4. **Entrega o projeto pronto** com código funcional

### Workflow da IA (SDLC)

Cada card passa por um ciclo de desenvolvimento completo:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CICLO DE VIDA DO CARD                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   BACKLOG → PLAN → IMPLEMENT → TEST → REVIEW → DONE                    │
│      │        │         │        │       │       │                      │
│      ↓        ↓         ↓        ↓       ↓       ↓                      │
│   Tarefa   IA cria   IA escreve  IA    IA      Código                  │
│   criada   o plano   o código   roda  verifica  pronto!                │
│            técnico   seguindo   tests  qualidade                       │
│                      o plano                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Estados do Kanban:**
- **Backlog**: Tarefas aguardando execução
- **Planning**: IA analisando e criando plano técnico
- **Implementing**: IA escrevendo código
- **Testing**: IA rodando testes
- **Reviewing**: IA verificando qualidade
- **Done**: Tarefa concluída

### Componentes Atuais

```
┌────────────────────────────────────────────────────────────────┐
│                      ARQUITETURA ATUAL                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   Frontend (React + TypeScript)                                │
│   ├── KanbanBoard → Visualiza cards e estados                  │
│   ├── Chat → Conversa com a IA                                 │
│   ├── ExecutionLogs → Logs em tempo real                       │
│   └── ProjectSwitcher → Troca entre projetos                   │
│                                                                │
│   Backend (FastAPI + Python)                                   │
│   ├── Orchestrator → Gerencia fluxo de trabalho                │
│   ├── CardService → CRUD de cards                              │
│   ├── ExecutionService → Executa comandos /plan, /implement    │
│   ├── WebSocket → Atualização em tempo real                    │
│   └── SQLite → Banco de dados                                  │
│                                                                │
│   Integração IA                                                │
│   ├── Claude API → Gera planos e código                        │
│   └── Claude Code → Executa comandos no terminal               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Problema Atual

Hoje o sistema é privado - só você (admin) tem acesso. Queremos criar uma experiência pública onde:

- **Espectadores** assistem a IA trabalhando em tempo real
- **Comunidade** vota em qual projeto a IA deve fazer em seguida
- **Galeria** mostra projetos prontos com sistema de likes

---

## O que é o Sistema /live

### Visão Geral

O `/live` é uma **janela pública** para o orquestrador. Espectadores veem uma versão simplificada e read-only do que a IA está fazendo.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   VOCÊ (Admin)                    ESPECTADORES (/live)           │
│   ────────────                    ────────────────────           │
│                                                                  │
│   ✓ Criar projetos                ✗ Não pode criar              │
│   ✓ Editar cards                  ✗ Não pode editar             │
│   ✓ Conversar com IA              ✗ Não pode conversar          │
│   ✓ Controle total                ✓ Apenas observar              │
│                                   ✓ Votar no próximo projeto     │
│                                   ✓ Dar like em projetos prontos │
│                                   ✓ Ver quantas pessoas assistem │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Jornada do Espectador

```
┌─────────────────────────────────────────────────────────────────────┐
│                     JORNADA DO ESPECTADOR                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. CHEGADA                                                         │
│     └── Acessa IP/live → Vê dashboard com status da IA              │
│                                                                     │
│  2. ASSISTINDO (IA trabalhando)                                     │
│     ├── Vê status: "🔨 Implementando: jogo de Snake"                │
│     ├── Vê Kanban: cards movendo entre colunas                      │
│     ├── Vê logs: mensagens em tempo real da IA                      │
│     └── Vê contador: "👁 42 pessoas assistindo"                     │
│                                                                     │
│  3. VOTAÇÃO (IA terminou projeto)                                   │
│     ├── Timer de 5 minutos aparece                                  │
│     ├── Opções de voto: [Jogo][Arte][App][Site]                     │
│     ├── Vê votos em tempo real: Jogo 15, Site 12...                 │
│     └── Quando timer acaba → IA começa projeto vencedor             │
│                                                                     │
│  4. GALERIA (projetos prontos)                                      │
│     ├── Cards com preview/screenshot                                │
│     ├── Botão de like (❤️ 234)                                      │
│     └── Ranking por likes                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

```
┌────────────────────────────────────────────────────────────────────┐
│                    FLUXO DE DADOS /LIVE                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   [Orquestrador]                                                   │
│        │                                                           │
│        │ (eventos: card_moved, log_entry, project_done)            │
│        ↓                                                           │
│   [LiveBroadcastService] ←── Agrega eventos do sistema             │
│        │                                                           │
│        │ (WebSocket: /api/live/ws)                                 │
│        ↓                                                           │
│   [Espectadores] ←── Recebem atualizações em tempo real            │
│        │                                                           │
│        │ (POST: /api/live/vote, /api/live/projects/{id}/like)      │
│        ↓                                                           │
│   [VotingService / ProjectGallery] ←── Processa interações         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Decisões do Usuário

| Aspecto | Decisão |
|---------|---------|
| Tela inicial | Dashboard completo com várias áreas |
| IA em tempo real | Combinação: Status + Kanban + logs simplificados |
| Interação | Só votação (sem chat livre) |
| Quando votar | Quando IA termina projeto → 5 min de votação |
| O que votar | Próximo projeto + likes nos prontos |
| Projetos prontos | Preview/screenshot por agora |
| Espectadores | 100% anônimo, voto por sessão/IP |
| Contador | "X pessoas assistindo" em destaque |
| Admin | Protegido com Basic Auth (Nginx) |

---

## Arquitetura

```
http://IP/       → Admin (protegido Nginx Basic Auth)
http://IP/live   → Público (espectadores)
```

### Layout do /live

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Live Studio          [👁 42 assistindo]              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │ STATUS ATUAL     │  │ KANBAN (readonly)               │  │
│  │ 🔨 Criando...    │  │ [Backlog][Doing][Review][Done]  │  │
│  │ "Jogo de Snake"  │  │                                 │  │
│  │ ████████░░ 80%   │  │                                 │  │
│  │                  │  │                                 │  │
│  │ 📝 Logs recentes │  │                                 │  │
│  └──────────────────┘  └─────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 🗳 VOTAÇÃO (4:32 restantes)                             ││
│  │ [🎮 Jogo - 15] [🎨 Arte - 8] [📱 App - 3] [🌐 Site - 12]││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 🏆 GALERIA                                              ││
│  │ [Tetris ❤️234] [Snake ❤️189] [Arte ❤️56] [Site ❤️23]   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 1: Infraestrutura WebSocket (Resolver problemas existentes)

### Objetivo
Criar base robusta de WebSocket que resolve os problemas atuais de reconexão.

### Arquivos a criar

**`frontend/src/hooks/useWebSocketBase.ts`**
- Hook base com reconexão robusta (exponential backoff + jitter)
- Heartbeat automático (ping/pong a cada 30s)
- Fila de mensagens durante reconexão
- Estados: connecting | connected | disconnected | error

**`frontend/src/api/wsConfig.ts`**
- Centralizar todas as URLs de WebSocket
- Usar variáveis de ambiente

### Arquivos a modificar

| Arquivo | Modificação |
|---------|-------------|
| `frontend/src/hooks/useCardWebSocket.ts` | Refatorar para usar useWebSocketBase |
| `frontend/src/hooks/useExecutionWebSocket.ts` | Refatorar para usar useWebSocketBase |
| `frontend/src/hooks/useChat.ts` | Refatorar para usar useWebSocketBase |
| `frontend/src/api/config.ts` | Adicionar WS_ENDPOINTS |

---

## Fase 2: Backend /live

### Novos arquivos

| Arquivo | Descrição |
|---------|-----------|
| `backend/src/routes/live.py` | Endpoints REST + WebSocket |
| `backend/src/services/presence_service.py` | Contador de espectadores |
| `backend/src/services/voting_service.py` | Sistema de votação |
| `backend/src/services/live_broadcast_service.py` | Agregador de eventos |
| `backend/src/models/vote.py` | Model SQLAlchemy para votos |
| `backend/src/models/project_gallery.py` | Model para galeria |
| `backend/src/schemas/live.py` | Schemas Pydantic |

### Endpoints

```
GET  /api/live/status          → Status atual da IA
GET  /api/live/projects        → Galeria de projetos
GET  /api/live/voting          → Estado da votação
POST /api/live/vote            → Registrar voto
POST /api/live/projects/{id}/like → Like em projeto
WS   /api/live/ws              → WebSocket unificado
```

### Mensagens WebSocket (/api/live/ws)

```typescript
// Servidor → Cliente
{ type: 'presence_update', spectatorCount: number }
{ type: 'card_update', cards: Card[] }
{ type: 'status_update', status: string, currentCard: Card, stage: string }
{ type: 'log_entry', content: string, timestamp: string }
{ type: 'voting_started', options: VoteOption[], endsAt: string }
{ type: 'voting_update', votes: Record<string, number> }
{ type: 'voting_ended', winner: VoteOption, results: VoteResult[] }
{ type: 'project_liked', projectId: string, likes: number }
```

### Modificar

| Arquivo | Modificação |
|---------|-------------|
| `backend/src/main.py` | Registrar live_router |
| `backend/src/config/settings.py` | VOTING_DURATION_SECONDS = 300 |

---

## Fase 3: Frontend /live

### Novos arquivos

| Arquivo | Descrição |
|---------|-----------|
| `frontend/src/pages/LivePage.tsx` | Página principal |
| `frontend/src/pages/LivePage.module.css` | Estilos |
| `frontend/src/hooks/useLiveWebSocket.ts` | Hook para /api/live/ws |
| `frontend/src/types/live.ts` | Tipos TypeScript |
| `frontend/src/components/Live/LiveHeader.tsx` | Contador espectadores |
| `frontend/src/components/Live/LiveStatus.tsx` | Status da IA |
| `frontend/src/components/Live/LiveKanban.tsx` | Kanban readonly |
| `frontend/src/components/Live/LiveLogs.tsx` | Logs simplificados |
| `frontend/src/components/Live/VotingPanel.tsx` | Área de votação |
| `frontend/src/components/Live/ProjectGallery.tsx` | Galeria |
| `frontend/src/components/Live/ProjectCard.tsx` | Card com like |

### Modificar

| Arquivo | Modificação |
|---------|-------------|
| `frontend/src/App.tsx` | Adicionar rota /live |

---

## Fase 4: Configuração Nginx (Proteção)

### Modificar na VPS

**`/etc/nginx/sites-available/zenflow`**

```nginx
server {
    listen 80;

    # Área pública - SEM AUTH
    location /live {
        root /opt/zenflow/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/live {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Área protegida - COM AUTH
    location / {
        auth_basic "Admin Area";
        auth_basic_user_file /etc/nginx/.htpasswd;
        root /opt/zenflow/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        auth_basic "Admin Area";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /ws {
        auth_basic "Admin Area";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### Criar senha

```bash
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin
# Digitar senha quando solicitado
```

---

## Ordem de Implementação

### Passo 1: useWebSocketBase
- [ ] Criar hook base com reconexão robusta
- [ ] Testar reconexão (desligar/ligar rede)

### Passo 2: Refatorar hooks existentes
- [ ] useCardWebSocket → usar useWebSocketBase
- [ ] useExecutionWebSocket → usar useWebSocketBase
- [ ] useChat → usar useWebSocketBase
- [ ] Testar que tudo continua funcionando

### Passo 3: Backend /live
- [ ] Criar models (Vote, ProjectGallery)
- [ ] Criar PresenceService
- [ ] Criar VotingService
- [ ] Criar LiveBroadcastService
- [ ] Criar routes/live.py
- [ ] Registrar em main.py
- [ ] Testar endpoints

### Passo 4: Frontend /live
- [ ] Criar tipos (types/live.ts)
- [ ] Criar useLiveWebSocket
- [ ] Criar componentes Live/*
- [ ] Criar LivePage
- [ ] Adicionar rota em App.tsx
- [ ] Testar página

### Passo 5: Sistema de votação
- [ ] Lógica de início (quando IA termina)
- [ ] UI de votação
- [ ] Likes em projetos
- [ ] Rate limiting

### Passo 6: Nginx (VPS)
- [ ] Configurar Basic Auth
- [ ] Criar senha
- [ ] Testar /live público
- [ ] Testar / protegido

---

## Verificação

### Testes locais

```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate
uvicorn src.main:app --reload --port 3001

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Testar WebSocket
npx wscat -c ws://localhost:3001/api/live/ws

# Browser: Abrir múltiplas abas em http://localhost:5173/live
# Verificar contador de espectadores incrementa
```

### Testes na VPS

```bash
# Após deploy
curl http://178.128.75.139/live              # Deve abrir sem auth
curl http://178.128.75.139/                  # Deve pedir senha (401)
curl -u admin:senha http://178.128.75.139/  # Deve funcionar
```

---

## Arquivos Críticos (ler antes de implementar)

1. `backend/src/services/card_ws.py` - Padrão de broadcast WS
2. `frontend/src/hooks/useCardWebSocket.ts` - Base para useWebSocketBase
3. `backend/src/main.py` - Registro de routers
4. `frontend/src/App.tsx` - Sistema de navegação
5. `frontend/src/components/Board/Board.tsx` - Kanban para reutilizar
