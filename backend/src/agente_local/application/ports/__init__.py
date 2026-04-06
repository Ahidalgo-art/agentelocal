"""Application ports — abstraction layer for synchronization and triage."""

from agente_local.application.ports.sync_cursor import (
    CursorState,
    SyncCursorPort,
)
from agente_local.application.ports.gmail_sync import (
    EmailMessage,
    EmailThread,
    GmailSyncPort,
)
from agente_local.application.ports.calendar_sync import (
    CalendarEvent,
    CalendarSyncPort,
    CalendarSyncTokenExpiredError,
)
from agente_local.application.ports.calendar_repository import (
    CalendarEventEntity,
    CalendarRepositoryPort,
    CalendarSourceEntity,
)
from agente_local.application.ports.thread_repository import (
    ThreadEntity,
    ThreadRepositoryPort,
)
from agente_local.application.ports.triage_service import (
    TriageResult,
    TriageServicePort,
)
from agente_local.application.ports.drafting_service import (
    DraftProposal,
    DraftingServicePort,
)

__all__ = [
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
]
