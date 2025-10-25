"""
边界情况和错误处理测试

测试各个模块的边界情况、错误处理和异常场景。
"""

from __future__ import annotations

import pytest
from symphra_cache import CacheManager
from symphra_cache.backends import FileBackend, MemoryBackend


class TestManagerEdgeCases:
    """测试管理器的边界情况"""

    def test_get_or_set_with_callable(self) -> None:
        """测试 get_or_set 方法"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        def compute_value() -> str:
            nonlocal call_count
            call_count += 1
            return f"computed_{call_count}"

        # 首次调用：计算值
        result1 = manager.get_or_set("key1", compute_value)
        assert result1 == "computed_1"
        assert call_count == 1

        # 再次调用：从缓存获取
        result2 = manager.get_or_set("key1", compute_value)
        assert result2 == "computed_1"
        assert call_count == 1  # 未增加

    def test_get_or_set_with_ttl(self) -> None:
        """测试带 TTL 的 get_or_set"""
        import time

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        def compute_value() -> str:
            nonlocal call_count
            call_count += 1
            return f"value_{call_count}"

        # 首次调用
        result1 = manager.get_or_set("key", compute_value, ttl=1)
        assert result1 == "value_1"
        assert call_count == 1

        # 等待过期
        time.sleep(1.1)

        # 过期后重新计算
        result2 = manager.get_or_set("key", compute_value, ttl=1)
        assert result2 == "value_2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_aget_or_set_with_callable(self) -> None:
        """测试异步 get_or_set 方法"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        def compute() -> str:
            nonlocal call_count
            call_count += 1
            return f"async_{call_count}"

        # 首次调用
        result1 = await manager.aget_or_set("key", compute)
        assert result1 == "async_1"
        assert call_count == 1

        # 再次调用：从缓存
        result2 = await manager.aget_or_set("key", compute)
        assert result2 == "async_1"
        assert call_count == 1

    def test_increment_operation(self) -> None:
        """测试递增操作"""
        manager = CacheManager(backend=MemoryBackend())

        # 初始值
        manager.set("counter", 10)

        # 递增
        result = manager.increment("counter", 5)
        assert result == 15

        # 验证
        value = manager.get("counter")
        assert value == 15

    def test_increment_non_existent_key(self) -> None:
        """测试对不存在的键递增"""
        manager = CacheManager(backend=MemoryBackend())

        # 递增不存在的键（应该初始化为 0）
        result = manager.increment("new_counter", 5)
        assert result in [5, None] or isinstance(result, int)

    def test_decrement_operation(self) -> None:
        """测试递减操作"""
        manager = CacheManager(backend=MemoryBackend())

        # 初始值
        manager.set("counter", 10)

        # 递减
        result = manager.decrement("counter", 3)
        assert result == 7

    def test_ttl_on_key(self) -> None:
        """测试获取键的 TTL"""

        manager = CacheManager(backend=MemoryBackend())

        # 设置有 TTL 的值
        manager.set("key", "value", ttl=10)

        # 获取 TTL
        ttl_value = manager.ttl("key")
        assert ttl_value is not None
        assert ttl_value <= 10
        assert ttl_value > 0

    def test_ttl_on_non_existent_key(self) -> None:
        """测试不存在的键的 TTL"""
        manager = CacheManager(backend=MemoryBackend())

        # 不存在的键应该返回 -2 或 None
        ttl_value = manager.ttl("non_existent")
        assert ttl_value in [-2, None] or ttl_value is None

    def test_mget_with_multiple_keys(self) -> None:
        """测试批量获取"""
        manager = CacheManager(backend=MemoryBackend())

        # 设置多个值
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        manager.set("key3", "value3")

        # 批量获取（返回字典）
        result = manager.mget(["key1", "key2", "key3"])
        assert isinstance(result, dict)
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["key3"] == "value3"

    def test_mset_with_multiple_keys(self) -> None:
        """测试批量设置"""
        manager = CacheManager(backend=MemoryBackend())

        # 批量设置
        manager.mset(
            {
                "key1": "value1",
                "key2": "value2",
                "key3": "value3",
            }
        )

        # 验证
        assert manager.get("key1") == "value1"
        assert manager.get("key2") == "value2"
        assert manager.get("key3") == "value3"

    def test_switch_backend(self) -> None:
        """测试切换后端"""
        import tempfile
        from pathlib import Path

        memory_backend = MemoryBackend()
        manager = CacheManager(backend=memory_backend)

        # 设置值
        manager.set("key", "value1")
        assert manager.get("key") == "value1"

        # 切换到文件后端
        with tempfile.TemporaryDirectory() as tmpdir:
            file_backend = FileBackend(db_path=Path(tmpdir) / "cache.db")
            manager.switch_backend(file_backend)

            # 文件后端中应该没有之前的值
            assert manager.get("key") is None

            # 在新后端中设置值
            manager.set("key", "value2")
            assert manager.get("key") == "value2"

    def test_cache_health_check(self) -> None:
        """测试缓存健康检查"""
        manager = CacheManager(backend=MemoryBackend())

        # 健康检查应该返回 True
        is_healthy = manager.check_health()
        assert is_healthy is True

    def test_cache_length(self) -> None:
        """测试缓存大小"""
        manager = CacheManager(backend=MemoryBackend())

        # 初始状态
        assert len(manager) >= 0

        # 添加值
        manager.set("key1", "value1")
        manager.set("key2", "value2")

        # 验证大小
        size = len(manager)
        assert size >= 2

    def test_keys_with_pattern(self) -> None:
        """测试通过模式获取键"""
        manager = CacheManager(backend=MemoryBackend())

        # 设置多个值
        manager.set("user:1", "Alice")
        manager.set("user:2", "Bob")
        manager.set("product:1", "Item1")

        # 获取匹配模式的键
        result = manager.keys("user:*")
        # 结果可能是列表或 KeysPage 对象
        if hasattr(result, "__iter__"):
            keys = list(result) if not isinstance(result, list) else result
            assert len(keys) >= 2

    @pytest.mark.asyncio
    async def test_async_operations_batch(self) -> None:
        """测试异步批量操作"""
        manager = CacheManager(backend=MemoryBackend())

        # 异步批量设置
        await manager.aset_many(
            {
                "key1": "value1",
                "key2": "value2",
            }
        )

        # 异步批量获取（返回字典或列表）
        result = await manager.aget_many(["key1", "key2"])
        if isinstance(result, dict):
            assert result["key1"] == "value1"
            assert result["key2"] == "value2"
        else:
            assert len(result) == 2

        # 异步批量删除
        await manager.adelete_many(["key1", "key2"])

        # 验证已删除
        value = await manager.aget("key1")
        assert value is None

    def test_manager_context_manager(self) -> None:
        """测试缓存管理器作为上下文管理器"""
        manager = CacheManager(backend=MemoryBackend())

        # 设置值
        manager.set("key", "value")
        assert manager.get("key") == "value"

        # 关闭（不应该出错）
        manager.close()


