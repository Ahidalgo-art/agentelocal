from __future__ import annotations

from dataclasses import dataclass

from agente_local.application.ports.calendar_repository import CalendarRepositoryPort
from agente_local.application.ports.calendar_sync import (
    CalendarSyncPort,
    CalendarSyncTokenExpiredError,
)
from agente_local.application.ports.gmail_sync import GmailSyncPort
from agente_local.application.ports.sync_cursor import SyncCursorPort
from agente_local.application.ports.thread_repository import ThreadRepositoryPort


@dataclass(frozen=True)
class SyncWorkspaceResult:
    """Summary of one sync execution."""

    gmail_threads_seen: int
    calendars_seen: int
    calendar_events_seen: int
    gmail_cursor_updated: bool
    calendar_cursors_updated: int


class SyncWorkspaceService:
    """Orchestrates Gmail and Calendar incremental sync with cursor handling."""

    def __init__(
        self,
        gmail_sync: GmailSyncPort,
        calendar_sync: CalendarSyncPort,
        cursor_repository: SyncCursorPort,
        thread_repository: ThreadRepositoryPort,
        calendar_repository: CalendarRepositoryPort,
    ) -> None:
        self._gmail_sync = gmail_sync
        self._calendar_sync = calendar_sync
        self._cursor_repository = cursor_repository
        self._thread_repository = thread_repository
        self._calendar_repository = calendar_repository

    async def execute(self, account_id: str, sync_run_id: str) -> SyncWorkspaceResult:
        gmail_threads_seen = 0
        calendars_seen = 0
        calendar_events_seen = 0
        gmail_cursor_updated = False
        calendar_cursors_updated = 0

        # Gmail incremental sync
        gmail_cursor = await self._cursor_repository.get_cursor(account_id, "gmail_history", "inbox")
        history_id = gmail_cursor.value if gmail_cursor.status == "valid" else None
        threads, next_history_id = await self._gmail_sync.list_threads(account_id, history_id=history_id)

        for thread in threads:
            await self._thread_repository.upsert(
                account_id=account_id,
                gmail_thread_id=thread.gmail_thread_id,
                subject=thread.subject_normalized,
                message_count=thread.message_count,
                has_unread=thread.has_unread,
                is_important_label=thread.is_important_label,
                participants_cache=thread.participants_cache,
                agent_state="synced",
                last_message_at=thread.last_message_at,
            )
            gmail_threads_seen += 1

        if next_history_id:
            await self._cursor_repository.update_cursor(
                account_id=account_id,
                resource_type="gmail_history",
                resource_key="inbox",
                cursor_value=next_history_id,
                new_status="valid",
                sync_run_id=sync_run_id,
            )
            gmail_cursor_updated = True

        # Calendar incremental sync by calendar id
        calendars = await self._calendar_sync.list_calendars(account_id)
        calendars_seen = len(calendars)

        for calendar in calendars:
            calendar_id = str(calendar["id"])
            source = await self._calendar_repository.upsert_calendar_source(
                account_id=account_id,
                google_calendar_id=calendar_id,
                summary=calendar.get("summary"),
                primary_flag=bool(calendar.get("primary_flag", False)),
                selected_flag=bool(calendar.get("selected_flag", True)),
                timezone=calendar.get("timezone"),
            )

            cursor = await self._cursor_repository.get_cursor(account_id, "calendar_sync", calendar_id)
            sync_token = cursor.value if cursor.status == "valid" else None

            try:
                events, next_sync_token = await self._calendar_sync.list_events(
                    account_id=account_id,
                    calendar_id=calendar_id,
                    sync_token=sync_token,
                )
            except CalendarSyncTokenExpiredError:
                await self._cursor_repository.mark_stale(account_id, "calendar_sync", calendar_id)
                events, next_sync_token = await self._calendar_sync.list_events(
                    account_id=account_id,
                    calendar_id=calendar_id,
                    sync_token=None,
                )

            calendar_events_seen += len(events)

            for event in events:
                await self._calendar_repository.upsert_calendar_event(
                    calendar_source_id=source.id,
                    google_event_id=event.google_event_id,
                    status=event.status,
                    summary=event.summary,
                    organizer_email=event.organizer_email,
                    attendees_json=event.attendees,
                    starts_at=event.starts_at,
                    ends_at=event.ends_at,
                    all_day=event.all_day,
                    location=event.location,
                    meet_link=event.meet_link,
                )

            if next_sync_token:
                await self._cursor_repository.update_cursor(
                    account_id=account_id,
                    resource_type="calendar_sync",
                    resource_key=calendar_id,
                    cursor_value=next_sync_token,
                    new_status="valid",
                    sync_run_id=sync_run_id,
                )
                calendar_cursors_updated += 1

        return SyncWorkspaceResult(
            gmail_threads_seen=gmail_threads_seen,
            calendars_seen=calendars_seen,
            calendar_events_seen=calendar_events_seen,
            gmail_cursor_updated=gmail_cursor_updated,
            calendar_cursors_updated=calendar_cursors_updated,
        )
