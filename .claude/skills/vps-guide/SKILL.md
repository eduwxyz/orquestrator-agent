---
name: vps-guide
description: Guia do projeto ZenFlow na VPS. Use quando precisar acessar, debugar, ou gerenciar o servidor de producao (live.vibeengineerbr.com).
---

# VPS Guide - ZenFlow Production Server

## Acesso SSH

```bash
ssh root@178.128.75.139
```

**IP**: 178.128.75.139
**Dominio**: live.vibeengineerbr.com
**Usuario**: root
**Provider**: DigitalOcean

---

## O que e o Projeto

ZenFlow e um sistema de Kanban com IA que executa tarefas de desenvolvimento automaticamente. Inclui:

- **Backend**: FastAPI (Python) com WebSocket para real-time
- **Frontend**: React/TypeScript com Vite
- **Banco**: SQLite com WAL mode
- **IA**: Integracao com Claude Code CLI para executar tarefas

### Modo Live (/live)

Pagina publica para espectadores assistirem a IA trabalhando em tempo real:
- Kanban readonly
- Sistema de votacao (60s)
- Galeria de projetos
- Contador de espectadores

---

## Estrutura de Arquivos na VPS

```
/opt/zenflow/
├── backend/
│   ├── src/
│   │   ├── main.py              # Ponto de entrada FastAPI
│   │   ├── config.py            # Configuracoes
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── routes/
│   │   │   ├── cards.py         # CRUD de cards
│   │   │   ├── live.py          # Endpoints /live
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── orchestrator_service.py  # Loop principal da IA
│   │   │   ├── voting_service.py        # Sistema de votacao
│   │   │   ├── card_ws.py               # WebSocket de cards
│   │   │   └── ...
│   │   ├── repositories/
│   │   │   └── card_repository.py       # Acesso ao banco
│   │   └── models/
│   │       └── card.py                  # SQLAlchemy models
│   ├── venv/                    # Virtual environment Python
│   └── .claude/
│       └── database.db          # Banco SQLite do projeto atual
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router principal
│   │   ├── pages/
│   │   │   ├── LivePage.tsx     # Pagina /live
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── Live/            # Componentes do modo live
│   │   │   ├── Board/           # Kanban board
│   │   │   └── ...
│   │   ├── hooks/
│   │   │   ├── useLiveWebSocket.ts
│   │   │   └── ...
│   │   └── api/
│   │       └── config.ts        # URLs de API/WS
│   └── dist/                    # Build de producao
│
└── projects/                    # Projetos completados pela IA
    └── {project-id}/            # Arquivos estaticos servidos
```

---

## Servicos Systemd

### zenflow.service (Backend)

```bash
# Status
systemctl status zenflow

# Logs em tempo real
journalctl -u zenflow -f

# Ultimas 100 linhas
journalctl -u zenflow -n 100 --no-pager

# Reiniciar
systemctl restart zenflow

# Parar
systemctl stop zenflow

# Iniciar
systemctl start zenflow
```

**Arquivo de configuracao**: `/etc/systemd/system/zenflow.service`

```ini
[Unit]
Description=ZenFlow Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/zenflow/backend
ExecStart=/opt/zenflow/backend/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 3001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## Nginx

**Arquivo de config**: `/etc/nginx/sites-available/zenflow`

### URLs

| URL | Descricao | Auth |
|-----|-----------|------|
| https://live.vibeengineerbr.com/ | Admin (Kanban) | Basic Auth |
| https://live.vibeengineerbr.com/live | Espectadores | Publico |
| https://live.vibeengineerbr.com/api/live/* | API Live | Publico |
| https://live.vibeengineerbr.com/projects/* | Projetos | Publico |

### Comandos

```bash
# Testar config
nginx -t

# Recarregar
systemctl reload nginx

# Ver logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

---

## Banco de Dados

**Tipo**: SQLite com WAL mode
**Localizacao**: `/opt/zenflow/backend/.claude/database.db`

### Consultas uteis

