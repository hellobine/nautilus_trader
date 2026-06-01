import pytest

from quantdeck_backend.bridge.binance_client import (
    BinanceKlineClient,
    build_signed_query,
    klines_url,
)


def test_klines_url_spot_vs_futures():
    assert klines_url("spot").endswith("/api/v3/klines")
    assert klines_url("futures").endswith("/fapi/v1/klines")


def test_build_signed_query_appends_signature():
    q = build_signed_query({"timestamp": 1}, secret="secret")
    assert "signature=" in q
    assert q.startswith("timestamp=1")


@pytest.mark.asyncio
async def test_fetch_klines_parses_rows(monkeypatch):
    client = BinanceKlineClient()
    sample = [
        [1700000000000, "100", "110", "90", "105", "12.5", 1700000059999, "0", 1, "0", "0", "0"],
    ]

    async def fake_get(url, params=None, headers=None):
        class R:
            status_code = 200

            def json(self_inner):
                return sample

            def raise_for_status(self_inner):
                pass

        return R()

    monkeypatch.setattr(client, "_get", fake_get)
    rows = await client.fetch_klines("spot", "BTCUSDT", "1m", 0, 1700000060000)
    assert rows == sample
