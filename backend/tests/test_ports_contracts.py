from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agente_local.application import ports
from agente_local.application.ports.calendar_repository import (
    CalendarEventEntity,
    CalendarRepositoryPort,
    CalendarSourceEntity,
)
from agente_local.application.ports.calendar_sync import CalendarEvent, CalendarSyncPort
from agente_local.application.ports.drafting_service import DraftProposal, DraftingServicePort
from agente_local.application.ports.gmail_sync import EmailMessage, EmailThread, GmailSyncPort
from agente_local.application.ports.sync_cursor import CursorState, SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadEntity, ThreadRepositoryPort
from agente_local.application.ports.triage_service import TriageResult, TriageServicePort


class DummySyncCursorPort(SyncCursorPort):
    async def get_cursor(self, account_id: str, resource_type: str, resource_key: str) -> CursorState:
        return CursorState(
            value=f"{account_id}:{resource_type}:{resource_key}",
            status="valid",
            last_synced_at=None,
            runs_count=1,
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
        return None

    async def mark_stale(self, account_id: str, resource_type: str, resource_key: str) -> None:
        return None


class DummyThreadRepositoryPort(ThreadRepositoryPort):
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.thread = ThreadEntity(
            id="thread-1",
            account_id="account-1",
            gmail_thread_id="gmail-1",
            subject_normalized="subject",
            message_count=2,
            has_unread=True,
            agent_state="discovered",
            triage_decision_id=None,
            draft_suggestion_id=None,
            created_at=now,
            updated_at=now,
        )

    async def upsert(
        self,
        account_id: str,
        gmail_thread_id: str,
        subject: str | None,
        **fields: object,
    ) -> ThreadEntity:
        return self.thread

    async def get_by_id(self, thread_id: str) -> ThreadEntity | None:
        return self.thread if thread_id == self.thread.id else None

    async def get_by_gmail_id(self, account_id: str, gmail_thread_id: str) -> ThreadEntity | None:
        if account_id == self.thread.account_id and gmail_thread_id == self.thread.gmail_thread_id:
            return self.thread
        return None

    async def list_by_state(
        self,
        account_id: str,
        state: str,
        limit: int = 100,
    ) -> list[ThreadEntity]:
        if account_id == self.thread.account_id and state == self.thread.agent_state and limit > 0:
            return [self.thread]
        return []

    async def update_state(self, thread_id: str, new_state: str) -> ThreadEntity:
        return ThreadEntity(
            id=self.thread.id,
            account_id=self.thread.account_id,
            gmail_thread_id=self.thread.gmail_thread_id,
            subject_normalized=self.thread.subject_normalized,
            message_count=self.thread.message_count,
            has_unread=self.thread.has_unread,
            agent_state=new_state,
            triage_decision_id=self.thread.triage_decision_id,
            draft_suggestion_id=self.thread.draft_suggestion_id,
            created_at=self.thread.created_at,
            updated_at=self.thread.updated_at,
        )


class DummyGmailSyncPort(GmailSyncPort):
    async def list_threads(
        self,
        account_id: str,
        history_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list[EmailThread], str | None]:
        return (
            [
                EmailThread(
                    gmail_thread_id="gmail-thread-1",
                    subject_normalized="hello",
                    last_message_at=datetime.now(timezone.utc),
                    message_count=1,
                    has_unread=True,
                    is_important_label=False,
                    participants_cache={"user@example.com": "User"},
                )
            ],
            "next-history-id",
        )

    async def get_thread_messages(self, account_id: str, thread_id: str) -> list[EmailMessage]:
        return [
            EmailMessage(
                gmail_message_id="gmail-message-1",
                gmail_internal_date_at=datetime.now(timezone.utc),
                sender_email="sender@example.com",
                snippet="snippet",
                is_inbound=True,
                labels=["INBOX"],
            )
        ]

    async def get_message_full(self, account_id: str, message_id: str) -> dict:
        return {"body_text": "text", "body_html": "<p>text</p>", "headers_json": {"x": "1"}}

    async def mark_as_read(self, account_id: str, message_ids: list[str]) -> None:
        return None


class DummyCalendarSyncPort(CalendarSyncPort):
    async def list_calendars(self, account_id: str) -> list[dict]:
        return [{"id": "primary", "summary": "Primary", "primary_flag": True}]

    async def list_events(
        self,
        account_id: str,
        calendar_id: str,
        sync_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> tuple[list[CalendarEvent], str | None]:
        return (
            [
                CalendarEvent(
                    google_event_id="event-1",
                    status="confirmed",
                    summary="Meeting",
                    organizer_email="owner@example.com",
                    attendees=[{"email": "a@example.com", "response_status": "accepted"}],
                    starts_at=time_min,
                    ends_at=time_max,
                    all_day=False,
                    location="Office",
                    meet_link="https://meet.google.com/example",
                )
            ],
            "next-sync-token",
        )


class DummyCalendarRepositoryPort(CalendarRepositoryPort):
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.source = CalendarSourceEntity(
            id="source-1",
            account_id="account-1",
            google_calendar_id="primary",
            summary="Primary",
            primary_flag=True,
            selected_flag=True,
            timezone="UTC",
            created_at=now,
            updated_at=now,
        )

    async def upsert_calendar_source(self, account_id: str, google_calendar_id: str, **fields):
        now = datetime.now(timezone.utc)
        return CalendarSourceEntity(
            id=self.source.id,
            account_id=account_id,
            google_calendar_id=google_calendar_id,
            summary=fields.get("summary"),
            primary_flag=bool(fields.get("primary_flag", True)),
            selected_flag=bool(fields.get("selected_flag", True)),
            timezone=fields.get("timezone"),
            created_at=now,
            updated_at=now,
        )

    async def get_calendar_source(self, account_id: str, google_calendar_id: str):
        if account_id == self.source.account_id and google_calendar_id == self.source.google_calendar_id:
            return self.source
        return None

    async def upsert_calendar_event(self, calendar_source_id: str, google_event_id: str, **fields):
        now = datetime.now(timezone.utc)
        return CalendarEventEntity(
            id="event-1",
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


class DummyTriageServicePort(TriageServicePort):
    async def score_thread(
        self,
        thread_id: str,
        participants: list[str],
        subject: str,
        latest_snippet: str,
        calendar_context: dict,
    ) -> TriageResult:
        return TriageResult(
            thread_id=thread_id,
            importance_score=0.9,
            confidence_score=0.8,
            priority_bucket="high",
            requires_response=True,
            reasons=["vip-sender"],
            signals={"participants": participants, "calendar": calendar_context},
        )


class DummyDraftingServicePort(DraftingServicePort):
    async def propose_draft(
        self,
        thread_id: str,
        subject: str,
        latest_sender: str,
        message_snippet: str,
        calendar_context: dict,
    ) -> DraftProposal:
        return DraftProposal(
            thread_id=thread_id,
            intent="acknowledge",
            summary_for_user="Reply with acknowledgement",
            why_this_reply="The request is clear",
            draft_subject=subject,
            draft_body_text=f"Thanks {latest_sender}",
            confidence_score=0.75,
        )


def test_ports_namespace_exports_expected_symbols() -> None:
    expected = {
        "CursorState",
        "SyncCursorPort",
        "EmailThread",
        "EmailMessage",
        "GmailSyncPort",
        "CalendarEvent",
        "CalendarSyncPort",
        "CalendarSyncTokenExpiredError",
        "CalendarSourceEntity",
        "CalendarEventEntity",
        "CalendarRepositoryPort",
        "ThreadEntity",
        "ThreadRepositoryPort",
        "TriageResult",
        "TriageServicePort",
        "DraftProposal",
        "DraftingServicePort",
    }

    assert set(ports.__all__) == expected


@pytest.mark.asyncio
async def test_sync_cursor_port_contract() -> None:
    adapter = DummySyncCursorPort()

    state = await adapter.get_cursor("account-1", "gmail_history", "inbox")
    await adapter.update_cursor("account-1", "gmail_history", "inbox", "123", "valid", "sync-run-1")
    await adapter.mark_stale("account-1", "gmail_history", "inbox")

    assert state.value == "account-1:gmail_history:inbox"
    assert state.status == "valid"
    assert state.runs_count == 1


@pytest.mark.asyncio
async def test_thread_repository_port_contract() -> None:
    repository = DummyThreadRepositoryPort()

    upserted = await repository.upsert("account-1", "gmail-1", "subject")
    by_id = await repository.get_by_id("thread-1")
    by_gmail = await repository.get_by_gmail_id("account-1", "gmail-1")
    by_state = await repository.list_by_state("account-1", "discovered")
    updated = await repository.update_state("thread-1", "triaged")

    assert upserted.gmail_thread_id == "gmail-1"
    assert by_id == upserted
    assert by_gmail == upserted
    assert by_state == [upserted]
    assert updated.agent_state == "triaged"


@pytest.mark.asyncio
async def test_gmail_sync_port_contract() -> None:
    adapter = DummyGmailSyncPort()

    threads, next_history_id = await adapter.list_threads("account-1")
    messages = await adapter.get_thread_messages("account-1", "gmail-thread-1")
    full_message = await adapter.get_message_full("account-1", "gmail-message-1")
    await adapter.mark_as_read("account-1", ["gmail-message-1"])

    assert threads[0].gmail_thread_id == "gmail-thread-1"
    assert next_history_id == "next-history-id"
    assert messages[0].labels == ["INBOX"]
    assert full_message["body_text"] == "text"


@pytest.mark.asyncio
async def test_calendar_sync_port_contract() -> None:
    adapter = DummyCalendarSyncPort()
    now = datetime.now(timezone.utc)

    calendars = await adapter.list_calendars("account-1")
    events, next_sync_token = await adapter.list_events(
        "account-1",
        "primary",
        time_min=now,
        time_max=now,
    )

    assert calendars[0]["primary_flag"] is True
    assert events[0].google_event_id == "event-1"
    assert next_sync_token == "next-sync-token"


@pytest.mark.asyncio
async def test_calendar_repository_port_contract() -> None:
    repository = DummyCalendarRepositoryPort()

    source = await repository.upsert_calendar_source(
        "account-1",
        "primary",
        summary="Primary",
        primary_flag=True,
    )
    fetched = await repository.get_calendar_source("account-1", "primary")
    event = await repository.upsert_calendar_event(
        source.id,
        "event-1",
        status="confirmed",
        attendees_json=[{"email": "a@example.com"}],
    )

    assert source.google_calendar_id == "primary"
    assert fetched is not None
    assert fetched.id == "source-1"
    assert event.google_event_id == "event-1"


@pytest.mark.asyncio
async def test_triage_and_drafting_ports_contract() -> None:
    triage = DummyTriageServicePort()
    drafting = DummyDraftingServicePort()

    triage_result = await triage.score_thread(
        "thread-1",
        ["user@example.com"],
        "Subject",
        "Snippet",
        {"days_ahead": []},
    )
    draft = await drafting.propose_draft(
        "thread-1",
        "Subject",
        "user@example.com",
        "Snippet",
        {"days_ahead": []},
    )

    assert triage_result.priority_bucket == "high"
    assert triage_result.requires_response is True
    assert draft.intent == "acknowledge"
    assert draft.draft_subject == "Subject"

