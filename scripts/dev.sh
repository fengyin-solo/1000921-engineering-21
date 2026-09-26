#!/usr/bin/env bash
# 本地开发一键链路：预检 -> 安装依赖（锁版本）-> 构建前端 -> 启动前后端 -> 就绪自检
#
# 用法：
#   scripts/dev.sh            构建前端并启动（后端 :8000 + 前端 :5173）
#   scripts/dev.sh --dev      前端走 vite dev（热更新），跳过生产构建
#   scripts/dev.sh check      只对已运行的服务做能力验证接口自检
#
# 设计目标：启动失败时明确指出是【缺依赖】还是【环境变量没配/配错】，
# 而不是抛一堆看不懂的堆栈。
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:${APP_PORT:-8000}}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
log()  { printf "${BLUE}==>${NC} ${BOLD}%s${NC}\n" "$*"; }
ok()   { printf "${GREEN}  ✓ %s${NC}\n" "$*"; }
warn() { printf "${YELLOW}  ! %s${NC}\n" "$*"; }
die()  { printf "\n${RED}${BOLD}[启动失败]${NC} ${RED}%s${NC}\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# check 子命令：只跑接口自检
# ---------------------------------------------------------------------------
if [ "${1:-}" = "check" ]; then
  shift || true
  CHECK_URL="${1:-$BACKEND_URL}"
  if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
    echo "尚未创建后端虚拟环境，请先运行 scripts/dev.sh 完成依赖安装。" >&2
    exit 1
  fi
  exec "$BACKEND_DIR/.venv/bin/python" "$BACKEND_DIR/scripts/check_ability.py" "$CHECK_URL"
fi

DEV_MODE=0
[ "${1:-}" = "--dev" ] && DEV_MODE=1

# ---------------------------------------------------------------------------
# 1) 依赖预检：先把"机器上缺什么基础工具"说清楚
# ---------------------------------------------------------------------------
log "第 1 步/共 4 步：检查本机依赖"
missing=()
command -v python3 >/dev/null 2>&1 || missing+=("python3 (需要 3.10 及以上)")
command -v node >/dev/null 2>&1 || missing+=("node (需要 18 及以上，建议 20)")
command -v npm >/dev/null 2>&1 || missing+=("npm")
command -v curl >/dev/null 2>&1 || missing+=("curl")
if [ "${#missing[@]}" -gt 0 ]; then
  printf "${RED}  ✗ 缺少基础依赖：${NC}\n"
  for item in "${missing[@]}"; do printf "${RED}      - %s${NC}\n" "$item"; done
  die "属于【依赖缺失】，请先安装上述工具后重新运行本脚本（不需要配置任何环境变量）。"
fi

# Python 版本 >= 3.10（代码使用 X | Y 类型语法）
py_major="$(python3 -c 'import sys; print(sys.version_info[0])')"
py_minor="$(python3 -c 'import sys; print(sys.version_info[1])')"
if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]; }; then
  die "属于【依赖缺失】：Python 版本需要 3.10+，当前为 $(python3 --version | awk '{print $2}')。"
fi
ok "python3 $(python3 --version | awk '{print $2}') / node $(node --version) / npm $(npm --version)"

# ---------------------------------------------------------------------------
# 2) 环境变量预检：从 .env（如有）加载，并校验取值
# ---------------------------------------------------------------------------
log "第 2 步/共 4 步：检查环境变量"
if [ -f "$ROOT_DIR/.env" ]; then
  set -a; # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"; set +a
  ok "已加载 .env"
else
  warn "未找到 .env，使用内置默认值（APP_PORT=8000 / 前端 5173）"
  warn "如需自定义：cp .env.example .env 后修改"
fi

# 校验 APP_PORT 是数字（与后端 config.py 的校验口径一致，提前在 shell 层给出中文提示）
if ! printf '%s' "${APP_PORT:-8000}" | grep -Eq '^[0-9]+$' \
   || [ "${APP_PORT:-8000}" -lt 1 ] || [ "${APP_PORT:-8000}" -gt 65535 ]; then
  die "属于【环境变量配置错误】：APP_PORT 必须是 1-65535 的端口号，当前为「${APP_PORT:-}」，请检查 .env。"
