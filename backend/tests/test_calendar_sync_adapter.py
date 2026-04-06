"""Unit tests for CalendarSyncAdapter — all Google API calls are mocked."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agente_local.infrastructure.calendar_sync import (
    CalendarSyncAdapter,
    _build_attendees,
    _event_from_raw,
    _extract_meet_link,
    _parse_datetime,
)


# ---------------------------------------------------------------------------
# Pure helper unit tests (no I/O)
# ---------------------------------------------------------------------------


def test_parse_datetime_iso_with_z() -> None:
    dt = _parse_datetime("2025-06-15T10:30:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2025
    assert dt.month == 6
    assert dt.day == 15


def test_parse_datetime_iso_with_offset() -> None:
    dt = _parse_datetime("2025-06-15T10:30:00+02:00")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_datetime_date_only_is_midnight_utc() -> None:
    dt = _parse_datetime("2025-06-15")
    assert dt is not None
    assert dt.tzinfo == UTC
    assert dt.hour == 0
    assert dt.minute == 0


def test_parse_datetime_none_returns_none() -> None:
    assert _parse_datetime(None) is None


def test_parse_datetime_empty_returns_none() -> None:
    assert _parse_datetime("") is None


def test_extract_meet_link_present() -> None:
    event = {
        "conferenceData": {
            "entryPoints": [
                {"entryPointType": "phone", "uri": "tel:+1234567890"},
                {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
            ]
        }
    }
    assert _extract_meet_link(event) == "https://meet.google.com/abc-defg-hij"


def test_extract_meet_link_no_conference_data() -> None:
    assert _extract_meet_link({}) is None


def test_extract_meet_link_no_video_entry_point() -> None:
    event = {"conferenceData": {"entryPoints": [{"entryPointType": "phone", "uri": "tel:+1"}]}}
    assert _extract_meet_link(event) is None


def test_build_attendees_normalises_fields() -> None:
    raw = [
        {"email": "a@x.com", "displayName": "Alice", "responseStatus": "accepted"},
        {"email": "b@x.com"},
    ]
    attendees = _build_attendees(raw)
    assert len(attendees) == 2
    assert attendees[0]["display_name"] == "Alice"
    assert attendees[0]["response_status"] == "accepted"
    assert attendees[1]["response_status"] == "needsAction"


def test_event_from_raw_all_day() -> None:
    raw = {
        "id": "evt_001",
        "status": "confirmed",
        "summary": "All Day Event",
        "start": {"date": "2025-06-20"},
        "end": {"date": "2025-06-21"},
        "organizer": {"email": "org@example.com"},
    }
    event = _event_from_raw(raw)
    assert event.all_day is True
    assert event.starts_at is not None
    assert event.starts_at.tzinfo == UTC


def test_event_from_raw_timed_event() -> None:
    raw = {
        "id": "evt_002",
        "status": "confirmed",
        "summary": "Meeting",
        "start": {"dateTime": "2025-06-20T09:00:00Z"},
        "end": {"dateTime": "2025-06-20T10:00:00Z"},
    }
    event = _event_from_raw(raw)
    assert event.all_day is False
    assert event.starts_at is not None
    assert event.organizer_email is None


def test_event_from_raw_meet_link_populated() -> None:
    raw = {
        "id": "evt_003",
        "status": "confirmed",
        "start": {"dateTime": "2025-06-20T09:00:00Z"},
        "end": {"dateTime": "2025-06-20T10:00:00Z"},
        "conferenceData": {
            "entryPoints": [
                {"entryPointType": "video", "uri": "https://meet.google.com/zzz-zzzz-zzz"}
            ]
        },
    }
    event = _event_from_raw(raw)
    assert event.meet_link == "https://meet.google.com/zzz-zzzz-zzz"


# ---------------------------------------------------------------------------
# CalendarSyncAdapter — integration with mocked Google API client
# ---------------------------------------------------------------------------

_FAKE_CALENDAR_ID = "primary"
_FAKE_SYNC_TOKEN = "sync_token_abc123"
_FAKE_NEXT_SYNC_TOKEN = "sync_token_next_456"


def _make_fake_credential() -> MagicMock:
    creds = MagicMock()
    creds.valid = True
    return creds


def _make_calendar_list_response() -> dict:
    return {
        "items": [
            {"id": "primary", "summary": "My Calendar", "primary": True, "timeZone": "Europe/Madrid"},
            {"id": "work@x.com", "summary": "Work", "timeZone": "UTC"},
        ]
    }


def _make_events_list_response(with_next_page: bool = False) -> dict:
    item = {
        "id": "evt_001",
        "status": "confirmed",
        "summary": "Test Event",
        "start": {"dateTime": "2025-06-15T10:00:00Z"},
        "end": {"dateTime": "2025-06-15T11:00:00Z"},
        "organizer": {"email": "org@example.com"},
        "attendees": [
            {"email": "a@x.com", "displayName": "Alice", "responseStatus": "accepted"},
        ],
    }
    resp: dict = {"items": [item]}
    if with_next_page:
        resp["nextPageToken"] = "page_token_2"
    else:
        resp["nextSyncToken"] = _FAKE_NEXT_SYNC_TOKEN
    return resp


def _make_events_page2_response() -> dict:
    item = {
        "id": "evt_002",
        "status": "confirmed",
        "summary": "Second Event",
        "start": {"dateTime": "2025-06-16T10:00:00Z"},
        "end": {"dateTime": "2025-06-16T11:00:00Z"},
    }
    return {"items": [item], "nextSyncToken": _FAKE_NEXT_SYNC_TOKEN}


@pytest.fixture()
def mock_credential_provider() -> MagicMock:
    provider = MagicMock()
    provider.get_credentials = AsyncMock(return_value=_make_fake_credential())
    return provider


@pytest.fixture()
def adapter(mock_credential_provider: MagicMock) -> CalendarSyncAdapter:
    return CalendarSyncAdapter(credential_provider=mock_credential_provider)


@pytest.mark.asyncio
async def test_list_calendars_returns_all(adapter: CalendarSyncAdapter) -> None:
    with patch("agente_local.infrastructure.calendar_sync.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        service.calendarList.return_value.list.return_value.execute.return_value = (
            _make_calendar_list_response()
        )

        result = await adapter.list_calendars("account_001")

    assert len(result) == 2
    primary = next(r for r in result if r["id"] == "primary")
    assert primary["primary_flag"] is True
    assert primary["timezone"] == "Europe/Madrid"
    work = next(r for r in result if r["id"] == "work@x.com")
    assert work["primary_flag"] is False


@pytest.mark.asyncio
async def test_list_calendars_empty(adapter: CalendarSyncAdapter) -> None:
    with patch("agente_local.infrastructure.calendar_sync.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        service.calendarList.return_value.list.return_value.execute.return_value = {"items": []}

        result = await adapter.list_calendars("account_001")

    assert result == []


@pytest.mark.asyncio
async def test_list_events_with_sync_token(adapter: CalendarSyncAdapter) -> None:
    with patch("agente_local.infrastructure.calendar_sync.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        service.events.return_value.list.return_value.execute.return_value = (
            _make_events_list_response()
        )

        events, next_token = await adapter.list_events(
            "account_001", _FAKE_CALENDAR_ID, sync_token=_FAKE_SYNC_TOKEN
        )

    assert len(events) == 1
    assert events[0].google_event_id == "evt_001"
    assert events[0].summary == "Test Event"
    assert events[0].all_day is False
    assert events[0].attendees[0]["email"] == "a@x.com"
    assert next_token == _FAKE_NEXT_SYNC_TOKEN

    call_kwargs = service.events.return_value.list.call_args
    assert call_kwargs.kwargs.get("syncToken") == _FAKE_SYNC_TOKEN


@pytest.mark.asyncio
async def test_list_events_with_time_window(adapter: CalendarSyncAdapter) -> None:
    time_min = datetime(2025, 6, 1, tzinfo=UTC)
    time_max = datetime(2025, 6, 30, tzinfo=UTC)

    with patch("agente_local.infrastructure.calendar_sync.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        service.events.return_value.list.return_value.execute.return_value = (
            _make_events_list_response()
        )

        events, next_token = await adapter.list_events(
            "account_001", _FAKE_CALENDAR_ID, time_min=time_min, time_max=time_max
        )

    assert len(events) == 1
    call_kwargs = service.events.return_value.list.call_args
    # syncToken must NOT be present when using time window
    assert "syncToken" not in call_kwargs.kwargs
    assert "timeMin" in call_kwargs.kwargs
    assert "timeMax" in call_kwargs.kwargs


@pytest.mark.asyncio
async def test_list_events_paginated(adapter: CalendarSyncAdapter) -> None:
    """Two pages are fetched and events from both are returned."""
    with patch("agente_local.infrastructure.calendar_sync.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        service.events.return_value.list.return_value.execute.side_effect = [
            _make_events_list_response(with_next_page=True),
            _make_events_page2_response(),
        ]

        events, next_token = await adapter.list_events(
            "account_001", _FAKE_CALENDAR_ID
        )

    assert len(events) == 2
    assert events[0].google_event_id == "evt_001"
    assert events[1].google_event_id == "evt_002"
    assert next_token == _FAKE_NEXT_SYNC_TOKEN


@pytest.mark.asyncio
async def test_list_events_skips_blank_cancelled(adapter: CalendarSyncAdapter) -> None:
    """Cancelled tombstone entries without summary are skipped."""
    with patch("agente_local.infrastructure.calendar_sync.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        cancelled_tombstone = {
            "id": "deleted_evt",
            "status": "cancelled",
            "start": {},
            "end": {},
        }
        service.events.return_value.list.return_value.execute.return_value = {
            "items": [cancelled_tombstone],
            "nextSyncToken": _FAKE_NEXT_SYNC_TOKEN,
        }

        events, _ = await adapter.list_events(
            "account_001", _FAKE_CALENDAR_ID, sync_token=_FAKE_SYNC_TOKEN
        )

    assert events == []
