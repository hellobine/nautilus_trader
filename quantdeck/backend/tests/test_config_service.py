import pytest

from quantdeck_backend.bridge.config_service import ConfigService
from quantdeck_backend.bridge.secrets import SecretStore
from quantdeck_backend.models.config import ExchangeCredentialIn


def make_service(tmp_path):
    store = SecretStore(str(tmp_path / "secrets.enc"))
    return ConfigService(store)


def test_set_list_mask(tmp_path):
    svc = make_service(tmp_path)
    svc.store.unlock("pw")
    svc.set_exchange("binance", ExchangeCredentialIn(api_key="abcdefghij", api_secret="s", testnet=False))
    out = svc.list_exchanges()
    assert len(out) == 1
    assert out[0].name == "binance"
    assert out[0].api_key == "abcd****ghij"


def test_delete(tmp_path):
    svc = make_service(tmp_path)
    svc.store.unlock("pw")
    svc.set_exchange("binance", ExchangeCredentialIn(api_key="abcdefghij", api_secret="s", testnet=False))
    svc.delete_exchange("binance")
    assert svc.list_exchanges() == []


@pytest.mark.asyncio
async def test_test_connection_ok(tmp_path):
    svc = make_service(tmp_path)
    svc.store.unlock("pw")
    svc.set_exchange("binance", ExchangeCredentialIn(api_key="k", api_secret="s", testnet=False))

    async def fake_get_account(market, api_key, api_secret, testnet=False):
        return {"accountType": "SPOT"}

    svc.client.get_account = fake_get_account  # type: ignore
    status = await svc.test_connection("binance")
    assert status.ok is True


@pytest.mark.asyncio
async def test_test_connection_unconfigured(tmp_path):
    svc = make_service(tmp_path)
    svc.store.unlock("pw")
    status = await svc.test_connection("binance")
    assert status.ok is False
    assert "未配置" in status.message
