# QuantDeck 地基 (Foundation) 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭好 QuantDeck 的可运行地基——一个能 `import nautilus_trader` 的 FastAPI 后端（含健康检查、NautilusBridge 抽象、WebSocket hub、结构化错误）+ 一个 React/TS/Vite 前端壳（五页路由、布局、REST/WS 客户端），前后端能联通。

**Architecture:** Python 3.12 FastAPI 后端，复用从源码编译的 nautilus_trader 的 uv 虚拟环境；React+TS+Vite 前端经 Vite dev proxy 调后端 REST，并通过自动重连的 WebSocket 接收实时流。

**Tech Stack:** Python 3.12 / FastAPI / Uvicorn / pytest / nautilus_trader（源码编译）；Node 22 / React / TypeScript / Vite / Vitest / React Testing Library。

**约定（贯穿全计划）：**
- 仓库根：`/home/ypw/workspace`（已是 git 仓库，`.gitignore` 已排除 `nautilus_trader/`）。
- Nautilus 虚拟环境 python：`/home/ypw/workspace/nautilus_trader/.venv/bin/python`（Task 0 产出）。下文记作 `$NTPY`。后端运行与测试都用它。
- 后端代码在 `quantdeck/backend/`，前端在 `quantdeck/frontend/`。
- 每个任务结尾 commit；commit message 用中文，结尾不加署名行（本仓库非协作仓库，保持简洁）。

---

### Task 0: 环境搭建（从源码编译 nautilus_trader）

**Files:**
- Create: 无（系统级安装 + 编译）

> 本任务是硬前提，且涉及系统级安装与一次较久的编译（10–30 分钟）。逐步执行并验证。`sudo apt-get` 可能需要输入密码。

- [ ] **Step 1: 安装 clang 与 lld（Rust 链接器）**

Run:
```bash
sudo apt-get update && sudo apt-get install -y clang lld
```
Expected: 安装成功。验证：
```bash
clang --version
```
Expected: 输出 clang 版本号（如 `clang version 14...`）。

- [ ] **Step 2: 安装 rustup + Rust 工具链**

Run:
```bash
curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"
```
Expected: 安装成功。

- [ ] **Step 3: 验证 Rust 版本满足要求（rust-toolchain.toml 指定 1.96.0）**

Run:
```bash
cd /home/ypw/workspace/nautilus_trader && rustc --version
```
Expected: 进入目录后 rustup 自动按 `rust-toolchain.toml` 解析为 `rustc 1.96.0`（首次会自动下载该版本）。

- [ ] **Step 4: 安装 uv**

Run:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
uv --version
```
Expected: 输出 uv 版本号。

- [ ] **Step 5: 从源码编译并安装 nautilus_trader（含全部 extras）**

Run:
```bash
cd /home/ypw/workspace/nautilus_trader && uv sync --all-extras
```
Expected: uv 创建 `.venv`（Python 3.12），编译 Rust crates 与 Cython 扩展，最终安装 nautilus_trader。耗时较长，结尾无报错。

- [ ] **Step 6: 验证 nautilus_trader 可导入**

Run:
```bash
/home/ypw/workspace/nautilus_trader/.venv/bin/python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```
Expected: 打印版本号（如 `1.2xx.x`），无 traceback。

- [ ] **Step 7: 把后端运行/测试依赖装进同一个 venv**

Run:
```bash
cd /home/ypw/workspace/nautilus_trader && \
uv pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" "pydantic>=2" "pydantic-settings>=2" "redis>=5" "httpx>=0.27" "pytest>=8" "pytest-asyncio>=0.23"
```
Expected: 安装成功。验证：
```bash
/home/ypw/workspace/nautilus_trader/.venv/bin/python -c "import fastapi, uvicorn, pytest, httpx; print('deps ok')"
```
Expected: 打印 `deps ok`。

- [ ] **Step 8: 记录 venv python 路径，方便后续脚本引用**

Run:
```bash
cd /home/ypw/workspace && mkdir -p quantdeck && \
echo 'NTPY=/home/ypw/workspace/nautilus_trader/.venv/bin/python' > quantdeck/.env.local && \
cat quantdeck/.env.local
```
Expected: 文件内容为 `NTPY=/home/ypw/workspace/nautilus_trader/.venv/bin/python`。

- [ ] **Step 9: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/.env.local && \
git commit -m "chore: 搭建 nautilus_trader 源码编译环境，记录 venv 路径"
```

