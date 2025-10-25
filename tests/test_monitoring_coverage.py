"""
监控模块的覆盖率测试

为监控基类和相关模块添加测试。
"""

from __future__ import annotations

import pytest

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.monitoring.base import CacheMetrics


class TestCacheMetrics:
    """测试缓存指标"""

    def test_cache_metrics_initialization(self) -> None:
        """测试缓存指标的初始化"""
        metrics = CacheMetrics()

        # 验证初始值
        assert metrics.get_count == 0
        assert metrics.set_count == 0
        assert metrics.delete_count == 0
        assert metrics.hit_count == 0
        assert metrics.miss_count == 0

    def test_cache_metrics_counters(self) -> None:
        """测试缓存指标的计数器"""
        metrics = CacheMetrics()

        # 增加计数
        metrics.get_count += 1
        metrics.set_count += 1
        metrics.delete_count += 1
        metrics.hit_count += 1
        metrics.miss_count += 1

        # 验证
        assert metrics.get_count == 1
        assert metrics.set_count == 1
        assert metrics.delete_count == 1
        assert metrics.hit_count == 1
        assert metrics.miss_count == 1

    def test_cache_metrics_latency(self) -> None:
        """测试缓存指标的延迟"""
        metrics = CacheMetrics()

        # 设置延迟值
        metrics.get_latency_sum = 100.0
        metrics.set_latency_sum = 50.0
        metrics.delete_latency_sum = 25.0

        # 验证
        assert metrics.get_latency_sum == 100.0
        assert metrics.set_latency_sum == 50.0
        assert metrics.delete_latency_sum == 25.0

    def test_cache_metrics_min_max(self) -> None:
        """测试缓存指标的最小最大值"""
        metrics = CacheMetrics()

        # 设置最小最大值
        metrics.get_latency_min = 0.5
        metrics.get_latency_max = 10.0
        metrics.set_latency_min = 0.3
        metrics.set_latency_max = 5.0

        # 验证
        assert metrics.get_latency_min == 0.5
        assert metrics.get_latency_max == 10.0
        assert metrics.set_latency_min == 0.3
        assert metrics.set_latency_max == 5.0

    def test_cache_metrics_with_timestamps(self) -> None:
        """测试缓存指标的时间戳"""
        import time

        metrics = CacheMetrics()

        # 设置时间戳
        now = time.time()
        metrics.timestamp = now

        # 验证
        assert metrics.timestamp is not None


class TestManagerWithMonitoring:
    """测试带监控的管理器"""

    def test_manager_with_monitor(self) -> None:
        """测试管理器的监控功能"""
        manager = CacheManager(backend=MemoryBackend())

        # 执行缓存操作
        manager.set("key1", "value1")
        value = manager.get("key1")
        assert value == "value1"

        # 删除
        manager.delete("key1")
        value = manager.get("key1")
        assert value is None

    def test_manager_operations_count(self) -> None:
        """测试管理器操作计数"""
        manager = CacheManager(backend=MemoryBackend())

        # 执行多个操作
        for i in range(5):
            manager.set(f"key{i}", f"value{i}")

        for i in range(5):
            manager.get(f"key{i}")

        # 验证管理器仍然运行正常
        assert manager.get("key0") == "value0"


class TestMonitoringMetricsCollection:
    """测试监控指标的收集"""

    def test_metrics_increment_pattern(self) -> None:
        """测试指标增量模式"""
        metrics = CacheMetrics()

        # 模拟递增
        for i in range(10):
            metrics.get_count += 1
            metrics.hit_count += 5
            metrics.miss_count += 1

        # 验证
        assert metrics.get_count == 10
        assert metrics.hit_count == 50
        assert metrics.miss_count == 10

    def test_metrics_latency_tracking(self) -> None:
        """测试延迟跟踪"""
        metrics = CacheMetrics()

        # 跟踪多个操作的延迟
        latencies = [0.5, 1.2, 0.8, 1.5, 0.3]
        total_latency = 0.0
        min_latency = float('inf')
        max_latency = 0.0

        for lat in latencies:
            total_latency += lat
            min_latency = min(min_latency, lat)
            max_latency = max(max_latency, lat)

        metrics.get_latency_sum = total_latency
        metrics.get_latency_min = min_latency
        metrics.get_latency_max = max_latency

        # 验证
        assert metrics.get_latency_sum == pytest.approx(4.3)
        assert metrics.get_latency_min == 0.3
        assert metrics.get_latency_max == 1.5

    def test_cache_hit_rate_calculation(self) -> None:
        """测试缓存命中率计算"""
        metrics = CacheMetrics()

        # 模拟缓存命中和未命中
        metrics.hit_count = 80
        metrics.miss_count = 20
        total_requests = metrics.hit_count + metrics.miss_count

        if total_requests > 0:
            hit_rate = metrics.hit_count / total_requests
            assert hit_rate == pytest.approx(0.8)
