"""能力验证链路自检脚本：启动后跑一遍，确认报名与评定接口都能用。

用法：
    python scripts/check_ability.py [base_url]

退出码 0 表示全部通过；非 0 表示有检查项失败（可直接接 CI）。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8000"


def fetch(method: str, url: str, payload: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except (urllib.error.URLError, ConnectionError, OSError) as exc:
        return 0, str(exc)
    try:
        return 200, json.loads(raw)
    except json.JSONDecodeError:
        return 200, raw


def main(base_url: str) -> int:
    failures: list[str] = []

    print(f"目标后端：{base_url}")
    code, body = fetch("GET", f"{base_url}/api/health")
    if code != 200 or not isinstance(body, dict) or not body.get("ok"):
        print(f"  ✗ /api/health 无响应（code={code}），后端是否已启动？")
        print(f"    详情：{body}")
        return 1
    print(f"  ✓ 健康检查正常，已加载 {body.get('modules')} 个业务模块")

    # 1) 列表接口 + 四种状态样例齐全
    code, body = fetch("GET", f"{base_url}/api/health/ability")
    if code != 200 or not isinstance(body, dict):
        print(f"  ✗ 能力验证自检端点异常：{body}")
        return 1
    print(f"  能力验证示例数据共 {body['total']} 条：")
    for status, count in body["status_count"].items():
        mark = "✓" if count else "✗"
        print(f"    {mark} {status}：{count} 条")
        if not count:
            failures.append(f"缺少「{status}」状态示例数据")
    for name, passed in body["checks"].items():
        if not passed:
            failures.append(name)

    # 2) 报名接口走通：新建一条 -> 报名参加 -> 待评定
    code, created = fetch("POST", f"{base_url}/api/ability", {
        "values": {
            "验证编号": "ABIL-CHECK-NEW",
            "组织方": "自检脚本临时数据",
            "检测项目": "自检项目",
        }
    })
    new_id = created.get("entry", {}).get("id") if isinstance(created, dict) else None
    if code == 200 and isinstance(created, dict) and created.get("ok") and new_id:
        print(f"  ✓ 登记接口可用：新建自检记录 id={new_id}")
    else:
        print(f"  ✗ 登记接口失败：{created}")
        failures.append("POST /api/ability 登记")
        new_id = None

    if new_id is not None:
        action_url = f"{base_url}/api/ability/{new_id}/actions"
        code, signed = fetch("POST", action_url, {"values": {"action": "报名参加", "参加人员": "自检员"}})
        if code == 200 and isinstance(signed, dict) and signed.get("ok") \
                and signed["entry"]["status"] == "待评定":
            print("  ✓ 报名接口可用：待参加 -> 待评定")
        else:
            print(f"  ✗ 报名参加失败：{signed}")
            failures.append("报名参加动作")

        # 3) 上报结果（停留在待评定）
        code, reported = fetch("POST", action_url, {"values": {"action": "上报结果", "上报日期": "2026-09-26"}})
        if code == 200 and isinstance(reported, dict) and reported.get("ok") \
                and reported["entry"]["status"] == "待评定":
            print("  ✓ 上报结果接口可用：已补录上报日期")
        else:
            print(f"  ✗ 上报结果失败：{reported}")
            failures.append("上报结果动作")

        # 4) 评定接口走通：先评不合格 -> 未通过（状态机也验证了结论分流）
        code, judged = fetch("POST", action_url, {"values": {"action": "接收评定", "结果评定": "不合格"}})
        if code == 200 and isinstance(judged, dict) and judged.get("ok") \
                and judged["entry"]["status"] == "未通过":
            print("  ✓ 评定接口可用：待评定 -> 未通过（结论=不合格）")
        else:
            print(f"  ✗ 接收评定(不合格)失败：{judged}")
            failures.append("接收评定-不合格")

        # 5) 终态再动作应被拦截
        code, blocked = fetch("POST", action_url, {"values": {"action": "报名参加", "参加人员": "x"}})
        if isinstance(blocked, dict) and not blocked.get("ok"):
            print(f"  ✓ 状态守卫生效：终态动作被拦截（{blocked.get('message')}）")
        else:
            failures.append("终态应拒绝继续动作")

        # 6) 合格结论新建一条，验证已通过分流
        code, second = fetch("POST", f"{base_url}/api/ability", {
            "values": {"验证编号": "ABIL-CHECK-PASS", "组织方": "自检脚本临时数据", "检测项目": "自检项目2"}
        })
        sid = second.get("entry", {}).get("id") if isinstance(second, dict) else None
        if sid:
            url2 = f"{base_url}/api/ability/{sid}/actions"
            fetch("POST", url2, {"values": {"action": "报名参加", "参加人员": "自检员"}})
            fetch("POST", url2, {"values": {"action": "上报结果", "上报日期": "2026-09-26"}})
            code, passed = fetch("POST", url2, {"values": {"action": "接收评定", "结果评定": "合格"}})
            if code == 200 and isinstance(passed, dict) and passed.get("ok") \
                    and passed["entry"]["status"] == "已通过":
                print("  ✓ 评定接口可用：待评定 -> 已通过（结论=合格）")
            else:
                print(f"  ✗ 接收评定(合格)失败：{passed}")
                failures.append("接收评定-合格")

    print()
    if failures:
        print("未通过项：")
        for item in failures:
            print(f"  - {item}")
        print("\n结论：能力验证模块自检未通过")
        return 1
    print("结论：能力验证报名与评定接口全部可用 ✓")
    return 0


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    raise SystemExit(main(base.rstrip("/")))
