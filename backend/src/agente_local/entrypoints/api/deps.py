"""FastAPI shared dependency providers."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agente_local.application.ports.sync_cursor import SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadRepositoryPort
from agente_local.infrastructure.persistence.database import create_session_factory
from agente_local.infrastructure.persistence.repositories import (
    SqlAlchemySyncCursorRepository,
    SqlAlchemyThreadRepository,
)


async def _get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield one AsyncSession per request, auto-closed on exit."""
    async with create_session_factory()() as session:
        yield session


def _get_thread_repository() -> ThreadRepositoryPort:
    return SqlAlchemyThreadRepository(create_session_factory())


def _get_cursor_repository() -> SyncCursorPort:
    return SqlAlchemySyncCursorRepository(create_session_factory())


# Typed aliases — use these in endpoint signatures.
DbSession = Annotated[AsyncSession, Depends(_get_db_session)]
ThreadRepo = Annotated[ThreadRepositoryPort, Depends(_get_thread_repository)]
CursorRepo = Annotated[SyncCursorPort, Depends(_get_cursor_repository)]
