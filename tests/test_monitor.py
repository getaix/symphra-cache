"""
监控模块测试

测试 CacheMonitor 和 CacheStats 功能。
"""

import time

import pytest

from symphra_cache import CacheManager, CacheMonitor, CacheStats
from symphra_cache.backends import MemoryBackend


class TestCacheStats:
    """测试 CacheStats 数据类"""

    def test_default_values(self) -> None:
        """测试默认值"""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.gets == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.errors == 0
        assert stats.total_get_time == 0.0
        assert stats.total_set_time == 0.0
        assert stats.start_time > 0
        assert stats.last_reset > 0

    def test_hit_rate(self) -> None:
        """测试命中率计算"""
        stats = CacheStats()

        # 初始状态
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 0.0

        # 有命中和未命中
        stats.hits = 7
        stats.misses = 3

        assert stats.hit_rate == 0.7
        assert stats.miss_rate == 0.3

        # 全部命中
        stats.hits = 10
        stats.misses = 0

        assert stats.hit_rate == 1.0
        assert stats.miss_rate == 0.0

    def test_avg_times(self) -> None:
        """测试平均时间计算"""
        stats = CacheStats()

        # 初始状态
        assert stats.avg_get_time == 0.0
        assert stats.avg_set_time == 0.0

        # 有操作
        stats.gets = 10
        stats.total_get_time = 0.05  # 50ms 总计

        stats.sets = 5
        stats.total_set_time = 0.01  # 10ms 总计

        assert stats.avg_get_time == 5.0  # 平均 5ms
        assert stats.avg_set_time == 2.0  # 平均 2ms

    def test_uptime(self) -> None:
        """测试运行时间"""
        stats = CacheStats()

        time.sleep(0.1)

        assert stats.uptime >= 0.1

    def test_to_dict(self) -> None:
        """测试转换为字典"""
        stats = CacheStats(
            hits=10,
            misses=5,
            gets=15,
            sets=20,
            deletes=3,
            errors=1,
        )

        result = stats.to_dict()

        assert result["hits"] == 10
        assert result["misses"] == 5
        assert result["hit_rate"] == pytest.approx(0.666, rel=0.01)
        assert result["gets"] == 15
        assert result["sets"] == 20
        assert result["deletes"] == 3
        assert result["errors"] == 1
        assert "uptime_seconds" in result
        assert "start_time" in result


