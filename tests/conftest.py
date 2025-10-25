"""
Pytest 配置和全局 fixtures

本模块提供测试所需的公共 fixtures 和配置。
"""

import asyncio
from collections.abc import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建全局事件循环 fixture

    用于支持异步测试，确保所有测试共享同一个事件循环。
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
