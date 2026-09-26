#!/usr/bin/env bash
# 能力验证模块接口自检入口（make check）。
# 确认后端在跑之后，用 Python 标准库依次验证报名与评定接口。
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null 2>&1 \
  || { echo '[检查失败] 依赖缺失：未找到 python3，请安装 Python 3.11+' >&2; exit 1; }

# 根目录有 .env 就读取端口，保证和 make dev 用同一套配置
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

export BACKEND_BASE="${BACKEND_BASE:-http://127.0.0.1:${APP_PORT:-8000}}"
export FRONTEND_BASE="${FRONTEND_BASE:-http://127.0.0.1:${FRONTEND_PORT:-5173}}"
exec python3 scripts/check-ability.py "$@"
