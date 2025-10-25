"""
CacheManager 测试

测试缓存管理器的核心功能。
"""

import tempfile
from pathlib import Path

import pytest
from symphra_cache import CacheManager
from symphra_cache.backends import FileBackend, MemoryBackend
from symphra_cache.config import CacheConfig


class TestCacheManagerBasics:
    """测试 CacheManager 基础功能"""

    def test_initialization_with_backend(self) -> None:
        """测试通过后端实例初始化"""
        backend = MemoryBackend()
        manager = CacheManager(backend=backend)

        assert manager.backend == backend

    def test_initialization_from_config_dict(self) -> None:
        """测试通过配置字典初始化"""
        manager = CacheManager.from_config({"backend": "memory", "options": {}})

        assert isinstance(manager.backend, MemoryBackend)

    def test_initialization_from_config_object(self) -> None:
        """测试通过配置对象初始化"""
        config = CacheConfig(backend="memory", options={})
        manager = CacheManager.from_config(config)

        assert isinstance(manager.backend, MemoryBackend)

    def test_initialization_from_file(self) -> None:
        """测试从配置文件初始化"""
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"backend": "memory", "options": {"max_size": 1000}}, f)
            config_path = f.name

        try:
            manager = CacheManager.from_file(config_path)
            assert isinstance(manager.backend, MemoryBackend)
        finally:
            Path(config_path).unlink()

    def test_get_set_delete(self) -> None:
        """测试基础操作"""
        manager = CacheManager(backend=MemoryBackend())

        # Set
        result = manager.set("key", "value")
        assert result is True

        # Get
        value = manager.get("key")
        assert value == "value"

        # Delete
        result = manager.delete("key")
        assert result is True

        # Get after delete
        value = manager.get("key")
        assert value is None

    def test_exists(self) -> None:
        """测试键存在性检查"""
        manager = CacheManager(backend=MemoryBackend())

        assert manager.exists("key") is False

        manager.set("key", "value")
        assert manager.exists("key") is True

        manager.delete("key")
        assert manager.exists("key") is False

    def test_clear(self) -> None:
        """测试清空缓存"""
        manager = CacheManager(backend=MemoryBackend())

        manager.set("key1", "value1")
        manager.set("key2", "value2")

        manager.clear()

        assert manager.get("key1") is None
        assert manager.get("key2") is None

    def test_ttl_expiration(self) -> None:
        """测试 TTL 过期"""
        import time

        manager = CacheManager(backend=MemoryBackend())

        manager.set("key", "value", ttl=1)

        # 立即获取应该成功
        assert manager.get("key") == "value"

        # 等待过期
        time.sleep(1.1)

        assert manager.get("key") is None

    def test_nx_flag(self) -> None:
        """测试 NX (仅当不存在时设置) 标志"""
        manager = CacheManager(backend=MemoryBackend())

        # 第一次设置应该成功
        result = manager.set("key", "value1", nx=True)
        assert result is True
        assert manager.get("key") == "value1"

        # 第二次设置应该失败(键已存在)
        result = manager.set("key", "value2", nx=True)
        assert result is False
        assert manager.get("key") == "value1"  # 值未改变


class TestCacheManagerBatchOperations:
    """测试批量操作"""

    def test_get_many(self) -> None:
        """测试批量获取"""
        manager = CacheManager(backend=MemoryBackend())

        manager.set("key1", "value1")
        manager.set("key2", "value2")
        manager.set("key3", "value3")

        result = manager.get_many(["key1", "key2", "key4"])

        assert result == {"key1": "value1", "key2": "value2"}

    def test_set_many(self) -> None:
        """测试批量设置"""
        manager = CacheManager(backend=MemoryBackend())

        manager.set_many({"key1": "value1", "key2": "value2", "key3": "value3"})

        assert manager.get("key1") == "value1"
        assert manager.get("key2") == "value2"
        assert manager.get("key3") == "value3"

    def test_set_many_with_ttl(self) -> None:
        """测试批量设置带 TTL"""
        import time

        manager = CacheManager(backend=MemoryBackend())

        manager.set_many({"key1": "value1", "key2": "value2"}, ttl=1)

        assert manager.get("key1") == "value1"

        time.sleep(1.1)

        assert manager.get("key1") is None
        assert manager.get("key2") is None

    def test_delete_many(self) -> None:
        """测试批量删除"""
        manager = CacheManager(backend=MemoryBackend())

        manager.set("key1", "value1")
        manager.set("key2", "value2")
        manager.set("key3", "value3")

        count = manager.delete_many(["key1", "key2", "key4"])

        assert count == 2  # key1 和 key2 被删除
        assert manager.get("key1") is None
        assert manager.get("key2") is None
        assert manager.get("key3") == "value3"