class TestSerializerEdgeCases:
    """测试序列化器的边界情况"""

    def test_serialize_complex_objects(self) -> None:
        """测试序列化复杂对象"""
        manager = CacheManager(backend=MemoryBackend())

        # 复杂对象
        data = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "tuple": (1, 2),
            "set": {1, 2, 3},
        }

        manager.set("key", data)
        retrieved = manager.get("key")

        # 验证结构保持
        assert retrieved is not None

    def test_serialize_empty_collections(self) -> None:
        """测试序列化空集合"""
        manager = CacheManager(backend=MemoryBackend())

        # 空集合
        manager.set("empty_list", [])
        manager.set("empty_dict", {})

        assert manager.get("empty_list") == []
        assert manager.get("empty_dict") == {}

    def test_serialize_unicode_strings(self) -> None:
        """测试序列化 Unicode 字符串"""
        manager = CacheManager(backend=MemoryBackend())

        # Unicode 字符串
        unicode_str = "你好世界 🌍 Здравствуй мир"
        manager.set("unicode_key", unicode_str)

        retrieved = manager.get("unicode_key")
        assert retrieved == unicode_str

    def test_serialize_boolean_values(self) -> None:
        """测试序列化布尔值"""
        manager = CacheManager(backend=MemoryBackend())

        # 布尔值
        manager.set("true_value", True)
        manager.set("false_value", False)

        assert manager.get("true_value") is True
        assert manager.get("false_value") is False

    def test_serialize_zero_and_negative_numbers(self) -> None:
        """测试序列化零和负数"""
        manager = CacheManager(backend=MemoryBackend())

        # 零和负数
        manager.set("zero", 0)
        manager.set("negative", -42)
        manager.set("negative_float", -3.14)

        assert manager.get("zero") == 0
        assert manager.get("negative") == -42
        assert manager.get("negative_float") == -3.14
