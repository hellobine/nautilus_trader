import hashlib
import hmac
import time
import urllib.parse

import httpx

SPOT_BASE = "https://api.binance.com"
FUT_BASE = "https://fapi.binance.com"
SPOT_TESTNET = "https://testnet.binance.vision"
FUT_TESTNET = "https://testnet.binancefuture.com"


def _base(market: str, testnet: bool = False) -> str:
    if market == "futures":
        return FUT_TESTNET if testnet else FUT_BASE
    return SPOT_TESTNET if testnet else SPOT_BASE


def klines_url(market: str, testnet: bool = False) -> str:
    path = "/fapi/v1/klines" if market == "futures" else "/api/v3/klines"
    return _base(market, testnet) + path


def account_url(market: str, testnet: bool = False) -> str:
    path = "/fapi/v2/account" if market == "futures" else "/api/v3/account"
    return _base(market, testnet) + path


def build_signed_query(params: dict, secret: str) -> str:
    query = urllib.parse.urlencode(params)
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={sig}"


class BinanceKlineClient:
    """Binance REST 客户端：公开 klines + 签名账户查询。"""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    async def _get(self, url: str, params=None, headers=None):
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            return await c.get(url, params=params, headers=headers)

    async def fetch_klines(
        self, market: str, symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1000, testnet: bool = False
    ) -> list:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
        resp = await self._get(klines_url(market, testnet), params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_account(
        self, market: str, api_key: str, api_secret: str, testnet: bool = False
    ) -> dict:
        params = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
        query = build_signed_query(params, api_secret)
        url = f"{account_url(market, testnet)}?{query}"
        resp = await self._get(url, headers={"X-MBX-APIKEY": api_key})
        resp.raise_for_status()
        return resp.json()
