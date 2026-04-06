"""GmailSyncPort — incremental read from Gmail."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class EmailThread:
    """Email thread aggregate."""

    gmail_thread_id: str
    subject_normalized: Optional[str]
    last_message_at: Optional[datetime]
    message_count: int
    has_unread: bool
    is_important_label: bool
    participants_cache: dict  # {email: name}


@dataclass(frozen=True)
class EmailMessage:
    """Individual email message."""

    gmail_message_id: str
    gmail_internal_date_at: Optional[datetime]
    sender_email: Optional[str]
    snippet: Optional[str]
    is_inbound: bool
    labels: List[str]


class GmailSyncPort(ABC):
    """Read Gmail in incremental mode."""

    @abstractmethod
    async def list_threads(
        self,
        account_id: str,
        history_id: Optional[str] = None,  # None = full resync
        limit: int = 100,
    ) -> tuple[list[EmailThread], Optional[str]]:
        """
        List threads modified since history_id.

        Returns: (threads, next_history_id)
        """
        pass

    @abstractmethod
    async def get_thread_messages(
        self,
        account_id: str,
        thread_id: str,
    ) -> list[EmailMessage]:
        """Get all messages of a thread."""
        pass

    @abstractmethod
    async def get_message_full(
        self,
        account_id: str,
        message_id: str,
    ) -> dict:
        """
        Get full payload: body_text, body_html, headers.

        Returns dict with keys: body_text, body_html, headers_json
        """
        pass

    @abstractmethod
    async def mark_as_read(
        self,
        account_id: str,
        message_ids: list[str],
    ) -> None:
        """Mark messages as read."""
        pass
