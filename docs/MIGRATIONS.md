# Database Migrations System

Este documento explica como o sistema de migrations funciona no projeto Zenflow.

## Como Funciona

As migrations de banco de dados são executadas **automaticamente** quando um card chega na coluna "done" do Kanban.

### Fluxo de Execução

1. **Desenvolvimento**: Durante o trabalho em um card, você cria arquivos de migration SQL
2. **Card → Done**: Quando o card é movido para "done" no Kanban
3. **Auto-Migration**: O sistema detecta e aplica automaticamente todas as migrations pendentes
4. **Tracking**: As migrations aplicadas são registradas para não serem executadas novamente

## Criando Migrations

### 1. Nomeação

Use o formato: `XXX_description.sql`

Exemplos:
- `010_add_metrics_tables.sql`
- `011_add_user_preferences.sql`
- `012_alter_cards_add_priority.sql`

**Importante:** Use o próximo número sequencial disponível. Verifique os arquivos existentes em `backend/migrations/`.

### 2. Local

Coloque os arquivos em: `backend/migrations/`

### 3. Formato SQL

```sql
-- Migration: Brief description

-- Create tables
CREATE TABLE IF NOT EXISTS example_table (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add columns
ALTER TABLE existing_table ADD COLUMN new_field TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_example ON example_table(name);
```

**Dicas:**
- Use `IF NOT EXISTS` para evitar erros se a migration já foi parcialmente aplicada
- Sempre adicione comentários explicativos
- Teste a migration localmente antes de commitar

## Quando São Executadas

As migrations são executadas em dois momentos:

### 1. Card Reaches Done (Principal)

Quando um card é movido para a coluna "done" no Kanban:
- O sistema verifica migrations pendentes
- Aplica todas as migrations que ainda não foram executadas
- Registra no log do backend
- Não bloqueia o card se houver erro (apenas avisa)

### 2. Backend Startup (Fallback - REMOVIDO)

**ATUALIZAÇÃO:** A execução automática no startup foi **removida**.

Migrations agora rodam **apenas** quando cards chegam em "done".

## Migration Tracking

O sistema mantém uma tabela `applied_migrations` no banco:

```sql
CREATE TABLE applied_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Cada migration executada é registrada, garantindo que não seja aplicada duas vezes.

## Troubleshooting

### Migration não foi aplicada

1. Verifique se o arquivo está em `backend/migrations/`
2. Verifique se o card chegou em "done"
3. Veja os logs do backend para erros

### Erro na Migration

Se uma migration falhar:
- O erro é logado no backend
- O card ainda é movido para "done" (não bloqueia)
- Corrija a migration e mova outro card para "done" para re-executar

### Forçar Re-execução

Se precisar re-executar uma migration:

```bash
# Remover registro da migration
sqlite3 .claude/database.db "DELETE FROM applied_migrations WHERE migration_name='XXX_description.sql'"

# Mover um card para "done" para trigger o sistema
```

## Exemplo Completo

### Cenário: Adicionar tabela de notificações

1. **Durante implementação**, crie o arquivo:

`backend/migrations/011_add_notifications.sql`:
```sql
-- Migration: Add notifications system

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_notifications_user
    ON notifications(user_id, created_at);
```

2. **Commite o arquivo** junto com o código

3. **Mova o card para "done"** no Kanban

4. **Verifique os logs** do backend:
```
[CardRepository] Running migrations for card Add notifications system reaching done...
[CardRepository] ✅ Migrations completed: Successfully applied 011_add_notifications.sql
```

5. **Pronto!** A migration foi aplicada automaticamente.

## Boas Práticas

1. ✅ **Sempre** crie migrations para mudanças no schema
2. ✅ **Sempre** use `IF NOT EXISTS` para idempotência
3. ✅ **Sempre** teste localmente antes de commitar
4. ✅ **Sempre** use comentários descritivos
5. ❌ **Nunca** modifique migrations já commitadas
6. ❌ **Nunca** execute migrations manualmente (deixe o sistema fazer)
7. ❌ **Nunca** delete migrations aplicadas

## FAQ

**P: O que acontece se eu mover vários cards para "done" ao mesmo tempo?**
R: Cada movimento executa as migrations pendentes. Se não houver pendências, nada acontece.

**P: Posso criar migrations manualmente durante desenvolvimento?**
R: Sim! Crie o arquivo SQL e aplique manualmente com `sqlite3 .claude/database.db < backend/migrations/XXX.sql` para testar.

**P: E se eu esquecer de criar a migration?**
R: Você terá erros SQL no backend quando tentar acessar tabelas/colunas inexistentes. Crie a migration e mova um card para "done".

**P: As migrations rodam em todos os databases do projeto?**
R: Sim, o sistema aplica migrations no database atual (`.claude/database.db`) e em databases legados (`.project_data/*/database.db`).
