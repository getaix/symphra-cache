"""
内存后端单元测试

测试 MemoryBackend 的所有功能：
- 基础 CRUD 操作
- TTL 过期验证
- LRU 淘汰验证
- 异步操作
- 批量操作
- 线程安全性
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from symphra_cache.backends.memory import MemoryBackend


class TestMemoryBackendBasics:
    """测试基础功能"""

    def test_set_and_get(self) -> None:
        """测试基础 set/get 操作"""
        backend = MemoryBackend()

        # 设置并获取
        backend.set("key1", "value1")
        assert backend.get("key1") == "value1"

        # 不存在的键返回 None
        assert backend.get("nonexistent") is None

    def test_set_with_different_types(self) -> None:
        """测试不同类型的值"""
        backend = MemoryBackend()

        # 字符串
        backend.set("str", "hello")
        assert backend.get("str") == "hello"

        # 数字
        backend.set("int", 123)
        assert backend.get("int") == 123

        # 字典
        backend.set("dict", {"name": "Alice", "age": 30})
        assert backend.get("dict") == {"name": "Alice", "age": 30}

        # 列表
        backend.set("list", [1, 2, 3])
        assert backend.get("list") == [1, 2, 3]

    def test_update_existing_key(self) -> None:
        """测试更新已存在的键"""
        backend = MemoryBackend()

        backend.set("key", "value1")
        assert backend.get("key") == "value1"

        # 更新值
        backend.set("key", "value2")
        assert backend.get("key") == "value2"

    def test_delete(self) -> None:
        """测试删除操作"""
        backend = MemoryBackend()

        backend.set("key", "value")
        assert backend.delete("key") is True
        assert backend.get("key") is None

        # 删除不存在的键返回 False
        assert backend.delete("nonexistent") is False

    def test_exists(self) -> None:
        """测试 exists 方法"""
        backend = MemoryBackend()

        # 键不存在
        assert backend.exists("key") is False

        # 设置后存在
        backend.set("key", "value")
        assert backend.exists("key") is True

        # 删除后不存在
        backend.delete("key")
        assert backend.exists("key") is False

    def test_clear(self) -> None:
        """测试清空所有缓存"""
        backend = MemoryBackend()

        # 添加多个键
        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")

        # 清空
        backend.clear()

        # 验证所有键都已删除
        assert backend.get("key1") is None
        assert backend.get("key2") is None
        assert backend.get("key3") is None
        assert len(backend) == 0


class TestMemoryBackendTTL:
    """测试 TTL 过期功能"""

    def test_ttl_expiration(self) -> None:
        """测试 TTL 过期"""
        backend = MemoryBackend()

        # 设置 1 秒过期
        backend.set("key", "value", ttl=1)
        assert backend.get("key") == "value"

        # 等待过期
        time.sleep(1.1)
        assert backend.get("key") is None

    def test_no_ttl(self) -> None:
        """测试无 TTL（永不过期）"""
        backend = MemoryBackend()

        backend.set("key", "value")  # 不设置 TTL
        time.sleep(0.5)
        assert backend.get("key") == "value"

    def test_ttl_update(self) -> None:
        """测试更新 TTL"""
        backend = MemoryBackend()

        # 设置 1 秒过期
        backend.set("key", "value1", ttl=1)

        # 更新为 5 秒过期
        backend.set("key", "value2", ttl=5)

        # 等待原本的 TTL 时间
        time.sleep(1.1)

        # 键仍然存在（因为更新了 TTL）
        assert backend.get("key") == "value2"

    def test_exists_with_expired_key(self) -> None:
        """测试 exists 对过期键返回 False"""
        backend = MemoryBackend()

        backend.set("key", "value", ttl=1)
        assert backend.exists("key") is True

        time.sleep(1.1)
        assert backend.exists("key") is False


class TestMemoryBackendLRU:
    """测试 LRU 淘汰策略"""

    def test_lru_eviction(self) -> None:
        """测试 LRU 淘汰"""
        backend = MemoryBackend(max_size=3)

        # 填满缓存
        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")

        # 添加第 4 个键，应淘汰 key1（最旧的）
        backend.set("key4", "value4")

        assert backend.get("key1") is None  # 被淘汰
        assert backend.get("key2") == "value2"
        assert backend.get("key3") == "value3"
        assert backend.get("key4") == "value4"

    def test_lru_access_updates_order(self) -> None:
        """测试访问更新 LRU 顺序"""
        backend = MemoryBackend(max_size=3)

        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")

        # 访问 key1，使其成为最近使用
        backend.get("key1")

        # 添加 key4，应淘汰 key2（现在是最旧的）
        backend.set("key4", "value4")

        assert backend.get("key1") == "value1"  # 未被淘汰
        assert backend.get("key2") is None  # 被淘汰
        assert backend.get("key3") == "value3"
        assert backend.get("key4") == "value4"

    def test_update_does_not_trigger_eviction(self) -> None:
        """测试更新已存在的键不触发淘汰"""
        backend = MemoryBackend(max_size=2)

        backend.set("key1", "value1")
        backend.set("key2", "value2")

        # 更新 key1（不增加新键）
        backend.set("key1", "new_value1")

        # 不应触发淘汰
        assert backend.get("key1") == "new_value1"
        assert backend.get("key2") == "value2"


class TestMemoryBackendAsync:
    """测试异步操作"""

    @pytest.mark.asyncio
    async def test_async_get_set(self) -> None:
        """测试异步 get/set"""
        backend = MemoryBackend()

        await backend.aset("key", "value")
        assert await backend.aget("key") == "value"

    @pytest.mark.asyncio
    async def test_async_delete(self) -> None:
        """测试异步删除"""
        backend = MemoryBackend()

        await backend.aset("key", "value")
        assert await backend.adelete("key") is True
        assert await backend.aget("key") is None

    @pytest.mark.asyncio
    async def test_async_with_ttl(self) -> None:
        """测试异步操作的 TTL"""
        backend = MemoryBackend()

        await backend.aset("key", "value", ttl=1)
        assert await backend.aget("key") == "value"

        await asyncio.sleep(1.1)
        assert await backend.aget("key") is None


class TestMemoryBackendBatchOperations:
    """测试批量操作"""

    def test_get_many(self) -> None:
        """测试批量获取"""
        backend = MemoryBackend()

        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")

        results = backend.get_many(["key1", "key2", "key4"])

        assert results == {
            "key1": "value1",
            "key2": "value2",
            # key4 不存在，不包含在结果中
        }

    def test_set_many(self) -> None:
        """测试批量设置"""
        backend = MemoryBackend()

        backend.set_many(
            {
                "key1": "value1",
                "key2": "value2",
                "key3": "value3",
            }
        )

        assert backend.get("key1") == "value1"
        assert backend.get("key2") == "value2"
        assert backend.get("key3") == "value3"

    def test_set_many_with_ttl(self) -> None:
        """测试批量设置带 TTL"""
        backend = MemoryBackend()

        backend.set_many({"key1": "value1", "key2": "value2"}, ttl=1)

        assert backend.get("key1") == "value1"
        assert backend.get("key2") == "value2"

        time.sleep(1.1)

        assert backend.get("key1") is None
        assert backend.get("key2") is None

    def test_delete_many(self) -> None:
        """测试批量删除"""
        backend = MemoryBackend()

        backend.set("key1", "value1")
        backend.set("key2", "value2")
        backend.set("key3", "value3")

        count = backend.delete_many(["key1", "key2", "key4"])

        assert count == 2  # key1 和 key2 成功删除
        assert backend.get("key1") is None
        assert backend.get("key2") is None
        assert backend.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_async_get_many(self) -> None:
        """测试异步批量获取"""
        backend = MemoryBackend()

        await backend.aset_many({"key1": "value1", "key2": "value2"})

        results = await backend.aget_many(["key1", "key2"])

        assert results == {"key1": "value1", "key2": "value2"}


class TestMemoryBackendThreadSafety:
    """测试线程安全性"""

    def test_concurrent_writes(self) -> None:
        """测试并发写入"""
        backend = MemoryBackend()
        iterations = 1000

        def writer(key_prefix: str) -> None:
            for i in range(iterations):
                backend.set(f"{key_prefix}:{i}", i)

        # 启动多个线程同时写入
        threads = [threading.Thread(target=writer, args=(f"thread{i}",)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 验证所有数据都写入成功
        for i in range(5):
            for j in range(iterations):
                assert backend.get(f"thread{i}:{j}") == j

    def test_concurrent_read_write(self) -> None:
        """测试并发读写"""
        backend = MemoryBackend()
        backend.set("shared", 0)

        def reader() -> None:
            for _ in range(100):
                backend.get("shared")

        def writer() -> None:
            for i in range(100):
                backend.set("shared", i)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        threads += [threading.Thread(target=writer) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 无异常即通过


class TestMemoryBackendEdgeCases:
    """测试边界条件"""

    def test_zero_max_size(self) -> None:
        """测试最大容量为 0"""
        backend = MemoryBackend(max_size=0)

        # 设置会立即淘汰
        backend.set("key", "value")
        assert backend.get("key") is None

    def test_len_method(self) -> None:
        """测试 len() 方法"""
        backend = MemoryBackend()

        assert len(backend) == 0

        backend.set("key1", "value1")
        assert len(backend) == 1

        backend.set("key2", "value2")
        assert len(backend) == 2

        backend.delete("key1")
        assert len(backend) == 1

    def test_repr_method(self) -> None:
        """测试 repr() 方法"""
        backend = MemoryBackend(max_size=100)

        backend.set("key1", "value1")
        backend.set("key2", "value2")

        repr_str = repr(backend)
        assert "MemoryBackend" in repr_str
        assert "size=2" in repr_str
        assert "max_size=100" in repr_str

    def test_background_cleanup(self) -> None:
        """测试后台清理任务"""
        backend = MemoryBackend(cleanup_interval=1)

        # 设置多个过期键
        for i in range(10):
            backend.set(f"key{i}", f"value{i}", ttl=1)

        # 验证键存在
        assert len(backend) == 10

        # 等待后台清理
        time.sleep(2)

        # 验证键已被清理
        assert len(backend) == 0
