"""Tests for the sync orchestration endpoint."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from agente_local.main import create_app


def test_sync_endpoint_app_loads() -> None:
    """Verify sync endpoint app loads without errors."""
    app = create_app()
    assert app is not None


def test_sync_endpoint_returns_clear_error_when_google_env_missing() -> None:
    """Sync endpoint must fail with actionable 503 when Google OAuth config is missing."""
    app = create_app()
    client = TestClient(app)

    response = client.post(f"/v1/sync/{uuid.uuid4()}", json={})

    assert response.status_code == 503
    payload = response.json()
    assert "Google OAuth configuration is missing" in payload["detail"]
    assert "GOOGLE_CLIENT_ID" in payload["detail"]
    assert "GOOGLE_CLIENT_SECRET" in payload["detail"]
