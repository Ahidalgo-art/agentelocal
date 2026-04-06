"""ThreadRepositoryPort — CRUD operations on threads."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ThreadEntity:
    """Persisted thread entity."""

    id: str  # UUID local
    account_id: str
    gmail_thread_id: str
    subject_normalized: Optional[str]
    message_count: int
    has_unread: bool
    agent_state: str  # discovered | triaged | draft_proposed | approved | created
    triage_decision_id: Optional[str]
    draft_suggestion_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class ThreadRepositoryPort(ABC):
    """CRUD operations on threads."""

    @abstractmethod
    async def upsert(
        self,
        account_id: str,
        gmail_thread_id: str,
        subject: Optional[str],
        **fields,
    ) -> ThreadEntity:
        """Insert or update (idempotent)."""
        pass

    @abstractmethod
    async def get_by_id(self, thread_id: str) -> Optional[ThreadEntity]:
        """Get by local UUID."""
        pass

    @abstractmethod
    async def get_by_gmail_id(
        self,
        account_id: str,
        gmail_thread_id: str,
    ) -> Optional[ThreadEntity]:
        """Get by gmail_thread_id."""
        pass

    @abstractmethod
    async def list_by_state(
        self,
        account_id: str,
        state: str,
        limit: int = 100,
    ) -> list[ThreadEntity]:
        """List by agent_state for processing."""
        pass

    @abstractmethod
    async def update_state(
        self,
        thread_id: str,
        new_state: str,
    ) -> ThreadEntity:
        """Change thread state."""
        pass