---

### Task 1: 后端项目骨架与配置

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/__init__.py`
- Create: `quantdeck/backend/quantdeck_backend/config.py`
- Create: `quantdeck/backend/tests/__init__.py`
- Create: `quantdeck/backend/tests/test_config.py`
- Create: `quantdeck/backend/pytest.ini`

- [ ] **Step 1: 写失败测试 —— 配置加载**

`quantdeck/backend/tests/test_config.py`:
```python
from quantdeck_backend.config import Settings


def test_defaults():
    s = Settings()
    assert s.redis_url == "redis://localhost:6379"
    assert s.runs_dir.endswith("runs")
    assert isinstance(s.cors_origins, list)


def test_env_override(monkeypatch):
    monkeypatch.setenv("QD_REDIS_URL", "redis://example:6380")
    s = Settings()
    assert s.redis_url == "redis://example:6380"
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_config.py -v
```
Expected: FAIL，`ModuleNotFoundError: No module named 'quantdeck_backend'`。

- [ ] **Step 3: 创建包与配置实现**

`quantdeck/backend/quantdeck_backend/__init__.py`:
```python
__version__ = "0.1.0"
```

`quantdeck/backend/quantdeck_backend/config.py`:
```python
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


class Settings(BaseSettings):
    """应用配置。环境变量前缀 QD_，例如 QD_REDIS_URL。"""

    model_config = SettingsConfigDict(env_prefix="QD_", extra="ignore")

    redis_url: str = "redis://localhost:6379"
    runs_dir: str = os.path.join(_REPO_ROOT, "quantdeck", "runs")
    cors_origins: list[str] = ["http://localhost:5173"]


def get_settings() -> Settings:
    return Settings()
```

`quantdeck/backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_config.py -v
```
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): 项目骨架与应用配置"
```

---

### Task 2: NautilusBridge 环境探针（验证可导入）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/bridge/__init__.py`
- Create: `quantdeck/backend/quantdeck_backend/bridge/nautilus_env.py`
- Create: `quantdeck/backend/tests/test_nautilus_env.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_nautilus_env.py`:
```python
from quantdeck_backend.bridge.nautilus_env import probe_nautilus


def test_probe_reports_available_and_version():
    info = probe_nautilus()
    assert info.available is True
    assert info.version  # 非空字符串
    assert info.error is None
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_nautilus_env.py -v
```
Expected: FAIL，`ModuleNotFoundError: No module named 'quantdeck_backend.bridge'`。

- [ ] **Step 3: 实现环境探针**

`quantdeck/backend/quantdeck_backend/bridge/__init__.py`:
```python
```

`quantdeck/backend/quantdeck_backend/bridge/nautilus_env.py`:
```python
from dataclasses import dataclass


@dataclass
class NautilusInfo:
    available: bool
    version: str | None
    error: str | None


def probe_nautilus() -> NautilusInfo:
    """探测 nautilus_trader 是否可导入，返回版本或错误信息。"""
    try:
        import nautilus_trader

        return NautilusInfo(
            available=True,
            version=getattr(nautilus_trader, "__version__", "unknown"),
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — 探针需吞掉所有导入错误
        return NautilusInfo(available=False, version=None, error=str(exc))
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_nautilus_env.py -v
```
Expected: 1 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): NautilusBridge 环境探针"
```

---

### Task 3: 结构化错误模型与异常处理器

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/models/__init__.py`
- Create: `quantdeck/backend/quantdeck_backend/models/common.py`
- Create: `quantdeck/backend/tests/test_errors.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_errors.py`:
```python
from quantdeck_backend.models.common import ApiError


def test_api_error_shape():
    err = ApiError(code="not_found", message="缺失")
    dumped = err.model_dump()
    assert dumped == {"code": "not_found", "message": "缺失", "detail": None}
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_errors.py -v
```
Expected: FAIL，`ModuleNotFoundError: No module named 'quantdeck_backend.models'`。

- [ ] **Step 3: 实现错误模型**

