from fastapi.testclient import TestClient

from quantdeck_backend.main import create_app


def test_health_ok():
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["nautilus"]["available"] is True
    assert body["nautilus"]["version"]
