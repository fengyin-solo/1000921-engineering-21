"""实验室样品检测管理平台 后端服务入口。

启动：uvicorn app.main:app --host 127.0.0.1 --port 8000
健康检查：GET /api/health
能力验证链路自检：GET /api/health/ability
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ROUTERS
from app.services.ability import STATUS_ORDER as ABILITY_STATUSES
from app.store import MODULE_ABILITY, store


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动后打印访问与自检地址，让"起没起来、去哪验证"一眼可见。"""
    base = f"http://{settings.host}:{settings.port}"
    print("=" * 64, flush=True)
    print(f"  {settings.app_name} 已启动（env={settings.env}）", flush=True)
    print(f"  服务地址   : {base}", flush=True)
    print(f"  健康检查   : {base}/api/health", flush=True)
    print(f"  能力验证自检: {base}/api/health/ability", flush=True)
    print(f"  能力验证列表: {base}/api/ability", flush=True)
    print("=" * 64, flush=True)
    yield


app = FastAPI(title="实验室样品检测管理平台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in ROUTERS:
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    """健康检查：确认服务已经监听、示例数据已经就绪。"""
    return {
        "ok": True,
        "app": settings.app_name,
        "env": settings.env,
        "modules": len(store.module_names()),
        "ability_records": len(store.rows(MODULE_ABILITY)),
    }


@app.get("/api/health/ability")
def health_ability() -> dict[str, object]:
    """能力验证链路自检：四种状态是否都有示例数据、报名与评定接口能否走通。"""
    rows = store.rows(MODULE_ABILITY)
    status_count = {status: 0 for status in ABILITY_STATUSES}
    for row in rows:
        status = str(row.get("status") or "")
        if status in status_count:
            status_count[status] += 1
    checks = {
        "列表接口": len(rows) > 0,
        "报名入口(待参加样例)": status_count["待参加"] > 0,
        "评定入口(待评定样例)": status_count["待评定"] > 0,
        "通过样例": status_count["已通过"] > 0,
        "未通过样例": status_count["未通过"] > 0,
    }
    return {
        "ok": all(checks.values()),
        "module": "ability",
        "total": len(rows),
        "status_count": status_count,
        "checks": checks,
        "endpoints": [
            "GET  /api/ability                 能力验证列表（支持 keyword、status 过滤）",
            "POST /api/ability                 登记：{\"values\": {\"验证编号\": ..., \"组织方\": ..., \"检测项目\": ...}}",
            "POST /api/ability/{id}/actions    动作：报名参加 / 上报结果 / 接收评定",
        ],
    }


@app.get("/api/overview")
def overview() -> dict[str, object]:
    """运营概览：把各业务模块的待处理量汇总成看板卡片。"""
    return store.overview()
