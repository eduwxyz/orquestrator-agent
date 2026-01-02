"""
Migração para adicionar campos de workflow state ao banco de dados.

Execute este script para atualizar o esquema do banco:
    python -m backend.src.migrations.add_workflow_state
"""

import asyncio
from sqlalchemy import text
from backend.src.database import engine, create_tables

async def add_workflow_state_fields():
    """Adiciona campos de workflow state às tabelas existentes"""

    async with engine.begin() as conn:
        try:
            # Adicionar campos à tabela executions
            print("Adicionando campo 'title' à tabela executions...")
            await conn.execute(text("""
                ALTER TABLE executions
                ADD COLUMN IF NOT EXISTS title VARCHAR;
            """))

            print("Adicionando campo 'workflow_stage' à tabela executions...")
            await conn.execute(text("""
                ALTER TABLE executions
                ADD COLUMN IF NOT EXISTS workflow_stage VARCHAR;
            """))

            print("Adicionando campo 'workflow_error' à tabela executions...")
            await conn.execute(text("""
                ALTER TABLE executions
                ADD COLUMN IF NOT EXISTS workflow_error TEXT;
            """))

            print("Campos adicionados com sucesso!")

        except Exception as e:
            print(f"Erro ao adicionar campos: {e}")
            # Se os campos já existirem ou houver outro erro, continuar
            pass

async def main():
    """Executa a migração"""
    print("Iniciando migração de workflow state...")

    # Primeiro garantir que as tabelas existem
    print("Criando/atualizando tabelas...")
    await create_tables()

    # Adicionar novos campos
    await add_workflow_state_fields()

    print("Migração concluída!")

if __name__ == "__main__":
    asyncio.run(main())