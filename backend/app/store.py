"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
SEED_DEMO_DATA=0 时启动为空仓库（联调用），默认灌入全部示例数据。
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.seed import SEED_ROWS

# 模块名常量：自检与启动横幅按名取表，避免各处硬编码字符串
MODULE_ABILITY = "ability"


class Store:
    def __init__(self, *, load_seed: bool | None = None) -> None:
        if load_seed is None:
            load_seed = settings.seed_demo_data
        self._tables: dict[str, list[dict[str, Any]]] = (
            {name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()}
            if load_seed
            else {name: [] for name in SEED_ROWS}
        )

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}


store = Store()
