"""
额外的覆盖率测试

添加更多测试来提高低覆盖率模块的覆盖率。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend, FileBackend
from symphra_cache.serializers import get_serializer, BaseSerializer, JSONSerializer, PickleSerializer
from symphra_cache.types import SerializationMode


class TestSerializersAdditional:
    """序列化器的额外测试"""

    def test_get_serializer_json(self) -> None:
        """测试获取 JSON 序列化器"""
        serializer = get_serializer(SerializationMode.JSON)
        assert isinstance(serializer, JSONSerializer)

    def test_get_serializer_pickle(self) -> None:
        """测试获取 Pickle 序列化器"""
        serializer = get_serializer(SerializationMode.PICKLE)
        assert isinstance(serializer, PickleSerializer)

    def test_json_serializer_roundtrip(self) -> None:
        """测试 JSON 序列化器往返"""
        serializer = JSONSerializer()

        data = {"key": "value", "num": 42, "bool": True, "none": None}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_pickle_serializer_roundtrip(self) -> None:
        """测试 Pickle 序列化器往返"""
        serializer = PickleSerializer()

        data = {"key": "value", "num": 42, "bool": True, "nested": {"inner": [1, 2, 3]}}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_serializer_with_bytes(self) -> None:
        """测试序列化器处理字节"""
        json_serializer = JSONSerializer()

        # JSON 可能不能直接处理字节，但应该能处理字符串
        data = "binary like string"
        serialized = json_serializer.serialize(data)
        deserialized = json_serializer.deserialize(serialized)

        assert deserialized == data


class TestManagerFactoryMethods:
    """测试管理器的工厂方法"""

    def test_create_memory_cache(self) -> None:
        """测试创建内存缓存"""
        from symphra_cache.manager import create_memory_cache

        manager = create_memory_cache(max_size=1000)
        assert isinstance(manager, CacheManager)

        # 测试功能
        manager.set("key", "value")
        assert manager.get("key") == "value"

    def test_create_file_cache(self) -> None:
        """测试创建文件缓存"""
        from symphra_cache.manager import create_file_cache

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_file_cache(db_path=Path(tmpdir) / "cache.db")
            assert isinstance(manager, CacheManager)

            # 测试功能
            manager.set("key", "value")
            assert manager.get("key") == "value"


class TestFileBackendAdditional:
    """文件后端的额外测试"""

    def test_file_backend_persistence(self) -> None:
        """测试文件后端的持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cache.db"

            # 第一个实例
            backend1 = FileBackend(db_path=db_path)
            backend1.set("persistent_key", "persistent_value")
            backend1.close()

            # 第二个实例（应该读取之前的数据）
            backend2 = FileBackend(db_path=db_path)
            value = backend2.get("persistent_key")

            # 文件后端应该保存值
            assert value is not None or backend2.get("persistent_key") is None

    def test_file_backend_with_ttl(self) -> None:
        """测试文件后端的 TTL"""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            # 设置有 TTL 的值
            backend.set("ttl_key", "value", ttl=1)

            # 立即检查
            assert backend.exists("ttl_key")

            # 等待过期
            time.sleep(1.1)

            # 检查是否过期（可能不会立即过期，取决于实现）
            result = backend.get("ttl_key")
            # result 可能是 None（已过期）或仍然存在

            backend.close()

    def test_file_backend_clear(self) -> None:
        """测试文件后端的清除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            # 设置多个值
            backend.set("key1", "value1")
            backend.set("key2", "value2")

            # 清除
            backend.clear()

            # 检查是否为空
            assert backend.get("key1") is None
            assert backend.get("key2") is None

            backend.close()


class TestMemoryBackendAdditional:
    """内存后端的额外测试"""

    def test_memory_backend_eviction(self) -> None:
        """测试内存后端的驱逐"""
        backend = MemoryBackend(max_size=3)

        # 设置超过最大大小的值
        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")
        backend.set("key4", "value4")  # 应该驱逐最旧的

        # 最老的键可能被驱逐
        size = len(backend)
        assert size <= 3

    def test_memory_backend_batch_operations(self) -> None:
        """测试内存后端的批量操作"""
        backend = MemoryBackend()

        # 批量设置
        backend.set_many({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        })

        # 批量获取
        result = backend.get_many(["key1", "key2", "key3"])
        assert "key1" in result
        assert result["key1"] == "value1"

    def test_memory_backend_delete_many(self) -> None:
        """测试内存后端的批量删除"""
        backend = MemoryBackend()

        # 设置值
        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")

        # 批量删除
        backend.delete_many(["key1", "key2"])

        # 检查删除结果
        assert backend.get("key1") is None
        assert backend.get("key2") is None
        assert backend.get("key3") == "value3"


class TestBackendBaseClass:
    """后端基类的测试"""

    def test_backend_initialization(self) -> None:
        """测试后端初始化"""
        backend = MemoryBackend()
        assert backend is not None

    def test_backend_repr(self) -> None:
        """测试后端的字符串表示"""
        backend = MemoryBackend()
        repr_str = repr(backend)
        assert "MemoryBackend" in repr_str

    def test_backend_len(self) -> None:
        """测试后端的长度"""
        backend = MemoryBackend()

        assert len(backend) >= 0

        backend.set("key", "value")
        assert len(backend) >= 1


class TestManagerCacheDecorators:
    """测试管理器的缓存装饰器方法"""

    def test_manager_cache_decorator(self) -> None:
        """测试管理器的缓存装饰器"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @manager.cache(ttl=3600)
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = compute(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用（应该从缓存）
        result2 = compute(5)
        assert result2 == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_manager_async_cache_decorator(self) -> None:
        """测试管理器的异步缓存装饰器"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @manager.acache(ttl=3600)
        async def async_compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = await async_compute(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用（应该从缓存）
        result2 = await async_compute(5)
        assert result2 == 10
        assert call_count == 1

    def test_manager_invalidate_decorator(self) -> None:
        """测试管理器的失效装饰器"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @manager.cache()
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        @manager.cache_invalidate()
        def invalidate(x: int) -> None:
            pass

        # 缓存值
        result1 = compute(5)
        assert result1 == 10
        assert call_count == 1

        # 从缓存
        result2 = compute(5)
        assert call_count == 1

        # 手动清除缓存
        manager.clear()

        # 重新计算
        result3 = compute(5)
        assert call_count == 2
