# Comandos Prontos - VPS ZenFlow

## Acesso

```bash
ssh root@178.128.75.139
```

---

## Monitoramento

### Status do servico
```bash
ssh root@178.128.75.139 "systemctl status zenflow --no-pager"
```

### Logs em tempo real
```bash
ssh root@178.128.75.139 "journalctl -u zenflow -f"
```

### Ultimas 50 linhas de log
```bash
ssh root@178.128.75.139 "journalctl -u zenflow -n 50 --no-pager"
```

### Filtrar logs por DEBUG
```bash
ssh root@178.128.75.139 "journalctl -u zenflow -n 100 --no-pager | grep DEBUG"
```

### Filtrar logs por ERROR
```bash
ssh root@178.128.75.139 "journalctl -u zenflow -n 100 --no-pager | grep -i error"
```

---

## Gerenciamento do Servico

### Reiniciar backend
```bash
ssh root@178.128.75.139 "systemctl restart zenflow"
```

### Parar backend
```bash
ssh root@178.128.75.139 "systemctl stop zenflow"
```

### Iniciar backend
```bash
ssh root@178.128.75.139 "systemctl start zenflow"
```

### Reiniciar nginx
```bash
ssh root@178.128.75.139 "systemctl reload nginx"
```

---

## Banco de Dados

### Ver todos os cards
```bash
ssh root@178.128.75.139 "sqlite3 /opt/zenflow/backend/.claude/database.db 'SELECT id, title, column_id FROM cards;'"
```

### Ver detalhes de um card
```bash
ssh root@178.128.75.139 "sqlite3 /opt/zenflow/backend/.claude/database.db 'SELECT * FROM cards LIMIT 1;'"
```

### Ver galeria de projetos
```bash
ssh root@178.128.75.139 "sqlite3 /opt/zenflow/backend/.claude/database.db 'SELECT * FROM project_gallery;'"
```

### Ver votos
```bash
ssh root@178.128.75.139 "sqlite3 /opt/zenflow/backend/.claude/database.db 'SELECT * FROM votes;'"
```

### Limpar banco (CUIDADO!)
```bash
ssh root@178.128.75.139 "systemctl stop zenflow && rm /opt/zenflow/backend/.claude/database.db* && systemctl start zenflow"
```

### Deletar todos os cards
```bash
ssh root@178.128.75.139 "sqlite3 /opt/zenflow/backend/.claude/database.db 'DELETE FROM cards;'"
```

---

## Troubleshooting

### Ver o que usa porta 3001
```bash
ssh root@178.128.75.139 "lsof -i :3001"
```

### Matar processos uvicorn orfaos
```bash
ssh root@178.128.75.139 "pkill -9 uvicorn; sleep 2; systemctl start zenflow"
```

### Parar tudo e limpar porta
```bash
ssh root@178.128.75.139 "systemctl stop zenflow && pkill -9 uvicorn 2>/dev/null; sleep 3 && systemctl start zenflow"
```

### Testar API localmente na VPS
```bash
ssh root@178.128.75.139 "curl -s http://localhost:3001/api/health"
```

### Testar config nginx
```bash
ssh root@178.128.75.139 "nginx -t"
```

### Ver logs nginx
```bash
ssh root@178.128.75.139 "tail -20 /var/log/nginx/error.log"
```

---

## Deploy

### Sincronizar backend local para VPS
```bash
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  ../backend/ root@178.128.75.139:/opt/zenflow/backend/
```

### Sincronizar frontend local para VPS
```bash
rsync -avz --exclude 'node_modules' --exclude '.git' \
  ./ root@178.128.75.139:/opt/zenflow/frontend/
```

### Rebuild frontend na VPS
```bash
ssh root@178.128.75.139 "cd /opt/zenflow/frontend && npm run build"
```

### Deploy completo
```bash
rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  ../ root@178.128.75.139:/opt/zenflow/ && \
ssh root@178.128.75.139 "cd /opt/zenflow/frontend && npm run build && systemctl restart zenflow"
```

---

## Editar arquivos na VPS

### Abrir arquivo com nano
```bash
ssh root@178.128.75.139 "nano /opt/zenflow/backend/src/services/orchestrator_service.py"
```

### Ver conteudo de arquivo
```bash
ssh root@178.128.75.139 "cat /opt/zenflow/backend/src/repositories/card_repository.py"
```

### Buscar texto em arquivos
```bash
ssh root@178.128.75.139 "grep -r 'ALLOWED_TRANSITIONS' /opt/zenflow/backend/src/"
```

---

## URLs de Teste

- **Admin**: https://live.vibeengineerbr.com/
- **Live (publico)**: https://live.vibeengineerbr.com/live
- **API Health**: https://live.vibeengineerbr.com/api/health
- **API Live Status**: https://live.vibeengineerbr.com/api/live/status