`quantdeck/backend/quantdeck_backend/models/__init__.py`:
```python
```

`quantdeck/backend/quantdeck_backend/models/common.py`:
```python
from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    """统一的结构化错误返回体。"""

    code: str
    message: str
    detail: Any | None = None
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_errors.py -v
```
Expected: 1 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): 统一结构化错误模型"
```

---

### Task 4: 健康检查端点与 FastAPI 应用工厂

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/api/__init__.py`
- Create: `quantdeck/backend/quantdeck_backend/api/health.py`
- Create: `quantdeck/backend/quantdeck_backend/main.py`
- Create: `quantdeck/backend/tests/test_health.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_health.py`:
```python
from fastapi.testclient import TestClient

from quantdeck_backend.main import create_app


def test_health_ok():
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["nautilus"]["available"] is True
    assert body["nautilus"]["version"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_health.py -v
```
Expected: FAIL，`ModuleNotFoundError: No module named 'quantdeck_backend.main'`。

- [ ] **Step 3: 实现 health 路由与应用工厂**

`quantdeck/backend/quantdeck_backend/api/__init__.py`:
```python
```

`quantdeck/backend/quantdeck_backend/api/health.py`:
```python
from fastapi import APIRouter

from quantdeck_backend.bridge.nautilus_env import probe_nautilus

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    info = probe_nautilus()
    return {
        "status": "ok",
        "nautilus": {
            "available": info.available,
            "version": info.version,
            "error": info.error,
        },
    }
```

`quantdeck/backend/quantdeck_backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quantdeck_backend.api import health
from quantdeck_backend.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="QuantDeck API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_health.py -v
```
Expected: 1 passed。

- [ ] **Step 5: 手动起服务验证**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m uvicorn quantdeck_backend.main:app --port 8000 &
sleep 3 && curl -s http://localhost:8000/api/health && kill %1
```
Expected: 返回 `{"status":"ok","nautilus":{"available":true,...}}`。

- [ ] **Step 6: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): 健康检查端点与 FastAPI 应用工厂"
```

---

### Task 5: WebSocket hub（连接管理 + 广播 + echo）

**Files:**
- Create: `quantdeck/backend/quantdeck_backend/api/ws.py`
- Modify: `quantdeck/backend/quantdeck_backend/main.py`（注册 ws 路由）
- Create: `quantdeck/backend/tests/test_ws.py`

- [ ] **Step 1: 写失败测试**

`quantdeck/backend/tests/test_ws.py`:
```python
from fastapi.testclient import TestClient

from quantdeck_backend.main import create_app


def test_ws_echo_and_welcome():
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "welcome"
        ws.send_json({"type": "ping"})
        echo = ws.receive_json()
        assert echo == {"type": "echo", "payload": {"type": "ping"}}
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_ws.py -v
```
Expected: FAIL（`/ws` 不存在，连接被拒）。

- [ ] **Step 3: 实现 WebSocket hub**

`quantdeck/backend/quantdeck_backend/api/ws.py`:
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class WsHub:
    """管理活动 WebSocket 连接，支持广播。"""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, message: dict) -> None:
        for ws in list(self._clients):
            await ws.send_json(message)


hub = WsHub()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    await ws.send_json({"type": "welcome"})
    try:
        while True:
            data = await ws.receive_json()
            await ws.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        hub.disconnect(ws)
```

`quantdeck/backend/quantdeck_backend/main.py` —— 修改 `create_app`，在 `app.include_router(health.router)` 之后加入：
```python
    from quantdeck_backend.api import ws

    app.include_router(ws.router)
```
（在 `main.py` 顶部已有的 `from quantdeck_backend.api import health` 下方，可改为 `from quantdeck_backend.api import health, ws`，并把上面那行 import 删除——二选一，保持单一 import 风格。）

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest tests/test_ws.py -v
```
Expected: 1 passed。

- [ ] **Step 5: 跑全部后端测试**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest -v
```
Expected: 全部 passed。

- [ ] **Step 6: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend && \
git commit -m "feat(backend): WebSocket hub（欢迎/广播/echo）"
```

---

### Task 6: 后端启动脚本

**Files:**
- Create: `quantdeck/backend/run.sh`

