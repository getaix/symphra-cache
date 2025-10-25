"""
集成测试

测试整个系统的端到端功能。
"""

import tempfile
import time
from pathlib import Path

import pytest
from symphra_cache import CacheManager, CacheMonitor
from symphra_cache.backends import FileBackend, MemoryBackend
from symphra_cache.config import CacheConfig
from symphra_cache.decorators import cache


class TestEndToEnd:
    """端到端测试"""

    def test_complete_workflow(self) -> None:
        """测试完整工作流"""
        # 1. 从配置创建管理器
        config = CacheConfig(backend="memory", options={"max_size": 1000})
        manager = CacheManager.from_config(config)

        # 2. 创建监控器
        monitor = CacheMonitor(manager)

        # 3. 执行缓存操作
        manager.set("user:1", {"name": "Alice", "age": 30})
        manager.set("user:2", {"name": "Bob", "age": 25})

        # 4. 获取数据
        user1 = manager.get("user:1")
        user2 = manager.get("user:2")

        assert user1["name"] == "Alice"
        assert user2["age"] == 25

        # 5. 检查统计
        stats = monitor.get_stats()
        assert stats.sets == 2
        assert stats.gets == 2
        assert stats.hits == 2

        # 6. 健康检查
        assert manager.check_health() is True

    def test_decorator_with_monitor(self) -> None:
        """测试装饰器与监控集成"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        @cache(manager, ttl=60)
        def expensive_function(x: int) -> int:
            time.sleep(0.1)  # 模拟耗时操作
            return x * 2

        # 第一次调用（未命中）
        result1 = expensive_function(5)
        assert result1 == 10

        # 第二次调用（命中）
        result2 = expensive_function(5)
        assert result2 == 10

        # 检查统计（注意：装饰器可能增加额外的 get/set）
        stats = monitor.get_stats()
        assert stats.gets > 0
        assert stats.sets > 0

    def test_multi_backend_workflow(self) -> None:
        """测试多后端工作流"""
        # Memory 后端
        mem_cache = CacheManager(backend=MemoryBackend())
        mem_cache.set("temp", "data")

        # File 后端
        with tempfile.TemporaryDirectory() as tmpdir:
            file_cache = CacheManager(backend=FileBackend(db_path=Path(tmpdir) / "cache.db"))
            file_cache.set("persistent", "data")

            # 验证独立性
            assert mem_cache.get("persistent") is None
            assert file_cache.get("temp") is None

            # 验证持久化
            file_value = file_cache.get("persistent")
            assert file_value == "data"


class TestConcurrency:
    """并发测试"""

    def test_concurrent_reads(self) -> None:
        """测试并发读取"""
        import threading

        manager = CacheManager(backend=MemoryBackend())

        # 预设数据
        for i in range(100):
            manager.set(f"key{i}", f"value{i}")

        results = []
        errors = []

        def read_worker():
            try:
                for i in range(100):
                    value = manager.get(f"key{i}")
                    results.append(value)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_worker) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 不应该有错误
        assert len(errors) == 0

        # 应该有 1000 次成功读取
        assert len(results) == 1000

    def test_concurrent_writes(self) -> None:
        """测试并发写入"""
        import threading

        manager = CacheManager(backend=MemoryBackend(max_size=10000))

        errors = []

        def write_worker(worker_id):
            try:
                for i in range(100):
                    manager.set(f"key_{worker_id}_{i}", f"value_{worker_id}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 不应该有错误
        assert len(errors) == 0


class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    def test_backend_failure_recovery(self) -> None:
        """测试后端故障恢复"""
        manager = CacheManager(backend=MemoryBackend())

        # 正常操作
        manager.set("key", "value")
        assert manager.get("key") == "value"

        # 模拟后端故障
        original_get = manager._backend.get

        def failing_get(key):
            raise RuntimeError("Backend failure")

        manager._backend.get = failing_get

        # 应该抛出异常
        with pytest.raises(RuntimeError):
            manager.get("key")

        # 恢复后端
        manager._backend.get = original_get

        # 应该恢复正常
        assert manager.get("key") == "value"

    def test_monitor_with_errors(self) -> None:
        """测试监控器记录错误"""
        manager = CacheManager(backend=MemoryBackend())
        monitor = CacheMonitor(manager)

        # 注入失败的操作
        original_get = manager._backend.get

        def failing_get(key):
            raise RuntimeError("Test error")

        manager._backend.get = failing_get

        # 尝试获取（应该失败）
        with pytest.raises(RuntimeError):
            manager.get("key")

        # 检查错误统计
        stats = monitor.get_stats()
        assert stats.errors > 0

        # 恢复
        manager._backend.get = original_get


class TestPersistenceIntegration:
    """持久化集成测试"""

    def test_file_backend_persistence(self) -> None:
        """测试文件后端持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cache.db"

            # 第一个管理器实例
            cache1 = CacheManager(backend=FileBackend(db_path=db_path))
            cache1.set("persistent_key", "persistent_value")
            cache1.close()

            # 第二个管理器实例（重新打开数据库）
            cache2 = CacheManager(backend=FileBackend(db_path=db_path))
            value = cache2.get("persistent_key")

            assert value == "persistent_value"
            cache2.close()


class TestConfigurationIntegration:
    """配置集成测试"""

    def test_yaml_config_integration(self) -> None:
        """测试 YAML 配置集成"""
        import yaml

        config_data = {
            "backend": "memory",
            "options": {"max_size": 5000, "cleanup_interval": 120},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # 从文件加载配置
            manager = CacheManager.from_file(config_path)

            # 验证后端类型
            assert isinstance(manager.backend, MemoryBackend)

            # 验证配置生效
            assert manager.backend._max_size == 5000
            assert manager.backend._cleanup_interval == 120

            # 验证功能正常
            manager.set("key", "value")
            assert manager.get("key") == "value"

        finally:
            Path(config_path).unlink()


@pytest.mark.asyncio
class TestAsyncIntegration:
    """异步集成测试"""

    async def test_async_workflow(self) -> None:
        """测试异步工作流"""
        manager = CacheManager(backend=MemoryBackend())

        # 异步设置
        await manager.aset("user:1", {"name": "Alice"})
        await manager.aset("user:2", {"name": "Bob"})

        # 异步获取
        user1 = await manager.aget("user:1")
        user2 = await manager.aget("user:2")

        assert user1["name"] == "Alice"
        assert user2["name"] == "Bob"

        # 异步批量操作
        data = {f"key{i}": f"value{i}" for i in range(10)}
        await manager.aset_many(data)

        result = await manager.aget_many(list(data.keys()))
        assert len(result) == 10

    async def test_async_health_check(self) -> None:
        """测试异步健康检查"""
        manager = CacheManager(backend=MemoryBackend())

        is_healthy = await manager.acheck_health()
        assert is_healthy is True
