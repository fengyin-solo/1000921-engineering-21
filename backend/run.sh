#!/usr/bin/env bash
# 后端单独启动脚本：自检依赖与环境变量，失败时明确指出是哪一类问题。
# 一键同时拉起前后端请用仓库根目录的 scripts/dev.sh（make dev）。
set -euo pipefail
cd "$(dirname "$0")"

die() { printf '[启动失败] %s\n' "$*" >&2; exit 1; }
info() { printf '[后端] %s\n' "$*"; }

# ---- 环境变量：.env 缺失不致命（config.py 有默认值），但存在非法值会在导入时直接报错 ----
if [ ! -f ../.env ]; then
  info "未找到根目录 .env，使用代码内默认配置（可参考 .env.example 创建）"
fi

# ---- 依赖：python3 与 venv ----
command -v python3 >/dev/null 2>&1 \
  || die "依赖缺失：未找到 python3，请先安装 Python 3.11+"

if [ ! -x .venv/bin/python ] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  [ -d .venv ] && info "检测到损坏的 .venv（跨机器拷贝或创建不完整），删除后重建"
  rm -rf .venv
  python3 -m venv .venv \
    || die "依赖缺失：python3 -m venv 创建失败，Debian/Ubuntu 请先执行 apt install python3-venv"
fi

.venv/bin/python -c "import fastapi, uvicorn" >/dev/null 2>&1 || {
  info "安装后端依赖（requirements.txt 已精确锁定版本）"
  .venv/bin/python -m pip install -q -r requirements.txt \
    || die "依赖缺失：pip install -r requirements.txt 失败，请检查网络或 requirements.txt"
}

# ---- 环境变量：导入 config 触发校验，非法值会在这里以「环境变量」字样报错 ----
.venv/bin/python -c "from app.config import settings" \
  || die "环境变量未配置或配置非法：见上方错误详情（对照 .env.example 检查 .env）"

PORT="${APP_PORT:-8000}"
info "启动于 http://127.0.0.1:${PORT}（环境：${APP_ENV:-local}），健康检查 /api/health"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"