- [ ] **Step 1: 写启动脚本**

`quantdeck/backend/run.sh`:
```bash
#!/usr/bin/env bash
# 用 nautilus 的 venv 启动后端开发服务
set -euo pipefail
NTPY=/home/ypw/workspace/nautilus_trader/.venv/bin/python
cd "$(dirname "$0")"
PYTHONPATH=. exec "$NTPY" -m uvicorn quantdeck_backend.main:app --reload --port 8000
```

- [ ] **Step 2: 赋可执行权限并验证启动**

Run:
```bash
chmod +x /home/ypw/workspace/quantdeck/backend/run.sh && \
/home/ypw/workspace/quantdeck/backend/run.sh & sleep 4 && \
curl -s http://localhost:8000/api/health && kill %1
```
Expected: 返回 health JSON，`status: ok`。

- [ ] **Step 3: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/backend/run.sh && \
git commit -m "chore(backend): 开发启动脚本"
```

---

### Task 7: 前端脚手架（Vite + React + TS + Vitest）

**Files:**
- Create: `quantdeck/frontend/package.json`
- Create: `quantdeck/frontend/tsconfig.json`
- Create: `quantdeck/frontend/vite.config.ts`
- Create: `quantdeck/frontend/index.html`
- Create: `quantdeck/frontend/src/main.tsx`
- Create: `quantdeck/frontend/vitest.setup.ts`

- [ ] **Step 1: 创建 package.json**

`quantdeck/frontend/package.json`:
```json
{
  "name": "quantdeck-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^24.1.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.0",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 2: 创建配置文件**

`quantdeck/frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "vitest.setup.ts"]
}
```

`quantdeck/frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
```

`quantdeck/frontend/vitest.setup.ts`:
```typescript
import "@testing-library/jest-dom";
```

`quantdeck/frontend/index.html`:
```html
<!doctype html>
<html lang="zh">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>QuantDeck</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`quantdeck/frontend/src/main.tsx`:
```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 3: 安装依赖**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npm install
```
Expected: 安装成功，生成 `node_modules` 与 `package-lock.json`。

- [ ] **Step 4: 加前端 .gitignore**

`quantdeck/frontend/.gitignore`:
```
node_modules/
dist/
```

- [ ] **Step 5: Commit（App.tsx 在下个任务创建，此处先不构建）**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/package.json quantdeck/frontend/package-lock.json quantdeck/frontend/tsconfig.json quantdeck/frontend/vite.config.ts quantdeck/frontend/vitest.setup.ts quantdeck/frontend/index.html quantdeck/frontend/src/main.tsx quantdeck/frontend/.gitignore && \
git commit -m "chore(frontend): Vite+React+TS 脚手架与配置"
```

---

### Task 8: REST 客户端 + 健康状态 Hook（测试驱动）

**Files:**
- Create: `quantdeck/frontend/src/api/client.ts`
- Create: `quantdeck/frontend/src/api/useHealth.ts`
- Create: `quantdeck/frontend/src/api/useHealth.test.tsx`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/api/useHealth.test.tsx`:
```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { useHealth } from "./useHealth";

afterEach(() => vi.restoreAllMocks());

test("useHealth fetches and exposes status", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        nautilus: { available: true, version: "1.0.0", error: null },
      }),
    }),
  );

  const { result } = renderHook(() => useHealth());
  await waitFor(() => expect(result.current.health?.status).toBe("ok"));
  expect(result.current.health?.nautilus.version).toBe("1.0.0");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/api/useHealth.test.tsx
```
Expected: FAIL，找不到 `./useHealth`。

- [ ] **Step 3: 实现 REST 客户端与 hook**

`quantdeck/frontend/src/api/client.ts`:
```typescript
export interface ApiError {
  code: string;
  message: string;
  detail?: unknown;
}

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) {
    let err: ApiError = { code: "http_error", message: resp.statusText };
    try {
      err = await resp.json();
    } catch {
      /* 保留默认错误 */
    }
    throw err;
  }
  return (await resp.json()) as T;
}
```

`quantdeck/frontend/src/api/useHealth.ts`:
```typescript
import { useEffect, useState } from "react";
import { apiGet } from "./client";

