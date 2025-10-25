"""
分布式锁模块

基于缓存后端实现的分布式锁，用于并发控制。

使用示例：
    >>> from symphra_cache import CacheManager, RedisBackend
    >>> from symphra_cache.locks import DistributedLock
    >>>
    >>> manager = CacheManager(backend=RedisBackend())
    >>> lock = DistributedLock(manager, "my_resource", timeout=30)
    >>>
    >>> with lock:
    ...     # 临界区代码
    ...     process_shared_resource()
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import CacheManager


class DistributedLock:
    """
    分布式锁

    基于缓存后端的分布式锁实现，支持超时和自动释放。

    使用示例：
        >>> lock = DistributedLock(manager, "resource:123", timeout=10)
        >>> if lock.acquire():
        ...     try:
        ...         # 处理资源
        ...         pass
        ...     finally:
        ...         lock.release()
    """

    def __init__(
        self,
        manager: CacheManager,
        name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: float | None = None,
    ) -> None:
        """
        初始化分布式锁

        Args:
            manager: 缓存管理器
            name: 锁名称
            timeout: 锁超时时间（秒）
            blocking: 是否阻塞等待
            blocking_timeout: 阻塞超时（秒）
        """
        self.manager = manager
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.identifier = str(uuid.uuid4())  # 唯一标识符
        self._locked = False

    def acquire(self) -> bool:
        """
        获取锁

        Returns:
            是否成功获取锁
        """
        start_time = time.time()

        while True:
            # 尝试设置锁（使用 TTL 防止死锁）
            existing = self.manager.get(self.name)

            if existing is None:
                # 锁不存在，尝试获取
                self.manager.set(self.name, self.identifier, ttl=self.timeout)
                self._locked = True
                return True

            if not self.blocking:
                return False

            # 检查阻塞超时
            if (
                self.blocking_timeout is not None
                and time.time() - start_time >= self.blocking_timeout
            ):
                return False

            # 短暂休眠后重试
            time.sleep(0.01)

    def release(self) -> None:
        """释放锁"""
        if not self._locked:
            return

        # 验证是否是自己的锁
        current_value = self.manager.get(self.name)
        if current_value == self.identifier:
            self.manager.delete(self.name)
            self._locked = False

    def __enter__(self) -> DistributedLock:
        """上下文管理器：进入"""
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """上下文管理器：退出"""
        self.release()
