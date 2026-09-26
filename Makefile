.PHONY: up dev check install backend frontend build

# 默认目标：从零到能用（装依赖 + 构建 + 启动 + 自检）
up:
	@scripts/dev.sh

# 前端热更新模式（跳过生产构建）
dev:
	@scripts/dev.sh --dev

# 能力验证报名与评定接口自检
check:
	@scripts/dev.sh check

# 只装依赖（锁版本）
install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
	cd frontend && npm ci

# 单独启动
backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm ci && npm run build
