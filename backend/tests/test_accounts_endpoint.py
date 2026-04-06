"""Integration tests for POST & GET /v1/accounts."""
from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import delete

from agente_local.infrastructure.persistence.database import create_session_factory
from agente_local.infrastructure.persistence.models import WorkspaceAccountModel
from agente_local.main import app


@pytest.mark.asyncio
async def test_post_account_creates_new_account() -> None:
    email = f"{uuid.uuid4()}@example.com"
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/accounts", json={"email": email, "display_name": "Agent Test"})

    try:
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["display_name"] == "Agent Test"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
    finally:
        sf = create_session_factory()
        async with sf() as session:
            await session.execute(
                delete(WorkspaceAccountModel).where(
                    WorkspaceAccountModel.external_account_email == email
                )
            )
            await session.commit()


@pytest.mark.asyncio
async def test_post_account_existing_email_returns_200() -> None:
    email = f"{uuid.uuid4()}@example.com"
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/v1/accounts", json={"email": email})
        second = await client.post("/v1/accounts", json={"email": email})

    try:
        assert first.status_code == 201
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
    finally:
        sf = create_session_factory()
        async with sf() as session:
            await session.execute(
                delete(WorkspaceAccountModel).where(
                    WorkspaceAccountModel.external_account_email == email
                )
            )
            await session.commit()


@pytest.mark.asyncio
async def test_get_account_by_id_returns_account() -> None:
    email = f"{uuid.uuid4()}@example.com"
    transport = httpx.ASGITransport(app=app)
    created_id: str | None = None

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/v1/accounts", json={"email": email})
        created_id = created.json()["id"]
        response = await client.get(f"/v1/accounts/{created_id}")

    try:
        assert response.status_code == 200
        assert response.json()["id"] == created_id
        assert response.json()["email"] == email
    finally:
        sf = create_session_factory()
        async with sf() as session:
            await session.execute(
                delete(WorkspaceAccountModel).where(
                    WorkspaceAccountModel.external_account_email == email
                )
            )
            await session.commit()


@pytest.mark.asyncio
async def test_get_account_not_found_returns_404() -> None:
    transport = httpx.ASGITransport(app=app)
    random_id = str(uuid.uuid4())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/v1/accounts/{random_id}")

    assert response.status_code == 404
