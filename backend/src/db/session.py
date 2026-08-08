"""Gerenciamento de sessão assíncrona com AsyncPG.

A engine assíncrona conduz o caminho de request (FastAPI). Sessões são
configuradas com expire_on_commit=False para evitar MissingGreenlet quando
o FastAPI serializa o response em JSON após o commit (SQLAlchemy lazy-load
num contexto async levanta a exceção).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings


class DatabaseManagerNotInitializedError(RuntimeError):
    """Levantado quando o manager é usado após close() ter sido chamado."""

    def __init__(self) -> None:
        super().__init__("DatabaseSessionManager não está inicializado")


class DatabaseSessionManager:
    """Gerenciador centralizado da engine e fábrica de sessões assíncronas."""

    def __init__(self, host: str, engine_kwargs: dict[str, Any] | None = None) -> None:
        kwargs: dict[str, Any] = dict(engine_kwargs or {})
        self._engine: AsyncEngine | None = create_async_engine(
            host,
            **kwargs,
            pool_pre_ping=True,
            future=True,
        )
        # expire_on_commit=False é crítico - sem ele SQLAlchemy dispara IO
        # durante a serialização em contextos async (MissingGreenlet).
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise DatabaseManagerNotInitializedError
        return self._engine

    async def close(self) -> None:
        if self._engine is None:
            raise DatabaseManagerNotInitializedError
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection]:
        if self._engine is None:
            raise DatabaseManagerNotInitializedError
        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        if self._sessionmaker is None:
            raise DatabaseManagerNotInitializedError
        session: AsyncSession = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.database_url)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: fornece uma sessão async por request."""
    async with sessionmanager.session() as session:
        yield session
