"""pytest fixtures。

单元测试（tests/unit）仅测 domain 纯函数，无需任何基础设施。
集成/e2e 测试需 docker compose 起服务后运行。
"""
import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
