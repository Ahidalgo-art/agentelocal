"""DraftingServicePort — generate draft proposals."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DraftProposal:
    """Proposed draft text."""

    thread_id: str
    intent: str  # acknowledge | ask_clarification | propose_slots | commit | decline
    summary_for_user: str
    why_this_reply: str
    draft_subject: str
    draft_body_text: str
    confidence_score: float


class DraftingServicePort(ABC):
    """Generate draft proposals."""

    @abstractmethod
    async def propose_draft(
        self,
        thread_id: str,
        subject: str,
        latest_sender: str,
        message_snippet: str,
        calendar_context: dict,
    ) -> DraftProposal:
        """Propose draft text for reply."""
        pass
