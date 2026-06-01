import pytest
from fastapi.testclient import TestClient

import quantdeck_backend.services as services_mod
from quantdeck_backend.main import create_app
from quantdeck_backend.services import Services


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QD_CATALOG_DIR", str(tmp_path / "cat"))
    monkeypatch.setenv("QD_SECRETS_PATH", str(tmp_path / "secrets.enc"))
    # 重置单例，确保用到临时目录
    services_mod._SERVICES = Services.build()
    return TestClient(create_app())


def test_lock_status_then_unlock(client):
    r = client.get("/api/lock-status")
    assert r.status_code == 200
    assert r.json()["unlocked"] is False
    r = client.post("/api/unlock", json={"passphrase": "pw"})
    assert r.status_code == 200
    assert client.get("/api/lock-status").json()["unlocked"] is True


def test_exchanges_requires_unlock(client):
    r = client.get("/api/exchanges")
    assert r.status_code == 423


def test_exchange_crud_and_mask(client):
    client.post("/api/unlock", json={"passphrase": "pw"})
    r = client.put(
        "/api/exchanges/binance",
        json={"api_key": "abcdefghij", "api_secret": "s", "testnet": False},
    )
    assert r.status_code == 200
    listing = client.get("/api/exchanges").json()
    assert listing[0]["name"] == "binance"
    assert listing[0]["api_key"] == "abcd****ghij"
    assert client.delete("/api/exchanges/binance").status_code == 200
    assert client.get("/api/exchanges").json() == []


def test_catalog_empty(client):
    client.post("/api/unlock", json={"passphrase": "pw"})
    assert client.get("/api/catalog").json() == []


def test_create_download_returns_job(client, monkeypatch):
    client.post("/api/unlock", json={"passphrase": "pw"})

    async def fake_run_job(job_id):
        job = services_mod._SERVICES.downloads.get(job_id)
        job.status = "done"

    monkeypatch.setattr(services_mod._SERVICES.downloads, "run_job", fake_run_job)
    monkeypatch.setattr(
        services_mod._SERVICES.downloads, "start",
        lambda req: services_mod._SERVICES.downloads.create_job(req),
    )
    r = client.post(
        "/api/downloads",
        json={"market": "spot", "symbol": "BTCUSDT", "intervals": ["1m"],
              "start": "2024-01-01", "end": "2024-01-02"},
    )
    assert r.status_code == 200
    assert r.json()["id"].startswith("dl-")
