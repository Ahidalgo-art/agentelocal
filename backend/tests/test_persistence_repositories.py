from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete

from agente_local.infrastructure.persistence.database import create_session_factory
from agente_local.infrastructure.persistence.models import (
    CalendarEventModel,
    CalendarSourceModel,
    GmailThreadModel,
    SyncCursorModel,
    SyncRunModel,
    WorkspaceAccountModel,
)
from agente_local.infrastructure.persistence.repositories import (
    SqlAlchemyCalendarRepository,
    SqlAlchemySyncCursorRepository,
    SqlAlchemyThreadRepository,
)


@pytest.mark.asyncio
async def test_thread_repository_crud_against_postgres() -> None:
    session_factory = create_session_factory()
    repository = SqlAlchemyThreadRepository(session_factory)
    account_id = uuid.uuid4()
    thread_id: str | None = None

    async with session_factory() as session:
        session.add(
            WorkspaceAccountModel(
                id=account_id,
                external_account_email=f"{account_id}@example.com",
                display_name="Agent Local",
            )
        )
        await session.commit()

    try:
        created = await repository.upsert(
            account_id=str(account_id),
            gmail_thread_id="gmail-thread-42",
            subject="Initial subject",
            message_count=2,
            has_unread=True,
            agent_state="discovered",
            participants_cache=[{"email": "user@example.com"}],
            labels_cache=["INBOX"],
            last_message_at=datetime.now(timezone.utc),
        )
        thread_id = created.id

        fetched_by_id = await repository.get_by_id(created.id)
        fetched_by_gmail = await repository.get_by_gmail_id(str(account_id), "gmail-thread-42")
        listed = await repository.list_by_state(str(account_id), "discovered")
        updated = await repository.update_state(created.id, "triaged")

        assert created.gmail_thread_id == "gmail-thread-42"
        assert created.has_unread is True
        assert fetched_by_id is not None
        assert fetched_by_id.subject_normalized == "Initial subject"
        assert fetched_by_gmail is not None
        assert fetched_by_gmail.id == created.id
        assert len(listed) == 1
        assert listed[0].id == created.id
        assert updated.agent_state == "triaged"
    finally:
        async with session_factory() as session:
            if thread_id is not None:
                await session.execute(delete(GmailThreadModel).where(GmailThreadModel.id == uuid.UUID(thread_id)))
            await session.execute(delete(WorkspaceAccountModel).where(WorkspaceAccountModel.id == account_id))
            await session.commit()


@pytest.mark.asyncio
async def test_calendar_repository_upserts_sources_and_events_against_postgres() -> None:
    session_factory = create_session_factory()
    repository = SqlAlchemyCalendarRepository(session_factory)
    account_id = uuid.uuid4()
    source_id: str | None = None

    async with session_factory() as session:
        session.add(
            WorkspaceAccountModel(
                id=account_id,
                external_account_email=f"{account_id}@example.com",
                display_name="Agent Local",
            )
        )
        await session.commit()

    try:
        source = await repository.upsert_calendar_source(
            account_id=str(account_id),
            google_calendar_id="primary",
            summary="Primary",
            primary_flag=True,
            selected_flag=True,
            timezone="UTC",
        )
        fetched_source = await repository.get_calendar_source(str(account_id), "primary")
        event = await repository.upsert_calendar_event(
            calendar_source_id=source.id,
            google_event_id="event-42",
            status="confirmed",
            summary="Demo",
            organizer_email="owner@example.com",
            attendees_json=[{"email": "a@example.com", "response_status": "accepted"}],
            all_day=False,
        )

        source_id = source.id

        assert source.google_calendar_id == "primary"
        assert fetched_source is not None
        assert fetched_source.id == source.id
        assert event.google_event_id == "event-42"
        assert event.status == "confirmed"
    finally:
        async with session_factory() as session:
            if source_id is not None:
                await session.execute(
                    delete(CalendarEventModel).where(
                        CalendarEventModel.calendar_source_id == uuid.UUID(source_id)
                    )
                )
            await session.execute(
                delete(CalendarSourceModel).where(CalendarSourceModel.account_id == account_id)
            )
            await session.execute(delete(WorkspaceAccountModel).where(WorkspaceAccountModel.id == account_id))
            await session.commit()


@pytest.mark.asyncio
async def test_sync_cursor_repository_tracks_cursor_state_against_postgres() -> None:
    session_factory = create_session_factory()
    repository = SqlAlchemySyncCursorRepository(session_factory)
    account_id = uuid.uuid4()
    sync_run_id = uuid.uuid4()

    async with session_factory() as session:
        session.add(
            WorkspaceAccountModel(
                id=account_id,
                external_account_email=f"{account_id}@example.com",
                display_name="Agent Local",
            )
        )
        await session.commit()

        session.add(
            SyncRunModel(
                id=sync_run_id,
                account_id=account_id,
                resource_type="gmail_history",
                resource_key="inbox",
                mode="incremental",
                status="success",
                finished_at=datetime.now(timezone.utc),
                meta_json={"source": "test"},
            )
        )
        await session.commit()

    try:
        initial = await repository.get_cursor(str(account_id), "gmail_history", "inbox")
        await repository.update_cursor(
            str(account_id),
            "gmail_history",
            "inbox",
            "history-123",
            "valid",
            str(sync_run_id),
        )
        updated = await repository.get_cursor(str(account_id), "gmail_history", "inbox")
        await repository.mark_stale(str(account_id), "gmail_history", "inbox")
        stale = await repository.get_cursor(str(account_id), "gmail_history", "inbox")

        assert initial.status == "requires_full_resync"
        assert initial.runs_count == 1
        assert updated.value == "history-123"
        assert updated.status == "valid"
        assert updated.last_synced_at is not None
        assert stale.status == "stale"
        assert stale.runs_count == 1
    finally:
        async with session_factory() as session:
            await session.execute(delete(SyncCursorModel).where(SyncCursorModel.account_id == account_id))
            await session.execute(delete(SyncRunModel).where(SyncRunModel.id == sync_run_id))
            await session.execute(delete(WorkspaceAccountModel).where(WorkspaceAccountModel.id == account_id))
            await session.commit()