"""Workspace account registration and lookup."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from agente_local.entrypoints.api.deps import DbSession
from agente_local.infrastructure.persistence.models import WorkspaceAccountModel

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreateRequest(BaseModel):
    email: str
    display_name: str | None = None


class AccountResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    is_active: bool
    created_at: datetime


def _to_response(model: WorkspaceAccountModel) -> AccountResponse:
    return AccountResponse(
        id=str(model.id),
        email=model.external_account_email,
        display_name=model.display_name,
        is_active=model.is_active,
        created_at=model.created_at,
    )


@router.post("", response_model=AccountResponse)
async def create_or_get_account(
    payload: AccountCreateRequest,
    session: DbSession,
    response: Response,
) -> AccountResponse:
    """Register a Google workspace account (idempotent by email)."""
    result = await session.execute(
        select(WorkspaceAccountModel).where(
            WorkspaceAccountModel.external_account_email == payload.email
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _to_response(existing)

    account = WorkspaceAccountModel(
        id=uuid.uuid4(),
        external_account_email=payload.email,
        display_name=payload.display_name,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    response.status_code = status.HTTP_201_CREATED
    return _to_response(account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, session: DbSession) -> AccountResponse:
    """Fetch a workspace account by its local UUID."""
    try:
        uid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid UUID")

    result = await session.execute(
        select(WorkspaceAccountModel).where(WorkspaceAccountModel.id == uid)
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    return _to_response(account)
