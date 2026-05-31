# QuantDeck 模块 0：连接与配置管理 — 设计文档

- 日期：2026-05-31
- 状态：已通过头脑风暴评审，用户已预批，待写实现计划
- 上游设计：`2026-05-31-crypto-quant-web-console-design.md`
- 前置：地基（Foundation）已完成（FastAPI 后端 + WsHub + React 壳，全部测试通过）

## 1. 目标与范围

实现设计文档中的**模块 0：连接与配置管理**，这是「把加密量化能力完整开放对接网页」诉求的核心——让用户在网页上管理交易所凭证、查看本地数据目录、从交易所下载历史数据。

本模块为后续模块（回测、研究、实盘）提供**数据基础**：没有数据目录里的数据，回测与研究无从谈起。

### 范围（v1，先做初版，再完善）
- **交易所**：仅 Binance。
- **合约范围**：现货（spot）+ USDⓈ-M 永续合约（USDT-margined perpetual）。COIN-M 反向合约留待后续。
- **数据类型**：仅 OHLCV K 线（bars）。逐笔成交 / 盘口留待后续。
- **凭证**：主口令加密文件存储（Fernet + scrypt）。

### 非目标（YAGNI）
- 不做多交易所、多用户、远程鉴权。
- 不做逐笔 tick / 盘口下载。
- 不做凭证轮换、多套 key 并存（每交易所一套即可）。

## 2. 架构

后端在已有 `quantdeck_backend` 包内扩展，前端把 `ConfigPage` 占位替换为真实页面。

```
┌────────────────────────────┐         ┌──────────────────────────────────────────┐
│ React 连接配置页            │  REST   │ FastAPI 后端                               │
│  - 解锁门                  │ ──────> │  api/config.py   (unlock / exchanges)      │
│  - 凭证 CRUD + 连接测试    │         │  api/catalog.py  (列出已有数据)            │
│  - 数据目录浏览            │ <── WS ─│  api/downloads.py(建/查任务, 进度经 WsHub) │
│  - 下载任务 + 实时进度     │  进度   │                                            │
└────────────────────────────┘         │  bridge/secrets.py        SecretStore      │
                                        │  bridge/config_service.py 凭证 + 连接测试  │
                                        │  bridge/catalog_service.py ParquetCatalog  │
                                        │  bridge/download_service.py klines→Bar→写  │
                                        └──────────────────────────────────────────┘
                                                  │ httpx (公开 klines)   │ 认证端点(测连接)
                                                  v                       v
                                            Binance REST            Binance REST
                                       (api/fapi .../klines)     (/api/v3/account 等)
```

**选型（方案 A，已选）**：下载用 `httpx` 直接拉 Binance 公开 klines 端点（现货 `https://api.binance.com/api/v3/klines`、USDⓈ-M 合约 `https://fapi.binance.com/fapi/v1/klines`），分页拉取后转换为 Nautilus `Bar` 对象，经 `ParquetDataCatalog.write_data` 落盘。相比启动 Nautilus 实盘数据客户端，更轻量、对分页与限速完全可控，且公开 klines 无需 API key。

被否方案 B（复用 Nautilus Binance 适配器的 HTTP 客户端做历史请求）：需要装配 `BinanceHttpClient`、时钟等，面向实盘订阅，批量历史下载耦合更重、收益不抵成本。

## 3. 组件设计

### 3.1 SecretStore（`bridge/secrets.py`）
- 加密文件：`quantdeck/config/secrets.enc`（目录与文件均不进 git）。
- 主口令 → scrypt 派生 32 字节密钥 → Fernet 加解密 JSON（`{exchange: {api_key, api_secret, testnet}}`）。
- 盐值随密文一同存（独立 `secrets.salt` 或密文头），主口令本身永不落盘。
- 内存解锁态：进程持有派生密钥；未解锁时所有需要密钥的操作返回 `locked` 错误。
- 接口：`unlock(passphrase)`、`is_unlocked()`、`load() -> dict`、`save(dict)`、`set_credential(...)`、`get_credential(...)`、`delete_credential(...)`。
- 首次使用（文件不存在）：第一次 `unlock` 即以该口令初始化空库。

### 3.2 ConfigService（`bridge/config_service.py`）
- 依赖 SecretStore。
- `list_exchanges()` → 已配置交易所及**掩码**信息（不含明文密钥）。
- `set_exchange(name, api_key, api_secret, testnet)`、`delete_exchange(name)`。
- `test_connection(name)` → 用存的 key 调 Binance 认证端点（带签名，spot `/api/v3/account` 或 futures `/fapi/v2/account`），返回 `{ok, message, latency_ms}`。无 key 时返回未配置。

### 3.3 CatalogService（`bridge/catalog_service.py`）
- 包 `ParquetDataCatalog`，根目录取自 `Settings` 新增字段 `catalog_dir`（环境变量 `QD_CATALOG_DIR`，默认 `quantdeck/data/catalog`）。
- `list_entries()` → 遍历已有 bars：每条 `{instrument_id, bar_type, start, end, count}`。利用 `catalog.bars(...)` / `query_first_timestamp` / `query_last_timestamp`。
- 空目录返回空列表，不报错。

