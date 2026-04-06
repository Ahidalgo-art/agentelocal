from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agente_local.application.ports.calendar_repository import (
    CalendarEventEntity,
    CalendarRepositoryPort,
    CalendarSourceEntity,
)
from agente_local.application.ports.sync_cursor import CursorState, SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadEntity, ThreadRepositoryPort
from agente_local.infrastructure.persistence.models import (
    CalendarEventModel,
    CalendarSourceModel,
    GmailThreadModel,
    SyncCursorModel,
    SyncRunModel,
)


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


def _to_calendar_source_entity(model: CalendarSourceModel) -> CalendarSourceEntity:
    return CalendarSourceEntity(
        id=str(model.id),
        account_id=str(model.account_id),
        google_calendar_id=model.google_calendar_id,
        summary=model.summary,
        primary_flag=model.primary_flag,
        selected_flag=model.selected_flag,
        timezone=model.timezone,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_calendar_event_entity(model: CalendarEventModel) -> CalendarEventEntity:
    return CalendarEventEntity(
        id=str(model.id),
        calendar_source_id=str(model.calendar_source_id),
        google_event_id=model.google_event_id,
        status=model.status,
        summary=model.summary,
        description=model.description,
        organizer_email=model.organizer_email,
        attendees_json=model.attendees_json,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        all_day=model.all_day,
        location=model.location,
        meet_link=model.meet_link,
        etag=model.etag,
        updated_remote_at=model.updated_remote_at,
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


class SqlAlchemyCalendarRepository(CalendarRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_calendar_source(
        self,
        account_id: str,
        google_calendar_id: str,
        **fields: object,
    ) -> CalendarSourceEntity:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CalendarSourceModel).where(
                    CalendarSourceModel.account_id == uuid.UUID(account_id),
                    CalendarSourceModel.google_calendar_id == google_calendar_id,
                )
            )
            source = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if source is None:
                source = CalendarSourceModel(
                    id=uuid.uuid4(),
                    account_id=uuid.UUID(account_id),
                    google_calendar_id=google_calendar_id,
                    summary=fields.get("summary"),
                    primary_flag=bool(fields.get("primary_flag", False)),
                    selected_flag=bool(fields.get("selected_flag", True)),
                    timezone=fields.get("timezone"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(source)
            else:
                source.summary = fields.get("summary", source.summary)
                source.primary_flag = bool(fields.get("primary_flag", source.primary_flag))
                source.selected_flag = bool(fields.get("selected_flag", source.selected_flag))
                source.timezone = fields.get("timezone", source.timezone)
                source.updated_at = now

            await session.commit()
            await session.refresh(source)
            return _to_calendar_source_entity(source)

    async def get_calendar_source(self, account_id: str, google_calendar_id: str) -> CalendarSourceEntity | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CalendarSourceModel).where(
                    CalendarSourceModel.account_id == uuid.UUID(account_id),
                    CalendarSourceModel.google_calendar_id == google_calendar_id,
                )
            )
            source = result.scalar_one_or_none()
            return None if source is None else _to_calendar_source_entity(source)

    async def upsert_calendar_event(
        self,
        calendar_source_id: str,
        google_event_id: str,
        **fields: object,
    ) -> CalendarEventEntity:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CalendarEventModel).where(
                    CalendarEventModel.calendar_source_id == uuid.UUID(calendar_source_id),
                    CalendarEventModel.google_event_id == google_event_id,
                )
            )
            event = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if event is None:
                event = CalendarEventModel(
                    id=uuid.uuid4(),
                    calendar_source_id=uuid.UUID(calendar_source_id),
                    google_event_id=google_event_id,
                    status=str(fields.get("status", "confirmed")),
                    summary=fields.get("summary"),
                    description=fields.get("description"),
                    organizer_email=fields.get("organizer_email"),
                    attendees_json=list(fields.get("attendees_json", [])),
                    starts_at=fields.get("starts_at"),
                    ends_at=fields.get("ends_at"),
                    all_day=bool(fields.get("all_day", False)),
                    location=fields.get("location"),
                    meet_link=fields.get("meet_link"),
                    etag=fields.get("etag"),
                    updated_remote_at=fields.get("updated_remote_at"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(event)
            else:
                event.status = str(fields.get("status", event.status))
                event.summary = fields.get("summary", event.summary)
                event.description = fields.get("description", event.description)
                event.organizer_email = fields.get("organizer_email", event.organizer_email)
                event.attendees_json = list(fields.get("attendees_json", event.attendees_json))
                event.starts_at = fields.get("starts_at", event.starts_at)
                event.ends_at = fields.get("ends_at", event.ends_at)
                event.all_day = bool(fields.get("all_day", event.all_day))
                event.location = fields.get("location", event.location)
                event.meet_link = fields.get("meet_link", event.meet_link)
                event.etag = fields.get("etag", event.etag)
                event.updated_remote_at = fields.get("updated_remote_at", event.updated_remote_at)
                event.updated_at = now

            await session.commit()
            await session.refresh(event)
            return _to_calendar_event_entity(event)


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