```bash
# Acessar banco
sqlite3 /opt/zenflow/backend/.claude/database.db

# Ver cards
sqlite3 /opt/zenflow/backend/.claude/database.db "SELECT id, title, column_id FROM cards;"

# Ver card especifico
sqlite3 /opt/zenflow/backend/.claude/database.db "SELECT * FROM cards WHERE id='xxx';"

# Limpar todos os cards
sqlite3 /opt/zenflow/backend/.claude/database.db "DELETE FROM cards;"

# Ver votos
sqlite3 /opt/zenflow/backend/.claude/database.db "SELECT * FROM votes;"

# Ver galeria
sqlite3 /opt/zenflow/backend/.claude/database.db "SELECT * FROM project_gallery;"
```

### Resetar banco

```bash
systemctl stop zenflow
rm /opt/zenflow/backend/.claude/database.db*
systemctl start zenflow
```

---

## Deploy

### Atualizar Backend

```bash
cd /opt/zenflow/backend
git pull origin live-mode
systemctl restart zenflow
```

### Atualizar Frontend

```bash
cd /opt/zenflow/frontend
git pull origin live-mode
npm install
npm run build
# Frontend estatico ja servido pelo nginx
```

### Deploy completo (do local)

```bash
# No diretorio local do projeto
rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '.git' \
  ./ root@178.128.75.139:/opt/zenflow/

# Na VPS
ssh root@178.128.75.139
cd /opt/zenflow/backend && source venv/bin/activate && pip install -r requirements.txt
cd /opt/zenflow/frontend && npm install && npm run build
systemctl restart zenflow
```

---

## Troubleshooting

### Porta 3001 em uso

```bash
# Ver o que esta usando
lsof -i :3001

# Matar processo
kill -9 <PID>

# Ou matar todos uvicorn
pkill -9 uvicorn

# Reiniciar servico
systemctl restart zenflow
```

### Banco travado (database is locked)

```bash
# Parar servico
systemctl stop zenflow

# Remover arquivos WAL
rm /opt/zenflow/backend/.claude/database.db-shm
rm /opt/zenflow/backend/.claude/database.db-wal

# Reiniciar
systemctl start zenflow
```

### WebSocket nao conecta

```bash
# Verificar nginx proxy
nginx -t

# Ver se backend esta rodando
curl http://localhost:3001/api/health

# Ver logs
journalctl -u zenflow -n 50 --no-pager
```

### Frontend mostrando localhost

Verificar `/opt/zenflow/frontend/src/api/config.ts`:
- Em producao, deve usar URLs relativas
- Rebuild: `cd /opt/zenflow/frontend && npm run build`

### Cards em loop (nao param em done)

1. Ver coluna atual no banco:
```bash
sqlite3 /opt/zenflow/backend/.claude/database.db "SELECT id, title, column_id FROM cards;"
```

2. Verificar ALLOWED_TRANSITIONS em `card_repository.py`

3. Adicionar debug logs em `orchestrator_service.py`

### SSL/HTTPS nao funciona

```bash
# Renovar certificado
certbot renew

# Ver certificados
certbot certificates

# Recarregar nginx
systemctl reload nginx
```

---

## Comandos Rapidos

```bash
# Status geral
ssh root@178.128.75.139 "systemctl status zenflow && curl -s http://localhost:3001/api/health"

# Logs em tempo real
ssh root@178.128.75.139 "journalctl -u zenflow -f"

# Ver cards
ssh root@178.128.75.139 "sqlite3 /opt/zenflow/backend/.claude/database.db 'SELECT id, title, column_id FROM cards;'"

# Reiniciar tudo
ssh root@178.128.75.139 "systemctl restart zenflow && systemctl reload nginx"

# Limpar e reiniciar
ssh root@178.128.75.139 "systemctl stop zenflow && rm /opt/zenflow/backend/.claude/database.db* && systemctl start zenflow"
```

---

## Variaveis de Ambiente

No backend (`/opt/zenflow/backend`):
- `DATABASE_URL`: sqlite+aiosqlite:///.claude/database.db
- `ANTHROPIC_API_KEY`: Configurado no ambiente do sistema

No frontend (build time):
- `VITE_API_URL`: Nao usar em producao (usa URLs relativas)
- `VITE_WS_URL`: Nao usar em producao (usa URLs relativas)
