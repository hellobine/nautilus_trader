# QuantDeck 模块 0（连接与配置管理）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已完成的 QuantDeck 地基上实现模块 0——交易所凭证加密管理、Binance 连接状态检测、本地数据目录浏览、从 Binance（现货 + USDⓈ-M 永续）下载历史 K 线写入 ParquetDataCatalog，并在网页上完整操作。

**Architecture:** 后端在 `quantdeck_backend` 包内新增 `bridge/secrets.py`（Fernet+scrypt 加密存储）、`bridge/config_service.py`（凭证 CRUD + 连接测试）、`bridge/binance_client.py`（httpx 拉 klines / 签名查账户，可注入以便离线测试）、`bridge/catalog_service.py`（包 ParquetDataCatalog）、`bridge/download_service.py`（klines→Bar→写盘 + 任务进度），REST 路由分散到 `api/config.py`、`api/catalog.py`、`api/downloads.py`，下载进度复用地基的 `WsHub` 广播。前端把 `ConfigPage` 占位替换为真实页：解锁门 + 凭证 + 目录 + 下载四区。

**Tech Stack:** Python 3.12+（实际 venv 为 3.14）/ FastAPI / httpx / cryptography / pydantic / nautilus_trader（catalog、Bar/BarType）/ pytest；React + TS + Vite + Vitest。

**约定（贯穿全计划）：**
- 后端 venv python：`/home/ypw/workspace/nautilus_trader/.venv/bin/python`（记作 `$NTPY`）。
- 后端测试统一：`cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. $NTPY -m pytest <args>`。
- 前端：`cd /home/ypw/workspace/quantdeck/frontend`。
- 代码仓库为 `/home/ypw/workspace`（branch `quantdeck-foundation`），每个任务结尾 commit；commit message 中文，无署名行。
- **Binance 约定**：spot 实例 id `{SYM}.BINANCE`，USDⓈ-M 永续 id `{SYM}-PERP.BINANCE`；bar_type 形如 `BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL`。klines 公开无需 key；连接测试用签名端点。

---

### Task 0: 安装 cryptography 依赖

**Files:** 无（向 venv 安装）

- [ ] **Step 1: 安装 cryptography 到 nautilus venv**

Run:
```bash
cd /home/ypw/workspace/nautilus_trader && \
uv pip install "cryptography>=42"
```
Expected: 安装成功。

- [ ] **Step 2: 验证可导入**

Run:
```bash
/home/ypw/workspace/nautilus_trader/.venv/bin/python -c "from cryptography.fernet import Fernet; from cryptography.hazmat.primitives.kdf.scrypt import Scrypt; print('crypto ok')"
```
Expected: 打印 `crypto ok`。

- [ ] **Step 3: Commit（仅记录，无代码改动则跳过）**

无文件改动，跳过 commit。

---

### Task 1: 扩展 Settings（catalog 与 secrets 路径）

**Files:**
- Modify: `quantdeck/backend/quantdeck_backend/config.py`
- Modify: `quantdeck/backend/tests/test_config.py`

- [ ] **Step 1: 追加失败测试**

在 `quantdeck/backend/tests/test_config.py` 末尾追加：
```python
def test_catalog_and_secrets_paths():
    s = Settings()
    assert s.catalog_dir.endswith("catalog")
    assert s.secrets_path.endswith("secrets.enc")


def test_catalog_dir_env_override(monkeypatch):
    monkeypatch.setenv("QD_CATALOG_DIR", "/tmp/qd_cat")
    s = Settings()
    assert s.catalog_dir == "/tmp/qd_cat"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_config.py -v`
Expected: 新增两条 FAIL（`AttributeError: ... catalog_dir`）。

- [ ] **Step 3: 实现**

修改 `quantdeck/backend/quantdeck_backend/config.py`，在 `Settings` 类内 `cors_origins` 字段下方追加：
```python
    catalog_dir: str = os.path.join(_REPO_ROOT, "quantdeck", "data", "catalog")
    config_dir: str = os.path.join(_REPO_ROOT, "quantdeck", "config")
    secrets_path: str = os.path.join(
        _REPO_ROOT, "quantdeck", "config", "secrets.enc"
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_config.py -v`
Expected: 全部 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): Settings 增加 catalog 与 secrets 路径"
```

---

### Task 2: SecretStore（Fernet + scrypt 加密存储）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/secrets.py`
- Create: `quantdeck/backend/tests/test_secrets.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_secrets.py`:
```python
import os

import pytest

from quantdeck_backend.bridge.secrets import SecretStore


def make_store(tmp_path):
    return SecretStore(str(tmp_path / "secrets.enc"))


def test_unlock_initializes_empty(tmp_path):
    store = make_store(tmp_path)
    assert store.is_unlocked() is False
    store.unlock("pw123")
    assert store.is_unlocked() is True
    assert store.load() == {}


def test_set_get_roundtrip_persists_encrypted(tmp_path):
    store = make_store(tmp_path)
    store.unlock("pw123")
    store.set_credential("binance", {"api_key": "k", "api_secret": "s", "testnet": False})
    # 新实例、相同口令应能解出
    store2 = make_store(tmp_path)
    store2.unlock("pw123")
    assert store2.get_credential("binance") == {
        "api_key": "k",
        "api_secret": "s",
        "testnet": False,
    }
    # 落盘内容是密文，不含明文
    raw = open(tmp_path / "secrets.enc", "rb").read()
    assert b"api_secret" not in raw and b"\"s\"" not in raw


def test_wrong_passphrase_rejected(tmp_path):
    store = make_store(tmp_path)
    store.unlock("right")
    store.set_credential("binance", {"api_key": "k", "api_secret": "s", "testnet": False})
    store2 = make_store(tmp_path)
    with pytest.raises(ValueError):
        store2.unlock("wrong")


def test_delete_credential(tmp_path):
    store = make_store(tmp_path)
    store.unlock("pw")
    store.set_credential("binance", {"api_key": "k", "api_secret": "s", "testnet": False})
    store.delete_credential("binance")
    assert store.load() == {}


def test_operations_require_unlock(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(RuntimeError):
        store.load()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_secrets.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'quantdeck_backend.bridge.secrets'`。

- [ ] **Step 3: 实现 SecretStore**

