"""
缓存失效通知模块

提供缓存失效策略和通知机制，确保数据一致性。
支持主动失效、被动失效和分布式失效通知。

特性：
- 主动失效：手动触发缓存失效
- 被动失效：基于时间或条件的自动失效
- 分布式通知：多实例间的缓存同步
- 批量失效操作
- 失效策略配置

使用示例：
    >>> from symphra_cache import CacheManager, MemoryBackend
    >>> from symphra_cache.invalidation import CacheInvalidator
    >>>
    >>> cache = CacheManager(backend=MemoryBackend())
    >>> invalidator = CacheInvalidator(cache)
    >>>
    >>> # 主动失效特定键
    >>> await invalidator.invalidate_keys(["key1", "key2"])
    >>>
    >>> # 模式匹配失效
    >>> await invalidator.invalidate_pattern("user:*")
    >>>
    >>> # 批量失效
    >>> await invalidator.invalidate_all()
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .manager import CacheManager
    from .types import CacheKey


class CacheInvalidator:
    """
    缓存失效器

    提供多种缓存失效策略，确保数据一致性和缓存更新。

    失效策略：
    - 主动失效：手动指定要失效的键
    - 模式匹配失效：基于通配符模式失效
    - 批量失效：清空所有或特定类型的数据
    - 条件失效：基于条件表达式失效
    - 分布式失效：跨多个缓存实例失效

    使用示例：
        >>> invalidator = CacheInvalidator(cache)
        >>> await invalidator.invalidate_keys(["key1", "key2"])
        >>> await invalidator.invalidate_pattern("user:*")
    """

    def __init__(
        self,
        cache: CacheManager,
        batch_size: int = 100,
        enable_distributed: bool = False,
    ) -> None:
        """
        初始化缓存失效器

        Args:
            cache: 缓存管理器实例
            batch_size: 批量操作大小
            enable_distributed: 是否启用分布式失效
        """
        self.cache = cache
        self.batch_size = batch_size
        self.enable_distributed = enable_distributed
        self._invalidation_log: list[dict[str, Any]] = []
        self._last_invalidation_time = time.time()

    async def invalidate_keys(
        self,
        keys: list[CacheKey],
        batch_size: int | None = None,
    ) -> int:
        """
        失效指定的键

        Args:
            keys: 要失效的键列表
            batch_size: 批量大小

        Returns:
            实际失效的键数量
        """
        if not keys:
            return 0

        batch_size = batch_size if batch_size is not None else self.batch_size
        total_invalidated = 0

        # 批量失效，避免一次性操作过多数据
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i : i + batch_size]

            # 批量删除
            count = await self.cache.adelete_many(batch_keys)
            total_invalidated += count

            # 记录失效日志
            self._log_invalidation("keys", batch_keys, count)

            # 短暂休眠避免阻塞
            if i + batch_size < len(keys):
                await asyncio.sleep(0.01)

        self._last_invalidation_time = time.time()
        return total_invalidated

    async def invalidate_pattern(
        self,
        pattern: str,
        max_keys: int | None = None,
    ) -> int:
        """
        基于模式匹配失效键

        支持通配符模式（* 和 ?）。

        Args:
            pattern: 匹配模式（如 "user:*", "session:??"）
            max_keys: 最大失效键数量，None 表示无限制

        Returns:
            实际失效的键数量
        """
        # 扫描匹配的键
        all_keys: list[CacheKey] = []
        cursor = 0

        while True:
            page = await self.cache.akeys(pattern=pattern, cursor=cursor, count=100)
            all_keys.extend(page.keys)

            if not page.has_more or (max_keys and len(all_keys) >= max_keys):
                break
            cursor = page.cursor

        # 限制数量
        if max_keys:
            all_keys = all_keys[:max_keys]

        # 失效匹配的键
        invalidated_count = await self.invalidate_keys(all_keys)

        self._log_invalidation(
            "pattern", {"pattern": pattern, "matched_keys": len(all_keys)}, invalidated_count
        )
        return invalidated_count

    async def invalidate_prefix(self, prefix: str) -> int:
        """
        失效指定前缀的所有键

        Args:
            prefix: 键前缀

        Returns:
            实际失效的键数量
        """
        return await self.invalidate_pattern(f"{prefix}*", max_keys=None)

    async def invalidate_all(self) -> int:
        """
        失效所有缓存

        Returns:
            实际失效的键数量
        """
        try:
            # 使用缓存的 keys 方法获取所有键
            all_keys: list[CacheKey] = []
            cursor = 0

            while True:
                page = await self.cache.akeys(cursor=cursor, count=100)
                all_keys.extend(page.keys)

                if not page.has_more:
                    break
                cursor = page.cursor

            # 批量失效
            invalidated_count = await self.invalidate_keys(all_keys)

            self._log_invalidation("all", {"total_keys": len(all_keys)}, invalidated_count)
            return invalidated_count

        except Exception:
            # 如果扫描失败，使用 clear 方法
            await self.cache.aclear()
            self._log_invalidation("all", {"method": "clear"}, len(all_keys) if all_keys else 0)
            return len(all_keys) if all_keys else 0

    async def invalidate_by_condition(
        self,
        condition: Callable[[CacheKey, Any], bool],
        max_keys: int | None = None,
    ) -> int:
        """
        基于条件失效键

        Args:
            condition: 失效条件函数，接收 (key, value) 返回是否失效
            max_keys: 最大失效键数量

        Returns:
            实际失效的键数量
        """
        # 扫描所有键并检查条件
        all_keys_to_invalidate: list[CacheKey] = []
        cursor = 0
        total_scanned = 0

        while True:
            page = await self.cache.akeys(cursor=cursor, count=100)

            for key in page.keys:
                total_scanned += 1

                # 获取键值并检查条件
                try:
                    value = await self.cache.aget(key)
                    if value is not None and condition(key, value):
                        all_keys_to_invalidate.append(key)

                        # 检查是否达到上限
                        if max_keys and len(all_keys_to_invalidate) >= max_keys:
                            break

                except Exception:
                    # 忽略获取失败的键
                    continue

            if not page.has_more or (max_keys and len(all_keys_to_invalidate) >= max_keys):
                break
            cursor = page.cursor

        # 失效符合条件的键
        invalidated_count = await self.invalidate_keys(all_keys_to_invalidate)

        self._log_invalidation(
            "condition",
            {
                "condition_func": condition.__name__
                if hasattr(condition, "__name__")
                else str(condition),
                "total_scanned": total_scanned,
                "matched_keys": len(all_keys_to_invalidate),
            },
            invalidated_count,
        )
        return invalidated_count

    async def invalidate_with_dependencies(
        self,
        keys: list[CacheKey],
        dependency_resolver: Callable[[list[CacheKey]], list[CacheKey]],
    ) -> int:
        """
        失效键及其依赖项

        Args:
            keys: 主键列表
            dependency_resolver: 依赖解析函数，返回相关的依赖键

        Returns:
            实际失效的键数量
        """
        # 获取主键
        all_keys_to_invalidate = set(keys)

        # 解析依赖键
        try:
            dependency_keys = await asyncio.to_thread(dependency_resolver, keys)
            all_keys_to_invalidate.update(dependency_keys)
        except Exception as e:
            print(f"依赖解析失败: {e}")

        # 失效所有键
        invalidated_count = await self.invalidate_keys(list(all_keys_to_invalidate))

        self._log_invalidation(
            "dependencies",
            {"primary_keys": len(keys), "dependency_keys": len(all_keys_to_invalidate) - len(keys)},
            invalidated_count,
        )
        return invalidated_count

    def _log_invalidation(
        self,
        method: str,
        details: dict[str, Any],
        count: int,
    ) -> None:
        """
        记录失效操作日志

        Args:
            method: 失效方法
            details: 失效详情
            count: 失效键数量
        """
        log_entry = {
            "timestamp": time.time(),
            "method": method,
            "details": details,
            "invalidated_count": count,
        }
        self._invalidation_log.append(log_entry)

        # 保留最近100条日志
        if len(self._invalidation_log) > 100:
            self._invalidation_log.pop(0)

    def get_invalidation_stats(self) -> dict[str, Any]:
        """
        获取失效统计信息

        Returns:
            统计信息字典
        """
        total_invalidated = sum(entry["invalidated_count"] for entry in self._invalidation_log)
        last_operation = self._invalidation_log[-1] if self._invalidation_log else None

        return {
            "total_operations": len(self._invalidation_log),
            "total_invalidated_keys": total_invalidated,
            "last_invalidation_time": self._last_invalidation_time,
            "last_operation": last_operation,
            "batch_size": self.batch_size,
            "enable_distributed": self.enable_distributed,
        }

    def get_invalidation_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取失效历史记录

        Args:
            limit: 返回记录数量

        Returns:
            失效历史列表（按时间倒序）
        """
        return self._invalidation_log[-limit:][::-1]

    async def schedule_invalidation(
        self,
        keys: list[CacheKey],
        delay: float,
    ) -> asyncio.Task[int]:
        """
        延迟失效

        Args:
            keys: 要失效的键
            delay: 延迟时间（秒）

        Returns:
            异步任务对象
        """

        async def _delayed_invalidation() -> int:
            await asyncio.sleep(delay)
            return await self.invalidate_keys(keys)

        task = asyncio.create_task(_delayed_invalidation())
        return task

    async def conditional_invalidation(
        self,
        condition: Callable[[], bool],
        keys: list[CacheKey],
        check_interval: float = 1.0,
    ) -> asyncio.Task[int]:
        """
        条件失效

        当条件满足时才失效缓存。

        Args:
            condition: 失效条件函数
            keys: 要失效的键
            check_interval: 条件检查间隔（秒）

        Returns:
            异步任务对象
        """

        async def _conditional_invalidation() -> int:
            while True:
                if condition():
                    return await self.invalidate_keys(keys)
                await asyncio.sleep(check_interval)

        task = asyncio.create_task(_conditional_invalidation())
        return task

    def create_cache_group_invalidator(self, group_prefix: str) -> CacheGroupInvalidator:
        """
        创建缓存组失效器

        专门用于管理具有相同前缀的缓存键。

        Args:
            group_prefix: 组前缀

        Returns:
            缓存组失效器
        """
        return CacheGroupInvalidator(self, group_prefix)

    async def close(self) -> None:
        """
        关闭失效器
        """
        # 清理资源
        self._invalidation_log.clear()


