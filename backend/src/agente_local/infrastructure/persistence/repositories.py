from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agente_local.application.ports.sync_cursor import CursorState, SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadEntity, ThreadRepositoryPort
from agente_local.infrastructure.persistence.models import GmailThreadModel, SyncCursorModel, SyncRunModel


def _to_thread_entity(model: GmailThreadModel) -> ThreadEntity:
    return ThreadEntity(
        id=str(model.id),
        account_id=str(model.account_id),
        gmail_thread_id=model.gmail_thread_id,
        subject_normalized=model.subject_normalized,
        message_count=model.message_count,
        has_unread=model.has_unread,
        agent_state=model.agent_state,
        triage_decision_id=None,
        draft_suggestion_id=None,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyThreadRepository(ThreadRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert(
        self,
        account_id: str,
        gmail_thread_id: str,
        subject: str | None,
        **fields: object,
    ) -> ThreadEntity:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GmailThreadModel).where(
                    GmailThreadModel.account_id == uuid.UUID(account_id),
                    GmailThreadModel.gmail_thread_id == gmail_thread_id,
                )
            )
            thread = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if thread is None:
                thread = GmailThreadModel(
                    id=uuid.uuid4(),
                    account_id=uuid.UUID(account_id),
                    gmail_thread_id=gmail_thread_id,
                    subject_normalized=subject,
                    message_count=int(fields.get("message_count", 0)),
                    participants_cache=fields.get("participants_cache", []),
                    labels_cache=fields.get("labels_cache", []),
                    has_unread=bool(fields.get("has_unread", False)),
                    is_starred=bool(fields.get("is_starred", False)),
                    is_important_label=bool(fields.get("is_important_label", False)),
                    last_history_id=fields.get("last_history_id"),
                    agent_state=str(fields.get("agent_state", "discovered")),
                    requires_response=fields.get("requires_response"),
                    last_message_at=fields.get("last_message_at"),
                    last_triaged_at=fields.get("last_triaged_at"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(thread)
            else:
                thread.subject_normalized = subject
                thread.message_count = int(fields.get("message_count", thread.message_count))
                thread.participants_cache = fields.get("participants_cache", thread.participants_cache)
                thread.labels_cache = fields.get("labels_cache", thread.labels_cache)
                thread.has_unread = bool(fields.get("has_unread", thread.has_unread))
                thread.is_starred = bool(fields.get("is_starred", thread.is_starred))
                thread.is_important_label = bool(fields.get("is_important_label", thread.is_important_label))
                thread.last_history_id = fields.get("last_history_id", thread.last_history_id)
                thread.agent_state = str(fields.get("agent_state", thread.agent_state))
                thread.requires_response = fields.get("requires_response", thread.requires_response)
                thread.last_message_at = fields.get("last_message_at", thread.last_message_at)
                thread.last_triaged_at = fields.get("last_triaged_at", thread.last_triaged_at)
                thread.updated_at = now

            await session.commit()
            await session.refresh(thread)
            return _to_thread_entity(thread)

    async def get_by_id(self, thread_id: str) -> ThreadEntity | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GmailThreadModel).where(GmailThreadModel.id == uuid.UUID(thread_id))
            )
            model = result.scalar_one_or_none()
            return None if model is None else _to_thread_entity(model)

    async def get_by_gmail_id(self, account_id: str, gmail_thread_id: str) -> ThreadEntity | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GmailThreadModel).where(
                    GmailThreadModel.account_id == uuid.UUID(account_id),
                    GmailThreadModel.gmail_thread_id == gmail_thread_id,
                )
            )
            model = result.scalar_one_or_none()
            return None if model is None else _to_thread_entity(model)

    async def list_by_state(self, account_id: str, state: str, limit: int = 100) -> list[ThreadEntity]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GmailThreadModel)
                .where(
                    GmailThreadModel.account_id == uuid.UUID(account_id),
                    GmailThreadModel.agent_state == state,
                )
                .order_by(GmailThreadModel.last_message_at.desc().nullslast(), GmailThreadModel.created_at.desc())
                .limit(limit)
            )
            return [_to_thread_entity(model) for model in result.scalars().all()]

    async def update_state(self, thread_id: str, new_state: str) -> ThreadEntity:
        async with self._session_factory() as session:
            result = await session.execute(
                select(GmailThreadModel).where(GmailThreadModel.id == uuid.UUID(thread_id))
            )
            thread = result.scalar_one()
            thread.agent_state = new_state
            thread.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(thread)
            return _to_thread_entity(thread)


