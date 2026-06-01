from typing import Literal

from pydantic import BaseModel, field_validator


def mask_key(key: str) -> str:
    """保留首尾各 4 位，中间打码；过短则全打码。"""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


class ExchangeCredentialIn(BaseModel):
    api_key: str
    api_secret: str
    testnet: bool = False


class ExchangeCredentialOut(BaseModel):
    name: str
    api_key: str  # 存入时已是掩码或在构造处掩码
    testnet: bool

    @field_validator("api_key")
    @classmethod
    def _mask(cls, v: str) -> str:
        return mask_key(v)


class ConnectionStatus(BaseModel):
    ok: bool
    message: str
    latency_ms: int


class DownloadRequest(BaseModel):
    market: Literal["spot", "futures"]
    symbol: str
    intervals: list[str]
    start: str  # ISO 日期/时间，UTC
    end: str


class DownloadJob(BaseModel):
    id: str
    request: DownloadRequest
    status: Literal["pending", "running", "done", "error", "cancelled"]
    done: int = 0
    total: int = 0
    message: str = ""
    created_at: str


class CatalogEntry(BaseModel):
    instrument_id: str
    bar_type: str
    start: str | None
    end: str | None
    count: int
