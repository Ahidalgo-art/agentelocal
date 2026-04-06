"""CalendarRepositoryPort - persistence operations for calendars and events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CalendarSourceEntity:
    """Persisted calendar source metadata."""

    id: str
    account_id: str
    google_calendar_id: str
    summary: Optional[str]
    primary_flag: bool
    selected_flag: bool
    timezone: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CalendarEventEntity:
    """Persisted calendar event."""

    id: str
    calendar_source_id: str
    google_event_id: str
    status: str
    summary: Optional[str]
    description: Optional[str]
    organizer_email: Optional[str]
    attendees_json: list[dict]
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    all_day: bool
    location: Optional[str]
    meet_link: Optional[str]
    etag: Optional[str]
    updated_remote_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CalendarRepositoryPort(ABC):
    """Persistence operations for calendar sources and events."""

    @abstractmethod
    async def upsert_calendar_source(
        self,
        account_id: str,
        google_calendar_id: str,
        **fields: object,
    ) -> CalendarSourceEntity:
        """Insert or update a calendar source by account/calendar identifier."""
        pass

    @abstractmethod
    async def get_calendar_source(
        self,
        account_id: str,
        google_calendar_id: str,
    ) -> Optional[CalendarSourceEntity]:
        """Get a persisted calendar source by account/calendar identifier."""
        pass

    @abstractmethod
    async def upsert_calendar_event(
        self,
        calendar_source_id: str,
        google_event_id: str,
        **fields: object,
    ) -> CalendarEventEntity:
        """Insert or update an event by calendar source and Google event id."""
        pass
