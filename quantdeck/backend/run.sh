#!/usr/bin/env bash
# 用 nautilus 的 venv 启动后端开发服务
set -euo pipefail
NTPY=/home/ypw/workspace/nautilus_trader/.venv/bin/python
cd "$(dirname "$0")"
PYTHONPATH=. exec "$NTPY" -m uvicorn quantdeck_backend.main:app --reload --port 8000
