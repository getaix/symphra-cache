"""
监控基础模块

定义监控系统的核心接口和基础实现。
提供指标收集、统计计算和监控器基类。

特性：
- 统一的指标收集接口
- 性能数据统计
- 可扩展的监控架构
- 线程安全的指标存储

使用示例：
    >>> from symphra_cache.monitoring.base import CacheMonitor
    >>> monitor = CacheMonitor(cache)
    >>> metrics = monitor.collect_metrics()
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .manager import CacheManager


class CacheMetrics:
    """
    缓存指标数据结构

    存储缓存系统的各种性能指标。
    """

    def __init__(self) -> None:
        """初始化指标数据"""
        # 基础计数器
        self.get_count = 0
        self.set_count = 0
        self.delete_count = 0
        self.exists_count = 0

        # 命中率相关
        self.hit_count = 0
        self.miss_count = 0

        # 性能指标（毫秒）
        self.get_latency_sum = 0.0
        self.set_latency_sum = 0.0
        self.delete_latency_sum = 0.0

        self.get_latency_min: float | None = None
        self.get_latency_max: float | None = None
        self.set_latency_min: float | None = None
        self.set_latency_max: float | None = None
        self.delete_latency_min: float | None = None
        self.delete_latency_max: float | None = None

        # 时间戳
        self.start_time = time.time()
        self.last_reset_time = self.start_time

        # 锁保护并发访问
        self._lock = threading.RLock()

    def record_get(self, hit: bool, latency_ms: float) -> None:
        """记录 GET 操作"""
        with self._lock:
            self.get_count += 1
            if hit:
                self.hit_count += 1
            else:
                self.miss_count += 1

            self.get_latency_sum += latency_ms
            self._update_latency_stats("get", latency_ms)

    def record_set(self, latency_ms: float) -> None:
        """记录 SET 操作"""
        with self._lock:
            self.set_count += 1
            self.set_latency_sum += latency_ms
            self._update_latency_stats("set", latency_ms)

    def record_delete(self, latency_ms: float) -> None:
        """记录 DELETE 操作"""
        with self._lock:
            self.delete_count += 1
            self.delete_latency_sum += latency_ms
            self._update_latency_stats("delete", latency_ms)

    def _update_latency_stats(self, operation: str, latency_ms: float) -> None:
        """更新延迟统计"""
        min_attr = f"{operation}_latency_min"
        max_attr = f"{operation}_latency_max"

        # 确保属性存在
        if not hasattr(self, min_attr):
            setattr(self, min_attr, None)
        if not hasattr(self, max_attr):
            setattr(self, max_attr, None)

        current_min = getattr(self, min_attr)
        current_max = getattr(self, max_attr)

        if current_min is None or latency_ms < current_min:
            setattr(self, min_attr, latency_ms)

        if current_max is None or latency_ms > current_max:
            setattr(self, max_attr, latency_ms)

    def get_hit_rate(self) -> float:
        """获取命中率"""
        with self._lock:
            total = self.hit_count + self.miss_count
            return self.hit_count / total if total > 0 else 0.0

    def get_average_latency(self, operation: str) -> float:
        """获取平均延迟"""
        with self._lock:
            count_attr = f"{operation}_count"
            sum_attr = f"{operation}_latency_sum"

            count = getattr(self, count_attr)
            sum_latency = getattr(self, sum_attr)

            return sum_latency / count if count > 0 else 0.0

    def get_latency_stats(self, operation: str) -> dict[str, float | None]:
        """获取延迟统计"""
        with self._lock:
            min_attr = f"{operation}_latency_min"
            max_attr = f"{operation}_latency_max"

            current_min = getattr(self, min_attr)
            current_max = getattr(self, max_attr)

            return {
                "min": current_min,
                "max": current_max,
                "avg": self.get_average_latency(operation),
            }

    def get_total_operations(self) -> int:
        """获取总操作数"""
        with self._lock:
            return self.get_count + self.set_count + self.delete_count

    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            # 保留时间戳
            start_time = self.start_time

            # 重置所有计数器
            self.get_count = 0
            self.set_count = 0
            self.delete_count = 0
            self.exists_count = 0
            self.hit_count = 0
            self.miss_count = 0
            self.get_latency_sum = 0.0
            self.set_latency_sum = 0.0
            self.delete_latency_sum = 0.0
            self.get_latency_min = None
            self.get_latency_max = None
            self.set_latency_min = None
            self.set_latency_max = None
            self.delete_latency_min = None
            self.delete_latency_max = None

            self.last_reset_time = time.time()
            self.start_time = start_time

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        with self._lock:
            return {
                "get_count": self.get_count,
                "set_count": self.set_count,
                "delete_count": self.delete_count,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": self.get_hit_rate(),
                "total_operations": self.get_total_operations(),
                "get_latency": self.get_latency_stats("get"),
                "set_latency": self.get_latency_stats("set"),
                "delete_latency": self.get_latency_stats("delete"),
                "uptime_seconds": time.time() - self.start_time,
                "last_reset_time": self.last_reset_time,
            }


class CacheMonitor:
    """
    缓存监控器基类

    提供缓存性能监控的核心功能，可以被各种监控系统继承和扩展。

    监控指标：
    - 命中率（Hit Rate）
    - 操作延迟（Latency）
    - 吞吐量（Throughput）
    - 缓存大小（Cache Size）
    - 错误率（Error Rate）

    使用示例：
        >>> monitor = CacheMonitor(cache)
        >>> metrics = monitor.collect_metrics()
    """

    def __init__(self, cache: CacheManager) -> None:
        """
        初始化监控器

        Args:
            cache: 要监控的缓存管理器
        """
        self.cache = cache
        self.metrics = CacheMetrics()
        self._enabled = True
        self._lock = threading.RLock()

    def enable(self) -> None:
        """启用监控"""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """禁用监控"""
        with self._lock:
            self._enabled = False

    def is_enabled(self) -> bool:
        """检查监控是否启用"""
        with self._lock:
            return self._enabled

    async def collect_metrics(self) -> CacheMetrics:
        """
        收集当前缓存指标

        Returns:
            缓存指标对象
        """
        if not self.is_enabled():
            return CacheMetrics()

        # 收集基础指标
        metrics = CacheMetrics()

        # 获取缓存大小
        try:
            cache_size = len(self.cache)
            metrics.cache_size = cache_size
        except Exception:
            metrics.cache_size = 0

        # 获取命中率（如果后端支持）
        try:
            hit_rate = getattr(self.cache.backend, "hit_rate", 0.0)
            metrics.hit_rate = hit_rate
        except Exception:
            pass

        return metrics

    def record_operation(
        self,
        operation: str,
        hit: bool = False,
        latency_ms: float = 0.0,
    ) -> None:
        """
        记录操作指标

        Args:
            operation: 操作类型 ("get", "set", "delete")
            hit: 是否命中缓存
            latency_ms: 操作延迟（毫秒）
        """
        if not self.is_enabled():
            return

        if operation == "get":
            self.metrics.record_get(hit, latency_ms)
        elif operation == "set":
            self.metrics.record_set(latency_ms)
        elif operation == "delete":
            self.metrics.record_delete(latency_ms)

    def get_health_status(self) -> dict[str, Any]:
        """
        获取健康状态

        Returns:
            健康状态信息
        """
        try:
            # 检查缓存连接
            is_healthy = self.cache.check_health()

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "cache_size": len(self.cache),
                "hit_rate": self.metrics.get_hit_rate(),
                "uptime_seconds": time.time() - self.metrics.start_time,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "cache_size": 0,
            }

    def reset_metrics(self) -> None:
        """重置所有指标"""
        self.metrics.reset()

    def create_custom_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        创建自定义指标

        Args:
            name: 指标名称
            value: 指标值
            tags: 指标标签
        """
        # 子类可以重写此方法来支持自定义指标
        pass

    def export_metrics(self) -> str:
        """
        导出指标为字符串格式

        Returns:
            格式化的指标字符串
        """
        metrics = self.metrics.to_dict()
        lines = []

        for key, value in metrics.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if subvalue is not None:
                        lines.append(f"{key}_{subkey}: {subvalue}")
            else:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"CacheMonitor(cache={self.cache!r}, enabled={self.is_enabled()})"