class CacheGroupInvalidator:
    """
    缓存组失效器

    专门管理具有相同前缀的缓存键的失效。

    使用示例：
        >>> group_invalidator = invalidator.create_cache_group_invalidator("user:")
        >>> await group_invalidator.invalidate_all()
        >>> await group_invalidator.invalidate_pattern("*:profile")
    """

    def __init__(self, parent: CacheInvalidator, group_prefix: str) -> None:
        """
        初始化缓存组失效器

        Args:
            parent: 父失效器
            group_prefix: 组前缀
        """
        self.parent = parent
        self.group_prefix = group_prefix

    async def invalidate_all(self) -> int:
        """
        失效整个组的所有键

        Returns:
            实际失效的键数量
        """
        return await self.parent.invalidate_prefix(self.group_prefix)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        失效组内匹配模式的键

        Args:
            pattern: 相对于组前缀的模式

        Returns:
            实际失效的键数量
        """
        full_pattern = f"{self.group_prefix}{pattern}"
        return await self.parent.invalidate_pattern(full_pattern)

    async def invalidate_keys(self, relative_keys: list[str]) -> int:
        """
        失效组内的指定键

        Args:
            relative_keys: 相对于组前缀的键名列表

        Returns:
            实际失效的键数量
        """
        from typing import cast

        full_keys = cast("list[CacheKey]", [f"{self.group_prefix}{key}" for key in relative_keys])
        return await self.parent.invalidate_keys(full_keys)

    def get_stats(self) -> dict[str, Any]:
        """
        获取组失效统计

        Returns:
            统计信息
        """
        return {
            "group_prefix": self.group_prefix,
            "parent_stats": self.parent.get_invalidation_stats(),
        }


# 工厂函数
def create_invalidator(
    cache: CacheManager,
    strategy: str = "default",
    **kwargs: Any,
) -> CacheInvalidator:
    """
    创建缓存失效器工厂函数

    Args:
        cache: 缓存管理器
        strategy: 失效策略
        **kwargs: 其他参数

    Returns:
        缓存失效器实例
    """
    return CacheInvalidator(cache, **kwargs)
