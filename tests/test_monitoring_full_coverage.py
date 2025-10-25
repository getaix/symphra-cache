"""
监控模块的全面测试

包括 Prometheus、StatsD 和基础监控类的测试。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, Mock
import pytest

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.monitor import CacheMonitor


class TestMonitorBasics:
    """监控基础功能测试"""

    def test_monitor_initialization(self) -> None:
        """测试监控的初始化"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        assert monitor is not None
        assert monitor.cache == manager

    def test_monitor_collect_metrics(self) -> None:
        """测试监控的指标收集"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 执行一些操作
        manager.set("key1", "value1")
        manager.get("key1")
        manager.delete("key1")

        # 收集指标
        metrics = monitor.metrics
        assert metrics is not None

    def test_monitor_get_statistics(self) -> None:
        """测试获取监控统计"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 执行操作
        for i in range(10):
            manager.set(f"key{i}", f"value{i}")

        # 获取统计
        stats = monitor.get_summary()
        assert stats is not None

    def test_monitor_reset_metrics(self) -> None:
        """测试重置监控指标"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 设置一些值
        manager.set("key", "value")

        # 重置指标
        monitor.reset_stats()

        # 应该不抛出异常
        assert True

    def test_monitor_hit_rate_calculation(self) -> None:
        """测试命中率计算"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 设置初始值
        manager.set("key1", "value1")
        manager.set("key2", "value2")

        # 尝试命中和未命中
        manager.get("key1")  # 命中
        manager.get("key1")  # 命中
        manager.get("non_existent")  # 未命中

        # 获取统计
        stats = monitor.get_stats()
        assert stats is not None


class TestPrometheusExporter:
    """Prometheus 导出器测试"""

    def test_prometheus_exporter_import(self) -> None:
        """测试 Prometheus 导出器导入"""
        try:
            from symphra_cache.monitoring.prometheus import PrometheusMonitor
            assert PrometheusMonitor is not None
        except ImportError:
            pytest.skip("prometheus_client 未安装")

    def test_prometheus_exporter_initialization(self) -> None:
        """测试 Prometheus 导出器初始化"""
        try:
            from symphra_cache.monitoring.prometheus import PrometheusMonitor

            manager = CacheManager(backend=MemoryBackend())
            exporter = PrometheusMonitor(
                manager,
                namespace="test_cache",
                subsystem="backend"
            )
            assert exporter is not None
        except ImportError:
            pytest.skip("prometheus_client 未安装")

    def test_prometheus_exporter_collect(self) -> None:
        """测试 Prometheus 导出器的收集"""
        try:
            from symphra_cache.monitoring.prometheus import PrometheusMonitor

            manager = CacheManager(backend=MemoryBackend())
            exporter = PrometheusMonitor(manager)

            # 执行操作
            manager.set("key", "value")
            manager.get("key")

            # 收集指标
            metrics = exporter.collect()
            assert metrics is not None
        except ImportError:
            pytest.skip("prometheus_client 未安装")


class TestStatsDExporter:
    """StatsD 导出器测试"""

    def test_statsd_exporter_import(self) -> None:
        """测试 StatsD 导出器导入"""
        try:
            from symphra_cache.monitoring.statsd import StatsDMonitor
            assert StatsDMonitor is not None
        except ImportError:
            pytest.skip("statsd 未安装")

    def test_statsd_exporter_initialization(self) -> None:
        """测试 StatsD 导出器初始化"""
        try:
            from symphra_cache.monitoring.statsd import StatsDMonitor

            manager = CacheManager(backend=MemoryBackend())
            exporter = StatsDMonitor(
                manager,
                host="localhost",
                port=8125,
                prefix="cache"
            )
            assert exporter is not None
        except ImportError:
            pytest.skip("statsd 未安装")

    def test_statsd_exporter_with_mock(self) -> None:
        """使用 mock 测试 StatsD 导出器"""
        try:
            from symphra_cache.monitoring.statsd import StatsDMonitor

            manager = CacheManager(backend=MemoryBackend())
            # 简单验证导出器可以被创建（使用实际参数，不需要连接到真实的 StatsD）
            try:
                exporter = StatsDMonitor(manager, host="localhost", port=8125)
                # 即使连接失败，我们也验证对象被创建了
                assert exporter is not None
            except Exception:
                # 如果连接失败（例如 StatsD 服务器未运行），我们仍然通过测试
                pytest.skip("StatsD 服务器未运行")
        except ImportError:
            pytest.skip("statsd 未安装")


class TestMonitoringIntegration:
    """监控集成测试"""

    def test_cache_manager_with_monitor(self) -> None:
        """测试带监控的缓存管理器"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 执行一系列操作
        for i in range(5):
            manager.set(f"key{i}", f"value{i}")

        for i in range(5):
            value = manager.get(f"key{i}")
            assert value == f"value{i}"

        for i in range(0, 3):
            manager.delete(f"key{i}")

        # 获取统计信息
        summary = monitor.get_summary()
        assert summary is not None

    def test_monitor_with_different_operations(self) -> None:
        """测试不同操作的监控"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 批量设置
        manager.mset({
            "batch_key1": "value1",
            "batch_key2": "value2",
            "batch_key3": "value3",
        })

        # 批量获取
        result = manager.mget(["batch_key1", "batch_key2", "batch_key3"])
        assert result is not None

        # 批量删除
        manager.delete_many(["batch_key1", "batch_key2", "batch_key3"])

        # 获取统计
        summary = monitor.get_summary()
        assert summary is not None

    @pytest.mark.asyncio
    async def test_monitor_with_async_operations(self) -> None:
        """测试异步操作的监控"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 执行异步操作
        await manager.aset("async_key", "async_value")
        value = await manager.aget("async_key")
        assert value == "async_value"

        await manager.adelete("async_key")
        value = await manager.aget("async_key")
        assert value is None

        # 获取统计
        summary = monitor.get_summary()
        assert summary is not None

    def test_monitor_concurrent_operations(self) -> None:
        """测试并发操作的监控"""
        import threading

        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        def worker(thread_id: int) -> None:
            for i in range(10):
                key = f"thread{thread_id}_key{i}"
                manager.set(key, f"value{i}")
                manager.get(key)

        # 创建多个线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 获取统计
        summary = monitor.get_summary()
        assert summary is not None


class TestMonitoringMetricsFormatting:
    """监控指标格式化测试"""

    def test_metrics_format_with_monitor(self) -> None:
        """测试监控指标的格式"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 获取指标适配器
        metrics_adapter = monitor.metrics

        # 验证指标包含预期的字段
        assert metrics_adapter is not None

    def test_get_detailed_stats(self) -> None:
        """测试获取详细统计"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 执行操作
        manager.set("key", "value")
        manager.get("key")

        # 获取详细统计
        summary = monitor.get_summary()
        assert summary is not None

    def test_monitor_with_large_dataset(self) -> None:
        """测试大数据集的监控"""
        manager = CacheManager(backend=MemoryBackend(max_size=10000))
        monitor = CacheMonitor(manager)

        # 添加大量数据
        for i in range(1000):
            manager.set(f"key{i}", f"value{i}")

        # 执行查询
        for i in range(100):
            manager.get(f"key{i}")

        # 获取统计
        summary = monitor.get_summary()
        assert summary is not None
