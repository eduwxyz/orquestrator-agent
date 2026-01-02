"""Database manager for multi-project database isolation."""

import hashlib
from pathlib import Path
from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from .database import Base


class DatabaseManager:
    """Manages multiple isolated databases, one per project."""

    def __init__(self, base_data_dir: str = ".project_data"):
        """
        Initialize the database manager.

        Args:
            base_data_dir: Base directory for storing project databases
        """
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
        project_id = self.get_project_id(project_path)
        db_path = self.get_database_path(project_id)

        if project_id not in self.engines:
            # Create new engine for this project
            database_url = f"sqlite+aiosqlite:///{db_path}"
            engine = create_async_engine(database_url, echo=False, future=True)

            # Create session maker
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            self.engines[project_id] = engine
            self.sessions[project_id] = async_session

            # Create tables if new database
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        self.current_project_id = project_id
        return project_id

    async def initialize_history_database(self):
        """Initialize the global project history database."""
        if self._history_engine is None:
            db_path = self.get_history_database_path()
            database_url = f"sqlite+aiosqlite:///{db_path}"
            self._history_engine = create_async_engine(
                database_url, echo=False, future=True
            )

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
