"""
Test configuration and shared fixtures.

- Uses the app's TestClient for HTTP tests (no real server needed).
- Database isolation: each test runs in a transaction that is rolled back
  automatically, so tests never leave persistent state.
- The DATABASE_URL env var controls which database is used:
    - CI:    sqlite:///./ci.db  (set in backend_ci.yml)
    - Local: value from .env   (PostgreSQL recommended)
"""
import pytest
from fastapi.testclient import TestClient

from agente_local.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared HTTP test client for the whole session."""
    return TestClient(app)
