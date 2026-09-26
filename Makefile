.PHONY: install dev backend frontend check

# 首次准备：后端建 venv 装锁定依赖，前端按 package-lock.json 原样安装
install:
	cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
	cd frontend && npm ci

# 一条命令：预检 → 装依赖 → 前端构建 → 同时拉起前后端
dev:
	./scripts/dev.sh

backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev

# 能力验证报名与评定接口自检（服务在跑时执行）
check:
	./scripts/check-ability.sh
