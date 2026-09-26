"""能力验证模块接口自检：跑一遍确认模块真的可用。

检查项：
  1. 后端健康检查（服务在监听、示例数据已灌入）；
  2. 能力验证示例数据覆盖 待参加 → 待评定 → 已通过 → 未通过 四种状态；
  3. 报名链路：登记 → 报名参加 → 上报结果（状态到 已通过）；
  4. 评定链路：登记 → 报名参加 → 接收评定（状态到 未通过）；
  5. 未通过记录可按状态检索出来；
  6. 若前端 dev server 在运行，顺带验证 /api 代理已打通（不可达只提示，不算失败）。

自检会在内存库里新增两条 CHK- 前缀的自检记录，重启后端即还原，不影响示例数据。

用法：
  python3 scripts/check-ability.py [--base http://127.0.0.1:8000] [--frontend http://127.0.0.1:5173]
环境变量：BACKEND_BASE、FRONTEND_BASE 可替代对应参数。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

FAILURES = 0


def step(ok: bool, label: str, detail: str = "") -> None:
    global FAILURES
    print(f"  {'✓' if ok else '✗'} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES += 1


def note(text: str) -> None:
    print(f"  - {text}")


def http(method: str, url: str, payload: dict | None = None, timeout: float = 5) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def create_entry(base: str, code: str) -> dict | None:
    payload = {
        "values": {
            "验证编号": code,
            "组织方": "接口自检脚本",
            "检测项目": "自检项目（报名与评定链路）",
            "参加人员": "自检脚本",
        }
    }
    _, body = http("POST", f"{base}/api/ability", payload)
    if body.get("ok") and body.get("entry"):
        return body["entry"]
    step(False, f"登记自检记录 {code}", str(body.get("message", "")))
    return None


def run_action(base: str, entry_id: int, action: str) -> tuple[bool, str, str]:
    _, body = http("POST", f"{base}/api/ability/{entry_id}/actions", {"values": {"action": action}})
    entry = body.get("entry") or {}
    return bool(body.get("ok")), str(entry.get("status", "")), str(body.get("message", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="能力验证模块接口自检")
    parser.add_argument("--base", default=None, help="后端地址，默认读 BACKEND_BASE 或 http://127.0.0.1:8000")
    parser.add_argument("--frontend", default=None, help="前端地址，默认读 FRONTEND_BASE 或 http://127.0.0.1:5173")
    args = parser.parse_args()
    base = (args.base or os.environ.get("BACKEND_BASE") or "http://127.0.0.1:8000").rstrip("/")
    frontend = (args.frontend or os.environ.get("FRONTEND_BASE") or "http://127.0.0.1:5173").rstrip("/")

    print(f"能力验证接口自检（后端 {base}）")

    # 1. 健康检查：连不上就不必往下走了
    try:
        status, body = http("GET", f"{base}/api/health")
        step(
            status == 200 and body.get("ok") is True,
            "后端健康检查 GET /api/health",
            f"env={body.get('env')}，能力验证 {body.get('ability_rows')} 条",
        )
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        step(False, "后端健康检查 GET /api/health", f"连接失败：{exc}")
        note("后端没在运行？先执行 make dev（或 cd backend && ./run.sh）再自检")
        return 1

    # 2. 示例数据四态齐全
    try:
        _, body = http("GET", f"{base}/api/ability?size=200")
        items = body.get("items", [])
        statuses = {str(row.get("status", "")) for row in items}
        missing = [s for s in ("待参加", "待评定", "已通过", "未通过") if s not in statuses]
        step(
            not missing,
            "示例数据覆盖 待参加/待评定/已通过/未通过",
            ("缺少状态：" + "、".join(missing)) if missing else f"当前共 {len(items)} 条",
        )
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        step(False, "能力验证列表 GET /api/ability", f"请求失败：{exc}")

    # 3. 报名链路：登记 → 报名参加 → 上报结果（已通过）
    stamp = int(time.time())
    try:
        entry = create_entry(base, f"CHK-{stamp}-A")
        if entry:
            entry_id = int(entry["id"])
            ok, status_after, message = run_action(base, entry_id, "报名参加")
            step(ok and status_after == "待评定", "报名参加接口", f"{message}（状态：{status_after}）")
            ok, status_after, message = run_action(base, entry_id, "上报结果")
            step(ok and status_after == "已通过", "上报结果接口", f"{message}（状态：{status_after}）")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        step(False, "报名链路", f"请求失败：{exc}")

    # 4. 评定链路：登记 → 报名参加 → 接收评定（未通过）
    try:
        entry = create_entry(base, f"CHK-{stamp}-B")
        if entry:
            entry_id = int(entry["id"])
            ok, status_after, message = run_action(base, entry_id, "报名参加")
            step(ok and status_after == "待评定", "报名参加接口（评定链路）", f"{message}（状态：{status_after}）")
            ok, status_after, message = run_action(base, entry_id, "接收评定")
            step(ok and status_after == "未通过", "接收评定接口", f"{message}（状态：{status_after}）")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        step(False, "评定链路", f"请求失败：{exc}")

    # 5. 未通过记录可检索
    try:
        _, body = http("GET", f"{base}/api/ability?status=%E6%9C%AA%E9%80%9A%E8%BF%87")
        total = int(body.get("total", 0))
        step(total >= 1, "按状态检索未通过记录", f"命中 {total} 条")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        step(False, "按状态检索未通过记录", f"请求失败：{exc}")

    # 6. 前端代理（可选，不可达只提示）
    try:
        status, body = http("GET", f"{frontend}/api/ability?size=1", timeout=2)
        step(status == 200 and "items" in body, "前端代理 /api → 后端", f"{frontend} 已打通")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        note(f"前端 {frontend} 不可达，跳过代理检查（只起了后端时属正常）")

    if FAILURES:
        print(f"\n自检未通过：{FAILURES} 项失败")
        return 1
    print("\n自检通过：能力验证的报名与评定接口均可正常返回")
    return 0


if __name__ == "__main__":
    sys.exit(main())
