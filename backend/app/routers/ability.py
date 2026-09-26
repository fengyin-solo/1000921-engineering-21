"""能力验证接口：维护能力验证，覆盖报名参加、上报结果、接收评定等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.ability import AbilityService

router = APIRouter(prefix="/api/ability", tags=["能力验证"])

service = AbilityService()

LIST_FIELDS = ["验证编号", "组织方", "检测项目", "参加人员", "样品编号", "上报日期", "结果评定", "验证状态"]
STATUSES = ["待参加", "待评定", "已通过", "未通过"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按验证编号检索"),
    status: str | None = Query(default=None, description="待参加、待评定、已通过、未通过"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按验证编号与状态过滤能力验证列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条能力验证明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"能力验证 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条能力验证，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="能力验证已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条能力验证执行报名参加、上报结果、接收评定；不允许的动作会被拦下并说明原因。

    - 报名参加：values 里带「参加人员」（必填）、「样品编号」
    - 上报结果：values 里带「上报日期」（必填）、「样品编号」
    - 接收评定：values 里带「结果评定」=「合格」或「不合格」
    """
    action = str(payload.values.get("action") or "").strip()
    extra = {key: value for key, value in payload.values.items() if key != "action"}
    entry, message = service.run_action(entry_id, action, extra)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出能力验证清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "ability", "total": total, "items": items}
