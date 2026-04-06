"""CalendarSyncPort — read calendar for context."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class CalendarEvent:
    """Calendar event."""

    google_event_id: str
    status: str  # confirmed | tentative | cancelled
    summary: Optional[str]
    organizer_email: Optional[str]
    attendees: List[dict]  # {email: str, response_status: str}
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    all_day: bool
    location: Optional[str]
    meet_link: Optional[str]


class CalendarSyncPort(ABC):
    """Read calendar for context."""

    @abstractmethod
    async def list_calendars(
        self,
        account_id: str,
    ) -> List[dict]:
        """Return list of calendars: [id, summary, primary_flag]."""
        pass

    @abstractmethod
    async def list_events(
        self,
        account_id: str,
        calendar_id: str,
        sync_token: Optional[str] = None,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> tuple[list[CalendarEvent], Optional[str]]:
        """
        List events.

        If sync_token: incremental.
        If time_min/time_max: fixed window.
        Returns: (events, next_sync_token)
        """
        pass