### 3.4 DownloadService（`bridge/download_service.py`）
- `start_download(req) -> job_id`：创建后台任务（asyncio task），登记进 `JobRegistry`。
- 任务逻辑：按 `(market, symbol, interval)` 解析为 Nautilus `BarType`；用 `query_last_timestamp` 求增量起点；分页拉 klines（每页≤1000，遵守 Binance 限速）；转 `Bar`；批量 `catalog.write_data`；每页更新进度并经 WsHub 广播 `{type:"download_progress", job_id, done, total, status}`。
- 完成 / 失败 / 取消都更新任务终态并广播。
- `JobRegistry`：内存 `dict[job_id -> DownloadJob]`，提供 `list()` / `get()`。进程重启即清空（v1 可接受；持久化留后续）。

### 3.5 数据契约（`models/`）
- `ExchangeCredentialIn`（写：api_key, api_secret, testnet）/ `ExchangeCredentialOut`（读：name, api_key 掩码, testnet, configured）。
- `ConnectionStatus`（ok, message, latency_ms）。
- `CatalogEntry`（instrument_id, bar_type, start, end, count）。
- `DownloadRequest`（market: spot|futures, symbol, intervals: list, start, end）。
- `DownloadJob`（id, request, status: pending|running|done|error|cancelled, done, total, message, created_at）。
- 复用地基的 `ApiError` 结构化错误。

### 3.6 API 路由
- `GET  /api/lock-status` → `{unlocked: bool, initialized: bool}`
- `POST /api/unlock` `{passphrase}` → 成功/失败（失败计错误，不泄露细节）
- `GET  /api/exchanges` → `list[ExchangeCredentialOut]`
- `PUT  /api/exchanges/{name}` `ExchangeCredentialIn` → 保存
- `DELETE /api/exchanges/{name}`
- `POST /api/exchanges/{name}/test` → `ConnectionStatus`
- `GET  /api/catalog` → `list[CatalogEntry]`
- `POST /api/downloads` `DownloadRequest` → `DownloadJob`
- `GET  /api/downloads` → `list[DownloadJob]`
- `GET  /api/downloads/{id}` → `DownloadJob`
- 进度推送：复用 `/ws` 的 WsHub 广播 `download_progress` 帧。
- 需要密钥但未解锁 → 返回 `423 Locked` + `ApiError(code="locked")`。

### 3.7 前端（`src/pages/ConfigPage` 真实化）
- `src/api/config.ts`：封装上述 REST（含 `useLockStatus`、`useExchanges`、`useCatalog`、`useDownloads` hooks）。
- 解锁门组件 `UnlockGate`：`lock-status` 显示未解锁时，渲染主口令输入；解锁后渲染主体。
- 凭证区 `ExchangeCredentials`：列表 + 表单（Binance 一套 key + testnet 开关）+ 连接状态徽标 + 「测试连接」。
- 目录区 `CatalogBrowser`：表格列出已有数据。
- 下载区 `DownloadPanel`：表单（市场、品种、周期多选、起止日期）→ 建任务；任务表订阅 WS `download_progress` 实时更新进度条。

## 4. 横切关注点

- **安全**：`secrets.enc` / `secrets.salt` / `config/` 进 `.gitignore`；响应只回掩码；主口令仅用于派生、不落盘、不日志。
- **错误处理**：后端统一 `ApiError`；未解锁 `423`；下载失败记入任务终态并广播；前端断线由地基的自动重连 WS 客户端兜底，重连后重拉任务列表快照。
- **限速**：下载分页之间按 Binance 权重做保守 sleep，避免封禁。
- **测试**：
  - 后端：SecretStore 加解密往返 + 错误口令；ConfigService CRUD（临时目录）；CatalogService 列举（写入小样本 bars 后读出）；DownloadService 的 kline→Bar 转换与写 catalog（mock httpx 返回固定 klines）；连接测试 mock httpx；API 路由用 TestClient（解锁/未解锁两路径）。可借 Nautilus `test_kit` 造 instrument。
  - 前端：解锁流程、凭证表单提交、目录表渲染、下载任务进度（mock fetch + 注入 WS 消息）。

## 5. 验收标准

- [ ] 后端：解锁后可增删改查 Binance 凭证，响应不含明文密钥。
- [ ] 后端：`secrets.enc` 加密落盘，错误口令无法解密。
- [ ] 后端：`/api/exchanges/{name}/test` 能返回连接状态（mock 测试覆盖）。
- [ ] 后端：`/api/downloads` 能拉 Binance 现货 + USDⓈ-M K 线写入 catalog，`/api/catalog` 能列出。
- [ ] 后端：下载进度经 WS 广播；全部 pytest 通过。
- [ ] 前端：连接配置页有解锁门、凭证 CRUD + 连接状态、目录浏览、下载任务 + 实时进度。
- [ ] 前端：全部 vitest 通过，`npm run build` 无类型错误。
- [ ] `secrets.enc` 等敏感文件确认不进 git。

模块 0 完成后，下一个计划：**模块 1 回测分析**。