class TestCacheManagerAsyncOperations:
    """测试异步操作"""

    @pytest.mark.asyncio
    async def test_async_get_set(self) -> None:
        """测试异步 get 和 set"""
        manager = CacheManager(backend=MemoryBackend())

        await manager.aset("key", "value")
        value = await manager.aget("key")

        assert value == "value"

    @pytest.mark.asyncio
    async def test_async_delete(self) -> None:
        """测试异步删除"""
        manager = CacheManager(backend=MemoryBackend())

        await manager.aset("key", "value")
        result = await manager.adelete("key")

        assert result is True

        value = await manager.aget("key")
        assert value is None

    @pytest.mark.asyncio
    async def test_async_get_many(self) -> None:
        """测试异步批量获取"""
        manager = CacheManager(backend=MemoryBackend())

        await manager.aset("key1", "value1")
        await manager.aset("key2", "value2")

        result = await manager.aget_many(["key1", "key2", "key3"])

        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.asyncio
    async def test_async_set_many(self) -> None:
        """测试异步批量设置"""
        manager = CacheManager(backend=MemoryBackend())

        await manager.aset_many({"key1": "value1", "key2": "value2"})

        value1 = await manager.aget("key1")
        value2 = await manager.aget("key2")

        assert value1 == "value1"
        assert value2 == "value2"

    @pytest.mark.asyncio
    async def test_async_delete_many(self) -> None:
        """测试异步批量删除"""
        manager = CacheManager(backend=MemoryBackend())

        await manager.aset("key1", "value1")
        await manager.aset("key2", "value2")

        count = await manager.adelete_many(["key1", "key2"])

        assert count == 2


class TestCacheManagerExtendedMethods:
    """测试扩展方法"""

    def test_keys_scanning(self) -> None:
        """测试键扫描"""
        manager = CacheManager(backend=MemoryBackend())

        manager.set("user:1", "data1")
        manager.set("user:2", "data2")
        manager.set("product:1", "data3")

        page = manager.keys(pattern="user:*")

        assert "user:1" in page.keys
        assert "user:2" in page.keys
        assert "product:1" not in page.keys

    def test_ttl_method(self) -> None:
        """测试 TTL 查询"""
        manager = CacheManager(backend=MemoryBackend())

        manager.set("key", "value", ttl=60)

        ttl = manager.ttl("key")

        assert ttl > 0
        assert ttl <= 60

    def test_close(self) -> None:
        """测试关闭连接"""
        manager = CacheManager(backend=MemoryBackend())

        # 应该不抛出异常
        manager.close()

    def test_check_health(self) -> None:
        """测试健康检查"""
        manager = CacheManager(backend=MemoryBackend())

        is_healthy = manager.check_health()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_async_check_health(self) -> None:
        """测试异步健康检查"""
        manager = CacheManager(backend=MemoryBackend())

        is_healthy = await manager.acheck_health()

        assert is_healthy is True


class TestCacheManagerWithDifferentBackends:
    """测试不同后端"""

    def test_file_backend(self) -> None:
        """测试文件后端"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")
            manager = CacheManager(backend=backend)

            manager.set("key", "value")
            value = manager.get("key")

            assert value == "value"

    def test_backend_property(self) -> None:
        """测试 backend 属性访问"""
        backend = MemoryBackend()
        manager = CacheManager(backend=backend)

        assert manager.backend is backend


class TestCacheManagerErrorHandling:
    """测试错误处理"""

    def test_invalid_config(self) -> None:
        """测试无效配置"""
        with pytest.raises((ValueError, TypeError)):  # 配置验证错误
            CacheManager.from_config({"backend": "invalid_backend"})

    def test_repr(self) -> None:
        """测试字符串表示"""
        manager = CacheManager(backend=MemoryBackend())

        repr_str = repr(manager)

        # 应该包含类名
        assert "CacheManager" in repr_str or "symphra_cache" in repr_str
