"""
Script para criar a tabela activity_logs em todos os databases do sistema.
"""

import asyncio
import sqlite3
from pathlib import Path


def execute_migration(db_path: Path):
    """Executa a migration para criar a tabela activity_logs."""
    if not db_path.exists():
        print(f"Database {db_path} não existe, pulando...")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verificar se a tabela já existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity_logs'")
        if cursor.fetchone():
            print(f"✓ Tabela activity_logs já existe em {db_path}")
            conn.close()
            return

        print(f"Criando tabela activity_logs em {db_path}...")

        # Ler e executar a migration SQL
        migration_sql = """
-- Create activity_logs table
CREATE TABLE IF NOT EXISTS activity_logs (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    activity_type TEXT CHECK(activity_type IN ('created', 'moved', 'completed', 'archived', 'updated', 'executed', 'commented')) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Activity metadata
    from_column TEXT,
    to_column TEXT,
    old_value TEXT,
    new_value TEXT,
    user_id TEXT,
    description TEXT,

    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_activity_logs_card ON activity_logs(card_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_type ON activity_logs(activity_type);
"""

        # Executar cada statement separadamente
        for statement in migration_sql.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)

        conn.commit()
        print(f"✓ Tabela activity_logs criada com sucesso em {db_path}!")

        conn.close()
    except Exception as e:
        print(f"✗ Erro ao processar {db_path}: {e}")


async def main():
    """Executa a migration em todos os databases."""
    print("=" * 60)
    print("Criando tabela activity_logs em todos os databases")
    print("=" * 60)

    # Lista de databases para migrar
    databases = [
        Path("backend/auth.db"),
        Path(".claude/database.db"),
        Path("auth.db"),
        Path("backend/.project_data/project_history.db"),
    ]

    # Adicionar databases de projetos em .project_data
    project_data_dir = Path("backend/.project_data")
    if project_data_dir.exists():
        for project_dir in project_data_dir.iterdir():
            if project_dir.is_dir():
                db_path = project_dir / "database.db"
                if db_path.exists():
                    databases.append(db_path)

    # Processar cada database
    for db_path in databases:
        print(f"\n📁 Processando: {db_path}")
        execute_migration(db_path)

    print("\n" + "=" * 60)
    print("✓ Migration concluída!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