export interface Health {
  status: string;
  nautilus: { available: boolean; version: string | null; error: string | null };
}

export function useHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Health>("/api/health")
      .then(setHealth)
      .catch((e) => setError(String(e?.message ?? e)));
  }, []);

  return { health, error };
}
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/api/useHealth.test.tsx
```
Expected: 1 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/api && \
git commit -m "feat(frontend): REST 客户端与健康状态 hook"
```

---

### Task 9: WebSocket 客户端（自动重连，测试驱动）

**Files:**
- Create: `quantdeck/frontend/src/api/ws.ts`
- Create: `quantdeck/frontend/src/api/ws.test.ts`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/api/ws.test.ts`:
```typescript
import { afterEach, expect, test, vi } from "vitest";
import { createWsClient } from "./ws";

class FakeWS {
  static instances: FakeWS[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  readyState = 0;
  constructor(public url: string) {
    FakeWS.instances.push(this);
  }
  send() {}
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}

afterEach(() => {
  FakeWS.instances = [];
  vi.restoreAllMocks();
});

test("delivers parsed messages to handler", () => {
  vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  const received: unknown[] = [];
  createWsClient("/ws", (msg) => received.push(msg));
  const ws = FakeWS.instances[0];
  ws.onopen?.();
  ws.onmessage?.({ data: JSON.stringify({ type: "welcome" }) });
  expect(received).toEqual([{ type: "welcome" }]);
});

test("reconnects after close", () => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  createWsClient("/ws", () => {});
  expect(FakeWS.instances.length).toBe(1);
  FakeWS.instances[0].close();
  vi.advanceTimersByTime(2000);
  expect(FakeWS.instances.length).toBe(2);
  vi.useRealTimers();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/api/ws.test.ts
```
Expected: FAIL，找不到 `./ws`。

- [ ] **Step 3: 实现自动重连 WS 客户端**

`quantdeck/frontend/src/api/ws.ts`:
```typescript
export type WsHandler = (message: unknown) => void;

export interface WsClient {
  close: () => void;
}

export function createWsClient(
  path: string,
  onMessage: WsHandler,
  reconnectMs = 2000,
): WsClient {
  let socket: WebSocket | null = null;
  let closedByUser = false;

  const url =
    path.startsWith("ws://") || path.startsWith("wss://")
      ? path
      : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${path}`;

  const connect = () => {
    socket = new WebSocket(url);
    socket.onmessage = (e) => {
      try {
        onMessage(JSON.parse(e.data));
      } catch {
        /* 忽略非 JSON 帧 */
      }
    };
    socket.onclose = () => {
      if (!closedByUser) setTimeout(connect, reconnectMs);
    };
  };

  connect();

  return {
    close: () => {
      closedByUser = true;
      socket?.close();
    },
  };
}
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/api/ws.test.ts
```
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src/api/ws.ts quantdeck/frontend/src/api/ws.test.ts && \
git commit -m "feat(frontend): 自动重连 WebSocket 客户端"
```

---

### Task 10: 布局 + 五页路由 + App 壳（测试驱动）

**Files:**
- Create: `quantdeck/frontend/src/components/Layout.tsx`
- Create: `quantdeck/frontend/src/pages/index.tsx`
- Create: `quantdeck/frontend/src/App.tsx`
- Create: `quantdeck/frontend/src/App.test.tsx`

- [ ] **Step 1: 写失败测试**

`quantdeck/frontend/src/App.test.tsx`:
```typescript
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { App } from "./App";

test("renders nav with five module links and health badge area", () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        nautilus: { available: true, version: "1.0.0", error: null },
      }),
    }),
  );
  render(<App />);
  expect(screen.getByRole("link", { name: "连接配置" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "回测分析" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "数据研究" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "实盘监控" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "策略控制" })).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/App.test.tsx
```
Expected: FAIL，找不到 `./App`。

- [ ] **Step 3: 实现页面占位、布局与 App**

`quantdeck/frontend/src/pages/index.tsx`:
```typescript
function Placeholder({ title }: { title: string }) {
  return (
    <section>
      <h1>{title}</h1>
      <p>该模块将在后续计划中实现。</p>
    </section>
  );
}