class SqlAlchemySyncCursorRepository(SyncCursorPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_cursor(self, account_id: str, resource_type: str, resource_key: str) -> CursorState:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SyncCursorModel).where(
                    SyncCursorModel.account_id == uuid.UUID(account_id),
                    SyncCursorModel.resource_type == resource_type,
                    SyncCursorModel.resource_key == resource_key,
                )
            )
            cursor = result.scalar_one_or_none()
            runs_count = await self._count_runs(session, account_id, resource_type, resource_key)

            if cursor is None:
                return CursorState(
                    value=None,
                    status="requires_full_resync",
                    last_synced_at=None,
                    runs_count=runs_count,
                )

            return CursorState(
                value=cursor.cursor_value,
                status=cursor.cursor_status,
                last_synced_at=cursor.last_synced_at,
                runs_count=runs_count,
            )

    async def update_cursor(
        self,
        account_id: str,
        resource_type: str,
        resource_key: str,
        cursor_value: str | None,
        new_status: str,
        sync_run_id: str,
    ) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SyncCursorModel).where(
                    SyncCursorModel.account_id == uuid.UUID(account_id),
                    SyncCursorModel.resource_type == resource_type,
                    SyncCursorModel.resource_key == resource_key,
                )
            )
            cursor = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if cursor is None:
                cursor = SyncCursorModel(
                    id=uuid.uuid4(),
                    account_id=uuid.UUID(account_id),
                    resource_type=resource_type,
                    resource_key=resource_key,
                    cursor_value=cursor_value,
                    cursor_status=new_status,
                    last_synced_at=now,
                    last_successful_run_id=uuid.UUID(sync_run_id),
                    updated_at=now,
                    created_at=now,
                )
                session.add(cursor)
            else:
                cursor.cursor_value = cursor_value
                cursor.cursor_status = new_status
                cursor.last_synced_at = now
                cursor.last_successful_run_id = uuid.UUID(sync_run_id)
                cursor.updated_at = now

            await session.commit()

    async def mark_stale(self, account_id: str, resource_type: str, resource_key: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SyncCursorModel).where(
                    SyncCursorModel.account_id == uuid.UUID(account_id),
                    SyncCursorModel.resource_type == resource_type,
                    SyncCursorModel.resource_key == resource_key,
                )
            )
            cursor = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if cursor is None:
                cursor = SyncCursorModel(
                    id=uuid.uuid4(),
                    account_id=uuid.UUID(account_id),
                    resource_type=resource_type,
                    resource_key=resource_key,
                    cursor_value=None,
                    cursor_status="stale",
                    last_synced_at=None,
                    last_successful_run_id=None,
                    updated_at=now,
                    created_at=now,
                )
                session.add(cursor)
            else:
                cursor.cursor_status = "stale"
                cursor.updated_at = now

            await session.commit()

    async def _count_runs(
        self,
        session: AsyncSession,
        account_id: str,
        resource_type: str,
        resource_key: str,
    ) -> int:
        result = await session.execute(
            select(func.count(SyncRunModel.id)).where(
                SyncRunModel.account_id == uuid.UUID(account_id),
                SyncRunModel.resource_type == resource_type,
                SyncRunModel.resource_key == resource_key,
            )
        )
        return int(result.scalar_one())