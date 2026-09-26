#!/usr/bin/env bash
# 后端单独启动脚本（一键链路用 scripts/dev.sh；本脚本适合只调后端时使用）
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "[run.sh] 未找到 .venv，先创建虚拟环境"
  python3 -m venv .venv
fi

if ! .venv/bin/python -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "[run.sh] 依赖缺失或不完整，按 requirements.lock 安装"
  .venv/bin/pip install -q -r requirements.lock
fi

HOST="${APP_HOST:-127.0.0.1}"
PORT="${APP_PORT:-8000}"
exec .venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT"
