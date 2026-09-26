"""能力验证业务规则：状态流转、字段校验与筛选口径都收在这里。

状态机：
    待参加 --报名参加--> 待评定 --接收评定(合格)--> 已通过
                                      └─(不合格)─> 未通过
其中「上报结果」是待评定阶段的信息补录动作，不改变状态。
任何跨状态跳转（例如待参加直接评定）都会被拦下。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "ability"
REQUIRED_FIELDS = ["验证编号", "组织方", "检测项目"]
STATUS_ORDER = ["待参加", "待评定", "已通过", "未通过"]
# 动作 -> 当前必须处于的状态；None 表示不单独变更状态，只做信息补录
ACTION_FROM = {"报名参加": "待参加", "上报结果": "待评定", "接收评定": "待评定"}
# 接收评定按评定结论分流到两种终态
PASS_VERDICT = "合格"
FAIL_VERDICT = "不合格"
NEGATIVE_ACTIONS = []


class AbilityService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("验证编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        # 报名前允许先登记参加人员与样品编号
        entry["参加人员"] = str(values.get("参加人员") or "").strip()
        entry["样品编号"] = str(values.get("样品编号") or "").strip()
        entry["上报日期"] = ""
        entry["结果评定"] = ""
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(
        self, entry_id: int, action: str, values: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"能力验证 {entry_id} 不存在或已归档"
        if action not in ACTION_FROM:
            return None, f"动作「{action}」不属于能力验证可执行范围"
        expected = ACTION_FROM[action]
        current = str(entry.get("status") or "")
        if current != expected:
            return None, f"当前状态为「{current}」，不能执行「{action}」，需先处于「{expected}」"

        values = values or {}
        if action == "报名参加":
            participants = str(values.get("参加人员") or entry.get("参加人员") or "").strip()
            if not participants:
                return None, "报名参加需填写参加人员"
            sample_no = str(values.get("样品编号") or entry.get("样品编号") or "").strip()
            entry["参加人员"] = participants
            if sample_no:
                entry["样品编号"] = sample_no
            entry["status"] = "待评定"
            return entry, "能力验证已报名参加，等待上报结果"

        if action == "上报结果":
            report_date = str(values.get("上报日期") or "").strip()
            if not report_date:
                return None, "上报结果需填写上报日期"
            sample_no = str(values.get("样品编号") or entry.get("样品编号") or "").strip()
            entry["上报日期"] = report_date
            if sample_no:
                entry["样品编号"] = sample_no
            # 仍停留在待评定，等待组织方反馈结论
            return entry, "检测结果已上报，等待组织方评定"

        verdict = str(values.get("结果评定") or "").strip()
        if verdict not in (PASS_VERDICT, FAIL_VERDICT):
            return None, "接收评定需给出评定结论：合格 或 不合格"
        entry["结果评定"] = verdict
        target = "已通过" if verdict == PASS_VERDICT else "未通过"
        entry["status"] = target
        entry["pending"] = False
        entry["abnormal"] = verdict == FAIL_VERDICT
        return entry, f"能力验证评定完成，结论：{verdict}"
