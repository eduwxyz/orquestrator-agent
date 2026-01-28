# Análise Crítica do Serviço de Banco de Dados

> Análise realizada em: 2026-01-28

## Sumário

| Categoria | Severidade | Quantidade |
|-----------|------------|------------|
| Arquitetura | Alta | 4 |
| Inconsistência | Alta | 5 |
| Debt Técnico | Média | 4 |
| **Total** | | **13** |

---

## PROBLEMAS GRAVES

### 1. Duplicação de Código e Funções Redundantes

**Arquivos afetados:** `database.py`, `database_manager.py`

A função `_set_sqlite_pragma()` está **duplicada** em ambos os arquivos:
- `database.py:13-19`
- `database_manager.py:27-33`

Dois engines/session factories coexistem: um "legacy" e outro do `db_manager`. O código tem comentários como "legacy - kept for backward compatibility" - isso é debt técnico acumulado.

```python
# database.py:22-23
# Create async engine (legacy - kept for backward compatibility)
engine = create_async_engine(...)
```

**Impacto:** Manutenção duplicada, bugs podem ser corrigidos em um lugar e esquecidos no outro.

---

### 2. Sistema de Migrations Caótico

**Arquivos afetados:** `backend/migrations/`, `backend/src/migrations/`, `migration_service.py`

#### 2.1 Prefixos duplicados
Dois arquivos de migration com mesmo prefixo `002_`:
- `002_add_model_config_to_cards.sql`
- `002_migrate_archived_to_column.sql`

Isso quebra a ordenação e pode causar execução inconsistente.

#### 2.2 Migrations SQL + Python coexistem
- `backend/migrations/*.sql` (13 arquivos)
- `backend/src/migrations/*.py` (6 arquivos)

Não há unificação. O `MigrationService` só processa `.sql`, ignorando os Python.

#### 2.3 MigrationService usa conexão SÍNCRONA
```python
# migration_service.py:68
conn = sqlite3.connect(self.db_path)  # SÍNCRONO!
```

Enquanto o resto do projeto usa `aiosqlite` async.

**Impacto:** Migrations podem executar fora de ordem, código Python de migration nunca é executado automaticamente.

---

### 3. Multi-Database Mal Arquitetado

**Arquivos afetados:** `database_manager.py`, `database.py`

O projeto tenta manter **3 tipos de databases**:
1. `backend/auth.db` - "principal"
2. `.claude/database.db` - "por projeto"
3. `backend/.project_data/<hash>/database.db` - "legacy"

#### Problemas específicos:

- O `db_manager` usa **hash MD5** do path para gerar IDs de projeto - colisões são possíveis
- Não há **transações distribuídas** - se uma operação precisa escrever em múltiplos DBs, pode haver inconsistência
- O `get_session()` em `database.py` tem fallback silencioso:

```python
try:
    return db_manager.get_current_session()
except RuntimeError:
    return async_session_maker  # Fallback silencioso para legacy!
```

**Impacto:** Dados podem ser escritos no database errado sem aviso.

---

### 4. Models com Estilos Inconsistentes

**Arquivos afetados:** `models/card.py`, `models/execution.py`, `models/orchestrator.py`

Compare os estilos:

**`card.py` (SQLAlchemy 2.0 - moderno):**
```python
class Card(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
```

**`execution.py` (SQLAlchemy 1.x - antigo):**
```python
class Execution(Base):
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
```

- Um usa `Mapped[T]` (SQLAlchemy 2.0 style)
- Outro usa `Column()` (SQLAlchemy 1.x style)
- Geração de UUID inconsistente (alguns inline, outros no repository)

**Impacto:** Código confuso, type hints não funcionam consistentemente, manutenção difícil.

---

### 5. Foreign Keys sem CASCADE Consistente

**Arquivos afetados:** `models/card.py`, `models/execution.py`, `models/orchestrator.py`

```python
# card.py:35-38 - SET NULL
parent_card_id: Mapped[str | None] = mapped_column(
    String(36),
    ForeignKey("cards.id", ondelete="SET NULL"),
    nullable=True
)

# orchestrator.py:93 - CASCADE
goal_id: Mapped[str] = mapped_column(
    String(36),
    ForeignKey("goals.id", ondelete="CASCADE"),
    nullable=False
)

# execution.py:18 - NADA DEFINIDO!
card_id = Column(String, ForeignKey("cards.id"), nullable=False)
```

A FK de `Execution` para `Card` **não tem política de delete** - deletar um Card pode deixar execuções órfãs ou falhar silenciosamente.

**Impacto:** Inconsistência de dados, possíveis erros em cascata ao deletar cards.

---

### 6. DateTime sem Timezone

**Arquivos afetados:** Todos os models

```python
# card.py:27-31
created_at: Mapped[datetime] = mapped_column(
    DateTime, default=datetime.utcnow, nullable=False  # utcnow() sem timezone
)
```

