"""
缓存监控模块

提供缓存性能监控、统计和健康检查功能。

特性：
- 命中率统计（hits/misses）
- 操作计数（get/set/delete）
- 错误追踪
- 性能指标（平均响应时间）
- 健康检查

使用示例：
    >>> from symphra_cache import CacheManager, CacheMonitor
    >>> cache = CacheManager.from_config({"backend": "memory"})
    >>> monitor = CacheMonitor(cache)
    >>> monitor.get_stats()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import CacheManager


@dataclass
class CacheStats:
    """
    缓存统计信息

    所有计数器都是累积值，可通过 reset() 重置。
    """

    # 命中统计
    hits: int = 0  # 缓存命中次数
    misses: int = 0  # 缓存未命中次数

    # 操作统计
    gets: int = 0  # get 操作次数
    sets: int = 0  # set 操作次数
    deletes: int = 0  # delete 操作次数

    # 错误统计
    errors: int = 0  # 错误次数

    # 性能统计
    total_get_time: float = 0.0  # get 操作总耗时（秒）
    total_set_time: float = 0.0  # set 操作总耗时（秒）

    # 时间戳
    start_time: float = field(default_factory=time.time)  # 统计开始时间
    last_reset: float = field(default_factory=time.time)  # 上次重置时间

    @property
    def hit_rate(self) -> float:
        """命中率（0-1）"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """未命中率(0-1)"""
        total = self.hits + self.misses
        return self.misses / total if total > 0 else 0.0

    @property
    def avg_get_time(self) -> float:
        """平均 get 操作耗时（毫秒）"""
        return (self.total_get_time / self.gets * 1000) if self.gets > 0 else 0.0

    @property
    def avg_set_time(self) -> float:
        """平均 set 操作耗时（毫秒）"""
        return (self.total_set_time / self.sets * 1000) if self.sets > 0 else 0.0

    @property
    def uptime(self) -> float:
        """运行时间（秒）"""
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "gets": self.gets,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "avg_get_time_ms": self.avg_get_time,
            "avg_set_time_ms": self.avg_set_time,
            "uptime_seconds": self.uptime,
            "start_time": self.start_time,
            "last_reset": self.last_reset,
        }


class CacheMetricsAdapter:
    """
    适配器：为导出器提供统一的 metrics 接口

    将 CacheStats（库内实现）适配为 monitoring.base.CacheMetrics 所需的字段与方法。
    """

    def __init__(self, stats: CacheStats, monitor: "CacheMonitor") -> None:
        self._stats = stats
        self._monitor = monitor

    # 计数器属性（与导出器期望一致）
    @property
    def get_count(self) -> int:
        return self._stats.gets

    @property
    def set_count(self) -> int:
        return self._stats.sets

    @property
    def delete_count(self) -> int:
        return self._stats.deletes

    @property
    def hit_count(self) -> int:
        return self._stats.hits

    @property
    def miss_count(self) -> int:
        return self._stats.misses

    # 速率/聚合
    def get_hit_rate(self) -> float:
        return self._stats.hit_rate

    def get_total_operations(self) -> int:
        return self._stats.gets + self._stats.sets + self._stats.deletes

    # 延迟统计（毫秒）
    def get_average_latency(self, operation: str) -> float:
        if operation == "get":
            return self._stats.avg_get_time
        if operation == "set":
            return self._stats.avg_set_time
        # delete 未统计延迟，返回 0
        return 0.0

    def get_latency_stats(self, operation: str) -> dict[str, float | None]:
        if operation == "get":
            return {
                "min": self._monitor._latency_min.get("get"),
                "max": self._monitor._latency_max.get("get"),
                "avg": self._stats.avg_get_time,
            }
        if operation == "set":
            return {
                "min": self._monitor._latency_min.get("set"),
                "max": self._monitor._latency_max.get("set"),
                "avg": self._stats.avg_set_time,
            }
        return {"min": None, "max": None, "avg": 0.0}


class CacheMonitor:
    """
    缓存监控器

    提供缓存统计、监控和健康检查功能。
    线程安全。

    使用示例：
        >>> cache = CacheManager.from_config({"backend": "memory"})
        >>> monitor = CacheMonitor(cache)
        >>>
        >>> # 执行缓存操作
        >>> cache.set("key", "value")
        >>> cache.get("key")
        >>>
        >>> # 查看统计
        >>> stats = monitor.get_stats()
        >>> print(f"命中率: {stats.hit_rate:.2%}")
    """

    def __init__(self, cache_manager: CacheManager, *, enabled: bool = True) -> None:
        """
        初始化监控器

        Args:
            cache_manager: 缓存管理器实例
            enabled: 是否启用监控（禁用时性能开销为零）
        """
        self._cache = cache_manager
        # 为兼容导出器，公开 cache 属性
        self.cache = cache_manager

        self._enabled = enabled
        self._stats = CacheStats()
        self._lock = threading.RLock()

        # 记录延迟的 min/max（毫秒）以供导出器使用
        self._latency_min: dict[str, float] = {}
        self._latency_max: dict[str, float] = {}

        # 如果启用，替换缓存管理器的方法
        if self._enabled:
            self._wrap_cache_methods()

    def is_enabled(self) -> bool:
        """是否启用监控（为导出器兼容提供）"""
        return self._enabled

    @property
    def metrics(self) -> CacheMetricsAdapter:
        """提供与导出器兼容的指标接口"""
        return CacheMetricsAdapter(self._stats, self)

    def _wrap_cache_methods(self) -> None:
        """包装缓存管理器方法以收集统计信息"""
        original_get = self._cache.get
        original_set = self._cache.set
        original_delete = self._cache.delete

        def monitored_get(key):
            start = time.perf_counter()
            try:
                result = original_get(key)
                elapsed_s = time.perf_counter() - start
                latency_ms = elapsed_s * 1000.0
                with self._lock:
                    self._stats.gets += 1
                    self._stats.total_get_time += elapsed_s
                    # 更新 min/max（毫秒）
                    prev_min = self._latency_min.get("get")
                    prev_max = self._latency_max.get("get")
                    if prev_min is None or latency_ms < prev_min:
                        self._latency_min["get"] = latency_ms
                    if prev_max is None or latency_ms > prev_max:
                        self._latency_max["get"] = latency_ms
                    if result is not None:
                        self._stats.hits += 1
                    else:
                        self._stats.misses += 1
                return result
            except Exception as e:
                with self._lock:
                    self._stats.errors += 1
                raise e

        def monitored_set(key, value, ttl=None, ex=False, nx=False):
            start = time.perf_counter()
            try:
                result = original_set(key, value, ttl, ex, nx)
                elapsed_s = time.perf_counter() - start
                latency_ms = elapsed_s * 1000.0
                with self._lock:
                    self._stats.sets += 1
                    self._stats.total_set_time += elapsed_s
                    # 更新 min/max（毫秒）
                    prev_min = self._latency_min.get("set")
                    prev_max = self._latency_max.get("set")
                    if prev_min is None or latency_ms < prev_min:
                        self._latency_min["set"] = latency_ms
                    if prev_max is None or latency_ms > prev_max:
                        self._latency_max["set"] = latency_ms
                return result
            except Exception as e:
                with self._lock:
                    self._stats.errors += 1
                raise e

        def monitored_delete(key):
            try:
                result = original_delete(key)
                with self._lock:
                    self._stats.deletes += 1
                return result
            except Exception as e:
                with self._lock:
                    self._stats.errors += 1
                raise e

        # 替换方法
        self._cache.get = monitored_get
        self._cache.set = monitored_set
        self._cache.delete = monitored_delete

    def get_stats(self) -> CacheStats:
        """
        获取统计信息

        Returns:
            CacheStats 对象（副本）

        示例：
            >>> stats = monitor.get_stats()
            >>> print(f"命中率: {stats.hit_rate:.2%}")
            >>> print(f"平均响应时间: {stats.avg_get_time:.2f}ms")
        """
        with self._lock:
            # 返回副本
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                gets=self._stats.gets,
                sets=self._stats.sets,
                deletes=self._stats.deletes,
                errors=self._stats.errors,
                total_get_time=self._stats.total_get_time,
                total_set_time=self._stats.total_set_time,
                start_time=self._stats.start_time,
                last_reset=self._stats.last_reset,
            )

    def reset_stats(self) -> None:
        """
        重置统计信息

        保留 start_time，更新 last_reset。

        示例:
            >>> monitor.reset_stats()  # 重新开始统计
        """
        with self._lock:
            start_time = self._stats.start_time
            self._stats = CacheStats(start_time=start_time)
            # 清理延迟统计
            self._latency_min.clear()
            self._latency_max.clear()

    def check_health(self) -> dict:
        """
        执行健康检查

        Returns:
            健康检查结果字典

        示例：
            >>> health = monitor.check_health()
            >>> if health["healthy"]:
            ...     print("缓存健康")
        """
        try:
            # 测试基本操作
            test_key = "__health_check__"
            test_value = f"health_check_{time.time()}"

            # 测试写入
            self._cache.set(test_key, test_value, ttl=1)

            # 测试读取
            result = self._cache.get(test_key)
            read_ok = result == test_value

            # 清理
            self._cache.delete(test_key)

            # 获取后端健康状态
            backend_healthy = self._cache.backend.check_health()

            return {
                "healthy": read_ok and backend_healthy,
                "backend_healthy": backend_healthy,
                "test_passed": read_ok,
                "timestamp": time.time(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "backend_healthy": False,
                "test_passed": False,
                "error": str(e),
                "timestamp": time.time(),
            }

    def get_summary(self) -> dict:
        """
        获取监控摘要

        返回统计信息和健康状态的汇总。

        Returns:
            摘要字典

        示例：
            >>> summary = monitor.get_summary()
            >>> print(summary)
        """
        stats = self.get_stats()
        health = self.check_health()

        return {
            "stats": stats.to_dict(),
            "health": health,
        }

    def __repr__(self) -> str:
        """字符串表示"""
        stats = self.get_stats()
        return (
            f"CacheMonitor(enabled={self._enabled}, "
            f"hit_rate={stats.hit_rate:.2%}, "
            f"operations={stats.gets + stats.sets + stats.deletes}, "
            f"errors={stats.errors})"
        )


__all__ = ["CacheMonitor", "CacheStats"]