`quantdeck/backend/quantdeck_backend/bridge/secrets.py`:
```python
import base64
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

_SALT_LEN = 16
_MAGIC = b"QDS1"  # 文件头标识 + 版本


class SecretStore:
    """主口令加密的凭证存储。

    文件结构（二进制）：MAGIC(4) + salt(16) + Fernet密文。
    主口令经 scrypt 派生 32 字节密钥；口令本身不落盘、不驻留除派生外的用途。
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._key: bytes | None = None  # 派生出的 Fernet key（base64）

    # ---- 内部 ----
    def _derive(self, passphrase: str, salt: bytes) -> bytes:
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        raw = kdf.derive(passphrase.encode("utf-8"))
        return base64.urlsafe_b64encode(raw)

    def _read_file(self) -> tuple[bytes, bytes] | None:
        if not os.path.exists(self._path):
            return None
        blob = open(self._path, "rb").read()
        if blob[:4] != _MAGIC:
            raise ValueError("secrets 文件格式不正确")
        salt = blob[4 : 4 + _SALT_LEN]
        cipher = blob[4 + _SALT_LEN :]
        return salt, cipher

    def _write_file(self, salt: bytes, data: dict) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        token = Fernet(self._key).encrypt(json.dumps(data).encode("utf-8"))
        with open(self._path, "wb") as f:
            f.write(_MAGIC + salt + token)
        os.chmod(self._path, 0o600)
        self._salt = salt

    # ---- 公开 ----
    def is_unlocked(self) -> bool:
        return self._key is not None

    def unlock(self, passphrase: str) -> None:
        existing = self._read_file()
        if existing is None:
            # 首次：生成新盐并初始化空库
            salt = os.urandom(_SALT_LEN)
            self._key = self._derive(passphrase, salt)
            self._write_file(salt, {})
            return
        salt, cipher = existing
        self._key = self._derive(passphrase, salt)
        self._salt = salt
        try:
            Fernet(self._key).decrypt(cipher)
        except InvalidToken as exc:
            self._key = None
            raise ValueError("主口令错误") from exc

    def load(self) -> dict:
        if not self.is_unlocked():
            raise RuntimeError("未解锁")
        existing = self._read_file()
        if existing is None:
            return {}
        _salt, cipher = existing
        return json.loads(Fernet(self._key).decrypt(cipher).decode("utf-8"))

    def _save(self, data: dict) -> None:
        if not self.is_unlocked():
            raise RuntimeError("未解锁")
        self._write_file(self._salt, data)

    def set_credential(self, name: str, cred: dict) -> None:
        data = self.load()
        data[name] = cred
        self._save(data)

    def get_credential(self, name: str) -> dict | None:
        return self.load().get(name)

    def delete_credential(self, name: str) -> None:
        data = self.load()
        data.pop(name, None)
        self._save(data)

    def initialized(self) -> bool:
        return os.path.exists(self._path)
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_secrets.py -v`
Expected: 5 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): 主口令加密的 SecretStore"
```

---

### Task 3: 数据契约模型

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/models/config.py`
- Create: `quantdeck/backend/tests/test_models_config.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_models_config.py`:
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_models_config.py -v`
Expected: FAIL，`ModuleNotFoundError: ... models.config`。

- [ ] **Step 3: 实现模型**

`quantdeck/backend/quantdeck_backend/models/config.py`:
```python
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
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_models_config.py -v`
Expected: 5 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): 模块0 数据契约模型"
```

---

### Task 4: Binance 客户端（klines + 签名账户查询，可注入）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/binance_client.py`
- Create: `quantdeck/backend/tests/test_binance_client.py`

> 设计：把 HTTP 隔离在 `BinanceKlineClient` 内，方法 `fetch_klines` / `get_account` 是仅有的网络出口。单测用 `respx` 或 monkeypatch `httpx.AsyncClient` 拦截；本计划用 monkeypatch 替换实例方法的方式离线验证纯逻辑（URL/签名构造、kline 解析）。

- [ ] **Step 1: 写失败测试（纯逻辑：URL/签名/解析，不发真网络）**

`quantdeck/backend/tests/test_binance_client.py`:
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_binance_client.py -v`
Expected: FAIL，`ModuleNotFoundError: ... binance_client`。

- [ ] **Step 3: 实现 Binance 客户端**

`quantdeck/backend/quantdeck_backend/bridge/binance_client.py`:
```python
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
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_binance_client.py -v`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): Binance klines/账户 客户端"
```

---

### Task 5: kline→Bar 转换与 BarType 映射

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/convert.py`
- Create: `quantdeck/backend/tests/test_convert.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_convert.py`:
```python
from nautilus_trader.model.data import Bar

from quantdeck_backend.bridge.convert import (
    INTERVAL_MS,
    bar_type_str,
    kline_to_bar,
)


def test_bar_type_str_spot_and_futures():
    assert bar_type_str("spot", "btcusdt", "1m") == "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
    assert bar_type_str("futures", "btcusdt", "1h") == "BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"


def test_interval_ms_table():
    assert INTERVAL_MS["1m"] == 60_000
    assert INTERVAL_MS["1d"] == 86_400_000


def test_kline_to_bar():
    row = [1700000000000, "100", "110", "90", "105", "12.5", 1700000059999, "0", 1, "0", "0", "0"]
    bar = kline_to_bar("spot", "BTCUSDT", "1m", row)
    assert isinstance(bar, Bar)
    assert str(bar.bar_type) == "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
    assert str(bar.close) == "105"
    # ts_event 取 closeTime（ms→ns）
    assert bar.ts_event == 1700000059999 * 1_000_000
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_convert.py -v`
Expected: FAIL，`ModuleNotFoundError: ... convert`。

- [ ] **Step 3: 实现转换**

`quantdeck/backend/quantdeck_backend/bridge/convert.py`:
```python
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity

INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

_INTERVAL_SPEC = {
    "1m": "1-MINUTE",
    "5m": "5-MINUTE",
    "15m": "15-MINUTE",
    "1h": "1-HOUR",
    "4h": "4-HOUR",
    "1d": "1-DAY",
}


def instrument_id_str(market: str, symbol: str) -> str:
    sym = symbol.upper()
    return f"{sym}-PERP.BINANCE" if market == "futures" else f"{sym}.BINANCE"


def bar_type_str(market: str, symbol: str, interval: str) -> str:
    return f"{instrument_id_str(market, symbol)}-{_INTERVAL_SPEC[interval]}-LAST-EXTERNAL"


