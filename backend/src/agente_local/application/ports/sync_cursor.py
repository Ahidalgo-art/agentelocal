"""SyncCursorPort — manage incremental sync cursors per resource."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CursorState:
    """State of sync cursor — value + status."""

    value: Optional[str]
    status: str  # valid | stale | requires_full_resync
    last_synced_at: Optional[datetime]
    runs_count: int


class SyncCursorPort(ABC):
    """Manage incremental sync cursors by resource and account."""

    @abstractmethod
    async def get_cursor(
        self,
        account_id: str,
        resource_type: str,  # gmail_history | calendar_sync
        resource_key: str,  # inbox | calendar_id
    ) -> CursorState:
        """Get current cursor state."""
        pass

    @abstractmethod
    async def update_cursor(
        self,
        account_id: str,
        resource_type: str,
        resource_key: str,
        cursor_value: Optional[str],
        new_status: str,
        sync_run_id: str,
    ) -> None:
        """Update cursor after successful sync."""
        pass

    @abstractmethod
    async def mark_stale(
        self,
        account_id: str,
        resource_type: str,
        resource_key: str,
    ) -> None:
        """Mark cursor as stale — forces full resync."""
        pass
