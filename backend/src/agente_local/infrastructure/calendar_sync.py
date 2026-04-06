"""CalendarSyncAdapter — implements CalendarSyncPort using Google Calendar API.

Design decisions (aligned with ADR-010):
- Read-only: never writes to the calendar.
- Stateless: credentials fetched per call via GoogleCredentialProvider.
- Supports incremental sync via sync_token (preferred) and time-window fallback.
- All remote I/O wrapped in asyncio.to_thread() to keep the async contract.
- attendees_json list follows {email, display_name, response_status} shape
  consistent with the calendar_event table schema.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Optional

from googleapiclient.discovery import build

from agente_local.application.ports.calendar_sync import CalendarEvent, CalendarSyncPort
from agente_local.infrastructure.google_credentials import GoogleCredentialProvider


def _parse_datetime(value: str | None) -> Optional[datetime]:
    """Parse an RFC-3339 date or datetime string into an aware datetime."""
    if not value:
        return None
    # All-day events use date-only (YYYY-MM-DD); treat as midnight UTC.
    if "T" not in value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            return None
    # datetime with timezone offset or 'Z'
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_meet_link(event: dict) -> Optional[str]:
    """Return a Google Meet URL from conference data if present."""
    conference = event.get("conferenceData", {})
    for entry in conference.get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            return entry.get("uri")
    return None


def _build_attendees(raw: list[dict]) -> list[dict]:
    """Normalise the attendees list to the DB schema shape."""
    return [
        {
            "email": a.get("email", ""),
            "display_name": a.get("displayName", ""),
            "response_status": a.get("responseStatus", "needsAction"),
        }
        for a in raw
    ]


def _event_from_raw(raw: dict) -> CalendarEvent:
    start_raw = raw.get("start", {})
    end_raw = raw.get("end", {})
    all_day = "date" in start_raw and "dateTime" not in start_raw

    return CalendarEvent(
        google_event_id=raw["id"],
        status=raw.get("status", "confirmed"),
        summary=raw.get("summary"),
        organizer_email=raw.get("organizer", {}).get("email"),
        attendees=_build_attendees(raw.get("attendees", [])),
        starts_at=_parse_datetime(start_raw.get("dateTime") or start_raw.get("date")),
        ends_at=_parse_datetime(end_raw.get("dateTime") or end_raw.get("date")),
        all_day=all_day,
        location=raw.get("location"),
        meet_link=_extract_meet_link(raw),
    )


class CalendarSyncAdapter(CalendarSyncPort):
    """Concrete Calendar adapter using google-api-python-client."""

    def __init__(self, credential_provider: GoogleCredentialProvider) -> None:
        self._credential_provider = credential_provider

    async def list_calendars(self, account_id: str) -> list[dict]:
        """Return all accessible calendars for the account."""
        creds = await self._credential_provider.get_credentials(account_id)

        def _run() -> list[dict]:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            result = service.calendarList().list().execute()
            return [
                {
                    "id": item["id"],
                    "summary": item.get("summary", ""),
                    "primary_flag": item.get("primary", False),
                    "selected_flag": item.get("selected", True),
                    "timezone": item.get("timeZone"),
                }
                for item in result.get("items", [])
            ]

        return await asyncio.to_thread(_run)

    async def list_events(
        self,
        account_id: str,
        calendar_id: str,
        sync_token: Optional[str] = None,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> tuple[list[CalendarEvent], Optional[str]]:
        """List events incrementally (sync_token) or by time window."""
        creds = await self._credential_provider.get_credentials(account_id)

        def _run() -> tuple[list[CalendarEvent], Optional[str]]:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            events: list[CalendarEvent] = []
            next_sync_token: Optional[str] = None

            request_kwargs: dict = {
                "calendarId": calendar_id,
                "singleEvents": True,
                "maxResults": 250,
            }
            if sync_token:
                request_kwargs["syncToken"] = sync_token
            else:
                if time_min:
                    request_kwargs["timeMin"] = time_min.isoformat()
                if time_max:
                    request_kwargs["timeMax"] = time_max.isoformat()

            page_token: Optional[str] = None
            while True:
                if page_token:
                    request_kwargs["pageToken"] = page_token

                resp = service.events().list(**request_kwargs).execute()
                for item in resp.get("items", []):
                    # Skip cancelled deletions when they carry no useful data.
                    if item.get("status") == "cancelled" and "summary" not in item:
                        continue
                    events.append(_event_from_raw(item))

                page_token = resp.get("nextPageToken")
                if not page_token:
                    next_sync_token = resp.get("nextSyncToken")
                    break

            return events, next_sync_token

        return await asyncio.to_thread(_run)
