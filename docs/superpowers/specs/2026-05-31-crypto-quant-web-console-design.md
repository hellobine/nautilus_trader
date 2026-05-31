# 加密量化 Web 操作台 (QuantDeck) — 设计文档

- 日期：2026-05-31
- 状态：已通过头脑风暴评审，待用户最终过目
- 工作目录：`/home/ypw/workspace`
- 依赖项目：`/home/ypw/workspace/nautilus_trader`（NautilusTrader，Rust/Python 算法交易平台）

## 1. 目标与范围

构建一个**本地单人使用**的可视化 Web 操作台，把 NautilusTrader 加密货币量化工作流的**完整能力**搬到网页上操作——即用网页 GUI 全面替代「手写 Python 脚本 / 改 config」。

核心诉求（用户原话）：「把加密部分的功能完整开放对接网页操作」。因此本系统不只是「看」，更是「操作台」：凡是当前要写代码/配置才能做的加密量化操作，网页上都要有对应入口。

### 部署形态
- 主形态：本地单人用，localhost 访问，不做多用户/权限。
- 架构预留：前后端解耦、配置化，将来挂到自己服务器加一层登录即可远程使用。

### 非目标（YAGNI）
- 不做多租户、多用户权限、商业化。
- 不做复杂的因子研究平台——数据研究里的因子探索先做最小可用。

## 2. 架构

方案：**独立 Python 后端桥接 + React 前端**（评审中的方案 1）。

```
┌─────────────┐   REST 查询      ┌──────────────────┐
│  React 前端  │ ───────────────> │                  │      ┌─ 回测: Nautilus Python API / 结果文件
│  (浏览器)    │ <─── WebSocket ─ │  FastAPI 后端     │ ───> ├─ 实盘: Redis (msgbus 流 + cache)
│              │   实时推送        │  (NautilusBridge) │      └─ 研究: Parquet 数据目录 (catalog)
└─────────────┘                  └──────────────────┘
                                          │ 发命令 (启停/下单)
                                          └──> 实盘 TradingNode (经 Redis msgbus)
```

### 技术栈
- **后端**：Python 3.12 + FastAPI + Uvicorn，与 NautilusTrader 同环境，直接 `import nautilus_trader` 复用其模型、`analysis/`、`indicators/`、`persistence/catalog`。REST 提供查询，WebSocket 提供实时推送。
- **前端**：React + TypeScript + Vite。
  - K 线 / 成交点：TradingView `lightweight-charts`。
  - 收益曲线 / 回撤 / 柱状指标：ECharts。
- **通信**：REST（查询、命令）+ WebSocket（实时流）。

### 核心抽象：NautilusBridge
后端核心抽象层，把三类数据源统一成前端可消费的格式，使前端组件在「回测 / 实盘」间可复用：
- `BacktestService` — 触发回测 + 读取存档结果。
- `LiveService` — 读 Redis cache 快照 + 订阅 msgbus 流增量。
- `ResearchService` — 读 Parquet 数据目录 + 叠加指标。
- `ControlService` — 反向发命令（启停 / 下单 / 平仓）。
- `ConfigService` — 交易所账户、API key、数据目录、数据下载管理。

## 3. 数据源对接细节

### ① 回测（静态数据）
- 触发回测：前端选策略 + 参数 + 品种 + 时间范围 → 后端用 `BacktestEngine` 跑 → 结果（账户报告、成交、持仓、收益序列）存为结构化文件 `runs/<run_id>/result.json` + parquet。
- 读取结果：前端列出历史 run 并查看，从存档读取，不重跑。
- 收益曲线、回撤、统计指标复用 Nautilus `analysis/`（analyzer、statistic、tearsheet）。

### ② 实盘（实时数据流）
- 前提：实盘 `TradingNode` 配置为 Redis 作 cache 后端 + msgbus 对外流式输出（Nautilus 原生支持）。
- 快照：开页时从 Redis cache 读当前持仓 / 订单 / 账户余额。
- 增量：订阅 Redis msgbus 流（成交、订单状态、行情 tick），经 WebSocket 推送前端。
- 断线重连：重新拉一次快照即可恢复。