export const ConfigPage = () => <Placeholder title="连接与配置管理" />;
export const BacktestPage = () => <Placeholder title="回测分析" />;
export const ResearchPage = () => <Placeholder title="数据研究" />;
export const LivePage = () => <Placeholder title="实盘监控" />;
export const ControlPage = () => <Placeholder title="策略控制" />;
```

`quantdeck/frontend/src/components/Layout.tsx`:
```typescript
import { Link, Outlet } from "react-router-dom";
import { useHealth } from "../api/useHealth";

const NAV = [
  { to: "/config", label: "连接配置" },
  { to: "/backtest", label: "回测分析" },
  { to: "/research", label: "数据研究" },
  { to: "/live", label: "实盘监控" },
  { to: "/control", label: "策略控制" },
];

export function Layout() {
  const { health } = useHealth();
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav style={{ width: 180, padding: 16, borderRight: "1px solid #ddd" }}>
        <h2>QuantDeck</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {NAV.map((n) => (
            <li key={n.to} style={{ margin: "8px 0" }}>
              <Link to={n.to}>{n.label}</Link>
            </li>
          ))}
        </ul>
        <div style={{ marginTop: 24, fontSize: 12 }}>
          后端：{health ? `已连接 (nautilus ${health.nautilus.version})` : "连接中…"}
        </div>
      </nav>
      <main style={{ flex: 1, padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
```

`quantdeck/frontend/src/App.tsx`:
```typescript
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import {
  BacktestPage,
  ConfigPage,
  ControlPage,
  LivePage,
  ResearchPage,
} from "./pages";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/config" replace />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/live" element={<LivePage />} />
          <Route path="/control" element={<ControlPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npx vitest run src/App.test.tsx
```
Expected: 1 passed。

- [ ] **Step 5: 类型检查 + 构建验证**

Run:
```bash
cd /home/ypw/workspace/quantdeck/frontend && npm run build
```
Expected: tsc 无类型错误，vite 构建出 `dist/`。

- [ ] **Step 6: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/frontend/src && \
git commit -m "feat(frontend): 布局、五页路由与应用壳"
```

---

### Task 11: 端到端联通冒烟 + 项目 README

**Files:**
- Create: `quantdeck/README.md`

- [ ] **Step 1: 写 README**

`quantdeck/README.md`:
````markdown
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
0. 连接与配置管理　1. 回测分析　2. 数据研究　3. 实盘监控　4. 策略控制

详见 `../nautilus_trader/docs/superpowers/specs/2026-05-31-crypto-quant-web-console-design.md`。
````

- [ ] **Step 2: 端到端冒烟：同时起前后端，验证前端能展示后端健康状态**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && ./run.sh & sleep 4
cd /home/ypw/workspace/quantdeck/frontend && npm run dev & sleep 5
curl -s http://localhost:5173/api/health
```
Expected: 经 Vite 代理返回后端 `{"status":"ok",...}`，证明前端→代理→后端链路通。验证后：
```bash
kill %1 %2 2>/dev/null
```

- [ ] **Step 3: 跑全部测试做最终回归**

Run:
```bash
cd /home/ypw/workspace/quantdeck/backend && PYTHONPATH=. /home/ypw/workspace/nautilus_trader/.venv/bin/python -m pytest -v
cd /home/ypw/workspace/quantdeck/frontend && npm test
```
Expected: 后端全部 passed；前端全部 passed。

- [ ] **Step 4: Commit**

```bash
cd /home/ypw/workspace && git add quantdeck/README.md && \
git commit -m "docs(quantdeck): 项目 README 与启动说明"
```

---

## 完成标准（地基验收）

- [ ] `nautilus_trader` 可在后端 venv 中导入。
- [ ] 后端 `/api/health` 返回 `status: ok` 且包含 nautilus 版本。
- [ ] 后端 `/ws` 可连接、收到 welcome、能 echo。
- [ ] 后端全部 pytest 通过。
- [ ] 前端五页路由可访问，导航栏显示后端连接状态。
- [ ] 前端全部 vitest 通过，`npm run build` 无类型错误。
- [ ] 前端经 Vite 代理可访问后端 `/api/health`。

地基完成后，下一个计划：**模块 0 连接与配置管理**。
