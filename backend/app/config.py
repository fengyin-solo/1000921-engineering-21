"""运行配置：端口、跨域、运行环境。

所有配置都可通过环境变量覆盖（本地零配置也能跑，变量均有默认值）：

- APP_ENV：运行环境，默认 local
- APP_PORT：后端监听端口，默认 8000
- APP_HOST：后端监听地址，默认 127.0.0.1
- CORS_ORIGINS：允许的前端来源，逗号分隔，默认本地两个 vite 地址
- SEED_DEMO_DATA：是否在启动时灌入示例数据，默认 1（能力验证演示需要）
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(RuntimeError):
    """配置非法：消息要能直接告诉使用者该改哪个环境变量。"""


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _build_settings() -> "Settings":
    port_raw = os.environ.get("APP_PORT", "8000").strip()
    try:
        port = int(port_raw)
    except ValueError:
        raise ConfigError(
            f"环境变量 APP_PORT 必须是端口号（1-65535），当前值为「{port_raw}」。"
            "请检查 .env 或 shell 环境变量后重试。"
        ) from None
    if not 1 <= port <= 65535:
        raise ConfigError(
            f"环境变量 APP_PORT 超出 1-65535 范围，当前值为「{port_raw}」。"
        )

    env = os.environ.get("APP_ENV", "local").strip() or "local"

    host = os.environ.get("APP_HOST", "127.0.0.1").strip() or "127.0.0.1"

    cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
    if cors_raw:
        allowed_origins = [item.strip().rstrip("/") for item in cors_raw.split(",") if item.strip()]
        bad = [item for item in allowed_origins if not item.startswith(("http://", "https://"))]
        if bad:
            raise ConfigError(
                "环境变量 CORS_ORIGINS 里的来源必须以 http:// 或 https:// 开头，"
                f"非法值：{'、'.join(bad)}。多个来源用英文逗号分隔。"
            )
    else:
        allowed_origins = [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]

    return Settings(
        app_name="实验室样品检测管理平台",
        env=env,
        host=host,
        port=port,
        allowed_origins=allowed_origins,
        seed_demo_data=_parse_bool(os.environ.get("SEED_DEMO_DATA"), True),
    )


@dataclass(frozen=True)
class Settings:
    app_name: str
    env: str
    host: str
    port: int
    allowed_origins: list[str] = field(default_factory=list)
    page_size_default: int = 20
    page_size_max: int = 200
    seed_demo_data: bool = True


settings = _build_settings()