### ③ 数据研究（历史数据）
- 读 `ParquetDataCatalog`：列出品种 / 周期 / 时间范围，按需加载 K 线。
- 叠加指标：复用 Nautilus `indicators/`（EMA、RSI、MACD、布林带等）。

### ④ 策略控制（发命令）
- 启停策略、手动下单 / 撤单 / 平仓、一键清仓（kill switch）。
- 经 Redis 往实盘节点 msgbus 命令主题发消息。
- **风险控制**：所有写操作二次确认弹窗 + 完整操作日志（时间、操作内容）。

## 4. 五大功能模块

### 模块 0：连接与配置管理（核心，对应「完整开放对接」诉求）
- 交易所账户 / API key 管理（binance、bybit、okx、deribit、hyperliquid 等），连接状态显示。
- 数据目录管理：查看已有数据。
- 从交易所下载历史数据进数据目录。

### 模块 1：回测分析页
- 选历史 run / 新建回测（策略、参数、品种、时间范围）。
- 收益曲线 + 回撤曲线（ECharts，可缩放）。
- 核心指标卡片：总收益、夏普、最大回撤、胜率、盈亏比、交易次数等。
- 成交明细表（排序 / 筛选）。
- K 线叠加买卖点（lightweight-charts），表格成交可定位到图上。

### 模块 2：数据研究页
- 左侧：数据目录浏览（品种 / 周期 / 时间范围）。
- 主区：K 线图，叠加指标（EMA/RSI/MACD/布林带），多周期切换、缩放。
- 轻量因子探索（最小可用）：选指标 + 品种，看分布 / 相关性。

### 模块 3：实盘监控页（第二阶段）
- 总览：账户余额、总持仓、当日盈亏（实时）。
- 持仓表、活动订单表（WebSocket 实时更新）。
- 实时 K 线 + 当前挂单 / 成交标记。
- 策略运行状态指示灯。

### 模块 4：策略控制页（第二阶段）
- 策略列表：启动 / 停止、查看 / 修改参数。
- 手动操作面板：下单、撤单、平某仓、一键清仓。
- 所有写操作：二次确认弹窗 + 操作日志。

## 5. 工程结构

```
quantdeck/
  backend/          # FastAPI 服务
    bridge/         # NautilusBridge: backtest / live / research / control / config 五个 service
    api/            # REST 路由 + WebSocket
    models/         # 前后端数据契约 (pydantic)
    main.py
  frontend/         # React + TS + Vite
    src/pages/      # 五个模块对应页面
    src/components/ # 图表、表格等复用组件
    src/api/        # 调后端的封装
  runs/             # 回测结果存档
  config/           # 应用配置 (不含明文密钥)
```

## 6. 横切关注点

- **安全**：API key 本地加密存储，不进 git、不明文；所有实盘写操作二次确认 + 操作日志。
- **错误处理**：后端统一异常 → 结构化错误返回；WebSocket 断线前端自动重连并重拉快照；回测 / 下载等长任务用任务状态轮询。
- **测试**：后端用 NautilusTrader 自带 `test_kit` 造数据，service 层单测；前端关键组件测渲染与交互。

## 7. 实现顺序

每块独立「设计 → 计划 → 实现」小循环：

1. **地基**：后端骨架（FastAPI + NautilusBridge 抽象 + WebSocket hub）+ 前端壳（路由、布局、API 封装）。
2. **模块 0**：连接与配置管理。
3. **模块 1**：回测分析。
4. **模块 2**：数据研究。
5. **（用户上实盘后）模块 3**：实盘监控。
6. **模块 4**：策略控制。

第 1~4 步靠静态 / 历史数据，不依赖实盘节点，立即可用；第 5~6 步按 Redis 方案预留，用户上实盘时配置一开即接。

## 8. 待办与开放问题

- 第一阶段（地基 + 模块 0/1/2）将作为首个实现计划。
- 实盘相关模块（3/4）的细化在用户开始实盘、确定 Redis 配置后再进入各自的设计循环。
