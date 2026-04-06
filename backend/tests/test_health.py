from fastapi.testclient import TestClient

from agente_local.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload
