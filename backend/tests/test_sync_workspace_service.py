from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from agente_local.application.ports.calendar_repository import (
    CalendarEventEntity,
    CalendarRepositoryPort,
    CalendarSourceEntity,
)
from agente_local.application.ports.calendar_sync import (
    CalendarEvent,
    CalendarSyncPort,
    CalendarSyncTokenExpiredError,
)
from agente_local.application.ports.gmail_sync import EmailThread, GmailSyncPort
from agente_local.application.ports.sync_cursor import CursorState, SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadEntity, ThreadRepositoryPort
from agente_local.application.services.sync_workspace_service import SyncWorkspaceService


@dataclass(frozen=True)
class _RecordedCursorUpdate:
    resource_type: str
    resource_key: str
    cursor_value: str | None
    new_status: str
    sync_run_id: str


class _FakeCursorRepository(SyncCursorPort):
    def __init__(self) -> None:
        self.states: dict[tuple[str, str], CursorState] = {
            ("gmail_history", "inbox"): CursorState(
                value="history-100",
                status="valid",
                last_synced_at=None,
                runs_count=3,
            ),
            ("calendar_sync", "primary"): CursorState(
                value="token-aaa",
                status="valid",
                last_synced_at=None,
                runs_count=3,
            ),
            ("calendar_sync", "team"): CursorState(
                value=None,
                status="requires_full_resync",
                last_synced_at=None,
                runs_count=0,
            ),
        }
        self.updates: list[_RecordedCursorUpdate] = []
        self.stale_marks: list[tuple[str, str]] = []

    async def get_cursor(self, account_id: str, resource_type: str, resource_key: str) -> CursorState:
        return self.states.get(
            (resource_type, resource_key),
            CursorState(value=None, status="requires_full_resync", last_synced_at=None, runs_count=0),
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
        self.updates.append(
            _RecordedCursorUpdate(
                resource_type=resource_type,
                resource_key=resource_key,
                cursor_value=cursor_value,
                new_status=new_status,
                sync_run_id=sync_run_id,
            )
        )

    async def mark_stale(self, account_id: str, resource_type: str, resource_key: str) -> None:
        self.stale_marks.append((resource_type, resource_key))
        self.states[(resource_type, resource_key)] = CursorState(
            value=None,
            status="stale",
            last_synced_at=None,
            runs_count=0,
        )


class _FakeGmailSync(GmailSyncPort):
    def __init__(self) -> None:
        self.received_history_id: str | None = None

    async def list_threads(
        self,
        account_id: str,
        history_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list[EmailThread], str | None]:
        self.received_history_id = history_id
        return (
            [
                EmailThread(
                    gmail_thread_id="thread-1",
                    subject_normalized="Subject 1",
                    last_message_at=datetime.now(timezone.utc),
                    message_count=2,
                    has_unread=True,
                    is_important_label=False,
                    participants_cache={"user@example.com": "User"},
                ),
                EmailThread(
                    gmail_thread_id="thread-2",
                    subject_normalized="Subject 2",
                    last_message_at=datetime.now(timezone.utc),
                    message_count=1,
                    has_unread=False,
                    is_important_label=True,
                    participants_cache={"other@example.com": "Other"},
                ),
            ],
            "history-101",
        )

    async def get_thread_messages(self, account_id: str, thread_id: str):
        return []

    async def get_message_full(self, account_id: str, message_id: str):
        return {}

    async def mark_as_read(self, account_id: str, message_ids: list[str]) -> None:
        return None


class _FakeCalendarSync(CalendarSyncPort):
    def __init__(self) -> None:
        self.received_sync_tokens: dict[str, str | None] = {}

    async def list_calendars(self, account_id: str) -> list[dict]:
        return [{"id": "primary"}, {"id": "team"}]

    async def list_events(
        self,
        account_id: str,
        calendar_id: str,
        sync_token: str | None = None,
        time_min=None,
        time_max=None,
    ) -> tuple[list[CalendarEvent], str | None]:
        self.received_sync_tokens[calendar_id] = sync_token

        events = [
            CalendarEvent(
                google_event_id=f"evt-{calendar_id}",
                status="confirmed",
                summary="Meeting",
                organizer_email="owner@example.com",
                attendees=[],
                starts_at=None,
                ends_at=None,
                all_day=False,
                location=None,
                meet_link=None,
            )
        ]
        next_token = "token-bbb" if calendar_id == "primary" else "token-ccc"
        return events, next_token


class _FakeCalendarSyncTokenExpired(CalendarSyncPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def list_calendars(self, account_id: str) -> list[dict]:
        return [{"id": "primary"}]

    async def list_events(
        self,
        account_id: str,
        calendar_id: str,
        sync_token: str | None = None,
        time_min=None,
        time_max=None,
    ) -> tuple[list[CalendarEvent], str | None]:
        self.calls.append((calendar_id, sync_token))
        if sync_token is not None:
            raise CalendarSyncTokenExpiredError("expired")

        return (
            [
                CalendarEvent(
                    google_event_id="evt-primary-full",
                    status="confirmed",
                    summary="Recovered",
                    organizer_email="owner@example.com",
                    attendees=[],
                    starts_at=None,
                    ends_at=None,
                    all_day=False,
                    location=None,
                    meet_link=None,
                )
            ],
            "token-after-full",
        )


class _FakeThreadRepository(ThreadRepositoryPort):
    def __init__(self) -> None:
        self.upsert_calls: list[tuple[str, str]] = []

    async def upsert(self, account_id: str, gmail_thread_id: str, subject: str | None, **fields):
        self.upsert_calls.append((account_id, gmail_thread_id))
        now = datetime.now(timezone.utc)
        return ThreadEntity(
            id=f"id-{gmail_thread_id}",
            account_id=account_id,
            gmail_thread_id=gmail_thread_id,
            subject_normalized=subject,
            message_count=int(fields.get("message_count", 0)),
            has_unread=bool(fields.get("has_unread", False)),
            agent_state=str(fields.get("agent_state", "synced")),
            triage_decision_id=None,
            draft_suggestion_id=None,
            created_at=now,
            updated_at=now,
        )

    async def get_by_id(self, thread_id: str):
        return None

    async def get_by_gmail_id(self, account_id: str, gmail_thread_id: str):
        return None

    async def list_by_state(self, account_id: str, state: str, limit: int = 100):
        return []

    async def update_state(self, thread_id: str, new_state: str):
        raise NotImplementedError


class _FakeCalendarRepository(CalendarRepositoryPort):
    def __init__(self) -> None:
        self.sources_upserted: list[str] = []
        self.events_upserted: list[tuple[str, str]] = []

    async def upsert_calendar_source(self, account_id: str, google_calendar_id: str, **fields):
        self.sources_upserted.append(google_calendar_id)
        now = datetime.now(timezone.utc)
        return CalendarSourceEntity(
            id=f"source-{google_calendar_id}",
            account_id=account_id,
            google_calendar_id=google_calendar_id,
            summary=fields.get("summary"),
            primary_flag=bool(fields.get("primary_flag", False)),
            selected_flag=bool(fields.get("selected_flag", True)),
            timezone=fields.get("timezone"),
            created_at=now,
            updated_at=now,
        )

    async def get_calendar_source(self, account_id: str, google_calendar_id: str):
        return None

    async def upsert_calendar_event(self, calendar_source_id: str, google_event_id: str, **fields):
        self.events_upserted.append((calendar_source_id, google_event_id))
        now = datetime.now(timezone.utc)
        return CalendarEventEntity(
            id=f"event-{google_event_id}",
            calendar_source_id=calendar_source_id,
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


@pytest.mark.asyncio
async def test_sync_workspace_service_executes_incremental_sync() -> None:
    cursor_repo = _FakeCursorRepository()
    gmail_sync = _FakeGmailSync()
    calendar_sync = _FakeCalendarSync()
    thread_repo = _FakeThreadRepository()
    calendar_repo = _FakeCalendarRepository()

    service = SyncWorkspaceService(
        gmail_sync=gmail_sync,
        calendar_sync=calendar_sync,
        cursor_repository=cursor_repo,
        thread_repository=thread_repo,
        calendar_repository=calendar_repo,
    )

    result = await service.execute(account_id="account-1", sync_run_id="run-123")

    assert result.gmail_threads_seen == 2
    assert result.calendars_seen == 2
    assert result.calendar_events_seen == 2
    assert result.gmail_cursor_updated is True
    assert result.calendar_cursors_updated == 2

    assert gmail_sync.received_history_id == "history-100"
    assert calendar_sync.received_sync_tokens["primary"] == "token-aaa"
    assert calendar_sync.received_sync_tokens["team"] is None

    updated_keys = {(u.resource_type, u.resource_key) for u in cursor_repo.updates}
    assert ("gmail_history", "inbox") in updated_keys
    assert ("calendar_sync", "primary") in updated_keys
    assert ("calendar_sync", "team") in updated_keys

    assert len(thread_repo.upsert_calls) == 2
    assert calendar_repo.sources_upserted == ["primary", "team"]
    assert len(calendar_repo.events_upserted) == 2


@pytest.mark.asyncio
async def test_sync_workspace_service_recovers_from_expired_calendar_token() -> None:
    cursor_repo = _FakeCursorRepository()
    gmail_sync = _FakeGmailSync()
    calendar_sync = _FakeCalendarSyncTokenExpired()
    thread_repo = _FakeThreadRepository()
    calendar_repo = _FakeCalendarRepository()

    service = SyncWorkspaceService(
        gmail_sync=gmail_sync,
        calendar_sync=calendar_sync,
        cursor_repository=cursor_repo,
        thread_repository=thread_repo,
        calendar_repository=calendar_repo,
    )

    result = await service.execute(account_id="account-1", sync_run_id="run-456")

    assert result.calendars_seen == 1
    assert result.calendar_events_seen == 1
    assert result.calendar_cursors_updated == 1
    assert ("calendar_sync", "primary") in cursor_repo.stale_marks
    assert calendar_sync.calls == [("primary", "token-aaa"), ("primary", None)]