def kline_to_bar(market: str, symbol: str, interval: str, row: list) -> Bar:
    bt = BarType.from_str(bar_type_str(market, symbol, interval))
    close_ms = int(row[6])
    ts = close_ms * 1_000_000
    return Bar(
        bt,
        Price.from_str(str(row[1])),
        Price.from_str(str(row[2])),
        Price.from_str(str(row[3])),
        Price.from_str(str(row[4])),
        Quantity.from_str(str(row[5])),
        ts,
        ts,
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_convert.py -v`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): kline→Bar 转换与 BarType 映射"
```

---

### Task 6: CatalogService（列出已有数据）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/catalog_service.py`
- Create: `quantdeck/backend/tests/test_catalog_service.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_catalog_service.py`:
```python
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from quantdeck_backend.bridge.catalog_service import CatalogService


def _write_sample(path):
    cat = ParquetDataCatalog(path)
    bt = BarType.from_str("BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL")
    bars = [
        Bar(bt, Price.from_str("100"), Price.from_str("101"), Price.from_str("99"),
            Price.from_str("100"), Quantity.from_str("1"), i * 60_000_000_000, i * 60_000_000_000)
        for i in range(3)
    ]
    cat.write_data(bars)


def test_empty_catalog_returns_empty(tmp_path):
    svc = CatalogService(str(tmp_path))
    assert svc.list_entries() == []


def test_lists_written_bars(tmp_path):
    _write_sample(str(tmp_path))
    svc = CatalogService(str(tmp_path))
    entries = svc.list_entries()
    assert len(entries) == 1
    e = entries[0]
    assert e.bar_type == "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
    assert e.instrument_id == "BTCUSDT.BINANCE"
    assert e.count == 3
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_catalog_service.py -v`
Expected: FAIL，`ModuleNotFoundError: ... catalog_service`。

- [ ] **Step 3: 实现 CatalogService**

`quantdeck/backend/quantdeck_backend/bridge/catalog_service.py`:
```python
import os

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from quantdeck_backend.models.config import CatalogEntry


class CatalogService:
    """包 ParquetDataCatalog，列出已有 bar 数据。"""

    def __init__(self, catalog_dir: str) -> None:
        self._dir = catalog_dir
        os.makedirs(catalog_dir, exist_ok=True)
        self._cat = ParquetDataCatalog(catalog_dir)

    def write_bars(self, bars: list) -> None:
        """写入 bars（供下载服务调用，避免外部直接触碰 catalog 内部）。"""
        self._cat.write_data(bars)

    def _bar_type_dirs(self) -> list[str]:
        bar_root = os.path.join(self._dir, "data", "bar")
        if not os.path.isdir(bar_root):
            return []
        return sorted(
            name for name in os.listdir(bar_root)
            if os.path.isdir(os.path.join(bar_root, name))
        )

    def list_entries(self) -> list[CatalogEntry]:
        entries: list[CatalogEntry] = []
        for bt in self._bar_type_dirs():
            bars = self._cat.bars(bar_types=[bt])
            first = self._cat.query_first_timestamp(Bar, identifier=bt)
            last = self._cat.query_last_timestamp(Bar, identifier=bt)
            entries.append(
                CatalogEntry(
                    instrument_id=str(BarType.from_str(bt).instrument_id),
                    bar_type=bt,
                    start=str(first) if first is not None else None,
                    end=str(last) if last is not None else None,
                    count=len(bars),
                )
            )
        return entries
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_catalog_service.py -v`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): CatalogService 列出已有数据"
```

---

### Task 7: ConfigService（凭证 CRUD + 连接测试）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/config_service.py`
- Create: `quantdeck/backend/tests/test_config_service.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_config_service.py`:
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_config_service.py -v`
Expected: FAIL，`ModuleNotFoundError: ... config_service`。

- [ ] **Step 3: 实现 ConfigService**

`quantdeck/backend/quantdeck_backend/bridge/config_service.py`:
```python
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
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_config_service.py -v`
Expected: 4 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): ConfigService 凭证CRUD与连接测试"
```

---

### Task 8: DownloadService + JobRegistry（klines→写盘 + 进度回调）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/download_service.py`
- Create: `quantdeck/backend/tests/test_download_service.py`

> 设计：`DownloadService` 注入 `BinanceKlineClient`、`CatalogService`、以及一个 `on_progress(job)` 回调（路由层把它接到 WsHub 广播）。`run_job` 是可直接 await 的协程，便于测试；`start_download` 用 `asyncio.create_task` 起后台任务。进度回调用普通函数（同步），测试收集即可。

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_download_service.py`:
```python
import pytest

from quantdeck_backend.bridge.catalog_service import CatalogService
from quantdeck_backend.bridge.download_service import DownloadService
from quantdeck_backend.models.config import DownloadRequest


class FakeClient:
    def __init__(self, pages):
        self._pages = pages
        self.calls = 0

    async def fetch_klines(self, market, symbol, interval, start_ms, end_ms, limit=1000, testnet=False):
        page = self._pages[self.calls] if self.calls < len(self._pages) else []
        self.calls += 1
        return page


def _row(open_ms, close_ms, price):
    return [open_ms, str(price), str(price + 1), str(price - 1), str(price), "1.0", close_ms, "0", 1, "0", "0", "0"]


@pytest.mark.asyncio
async def test_run_job_writes_bars_and_reports_progress(tmp_path):
    # 两页，第二页空 → 结束
    page1 = [_row(i * 60_000, i * 60_000 + 59_999, 100 + i) for i in range(3)]
    client = FakeClient([page1, []])
    catalog = CatalogService(str(tmp_path))
    events = []
    svc = DownloadService(client, catalog, on_progress=events.append)
    req = DownloadRequest(market="spot", symbol="BTCUSDT", intervals=["1m"], start="1970-01-01", end="1970-01-02")
    job = svc.create_job(req)
    await svc.run_job(job.id)

    done_job = svc.get(job.id)
    assert done_job.status == "done"
    assert done_job.done == 3
    # catalog 里应有 3 根 bar
    entries = catalog.list_entries()
    assert entries[0].count == 3
    # 进度回调至少触发一次
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_run_job_error_marks_status(tmp_path):
    class BoomClient:
        async def fetch_klines(self, *a, **k):
            raise RuntimeError("boom")

    catalog = CatalogService(str(tmp_path))
    svc = DownloadService(BoomClient(), catalog, on_progress=lambda j: None)
    req = DownloadRequest(market="spot", symbol="BTCUSDT", intervals=["1m"], start="1970-01-01", end="1970-01-02")
    job = svc.create_job(req)
    await svc.run_job(job.id)
    assert svc.get(job.id).status == "error"


def test_list_and_get(tmp_path):
    catalog = CatalogService(str(tmp_path))
    svc = DownloadService(None, catalog, on_progress=lambda j: None)
    req = DownloadRequest(market="spot", symbol="BTCUSDT", intervals=["1m"], start="1970-01-01", end="1970-01-02")
    job = svc.create_job(req)
    assert svc.list()[0].id == job.id
    assert svc.get(job.id).id == job.id
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_download_service.py -v`
Expected: FAIL，`ModuleNotFoundError: ... download_service`。

- [ ] **Step 3: 实现 DownloadService**

`quantdeck/backend/quantdeck_backend/bridge/download_service.py`:
```python
import asyncio
import datetime as dt
import itertools
from collections.abc import Callable

from nautilus_trader.model.data import Bar

from quantdeck_backend.bridge.catalog_service import CatalogService
from quantdeck_backend.bridge.convert import INTERVAL_MS, bar_type_str, kline_to_bar
from quantdeck_backend.models.config import DownloadJob, DownloadRequest

_counter = itertools.count(1)


