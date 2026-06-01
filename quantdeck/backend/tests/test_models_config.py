from quantdeck_backend.models.config import (
    ConnectionStatus,
    DownloadRequest,
    ExchangeCredentialIn,
    ExchangeCredentialOut,
    mask_key,
)


def test_mask_key():
    assert mask_key("abcdefghij") == "abcd****ghij"
    assert mask_key("short") == "****"


def test_credential_out_masks():
    out = ExchangeCredentialOut(name="binance", api_key="abcdefghij", testnet=False)
    assert out.api_key == "abcd****ghij"


def test_download_request_defaults():
    req = DownloadRequest(
        market="spot", symbol="BTCUSDT", intervals=["1m"], start="2024-01-01", end="2024-01-02"
    )
    assert req.market == "spot"
    assert req.intervals == ["1m"]


def test_connection_status_shape():
    st = ConnectionStatus(ok=True, message="ok", latency_ms=12)
    assert st.model_dump() == {"ok": True, "message": "ok", "latency_ms": 12}


def test_credential_in_roundtrip():
    cin = ExchangeCredentialIn(api_key="k", api_secret="s", testnet=True)
    assert cin.model_dump() == {"api_key": "k", "api_secret": "s", "testnet": True}