fi
ok "APP_PORT=${APP_PORT:-8000}，后端地址 $BACKEND_URL"

# ---------------------------------------------------------------------------
# 3) 安装依赖（一律走锁文件，避免别人拉下来解析到新版本）
# ---------------------------------------------------------------------------
log "第 3 步/共 4 步：按锁文件安装依赖"
VENV_PY="$BACKEND_DIR/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  log "创建后端虚拟环境 backend/.venv"
  if ! python3 -m venv "$BACKEND_DIR/.venv" 2>/dev/null; then
    # Debian/Ubuntu 精简镜像常缺 ensurepip（python3-venv 包）
    if python3 -m venv --without-pip "$BACKEND_DIR/.venv" 2>/dev/null; then
      warn "系统 venv 缺 ensurepip，改用 get-pip.py 引导 pip"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py 2>/dev/null \
          && "$VENV_PY" /tmp/get-pip.py --quiet \
          || die "属于【依赖缺失】：pip 引导失败（无法访问 https://bootstrap.pypa.io），请检查网络或安装 python3-venv。"
      else
        die "属于【依赖缺失】：无法创建可用的 venv（缺 ensurepip 且无 curl），请安装 python3-venv。"
      fi
    else
      die "属于【依赖缺失】：python3 -m venv 不可用，请安装 python3-venv（Debian/Ubuntu）或等效包。"
    fi
  fi
fi
# venv 可能是别的机器/路径残留（shebang 失效），自检一下
if ! "$VENV_PY" -c 'import sys' >/dev/null 2>&1; then
  warn "已有 .venv 不可用（可能是跨机器拷贝残留），重建中"
  rm -rf "$BACKEND_DIR/.venv"
  exec "$0" $([ "$DEV_MODE" -eq 1 ] && printf '%s' "--dev")
fi
log "安装后端依赖（requirements.lock）"
"$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.lock" 2>/tmp/pip_err.log \
  || { cat /tmp/pip_err.log >&2; die "属于【依赖缺失/网络问题】：后端依赖安装失败，请检查网络或 requirements.lock。"; }
# 应用自身能否导入（任何二进制 wheel 不兼容都会在这里暴露）
( cd "$BACKEND_DIR" && "$VENV_PY" -c 'import fastapi, uvicorn, pydantic' ) \
  || die "属于【依赖缺失】：后端关键包导入失败，可能是 Python 版本/平台与锁文件不匹配。"
ok "后端依赖就绪"

log "安装前端依赖（package-lock.json, npm ci）"
( cd "$FRONTEND_DIR" && npm ci --no-audit --no-fund ) 2>/tmp/npm_err.log \
  || { cat /tmp/npm_err.log >&2; die "属于【依赖缺失/网络问题】：前端 npm ci 失败，请检查网络，勿手改 package-lock.json。"; }
ok "前端依赖就绪"

if [ "$DEV_MODE" -eq 0 ]; then
  log "构建前端（vue-tsc 类型检查 + vite build）"
  ( cd "$FRONTEND_DIR" && npm run build ) 2>/tmp/build_err.log \
    || { cat /tmp/build_err.log >&2; die "前端构建失败（属于代码/类型错误，不是环境变量问题），见上方日志。"; }
  ok "前端构建产物已生成到 frontend/dist"
fi

# ---------------------------------------------------------------------------
# 4) 启动前后端，等待就绪，打印验证入口
# ---------------------------------------------------------------------------
log "第 4 步/共 4 步：启动服务"
BACKEND_PID=""; FRONTEND_PID=""
# 递归回收整棵进程树：子 shell -> npx -> node(vite) 这种孙进程也要杀掉，
# 否则脚本退出后 5173 还被占用。
kill_tree() {
  local pid=$1 child
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null || true
}
cleanup() {
  [ -n "$FRONTEND_PID" ] && kill_tree "$FRONTEND_PID"
  [ -n "$BACKEND_PID" ] && kill_tree "$BACKEND_PID"
}
trap cleanup EXIT INT TERM