Usar `datetime.utcnow()` está **deprecated** desde Python 3.12. Deveria usar `datetime.now(timezone.utc)`.

**Impacto:** Problemas de timezone em deploys distribuídos, warnings de deprecation.

---

### 7. Lógica de Negócio no Repository

**Arquivo afetado:** `repositories/card_repository.py:177-194`

O método `move()` executa **migrations** quando um card chega em "done":

```python
if new_column_id == "done":
    from ..services.migration_service import MigrationService
    # ... runs migrations
```

Isso é **side effect** inesperado. Repository deveria apenas acessar dados, não executar migrations.

**Impacto:** Acoplamento alto, difícil de testar, comportamento inesperado.

---

### 8. Commit Duplo em Alguns Repositórios

**Arquivos afetados:** `repositories/execution_repository.py`, `database.py`

```python
# execution_repository.py:51-55
self.db.add(execution)
await self.db.commit()  # Commit no repository

# Enquanto em get_db():
async with session_factory() as session:
    yield session
    await session.commit()  # Commit no dependency também
```

O `ExecutionRepository` faz `commit()` internamente, mas `CardRepository` não. Inconsistência perigosa.

**Impacto:** Transações podem ser commitadas parcialmente, comportamento imprevisível.

---

### 9. Cache sem Invalidação Adequada

**Arquivo afetado:** `repositories/execution_repository.py`

Usa `execution_cache` mas:
- Não há TTL definido visível
- Invalidação manual espalhada pelo código
- Sem proteção contra race conditions

**Impacto:** Dados stale, possíveis inconsistências em operações concorrentes.

---

### 10. Imports Circulares Escondidos

**Arquivo afetado:** `database_manager.py:193`

```python
from .models.project_history import Base as HistoryBase
```

Import dentro de função para evitar circular. Isso indica design frágil.

**Impacto:** Difícil de refatorar, pode quebrar com mudanças aparentemente não relacionadas.

---

## PROBLEMAS MÉDIOS

### 11. Settings Hardcoded

**Arquivo afetado:** `config/settings.py:24`

```python
database_url: str = "sqlite+aiosqlite:///auth.db"
```

Path relativo sem consideração do CWD. Pode falhar se servidor rodar de diretório diferente.

**Impacto:** Erros de "database not found" dependendo de como o servidor é iniciado.

---

### 12. Cleanup Não Implementado

**Arquivo afetado:** `database_manager.py:272-282`

```python
async def cleanup_old_databases(self, days_old: int = 30, keep_count: int = 10):
    # TODO: Implement cleanup logic
    pass
```

Método vazio há 13 migrations atrás. Databases órfãos se acumulam.

**Impacto:** Uso de disco cresce indefinidamente.

---

### 13. Enum Handling Inconsistente

**Arquivos afetados:** `models/execution.py`, `models/orchestrator.py`

```python
# execution.py:19
status = Column(Enum(ExecutionStatus, native_enum=False, values_callable=...))

# orchestrator.py:39
status: Mapped[GoalStatus] = mapped_column(Enum(GoalStatus), ...)
```

Um usa `native_enum=False`, outro não especifica.

**Impacto:** Comportamento diferente entre databases, possíveis problemas de migração.

---

## Recomendações de Correção (Por Prioridade)

### Alta Prioridade
1. [ ] Adicionar `ondelete="CASCADE"` na FK de Execution → Card
2. [ ] Unificar `_set_sqlite_pragma()` em um único lugar
3. [ ] Corrigir prefixo duplicado `002_` nas migrations
4. [ ] Padronizar commits (ou no repository OU no dependency, não ambos)

### Média Prioridade
5. [ ] Padronizar todos os models para SQLAlchemy 2.0 style
6. [ ] Remover código legacy de `database.py`
7. [ ] Unificar sistema de migrations (escolher SQL ou Python, não ambos)
8. [ ] Remover lógica de migration do `card_repository.move()`

### Baixa Prioridade
9. [ ] Trocar `datetime.utcnow()` por `datetime.now(timezone.utc)`
10. [ ] Implementar `cleanup_old_databases()`
11. [ ] Padronizar enum handling
12. [ ] Resolver imports circulares
13. [ ] Tornar MigrationService async

---

## Arquivos Principais Afetados

| Arquivo | Problemas |
|---------|-----------|
| `database.py` | #1, #3, #10 |
| `database_manager.py` | #1, #3, #10, #12 |
| `models/execution.py` | #4, #5, #13 |
| `models/card.py` | #6 |
| `repositories/card_repository.py` | #7 |
| `repositories/execution_repository.py` | #8, #9 |
| `services/migration_service.py` | #2 |
| `config/settings.py` | #11 |
| `backend/migrations/` | #2 |
