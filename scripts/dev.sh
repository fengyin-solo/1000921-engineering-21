#!/usr/bin/env bash
# 本地开发一键启动：预检环境 → 安装/修复依赖 → 前端构建 → 同时拉起前后端。
#
# 失败信息分两类，方便直接定位：
#   [启动失败] 依赖缺失：...      —— python3/node/npm/venv/依赖包的问题
#   [启动失败] 环境变量未配置：... —— .env 缺失或取值非法
#
# 用法：make dev 或 ./scripts/dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."

info() { printf '\033[36m[启动]\033[0m %s\n' "$*"; }
die()  { printf '\033[31m[启动失败]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------- 1. 预检：工具链（依赖缺失类） ----------
command -v python3 >/dev/null 2>&1 \
  || die "依赖缺失：未找到 python3，请安装 Python 3.11+"
command -v node >/dev/null 2>&1 \
  || die "依赖缺失：未找到 node，请安装 Node.js 18+"
command -v npm >/dev/null 2>&1 \
  || die "依赖缺失：未找到 npm，请安装 Node.js 18+（自带 npm）"
node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 18 ? 0 : 1)" \
  || die "依赖缺失：Node.js 版本过低（$(node --version)），vite 5 需要 18+"

# ---------- 2. 预检：环境变量（环境变量类） ----------
[ -f .env ] \
  || die "环境变量未配置：缺少根目录 .env，请执行 cp .env.example .env 后重试"
set -a
# shellcheck disable=SC1091
. ./.env
set +a
[ -n "${APP_ENV:-}" ] \
  || die "环境变量未配置：.env 中 APP_ENV 为空，请对照 .env.example 补齐"

BACKEND_PORT="${APP_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# ---------- 3. 后端依赖（venv 损坏或缺包时自动修复） ----------
info "检查后端依赖"
# venv 健康的标准：python 可执行且自带 pip（跨机器拷贝或 ensurepip 失败留下的半成品都算损坏）
if [ ! -x backend/.venv/bin/python ] || ! backend/.venv/bin/python -m pip --version >/dev/null 2>&1; then
  [ -d backend/.venv ] && info "backend/.venv 已损坏（跨机器拷贝或创建不完整），删除后重建"
  rm -rf backend/.venv
  (cd backend && python3 -m venv .venv) \
    || die "依赖缺失：python3 -m venv 创建失败，Debian/Ubuntu 请先执行 apt install python3-venv"
fi
if ! (cd backend && .venv/bin/python -c "import fastapi, uvicorn") >/dev/null 2>&1; then
  info "安装后端依赖（requirements.txt 已精确锁定版本）"
  (cd backend && .venv/bin/python -m pip install -q -r requirements.txt) \
    || die "依赖缺失：pip install -r requirements.txt 失败，请检查网络后重试"
fi
# 环境变量合法性由后端 config 统一校验，非法值会带「环境变量」字样抛出
(cd backend && .venv/bin/python -c "from app.config import settings") \
  || die "环境变量未配置或取值非法：见上方错误详情（对照 .env.example 检查 .env）"

# ---------- 4. 前端依赖（node_modules 缺失或损坏时自动重装） ----------
info "检查前端依赖"
frontend_ok() {
  [ -d frontend/node_modules ] \
    && (cd frontend && node -e "require('rollup')") >/dev/null 2>&1
}
if ! frontend_ok; then
  info "安装前端依赖（package-lock.json 已锁定版本）"
  if [ -f frontend/package-lock.json ]; then
    (cd frontend && npm ci) || die "依赖缺失：npm ci 失败，请检查网络后重试"
  else
    (cd frontend && npm install) || die "依赖缺失：npm install 失败，请检查网络后重试"
  fi
  frontend_ok || die "依赖缺失：前端依赖安装后仍不可用，请删除 frontend/node_modules 后重试"
fi

# ---------- 5. 前端构建（类型检查 + 产物，提前暴露构建错误） ----------
info "构建前端（vue-tsc 类型检查 + vite build）"
(cd frontend && npm run build) || die "前端构建失败：见上方输出"

# ---------- 6. 同时拉起前后端 ----------
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait_http() { # wait_http <url> <pid> <名称>
  for _ in $(seq 1 40); do
    kill -0 "$2" 2>/dev/null || return 1
    if python3 -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('$1',timeout=1).status==200 else 1)" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

info "启动后端（http://127.0.0.1:${BACKEND_PORT}，环境：${APP_ENV}）"
(cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT}") &
BACKEND_PID=$!
wait_http "http://127.0.0.1:${BACKEND_PORT}/api/health" "$BACKEND_PID" \
  || die "后端启动失败：常见原因是端口 ${BACKEND_PORT} 被占用（可改 .env 的 APP_PORT），详见上方日志"

info "启动前端（http://127.0.0.1:${FRONTEND_PORT}）"
(cd frontend && VITE_PROXY_TARGET="http://127.0.0.1:${BACKEND_PORT}" FRONTEND_PORT="${FRONTEND_PORT}" \
  node_modules/.bin/vite) &
FRONTEND_PID=$!
wait_http "http://127.0.0.1:${FRONTEND_PORT}/" "$FRONTEND_PID" \
  || die "前端启动失败：常见原因是端口 ${FRONTEND_PORT} 被占用（可改 .env 的 FRONTEND_PORT），详见上方日志"

printf '\n\033[32m全部就绪\033[0m\n'
printf '  前端页面   http://127.0.0.1:%s （手动打开，不会自动弹窗）\n' "${FRONTEND_PORT}"
printf '  后端接口   http://127.0.0.1:%s/api/health\n' "${BACKEND_PORT}"
printf '  接口自检   另开终端执行 make check（验证能力验证报名与评定接口）\n'
printf '  停止服务   Ctrl+C\n\n'

# 任一进程退出即结束：另一个由 trap 收掉，退出原因看上方日志
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
die "有服务进程退出，详见上方日志"