# 端口占用提前报错，避免 uvicorn/vite 堆栈让人误以为是依赖问题
port_in_use() {
  python3 - "$1" <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(0.3)
sys.exit(0 if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}
port_in_use "${APP_PORT:-8000}" && die "属于【环境问题】：端口 ${APP_PORT:-8000} 已被占用，请改 .env 里的 APP_PORT（前端代理 VITE_PROXY_TARGET 也要同步）。"

(
  cd "$BACKEND_DIR"
  # 本地默认：示例数据随启动自动灌入（SEED_DEMO_DATA 可关）
  exec "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app \
    --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}"
) >/tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 前端：构建模式起 preview（代理需在 vite.config 里保留 proxy）；--dev 起 dev server
if [ "$DEV_MODE" -eq 0 ]; then
  ( cd "$FRONTEND_DIR" && VITE_PROXY_TARGET="$BACKEND_URL" \
      npx vite preview --host 127.0.0.1 --port "$FRONTEND_PORT" ) >/tmp/frontend.log 2>&1 &
else
  ( cd "$FRONTEND_DIR" && VITE_PROXY_TARGET="$BACKEND_URL" \
      npx vite --host 127.0.0.1 --port "$FRONTEND_PORT" ) >/tmp/frontend.log 2>&1 &
fi
FRONTEND_PID=$!

# 等待后端就绪（最多 ~30s）；失败时根据日志区分原因
ready=0
for i in $(seq 1 60); do
  if curl -fsS --max-time 1 "$BACKEND_URL/api/health" >/dev/null 2>&1; then ready=1; break; fi
  kill -0 "$BACKEND_PID" 2>/dev/null || {
    printf "\n${RED}后端进程已退出，日志末尾：${NC}\n" >&2
    tail -20 /tmp/backend.log >&2
    if grep -qiE 'ModuleNotFound|ImportError|No module named' /tmp/backend.log; then
      die "属于【依赖缺失】：后端启动时缺少 Python 包，请删除 backend/.venv 后重新运行本脚本。"
    fi
    if grep -qi 'ConfigError\|环境变量' /tmp/backend.log; then
      die "属于【环境变量配置错误】：详见上方日志，修改 .env 后重试。"
    fi
    die "后端启动失败，请把 /tmp/backend.log 的内容反馈给维护者。"
  }
  sleep 0.5
done
[ "$ready" -eq 1 ] || die "后端 30 秒内未就绪，见 /tmp/backend.log"
ok "后端已就绪：$BACKEND_URL"

# 前端就绪探测
front_ready=0
for i in $(seq 1 40); do
  curl -fsS --max-time 1 "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1 && { front_ready=1; break; }
  kill -0 "$FRONTEND_PID" 2>/dev/null || { tail -20 /tmp/frontend.log >&2; die "前端进程已退出，见上方日志。"; }
  sleep 0.5
done
[ "$front_ready" -eq 1 ] || warn "前端未在 20 秒内就绪，可查看 /tmp/frontend.log；后端不受影响"

# 能力验证链路自检
echo
log "能力验证模块自检"
"$0" check || true

cat <<EOF

${GREEN}${BOLD}服务已启动（Ctrl+C 同时停止前后端）${NC}
  平台首页     : http://127.0.0.1:${FRONTEND_PORT}/
  能力验证页面 : http://127.0.0.1:${FRONTEND_PORT}/ability
  后端健康检查 : ${BACKEND_URL}/api/health
  能力验证自检 : ${BACKEND_URL}/api/health/ability
  接口文档     : ${BACKEND_URL}/docs

  单独重跑自检 : scripts/dev.sh check
  日志         : /tmp/backend.log  /tmp/frontend.log
EOF

wait "$BACKEND_PID"
