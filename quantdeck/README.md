# QuantDeck

基于 NautilusTrader 的加密量化 Web 操作台（本地单人用）。

## 环境前提
- nautilus_trader 已从源码编译，venv 位于 `../nautilus_trader/.venv`（见设计文档）。

## 启动后端
```bash
cd backend && ./run.sh
# http://localhost:8000/api/health
```

## 启动前端
```bash
cd frontend && npm run dev
# http://localhost:5173
```

## 测试
- 后端：`cd backend && PYTHONPATH=. ../../nautilus_trader/.venv/bin/python -m pytest`
- 前端：`cd frontend && npm test`

## 模块路线
0. 连接与配置管理（✅ 已完成）　1. 回测分析　2. 数据研究　3. 实盘监控　4. 策略控制

详见 `../nautilus_trader/docs/superpowers/specs/2026-05-31-crypto-quant-web-console-design.md`。
