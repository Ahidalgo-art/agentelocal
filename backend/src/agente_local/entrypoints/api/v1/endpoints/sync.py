"""Workspace Gmail + Calendar sync orchestration."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from agente_local.application.services.sync_workspace_service import SyncWorkspaceService
from agente_local.entrypoints.api.deps import (
    CalendarRepo,
    CalendarSync,
    CursorRepo,
    GmailSync,
    ThreadRepo,
    get_missing_google_env_vars,
)

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """Request body for triggering a sync."""

    pass


class SyncResponse(BaseModel):
    """Response from a sync execution."""

    sync_run_id: str
    gmail_threads_seen: int
    calendars_seen: int
    calendar_events_seen: int
    gmail_cursor_updated: bool
    calendar_cursors_updated: int
    executed_at: datetime


@router.post("/{account_id}")
async def trigger_sync(
    request: Request,
    account_id: str,
    _payload: SyncRequest,
    thread_repo: ThreadRepo,
    cursor_repo: CursorRepo,
    calendar_repo: CalendarRepo,
    gmail_sync: GmailSync,
    calendar_sync: CalendarSync,
) -> SyncResponse:
    """Trigger an incremental Gmail+Calendar sync for the workspace account."""
    missing_vars = getattr(request.app.state, "missing_google_env_vars", None)
    if missing_vars is None:
        missing_vars = get_missing_google_env_vars()

    if missing_vars:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google OAuth configuration is missing. "
                f"Set these variables in backend/.env: {', '.join(missing_vars)}"
            ),
        )

    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid account_id UUID format",
        )

    account_id_str = str(account_uuid)
    sync_run_id = str(uuid.uuid4())

    service = SyncWorkspaceService(
        gmail_sync=gmail_sync,
        calendar_sync=calendar_sync,
        cursor_repository=cursor_repo,
        thread_repository=thread_repo,
        calendar_repository=calendar_repo,
    )

    result = await service.execute(account_id=account_id_str, sync_run_id=sync_run_id)

    return SyncResponse(
        sync_run_id=sync_run_id,
        gmail_threads_seen=result.gmail_threads_seen,
        calendars_seen=result.calendars_seen,
        calendar_events_seen=result.calendar_events_seen,
        gmail_cursor_updated=result.gmail_cursor_updated,
        calendar_cursors_updated=result.calendar_cursors_updated,
        executed_at=datetime.utcnow(),
    )
