"""TriageServicePort — importance scoring decision."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TriageResult:
    """Result of triage."""

    thread_id: str
    importance_score: float  # 0.0 — 1.0
    confidence_score: float
    priority_bucket: str  # critical | high | medium | low | fyi
    requires_response: bool
    reasons: List[str]
    signals: dict


class TriageServicePort(ABC):
    """Importance decision on threads."""

    @abstractmethod
    async def score_thread(
        self,
        thread_id: str,
        participants: List[str],
        subject: str,
        latest_snippet: str,
        calendar_context: dict,  # {days_ahead: events}
    ) -> TriageResult:
        """Calculate importance and priority."""
        pass