def _to_ms(iso: str) -> int:
    s = iso.replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        d = dt.datetime.fromisoformat(s + "T00:00:00+00:00")
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


class DownloadService:
    """从 Binance 下载 K 线写入 catalog，带任务登记与进度回调。"""

    def __init__(
        self,
        client,
        catalog: CatalogService,
        on_progress: Callable[[DownloadJob], None],
    ) -> None:
        self._client = client
        self._catalog = catalog
        self._on_progress = on_progress
        self._jobs: dict[str, DownloadJob] = {}

    def create_job(self, req: DownloadRequest) -> DownloadJob:
        job_id = f"dl-{next(_counter)}"
        start_ms, end_ms = _to_ms(req.start), _to_ms(req.end)
        total = 0
        for itv in req.intervals:
            total += max(0, (end_ms - start_ms) // INTERVAL_MS[itv])
        job = DownloadJob(
            id=job_id, request=req, status="pending", done=0, total=total,
            message="", created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job
        return job

    def list(self) -> list[DownloadJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> DownloadJob:
        return self._jobs[job_id]

    def start(self, req: DownloadRequest) -> DownloadJob:
        job = self.create_job(req)
        asyncio.create_task(self.run_job(job.id))
        return job

    async def run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = "running"
        self._on_progress(job)
        try:
            for itv in job.request.intervals:
                await self._download_interval(job, itv)
            job.status = "done"
            job.message = "完成"
        except Exception as exc:  # noqa: BLE001
            job.status = "error"
            job.message = str(exc)
        self._on_progress(job)

    async def _download_interval(self, job: DownloadJob, interval: str) -> None:
        req = job.request
        cur = _to_ms(req.start)
        end_ms = _to_ms(req.end)
        step = INTERVAL_MS[interval]
        while cur < end_ms:
            rows = await self._client.fetch_klines(
                req.market, req.symbol, interval, cur, end_ms, limit=1000
            )
            if not rows:
                break
            bars: list[Bar] = [kline_to_bar(req.market, req.symbol, interval, r) for r in rows]
            self._catalog.write_bars(bars)
            job.done += len(bars)
            self._on_progress(job)
            last_open = int(rows[-1][0])
            cur = last_open + step
            if len(rows) < 1000:
                break
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_download_service.py -v`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): DownloadService 下载K线写盘与进度"
```

---

### Task 9: 应用状态容器与 WsHub 广播辅助

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/services.py`
- Modify: `quantdeck/backend/quantdeck_backend/api/ws.py`
- Create: `quantdeck/backend/tests/test_services.py`

> 目的：集中构造并持有 SecretStore / ConfigService / CatalogService / DownloadService 单例，供各路由依赖；并给 WsHub 增加一个线程/事件循环安全的「同步触发广播」入口，供 DownloadService 的同步回调使用。

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_services.py`:
```python
from quantdeck_backend.services import Services


def test_services_singletons(tmp_path, monkeypatch):
    monkeypatch.setenv("QD_CATALOG_DIR", str(tmp_path / "cat"))
    monkeypatch.setenv("QD_SECRETS_PATH", str(tmp_path / "secrets.enc"))
    svcs = Services.build()
    assert svcs.config is not None
    assert svcs.catalog is not None
    assert svcs.downloads is not None
    # downloads 与 config 共用同一个 SecretStore 实例
    assert svcs.config.store is svcs.store
```

> 注：`QD_SECRETS_PATH` 需 Settings 支持。Task 1 已加 `secrets_path` 字段且默认前缀 `QD_`，故环境变量 `QD_SECRETS_PATH` 自动生效。

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_services.py -v`
Expected: FAIL，`ModuleNotFoundError: ... services`。

- [ ] **Step 3: 实现 Services 容器与 ws 广播辅助**

`quantdeck/backend/quantdeck_backend/services.py`:
```python
from dataclasses import dataclass

from quantdeck_backend.api.ws import hub
from quantdeck_backend.bridge.binance_client import BinanceKlineClient
from quantdeck_backend.bridge.catalog_service import CatalogService
from quantdeck_backend.bridge.config_service import ConfigService
from quantdeck_backend.bridge.download_service import DownloadService
from quantdeck_backend.bridge.secrets import SecretStore
from quantdeck_backend.config import get_settings
from quantdeck_backend.models.config import DownloadJob


@dataclass
class Services:
    store: SecretStore
    config: ConfigService
    catalog: CatalogService
    downloads: DownloadService

    @classmethod
    def build(cls) -> "Services":
        settings = get_settings()
        store = SecretStore(settings.secrets_path)
        client = BinanceKlineClient()
        config = ConfigService(store, client)
        catalog = CatalogService(settings.catalog_dir)

        def on_progress(job: DownloadJob) -> None:
            hub.broadcast_threadsafe(
                {"type": "download_progress", "job": job.model_dump()}
            )

        downloads = DownloadService(client, catalog, on_progress=on_progress)
        return cls(store=store, config=config, catalog=catalog, downloads=downloads)
```

在 `quantdeck/backend/quantdeck_backend/api/ws.py` 的 `WsHub` 类中追加同步广播方法（在 `broadcast` 方法下方）：
```python
    def broadcast_threadsafe(self, message: dict) -> None:
        """供同步回调触发广播：在当前事件循环里调度 broadcast。"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # 无运行中的事件循环（如纯同步测试），静默跳过
        loop.create_task(self.broadcast(message))
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_services.py -v`
Expected: 1 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): Services 容器与 WsHub 同步广播辅助"
```

---

### Task 10: config / catalog / downloads API 路由

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/api/config.py`
- Create: `quantdeck/backend/quantdeck_backend/api/catalog.py`
- Create: `quantdeck/backend/quantdeck_backend/api/downloads.py`
- Modify: `quantdeck/backend/quantdeck_backend/main.py`
- Create: `quantdeck/backend/tests/test_api_module0.py`

> 路由用一个模块级 `Services` 单例（`get_services()`），通过 FastAPI 依赖注入。未解锁时需要密钥的端点返回 423。

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_api_module0.py`:
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_api_module0.py -v`
Expected: FAIL（路由不存在 / 模块缺失）。

- [ ] **Step 3: 实现 services 单例访问 + 三个路由 + 注册**

在 `quantdeck/backend/quantdeck_backend/services.py` 末尾追加单例访问器：
```python
_SERVICES: "Services | None" = None


def get_services() -> "Services":
    global _SERVICES
    if _SERVICES is None:
        _SERVICES = Services.build()
    return _SERVICES
```

`quantdeck/backend/quantdeck_backend/api/config.py`:
```python
from fastapi import APIRouter, HTTPException

from quantdeck_backend.models.config import ExchangeCredentialIn
from quantdeck_backend.services import get_services

router = APIRouter()


@router.get("/api/lock-status")
def lock_status() -> dict:
    s = get_services()
    return {"unlocked": s.store.is_unlocked(), "initialized": s.store.initialized()}


@router.post("/api/unlock")
def unlock(body: dict) -> dict:
    s = get_services()
    try:
        s.store.unlock(body.get("passphrase", ""))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"code": "bad_passphrase", "message": str(exc)})
    return {"unlocked": True}


def _require_unlock():
    s = get_services()
    if not s.store.is_unlocked():
        raise HTTPException(status_code=423, detail={"code": "locked", "message": "未解锁"})
    return s


@router.get("/api/exchanges")
def list_exchanges() -> list:
    s = _require_unlock()
    return [c.model_dump() for c in s.config.list_exchanges()]


@router.put("/api/exchanges/{name}")
def put_exchange(name: str, cred: ExchangeCredentialIn) -> dict:
    s = _require_unlock()
    s.config.set_exchange(name, cred)
    return {"ok": True}


@router.delete("/api/exchanges/{name}")
def delete_exchange(name: str) -> dict:
    s = _require_unlock()
    s.config.delete_exchange(name)
    return {"ok": True}


@router.post("/api/exchanges/{name}/test")
async def test_exchange(name: str) -> dict:
    s = _require_unlock()
    status = await s.config.test_connection(name)
    return status.model_dump()
```

`quantdeck/backend/quantdeck_backend/api/catalog.py`:
```python
from fastapi import APIRouter

from quantdeck_backend.services import get_services

router = APIRouter()


@router.get("/api/catalog")
def list_catalog() -> list:
    s = get_services()
    return [e.model_dump() for e in s.catalog.list_entries()]
```

`quantdeck/backend/quantdeck_backend/api/downloads.py`:
```python
from fastapi import APIRouter, HTTPException

from quantdeck_backend.models.config import DownloadRequest
from quantdeck_backend.services import get_services

router = APIRouter()


@router.post("/api/downloads")
def create_download(req: DownloadRequest) -> dict:
    s = get_services()
    job = s.downloads.start(req)
    return job.model_dump()


@router.get("/api/downloads")
def list_downloads() -> list:
    s = get_services()
    return [j.model_dump() for j in s.downloads.list()]


@router.get("/api/downloads/{job_id}")
def get_download(job_id: str) -> dict:
    s = get_services()
    try:
        return s.downloads.get(job_id).model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "任务不存在"})
```

修改 `quantdeck/backend/quantdeck_backend/main.py`，把 import 行改为并注册新路由：
```python
from quantdeck_backend.api import catalog, config, downloads, health, ws
```
并在 `app.include_router(ws.router)` 之后追加：
```python
    app.include_router(config.router)
    app.include_router(catalog.router)
    app.include_router(downloads.router)
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_api_module0.py -v`
Expected: 5 passed。

- [ ] **Step 5: 跑全部后端测试回归**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest -v`
Expected: 全部 passed。

- [ ] **Step 6: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): 模块0 REST 路由（config/catalog/downloads）"
```

---

### Task 11: 后端 .gitignore（敏感文件不进 git）

**Files:**
- Modify: `/home/ypw/workspace/.gitignore`

- [ ] **Step 1: 追加忽略规则**

向 `/home/ypw/workspace/.gitignore` 追加：
```
# QuantDeck 敏感与数据产物
quantdeck/config/
quantdeck/data/
```

- [ ] **Step 2: 验证不被追踪**

Run:
```bash
cd /home/ypw/workspace && git check-ignore quantdeck/config/secrets.enc quantdeck/data/catalog
```
Expected: 两行均被列出（命中忽略规则）。

- [ ] **Step 3: Commit**

```bash
cd /home/ypw/workspace && git add .gitignore && \
git commit -m "chore: 忽略 QuantDeck 敏感凭证与数据目录"
```

---

### Task 12: 前端 API 封装（config/catalog/downloads + hooks）

**Files:**
- Create: `quantdeck/frontend/src/api/config.ts`
- Create: `quantdeck/frontend/src/api/config.test.ts`
- Modify: `quantdeck/frontend/src/api/client.ts`（增加 `apiPost`/`apiPut`/`apiDelete`）

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/api/config.test.ts`:
```typescript
import { afterEach, expect, test, vi } from "vitest";
import { getLockStatus, unlock, listExchanges } from "./config";

afterEach(() => vi.restoreAllMocks());

function stubJson(data: unknown, ok = true) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 423, json: async () => data }));
}

test("getLockStatus parses response", async () => {
  stubJson({ unlocked: false, initialized: true });
  const s = await getLockStatus();
  expect(s.unlocked).toBe(false);
});

test("unlock posts passphrase", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ unlocked: true }) });
  vi.stubGlobal("fetch", fetchMock);
  await unlock("pw");
  expect(fetchMock).toHaveBeenCalledWith("/api/unlock", expect.objectContaining({ method: "POST" }));
});

test("listExchanges returns array", async () => {
  stubJson([{ name: "binance", api_key: "abcd****ghij", testnet: false }]);
  const list = await listExchanges();
  expect(list[0].name).toBe("binance");
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/api/config.test.ts`
Expected: FAIL，找不到 `./config`。

- [ ] **Step 3: 扩展 client.ts 与实现 config.ts**

在 `quantdeck/frontend/src/api/client.ts` 末尾追加：
```typescript
async function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    let err: ApiError = { code: "http_error", message: resp.statusText };
    try {
      const j = await resp.json();
      err = j.detail ?? j;
    } catch {
      /* 保留默认错误 */
    }
    throw err;
  }
  return (await resp.json()) as T;
}

export const apiPost = <T>(path: string, body?: unknown) => send<T>(path, "POST", body);
export const apiPut = <T>(path: string, body?: unknown) => send<T>(path, "PUT", body);
export const apiDelete = <T>(path: string) => send<T>(path, "DELETE");
```

`quantdeck/frontend/src/api/config.ts`:
```typescript
import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface LockStatus {
  unlocked: boolean;
  initialized: boolean;
}
export interface ExchangeOut {
  name: string;
  api_key: string;
  testnet: boolean;
}
export interface ConnectionStatus {
  ok: boolean;
  message: string;
  latency_ms: number;
}
export interface CatalogEntry {
  instrument_id: string;
  bar_type: string;
  start: string | null;
  end: string | null;
  count: number;
}
export interface DownloadRequest {
  market: "spot" | "futures";
  symbol: string;
  intervals: string[];
  start: string;
  end: string;
}
export interface DownloadJob {
  id: string;
  request: DownloadRequest;
  status: "pending" | "running" | "done" | "error" | "cancelled";
  done: number;
  total: number;
  message: string;
  created_at: string;
}

export const getLockStatus = () => apiGet<LockStatus>("/api/lock-status");
export const unlock = (passphrase: string) => apiPost<{ unlocked: boolean }>("/api/unlock", { passphrase });
export const listExchanges = () => apiGet<ExchangeOut[]>("/api/exchanges");
export const putExchange = (name: string, body: { api_key: string; api_secret: string; testnet: boolean }) =>
  apiPut<{ ok: boolean }>(`/api/exchanges/${name}`, body);
export const deleteExchange = (name: string) => apiDelete<{ ok: boolean }>(`/api/exchanges/${name}`);
export const testExchange = (name: string) => apiPost<ConnectionStatus>(`/api/exchanges/${name}/test`);
export const listCatalog = () => apiGet<CatalogEntry[]>("/api/catalog");
export const createDownload = (req: DownloadRequest) => apiPost<DownloadJob>("/api/downloads", req);
export const listDownloads = () => apiGet<DownloadJob[]>("/api/downloads");
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/api/config.test.ts`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/api && \
git commit -m "feat(frontend): 模块0 API 封装与请求辅助"
```

---

### Task 13: UnlockGate 组件

**Files:**
- Create: `quantdeck/frontend/src/components/UnlockGate.tsx`
- Create: `quantdeck/frontend/src/components/UnlockGate.test.tsx`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/components/UnlockGate.test.tsx`:
```typescript
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { UnlockGate } from "./UnlockGate";

afterEach(() => vi.restoreAllMocks());

test("shows children when unlocked", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => ({ unlocked: true, initialized: true }),
  }));
  render(<UnlockGate><div>内部内容</div></UnlockGate>);
  await waitFor(() => expect(screen.getByText("内部内容")).toBeInTheDocument());
});

test("shows passphrase form when locked, unlocks on submit", async () => {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: { method?: string }) => {
    calls.push(`${opts?.method ?? "GET"} ${url}`);
    if (url === "/api/lock-status") {
      const unlocked = calls.filter((c) => c === "POST /api/unlock").length > 0;
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ unlocked, initialized: true }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ unlocked: true }) });
  }));
  render(<UnlockGate><div>内部内容</div></UnlockGate>);
  await waitFor(() => expect(screen.getByLabelText("主口令")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("主口令"), { target: { value: "pw" } });
  fireEvent.click(screen.getByRole("button", { name: "解锁" }));
  await waitFor(() => expect(screen.getByText("内部内容")).toBeInTheDocument());
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/UnlockGate.test.tsx`
Expected: FAIL，找不到 `./UnlockGate`。

- [ ] **Step 3: 实现 UnlockGate**

`quantdeck/frontend/src/components/UnlockGate.tsx`:
```typescript
import { useEffect, useState } from "react";
import { getLockStatus, unlock } from "../api/config";

export function UnlockGate({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => getLockStatus().then((s) => setUnlocked(s.unlocked)).catch(() => setUnlocked(false));
  useEffect(() => { refresh(); }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await unlock(pw);
      await refresh();
    } catch (err) {
      setError(String((err as { message?: string })?.message ?? "解锁失败"));
    }
  };

  if (unlocked === null) return <p>加载中…</p>;
  if (unlocked) return <>{children}</>;

  return (
    <form onSubmit={onSubmit} style={{ maxWidth: 320 }}>
      <h2>解锁凭证库</h2>
      <label htmlFor="pw">主口令</label>
      <input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      <button type="submit">解锁</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </form>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/UnlockGate.test.tsx`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/components/UnlockGate.tsx quantdeck/frontend/src/components/UnlockGate.test.tsx && \
git commit -m "feat(frontend): 解锁门组件"
```

---

### Task 14: ExchangeCredentials 组件

**Files:**
- Create: `quantdeck/frontend/src/components/ExchangeCredentials.tsx`
- Create: `quantdeck/frontend/src/components/ExchangeCredentials.test.tsx`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/components/ExchangeCredentials.test.tsx`:
```typescript
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ExchangeCredentials } from "./ExchangeCredentials";

afterEach(() => vi.restoreAllMocks());

test("lists existing credentials", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => [{ name: "binance", api_key: "abcd****ghij", testnet: false }],
  }));
  render(<ExchangeCredentials />);
  await waitFor(() => expect(screen.getByText("abcd****ghij")).toBeInTheDocument());
});

test("submits new credential", async () => {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: { method?: string }) => {
    calls.push({ url, method: opts?.method ?? "GET" });
    return Promise.resolve({ ok: true, status: 200, json: async () => (url === "/api/exchanges" ? [] : { ok: true }) });
  }));
  render(<ExchangeCredentials />);
  await waitFor(() => expect(screen.getByLabelText("API Key")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("API Key"), { target: { value: "mykey" } });
  fireEvent.change(screen.getByLabelText("API Secret"), { target: { value: "mysecret" } });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() => expect(calls.some((c) => c.method === "PUT" && c.url === "/api/exchanges/binance")).toBe(true));
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/ExchangeCredentials.test.tsx`
Expected: FAIL，找不到组件。

- [ ] **Step 3: 实现 ExchangeCredentials**

`quantdeck/frontend/src/components/ExchangeCredentials.tsx`:
```typescript
import { useEffect, useState } from "react";
import {
  type ConnectionStatus,
  type ExchangeOut,
  deleteExchange,
  listExchanges,
  putExchange,
  testExchange,
} from "../api/config";

export function ExchangeCredentials() {
  const [items, setItems] = useState<ExchangeOut[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [testnet, setTestnet] = useState(false);
  const [status, setStatus] = useState<Record<string, ConnectionStatus>>({});

  const refresh = () => listExchanges().then(setItems).catch(() => setItems([]));
  useEffect(() => { refresh(); }, []);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await putExchange("binance", { api_key: apiKey, api_secret: apiSecret, testnet });
    setApiKey(""); setApiSecret("");
    await refresh();
  };

  const onTest = async (name: string) => {
    const s = await testExchange(name);
    setStatus((prev) => ({ ...prev, [name]: s }));
  };

  return (
    <section>
      <h2>交易所凭证（Binance）</h2>
      <table>
        <tbody>
          {items.map((it) => (
            <tr key={it.name}>
              <td>{it.name}</td>
              <td>{it.api_key}</td>
              <td>{it.testnet ? "testnet" : "mainnet"}</td>
              <td><button onClick={() => onTest(it.name)}>测试连接</button></td>
              <td>{status[it.name] ? (status[it.name].ok ? "✅ " : "❌ ") + status[it.name].message : ""}</td>
              <td><button onClick={async () => { await deleteExchange(it.name); await refresh(); }}>删除</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <form onSubmit={onSave}>
        <div>
          <label htmlFor="ak">API Key</label>
          <input id="ak" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        </div>
        <div>
          <label htmlFor="as">API Secret</label>
          <input id="as" type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} />
        </div>
        <label>
          <input type="checkbox" checked={testnet} onChange={(e) => setTestnet(e.target.checked)} /> testnet
        </label>
        <button type="submit">保存</button>
      </form>
    </section>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/ExchangeCredentials.test.tsx`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/components/ExchangeCredentials.tsx quantdeck/frontend/src/components/ExchangeCredentials.test.tsx && \
git commit -m "feat(frontend): 交易所凭证管理组件"
```

---

### Task 15: CatalogBrowser 组件

**Files:**
- Create: `quantdeck/frontend/src/components/CatalogBrowser.tsx`
- Create: `quantdeck/frontend/src/components/CatalogBrowser.test.tsx`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/components/CatalogBrowser.test.tsx`:
```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { CatalogBrowser } from "./CatalogBrowser";

afterEach(() => vi.restoreAllMocks());

test("renders catalog entries", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => [
      { instrument_id: "BTCUSDT.BINANCE", bar_type: "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL",
        start: "2024-01-01", end: "2024-01-02", count: 1440 },
    ],
  }));
  render(<CatalogBrowser />);
  await waitFor(() => expect(screen.getByText("BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL")).toBeInTheDocument());
  expect(screen.getByText("1440")).toBeInTheDocument();
});

test("shows empty hint when no data", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] }));
  render(<CatalogBrowser />);
  await waitFor(() => expect(screen.getByText("暂无数据")).toBeInTheDocument());
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/CatalogBrowser.test.tsx`
Expected: FAIL，找不到组件。

- [ ] **Step 3: 实现 CatalogBrowser**

`quantdeck/frontend/src/components/CatalogBrowser.tsx`:
```typescript
import { useEffect, useState } from "react";
import { type CatalogEntry, listCatalog } from "../api/config";

export function CatalogBrowser() {
  const [entries, setEntries] = useState<CatalogEntry[]>([]);
  useEffect(() => { listCatalog().then(setEntries).catch(() => setEntries([])); }, []);

  return (
    <section>
      <h2>数据目录</h2>
      {entries.length === 0 ? (
        <p>暂无数据</p>
      ) : (
        <table>
          <thead>
            <tr><th>Bar 类型</th><th>起</th><th>止</th><th>数量</th></tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.bar_type}>
                <td>{e.bar_type}</td>
                <td>{e.start ?? "-"}</td>
                <td>{e.end ?? "-"}</td>
                <td>{e.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/CatalogBrowser.test.tsx`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/components/CatalogBrowser.tsx quantdeck/frontend/src/components/CatalogBrowser.test.tsx && \
git commit -m "feat(frontend): 数据目录浏览组件"
```

---

### Task 16: DownloadPanel 组件（建任务 + WS 实时进度）

**Files:**
- Create: `quantdeck/frontend/src/components/DownloadPanel.tsx`
- Create: `quantdeck/frontend/src/components/DownloadPanel.test.tsx`

> 进度通过地基的 `createWsClient` 订阅 `/ws`；收到 `{type:"download_progress", job}` 时更新对应任务。组件接受可选 `wsFactory` 注入便于测试。

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/components/DownloadPanel.test.tsx`:
```typescript
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { DownloadPanel } from "./DownloadPanel";

afterEach(() => vi.restoreAllMocks());

test("creates a download job on submit", async () => {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: { method?: string }) => {
    calls.push({ url, method: opts?.method ?? "GET" });
    if (url === "/api/downloads" && (opts?.method ?? "GET") === "POST") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({
        id: "dl-1", status: "pending", done: 0, total: 100, message: "",
        request: { market: "spot", symbol: "BTCUSDT", intervals: ["1m"], start: "2024-01-01", end: "2024-01-02" },
        created_at: "now",
      }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => [] });
  }));
  render(<DownloadPanel wsFactory={() => ({ close: () => {} })} />);
  await waitFor(() => expect(screen.getByLabelText("品种")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("品种"), { target: { value: "BTCUSDT" } });
  fireEvent.change(screen.getByLabelText("开始"), { target: { value: "2024-01-01" } });
  fireEvent.change(screen.getByLabelText("结束"), { target: { value: "2024-01-02" } });
  fireEvent.click(screen.getByRole("button", { name: "开始下载" }));
  await waitFor(() => expect(screen.getByText("dl-1")).toBeInTheDocument());
});

test("updates progress from ws message", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] }));
  let handler: (m: unknown) => void = () => {};
  render(<DownloadPanel wsFactory={(_p, onMsg) => { handler = onMsg; return { close: () => {} }; }} />);
  handler({ type: "download_progress", job: {
    id: "dl-9", status: "running", done: 50, total: 100, message: "",
    request: { market: "spot", symbol: "BTCUSDT", intervals: ["1m"], start: "a", end: "b" }, created_at: "now",
  } });
  await waitFor(() => expect(screen.getByText("dl-9")).toBeInTheDocument());
  expect(screen.getByText(/50 \/ 100/)).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/DownloadPanel.test.tsx`
Expected: FAIL，找不到组件。

- [ ] **Step 3: 实现 DownloadPanel**

`quantdeck/frontend/src/components/DownloadPanel.tsx`:
```typescript
import { useEffect, useState } from "react";
import { type DownloadJob, createDownload, listDownloads } from "../api/config";
import { createWsClient, type WsClient, type WsHandler } from "../api/ws";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"];

type WsFactory = (path: string, onMessage: WsHandler) => WsClient;

export function DownloadPanel({ wsFactory = createWsClient }: { wsFactory?: WsFactory }) {
  const [market, setMarket] = useState<"spot" | "futures">("spot");
  const [symbol, setSymbol] = useState("");
  const [intervals, setIntervals] = useState<string[]>(["1m"]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [jobs, setJobs] = useState<Record<string, DownloadJob>>({});

  useEffect(() => {
    listDownloads().then((list) => {
      setJobs(Object.fromEntries(list.map((j) => [j.id, j])));
    }).catch(() => {});
    const client = wsFactory("/ws", (msg) => {
      const m = msg as { type?: string; job?: DownloadJob };
      if (m.type === "download_progress" && m.job) {
        setJobs((prev) => ({ ...prev, [m.job!.id]: m.job! }));
      }
    });
    return () => client.close();
  }, [wsFactory]);

  const toggleInterval = (itv: string) =>
    setIntervals((prev) => (prev.includes(itv) ? prev.filter((x) => x !== itv) : [...prev, itv]));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const job = await createDownload({ market, symbol, intervals, start, end });
    setJobs((prev) => ({ ...prev, [job.id]: job }));
  };

  return (
    <section>
      <h2>下载历史数据</h2>
      <form onSubmit={onSubmit}>
        <label htmlFor="mkt">市场</label>
        <select id="mkt" value={market} onChange={(e) => setMarket(e.target.value as "spot" | "futures")}>
          <option value="spot">现货</option>
          <option value="futures">合约(USDⓈ-M)</option>
        </select>
        <label htmlFor="sym">品种</label>
        <input id="sym" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        <fieldset>
          <legend>周期</legend>
          {INTERVALS.map((itv) => (
            <label key={itv}>
              <input type="checkbox" checked={intervals.includes(itv)} onChange={() => toggleInterval(itv)} /> {itv}
            </label>
          ))}
        </fieldset>
        <label htmlFor="start">开始</label>
        <input id="start" value={start} onChange={(e) => setStart(e.target.value)} />
        <label htmlFor="end">结束</label>
        <input id="end" value={end} onChange={(e) => setEnd(e.target.value)} />
        <button type="submit">开始下载</button>
      </form>
      <table>
        <thead><tr><th>任务</th><th>状态</th><th>进度</th></tr></thead>
        <tbody>
          {Object.values(jobs).map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td>
              <td>{j.status}</td>
              <td>{j.done} / {j.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/components/DownloadPanel.test.tsx`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/components/DownloadPanel.tsx quantdeck/frontend/src/components/DownloadPanel.test.tsx && \
git commit -m "feat(frontend): 下载面板与实时进度组件"
```

---

### Task 17: 组装 ConfigPage 真实页 + 构建验证

**Files:**
- Modify: `quantdeck/frontend/src/pages/index.tsx`
- Create: `quantdeck/frontend/src/pages/ConfigPage.test.tsx`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/pages/ConfigPage.test.tsx`:
```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ConfigPage } from "./index";

afterEach(() => vi.restoreAllMocks());

test("renders all four sections when unlocked", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url === "/api/lock-status") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ unlocked: true, initialized: true }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => [] });
  }));
  render(<ConfigPage wsFactory={() => ({ close: () => {} })} />);
  await waitFor(() => expect(screen.getByText("交易所凭证（Binance）")).toBeInTheDocument());
  expect(screen.getByText("数据目录")).toBeInTheDocument();
  expect(screen.getByText("下载历史数据")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/pages/ConfigPage.test.tsx`
Expected: FAIL（`ConfigPage` 仍是占位、无这些区块）。

- [ ] **Step 3: 改写 ConfigPage**

修改 `quantdeck/frontend/src/pages/index.tsx`：把 `ConfigPage` 那一行替换为真实实现，并补充 import（其余 Placeholder 页保持不变）。文件顶部加：
```typescript
import { UnlockGate } from "../components/UnlockGate";
import { ExchangeCredentials } from "../components/ExchangeCredentials";
import { CatalogBrowser } from "../components/CatalogBrowser";
import { DownloadPanel } from "../components/DownloadPanel";
import type { WsClient, WsHandler } from "../api/ws";
```
把 `export const ConfigPage = () => <Placeholder title="连接与配置管理" />;` 替换为：
```typescript
export function ConfigPage({
  wsFactory,
}: {
  wsFactory?: (path: string, onMessage: WsHandler) => WsClient;
}) {
  return (
    <UnlockGate>
      <h1>连接与配置管理</h1>
      <ExchangeCredentials />
      <CatalogBrowser />
      <DownloadPanel wsFactory={wsFactory} />
    </UnlockGate>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/pages/ConfigPage.test.tsx`
Expected: 1 passed。

- [ ] **Step 5: 全部前端测试 + 构建**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npm test && npm run build
```
Expected: 全部 vitest passed；`tsc -b` 无类型错误，vite 构建出 `dist/`。

> 若 `npm run build` 因 `DownloadPanel` 默认参数 `wsFactory = createWsClient` 的类型不匹配报错，将 `createWsClient` 的签名核对：地基 `ws.ts` 的 `createWsClient(path, onMessage, reconnectMs?)` 与 `WsFactory` 前两参一致，TypeScript 允许少参赋值，无需改动。

- [ ] **Step 6: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/pages && \
git commit -m "feat(frontend): 组装连接配置页（解锁+凭证+目录+下载）"
```

---

### Task 18: 端到端冒烟 + 验收

**Files:** 无（验证）

- [ ] **Step 1: 后端全部测试回归**

Run: `cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest -v`
Expected: 全部 passed。

- [ ] **Step 2: 起后端，手动验证锁/解锁与目录端点**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m uvicorn quantdeck_backend.main:app --port 8000 & sleep 3
curl -s http://localhost:8000/api/lock-status
curl -s -X POST http://localhost:8000/api/unlock -H 'Content-Type: application/json' -d '{"passphrase":"pw"}'
curl -s http://localhost:8000/api/catalog
kill %1
```
Expected: 第一次 `unlocked:false`；unlock 后 `unlocked:true`；catalog 返回 `[]`。

- [ ] **Step 3: 真实下载一小段现货 K 线冒烟（需联网）**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m uvicorn quantdeck_backend.main:app --port 8000 & sleep 3
curl -s -X POST http://localhost:8000/api/unlock -H 'Content-Type: application/json' -d '{"passphrase":"pw"}'
curl -s -X POST http://localhost:8000/api/downloads -H 'Content-Type: application/json' \
  -d '{"market":"spot","symbol":"BTCUSDT","intervals":["1h"],"start":"2024-01-01","end":"2024-01-03"}'
sleep 5
curl -s http://localhost:8000/api/downloads
curl -s http://localhost:8000/api/catalog
kill %1
```
Expected: 下载任务最终 `status:"done"`，catalog 出现 `BTCUSDT.BINANCE-1-HOUR-LAST-EXTERNAL` 且 `count>0`。（若无网络则跳过此步并记录。）

- [ ] **Step 4: 确认敏感文件未被 git 追踪**

Run: `cd /home/ypw/workspace && git status --porcelain quantdeck/config quantdeck/data`
Expected: 无输出（被 .gitignore 排除）。

- [ ] **Step 5: 更新 README 模块进度**

在 `quantdeck/README.md` 的「模块路线」一节，把模块 0 标注为已完成（在该行追加 `（✅ 已完成）`）。

- [ ] **Step 6: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/README.md && \
git commit -m "docs(quantdeck): 模块0 完成，更新 README 进度"
```

---

## 完成标准（模块 0 验收）

- [ ] 解锁后可增删改查 Binance 凭证，列表只返回掩码 key。
- [ ] `secrets.enc` 为密文，错误主口令无法解锁。
- [ ] `/api/exchanges/{name}/test` 返回连接状态（单测覆盖 ok/未配置）。
- [ ] `/api/downloads` 能拉 Binance 现货 + USDⓈ-M K 线写入 catalog；`/api/catalog` 列出。
- [ ] 下载进度经 `/ws` 广播 `download_progress`。
- [ ] 后端全部 pytest 通过。
- [ ] 前端连接配置页含解锁门、凭证 CRUD+连接测试、目录浏览、下载任务+实时进度。
- [ ] 前端全部 vitest 通过，`npm run build` 无类型错误。
- [ ] `quantdeck/config/`、`quantdeck/data/` 不进 git。

模块 0 完成后，下一个计划：**模块 1 回测分析**。