class TestCacheMonitor:
    """测试 CacheMonitor 监控器"""

    def test_initialization(self) -> None:
        """测试初始化"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        assert monitor._enabled is True
        assert isinstance(monitor._stats, CacheStats)

    def test_disabled_monitor(self) -> None:
        """测试禁用监控"""
        cache = CacheManager(backend=MemoryBackend())
        original_get = cache.get

        monitor = CacheMonitor(cache, enabled=False)

        # 方法未被替换
        assert cache.get == original_get

        # 统计为零
        stats = monitor.get_stats()
        assert stats.gets == 0

    def test_get_operation_tracking(self) -> None:
        """测试 get 操作追踪"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        # 设置一些数据
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 重置统计（因为 set 也被追踪了）
        monitor.reset_stats()

        # 执行 get 操作
        cache.get("key1")  # 命中
        cache.get("key2")  # 命中
        cache.get("key3")  # 未命中

        stats = monitor.get_stats()

        assert stats.gets == 3
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == pytest.approx(0.666, rel=0.01)

    def test_set_operation_tracking(self) -> None:
        """测试 set 操作追踪"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=60)

        stats = monitor.get_stats()

        assert stats.sets == 2

    def test_delete_operation_tracking(self) -> None:
        """测试 delete 操作追踪"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        cache.set("key1", "value1")
        cache.delete("key1")
        cache.delete("key2")  # 不存在的键

        stats = monitor.get_stats()

        assert stats.deletes == 2

    def test_performance_tracking(self) -> None:
        """测试性能追踪"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        # 执行一些操作
        cache.set("key", "value")
        cache.get("key")

        stats = monitor.get_stats()

        # 应该有耗时记录
        assert stats.total_get_time > 0
        assert stats.total_set_time > 0
        assert stats.avg_get_time > 0
        assert stats.avg_set_time > 0

    def test_error_tracking(self) -> None:
        """测试错误追踪"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        # 手动注入错误
        original_get = cache._backend.get

        def failing_get(key):
            raise RuntimeError("Test error")

        cache._backend.get = failing_get

        # 尝试 get（会失败）
        with pytest.raises(RuntimeError):
            cache.get("key")

        stats = monitor.get_stats()

        # 应该记录错误
        assert stats.errors == 1

        # 恢复
        cache._backend.get = original_get

    def test_reset_stats(self) -> None:
        """测试重置统计"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        # 执行一些操作
        cache.set("key", "value")
        cache.get("key")

        stats = monitor.get_stats()
        assert stats.gets > 0
        assert stats.sets > 0

        # 重置
        monitor.reset_stats()

        stats = monitor.get_stats()
        assert stats.gets == 0
        assert stats.sets == 0
        assert stats.hits == 0
        assert stats.misses == 0

    def test_check_health(self) -> None:
        """测试健康检查"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        health = monitor.check_health()

        assert health["healthy"] is True
        assert health["backend_healthy"] is True
        assert health["test_passed"] is True
        assert "timestamp" in health

    def test_get_summary(self) -> None:
        """测试获取摘要"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        cache.set("key", "value")
        cache.get("key")

        summary = monitor.get_summary()

        assert "stats" in summary
        assert "health" in summary
        assert summary["stats"]["gets"] > 0
        assert summary["health"]["healthy"] is True

    def test_repr(self) -> None:
        """测试字符串表示"""
        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        cache.set("key", "value")
        cache.get("key")

        repr_str = repr(monitor)

        assert "CacheMonitor" in repr_str
        assert "enabled=True" in repr_str
        assert "hit_rate" in repr_str

    def test_concurrent_operations(self) -> None:
        """测试并发操作的统计正确性"""
        import threading

        cache = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(cache)

        # 预设一些数据
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        monitor.reset_stats()

        # 并发读取
        def worker():
            for i in range(100):
                cache.get(f"key{i % 10}")

        threads = [threading.Thread(target=worker) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        stats = monitor.get_stats()

        # 应该有 500 次 get 操作
        assert stats.gets == 500
        assert stats.hits == 500  # 全部命中


class TestMonitorIntegration:
    """测试监控与其他组件的集成"""

    def test_with_different_backends(self) -> None:
        """测试与不同后端的集成"""
        import tempfile
        from pathlib import Path

        from symphra_cache.backends import FileBackend

        # Memory 后端
        cache_mem = CacheManager(backend=MemoryBackend())
        monitor_mem = CacheMonitor(cache_mem)

        cache_mem.set("key", "value")
        cache_mem.get("key")

        assert monitor_mem.get_stats().gets == 1

        # File 后端
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = CacheManager(backend=FileBackend(db_path=Path(tmpdir) / "cache.db"))
            monitor_file = CacheMonitor(cache_file)

            cache_file.set("key", "value")
            cache_file.get("key")

            assert monitor_file.get_stats().gets == 1

    def test_stats_isolation(self) -> None:
        """测试不同监控器的统计隔离"""
        cache1 = CacheManager(backend=MemoryBackend())
        cache2 = CacheManager(backend=MemoryBackend())

        monitor1 = CacheMonitor(cache1)
        monitor2 = CacheMonitor(cache2)

        cache1.set("key", "value")
        cache2.set("key", "value")
        cache2.set("key2", "value2")

        stats1 = monitor1.get_stats()
        stats2 = monitor2.get_stats()

        assert stats1.sets == 1
        assert stats2.sets == 2
