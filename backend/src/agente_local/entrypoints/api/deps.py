"""FastAPI shared dependency providers."""
from __future__ import annotations

from collections.abc import AsyncGenerator
import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agente_local.application.ports.calendar_repository import CalendarRepositoryPort
from agente_local.application.ports.calendar_sync import CalendarSyncPort
from agente_local.application.ports.gmail_sync import GmailSyncPort
from agente_local.application.ports.sync_cursor import SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadRepositoryPort
from agente_local.infrastructure.calendar_sync import CalendarSyncAdapter
from agente_local.infrastructure.gmail_sync import GmailSyncAdapter
from agente_local.infrastructure.google_credentials import GoogleCredentialProvider
from agente_local.infrastructure.persistence.database import create_session_factory
from agente_local.infrastructure.persistence.repositories import (
    SqlAlchemyCalendarRepository,
    SqlAlchemySyncCursorRepository,
    SqlAlchemyThreadRepository,
)


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _build_google_credential_provider() -> GoogleCredentialProvider:
    _load_env_file()
    session_factory = create_session_factory()
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    token_uri = os.environ.get("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token").strip()
    return GoogleCredentialProvider(
        session_factory=session_factory,
        client_id=client_id,
        client_secret=client_secret,
        token_uri=token_uri,
    )


def get_missing_google_env_vars() -> list[str]:
    _load_env_file()
    missing_vars: list[str] = []
    for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
        value = os.environ.get(name, "").strip().lower()
        if value in {"", "change_me", "<tu_client_id>", "<tu_client_secret>"}:
            missing_vars.append(name)
    return missing_vars


async def _get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield one AsyncSession per request, auto-closed on exit."""
    async with create_session_factory()() as session:
        yield session


def _get_thread_repository() -> ThreadRepositoryPort:
    return SqlAlchemyThreadRepository(create_session_factory())


def _get_cursor_repository() -> SyncCursorPort:
    return SqlAlchemySyncCursorRepository(create_session_factory())



def _get_calendar_repository() -> CalendarRepositoryPort:
    return SqlAlchemyCalendarRepository(create_session_factory())


def _get_gmail_sync() -> GmailSyncPort:
    credential_provider = _build_google_credential_provider()
    return GmailSyncAdapter(credential_provider)


def _get_calendar_sync() -> CalendarSyncPort:
    credential_provider = _build_google_credential_provider()
    return CalendarSyncAdapter(credential_provider)


# Typed aliases — use these in endpoint signatures.
DbSession = Annotated[AsyncSession, Depends(_get_db_session)]
ThreadRepo = Annotated[ThreadRepositoryPort, Depends(_get_thread_repository)]
CursorRepo = Annotated[SyncCursorPort, Depends(_get_cursor_repository)]
CalendarRepo = Annotated[CalendarRepositoryPort, Depends(_get_calendar_repository)]
GmailSync = Annotated[GmailSyncPort, Depends(_get_gmail_sync)]
CalendarSync = Annotated[CalendarSyncPort, Depends(_get_calendar_sync)]
