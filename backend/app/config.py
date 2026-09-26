"""运行配置：从仓库根目录 .env 与进程环境读取端口、跨域、运行环境。

查找顺序：真实环境变量 > 仓库根目录 .env > 代码内默认值。
环境变量缺失或格式非法时在这里直接抛错，让启动失败原因可定位，
而不是带着错误配置静默跑起来。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"

ALLOWED_ENVS = ("local", "dev", "test", "prod")


def _load_dotenv(path: Path) -> None:
    """把 .env 里的 KEY=VALUE 补进 os.environ；不覆盖已存在的真实环境变量。

    刻意不引第三方库：这里只处理简单的 KEY=VALUE，注释/空行跳过，
    值两侧的成对引号剥掉，保持克隆即可用、无额外依赖。
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _required_str(key: str, default: str) -> str:
    value = os.environ.get(key, default).strip()
    if not value:
        raise RuntimeError(
            f"环境变量未配置：{key} 为空，请在 {ENV_FILE} 中补上后重启"
        )
    return value


def _required_port(key: str, default: int) -> int:
    raw = os.environ.get(key, str(default)).strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"环境变量配置错误：{key}={raw!r} 不是合法端口（应为 1-65535 的整数）"
        ) from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(f"环境变量配置错误：{key}={port} 超出端口范围 1-65535")
    return port


_load_dotenv(ENV_FILE)

_env = _required_str("APP_ENV", "local")
if _env not in ALLOWED_ENVS:
    raise RuntimeError(
        f"环境变量配置错误：APP_ENV={_env!r} 不被支持，"
        f"可选值：{ '、'.join(ALLOWED_ENVS) }（参考 .env.example）"
    )

_backend_port = _required_port("APP_PORT", 8000)
_frontend_port = _required_port("FRONTEND_PORT", 5173)


@dataclass(frozen=True)
class Settings:
    app_name: str = "实验室样品检测管理平台"
    env: str = _env
    port: int = _backend_port
    frontend_port: int = _frontend_port
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            f"http://127.0.0.1:{_frontend_port}",
            f"http://localhost:{_frontend_port}",
        ]
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
