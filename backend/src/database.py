"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.pool import NullPool

from .config import get_settings

settings = get_settings()


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better concurrency."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=60000")  # 60 seconds timeout
    cursor.execute("PRAGMA wal_autocheckpoint=100")  # Checkpoint every 100 pages
    cursor.close()


# Create async engine with NullPool for SQLite
# NullPool creates a new connection per request - better for SQLite concurrency
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={"timeout": 60, "check_same_thread": False},
    poolclass=NullPool,  # No connection pooling - best for SQLite
)

# Set pragmas for WAL mode
event.listen(engine.sync_engine, "connect", _set_sqlite_pragma)

# Create async session factory (legacy - kept for backward compatibility)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


async def create_tables() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session():
    """
    Get session factory for current project.

    Returns:
        Session factory for the current project
    """
    from .database_manager import db_manager

    try:
        return db_manager.get_current_session()
    except RuntimeError:
        # Fallback to legacy session if no project loaded
        return async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session for current project."""
    session_factory = get_session()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_history_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session for project history."""
    from .database_manager import db_manager

    session_factory = db_manager.get_history_session()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
