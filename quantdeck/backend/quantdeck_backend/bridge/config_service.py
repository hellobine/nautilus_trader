import time

from quantdeck_backend.bridge.binance_client import BinanceKlineClient
from quantdeck_backend.bridge.secrets import SecretStore
from quantdeck_backend.models.config import (
    ConnectionStatus,
    ExchangeCredentialIn,
    ExchangeCredentialOut,
)


class ConfigService:
    """交易所凭证管理与连接测试。"""

    def __init__(self, store: SecretStore, client: BinanceKlineClient | None = None) -> None:
        self.store = store
        self.client = client or BinanceKlineClient()

    def list_exchanges(self) -> list[ExchangeCredentialOut]:
        data = self.store.load()
        return [
            ExchangeCredentialOut(name=name, api_key=cred["api_key"], testnet=cred.get("testnet", False))
            for name, cred in data.items()
        ]

    def set_exchange(self, name: str, cred: ExchangeCredentialIn) -> None:
        self.store.set_credential(name, cred.model_dump())

    def delete_exchange(self, name: str) -> None:
        self.store.delete_credential(name)

    async def test_connection(self, name: str) -> ConnectionStatus:
        cred = self.store.get_credential(name)
        if cred is None:
            return ConnectionStatus(ok=False, message="未配置该交易所凭证", latency_ms=0)
        start = time.perf_counter()
        try:
            await self.client.get_account(
                "spot", cred["api_key"], cred["api_secret"], cred.get("testnet", False)
            )
            latency = int((time.perf_counter() - start) * 1000)
            return ConnectionStatus(ok=True, message="连接成功", latency_ms=latency)
        except Exception as exc:  # noqa: BLE001 — 连接测试需汇报任意失败
            latency = int((time.perf_counter() - start) * 1000)
            return ConnectionStatus(ok=False, message=f"连接失败：{exc}", latency_ms=latency)
