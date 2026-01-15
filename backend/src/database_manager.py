"""Database manager for multi-project database isolation.

Arquitetura de Databases:
    - backend/auth.db: Database principal/raiz do sistema
      Contém: users, cards, executions, execution_logs, active_project

    - .claude/database.db: Databases isolados por projeto
      Cada projeto tem seu próprio database em sua pasta .claude

    - backend/.project_data/: Diretório legacy (mantido para compatibilidade)
      Databases antigos são migrados automaticamente para .claude
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
import logging

from .database import Base


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better concurrency."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages multiple isolated databases, one per project.

    O DatabaseManager trabalha com dois tipos de databases:
    1. Database Principal (backend/auth.db): Database raiz do sistema
    2. Databases de Projeto (.claude/database.db): Databases isolados por projeto
    """

    def __init__(self, base_data_dir: str = ".project_data"):
        """
        Initialize the database manager.

        Args:
            base_data_dir: Base directory for storing legacy project databases
                          (novos databases são criados em .claude/)
        """
        # Database principal - sempre backend/auth.db
        self.main_database_path = Path("backend/auth.db")

        # Diretório para databases legados (compatibilidade)
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(exist_ok=True)

        self.engines: Dict[str, AsyncEngine] = {}
        self.sessions: Dict[str, Any] = {}
        self.current_project_id: Optional[str] = None
        self._history_engine: Optional[AsyncEngine] = None
        self._history_session: Optional[Any] = None

    def get_project_id(self, project_path: str) -> str:
        """
        Generate unique ID for project based on path.

        Args:
            project_path: Path to the project

        Returns:
            Unique MD5 hash ID for the project
        """
        return hashlib.md5(project_path.encode()).hexdigest()

    def get_database_path(self, project_id: str) -> Path:
        """
        Get database path for a project.

        Args:
            project_id: Unique project identifier

        Returns:
            Path to the project's database file
        """
        project_dir = self.base_data_dir / project_id
        project_dir.mkdir(exist_ok=True)
        return project_dir / "database.db"

    def get_history_database_path(self) -> Path:
        """
        Get path to the global project history database.

        Returns:
            Path to the global history database
        """
        return self.base_data_dir / "project_history.db"

    async def initialize_project_database(self, project_path: str) -> str:
        """
        Initialize or get database for a project.

        Args:
            project_path: Path to the project

        Returns:
            Project ID
        """
        # Normalize the path
        project_path = os.path.abspath(project_path)
        project_id = self.get_project_id(project_path)

        # NOVO: Create database inside the .claude folder of the project
        claude_dir = os.path.join(project_path, '.claude')

        # Ensure .claude folder exists
        if not os.path.exists(claude_dir):
            os.makedirs(claude_dir)
            logger.info(f"Created .claude directory at {claude_dir}")

        # Define database path in project
        db_path = os.path.join(claude_dir, 'database.db')

        # Check if there's a legacy database in .project_data (compatibility)
        legacy_db_path = self.get_database_path(project_id)

        # If legacy database exists and new one doesn't, copy it
        if os.path.exists(legacy_db_path) and not os.path.exists(db_path):
            shutil.copy2(legacy_db_path, db_path)
            logger.info(f"Migrated database from {legacy_db_path} to {db_path}")

        if project_id not in self.engines:
            # Create new engine for this project
            database_url = f"sqlite+aiosqlite:///{db_path}"
            engine = create_async_engine(
                database_url,
                echo=False,
                future=True,
                connect_args={"timeout": 30, "check_same_thread": False},
            )
            # Set pragmas for WAL mode
            event.listen(engine.sync_engine, "connect", _set_sqlite_pragma)

            # Create session maker
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            self.engines[project_id] = engine
            self.sessions[project_id] = async_session

            # Store additional metadata
            if not hasattr(self, 'project_metadata'):
                self.project_metadata = {}

            self.project_metadata[project_id] = {
                'path': project_path,
                'db_path': db_path
            }

            # Create tables if new database
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info(f"Initialized database for project at {project_path}")
            logger.info(f"Database location: {db_path}")

        self.current_project_id = project_id
        return project_id

    async def initialize_history_database(self):
        """Initialize the global project history database."""
        if self._history_engine is None:
            db_path = self.get_history_database_path()
            database_url = f"sqlite+aiosqlite:///{db_path}"
            self._history_engine = create_async_engine(
                database_url,
                echo=False,
                future=True,
                connect_args={"timeout": 30, "check_same_thread": False},
            )
            # Set pragmas for WAL mode
            event.listen(self._history_engine.sync_engine, "connect", _set_sqlite_pragma)

            self._history_session = sessionmaker(
                self._history_engine, class_=AsyncSession, expire_on_commit=False
            )

            # Import here to avoid circular imports
            from .models.project_history import Base as HistoryBase

            # Create tables
            async with self._history_engine.begin() as conn:
                await conn.run_sync(HistoryBase.metadata.create_all)

    def get_current_session(self):
        """
        Get session factory for current project.

        Returns:
            Session factory for the current project

        Raises:
            RuntimeError: If no project is loaded
        """
        if not self.current_project_id:
            raise RuntimeError("No project loaded")
        return self.sessions[self.current_project_id]

    def get_history_session(self):
        """
        Get session factory for history database.

        Returns:
            Session factory for the history database

        Raises:
            RuntimeError: If history database not initialized
        """
        if not self._history_session:
            raise RuntimeError("History database not initialized")
        return self._history_session

    def get_project_database_info(self, project_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get database information for a project.

        Args:
            project_path: Path to the project (optional, uses current if not provided)

        Returns:
            Dictionary with database information or None if project not found
        """
        if project_path:
            project_id = self.get_project_id(os.path.abspath(project_path))
        else:
            project_id = self.current_project_id

        if not project_id:
            return None

        # Check if we have metadata for this project
        if hasattr(self, 'project_metadata') and project_id in self.project_metadata:
            metadata = self.project_metadata[project_id]
            return {
                'database_path': metadata.get('db_path'),
                'project_path': metadata.get('path'),
                'is_active': project_id == self.current_project_id
            }

        return None

    def reset(self):
        """
        Reset database manager to initial state (no active project).
        This should be called when returning to root project.
        """
        logger.info("[DatabaseManager] Resetting to root project (no active project)")
        self.current_project_id = None

    async def close_all(self):
        """Close all database connections."""
        for engine in self.engines.values():
            await engine.dispose()

        if self._history_engine:
            await self._history_engine.dispose()

    async def cleanup_old_databases(self, days_old: int = 30, keep_count: int = 10):
        """
        Cleanup old project databases that haven't been accessed recently.

        Args:
            days_old: Remove databases older than this many days
            keep_count: Always keep at least this many most recent databases
        """
        # TODO: Implement cleanup logic based on last access time
        # This would query the history database and remove old project databases
        pass


# Global instance
db_manager = DatabaseManager()
