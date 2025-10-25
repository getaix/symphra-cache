"""
监控模块

提供缓存系统的性能监控和指标导出功能。
支持 Prometheus、StatsD 等监控系统集成。

特性：
- 性能指标收集（命中率、延迟、吞吐量）
- Prometheus 指标导出
- StatsD 指标导出
- 自定义指标支持
- 健康检查和告警

使用示例：
    >>> from symphra_cache import CacheManager, MemoryBackend
    >>> from symphra_cache.monitoring import CacheMonitor
    >>>
    >>> cache = CacheManager(backend=MemoryBackend())
    >>> monitor = CacheMonitor(cache)
    >>>
    >>> # 收集指标
    >>> metrics = monitor.collect_metrics()
    >>>
    >>> # Prometheus 导出
    >>> prometheus_handler = monitor.get_prometheus_handler()
"""

from __future__ import annotations

from .base import CacheMetrics, CacheMonitor
from .prometheus import PrometheusExporter
from .statsd import StatsDExporter

__all__ = [
    "CacheMonitor",
    "CacheMetrics",
    "PrometheusExporter",
    "StatsDExporter",
]
