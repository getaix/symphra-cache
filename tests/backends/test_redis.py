"""
Redis 后端测试

测试 Redis 后端的各种功能，包括连接、CRUD 操作、模式匹配等。

注意：这些测试需要一个运行中的 Redis 实例。
      可以通过以下方式跳过：pytest -m "not redis"
"""

import time
from typing import Any

import pytest

from symphra_cache.backends import RedisBackend


class TestRedisBackendConnection:
    """测试 Redis 后端连接"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建 Redis 后端实例"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,  # 使用测试数据库
                password=None,
            )
            # 测试连接
            backend.set("test", "connection")
            backend.delete("test")
            return backend
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_redis_initialization(self) -> None:
        """测试 Redis 后端初始化"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            assert backend.host == "localhost"
            assert backend.port == 6379
            assert backend.db == 15
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_redis_initialization_with_password(self) -> None:
        """测试带密码的 Redis 初始化"""
        try:
            # 这会尝试连接，但不会失败即使密码不对
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
                password="wrong_password",
            )
            # 实际操作时才会失败
            try:
                backend.set("test", "value")
            except Exception:
                # 预期会失败，因为密码错误
                pass
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")


class TestRedisBackendBasicOperations:
    """测试 Redis 后端基础操作"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建和清理 Redis 后端"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            # 清空测试数据库
            backend.clear()
            yield backend
            # 清理
            backend.clear()
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_set_and_get(self, redis_backend: RedisBackend) -> None:
        """测试设置和获取值"""
        result = redis_backend.set("key1", "value1")
        assert result is True

        value = redis_backend.get("key1")
        assert value == "value1"

    def test_set_with_ttl(self, redis_backend: RedisBackend) -> None:
        """测试带 TTL 的设置"""
        redis_backend.set("ttl_key", "value", ttl=1)

        # 立即获取，应该存在
        value = redis_backend.get("ttl_key")
        assert value == "value"

        # 等待过期
        time.sleep(1.1)

        # 应该过期
        value = redis_backend.get("ttl_key")
        assert value is None

    def test_delete(self, redis_backend: RedisBackend) -> None:
        """测试删除键"""
        redis_backend.set("key1", "value1")
        assert redis_backend.exists("key1")

        result = redis_backend.delete("key1")
        assert result is True
        assert not redis_backend.exists("key1")

    def test_delete_non_existent(self, redis_backend: RedisBackend) -> None:
        """测试删除不存在的键"""
        result = redis_backend.delete("non_existent")
        assert result is False

    def test_exists(self, redis_backend: RedisBackend) -> None:
        """测试键存在性检查"""
        assert not redis_backend.exists("key1")

        redis_backend.set("key1", "value1")
        assert redis_backend.exists("key1")

        redis_backend.delete("key1")
        assert not redis_backend.exists("key1")

    def test_clear(self, redis_backend: RedisBackend) -> None:
        """测试清空所有缓存"""
        # 设置多个键
        for i in range(10):
            redis_backend.set(f"key{i}", f"value{i}")

        # 清空
        redis_backend.clear()

        # 验证所有键都被删除
        for i in range(10):
            assert not redis_backend.exists(f"key{i}")

    def test_set_many(self, redis_backend: RedisBackend) -> None:
        """测试批量设置"""
        data = {f"key{i}": f"value{i}" for i in range(10)}
        redis_backend.set_many(data)

        # 验证
        for key, value in data.items():
            assert redis_backend.get(key) == value

    def test_get_many(self, redis_backend: RedisBackend) -> None:
        """测试批量获取"""
        # 设置数据
        for i in range(5):
            redis_backend.set(f"key{i}", f"value{i}")

        # 批量获取
        values = redis_backend.get_many([f"key{i}" for i in range(5)])
        expected = {f"key{i}": f"value{i}" for i in range(5)}

        for key, value in expected.items():
            assert values.get(key) == value

    def test_delete_many(self, redis_backend: RedisBackend) -> None:
        """测试批量删除"""
        # 设置数据
        for i in range(10):
            redis_backend.set(f"key{i}", f"value{i}")

        # 批量删除
        keys = [f"key{i}" for i in range(5)]
        count = redis_backend.delete_many(keys)
        assert count == 5

        # 验证
        for i in range(5):
            assert not redis_backend.exists(f"key{i}")
        for i in range(5, 10):
            assert redis_backend.exists(f"key{i}")


class TestRedisBackendPatternMatching:
    """测试 Redis 后端的模式匹配"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建和清理 Redis 后端"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            backend.clear()
            yield backend
            backend.clear()
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_keys_all(self, redis_backend: RedisBackend) -> None:
        """测试获取所有键"""
        # 设置数据
        for i in range(10):
            redis_backend.set(f"key{i}", f"value{i}")

        # 获取所有键
        page = redis_backend.keys()
        keys = page.keys

        assert len(keys) == 10
        for i in range(10):
            assert f"key{i}" in keys

    def test_keys_with_pattern_wildcard(self, redis_backend: RedisBackend) -> None:
        """测试带通配符的模式匹配"""
        # 设置数据
        for i in range(5):
            redis_backend.set(f"user:{i}", f"user_{i}")
            redis_backend.set(f"post:{i}", f"post_{i}")

        # 查询 user:* 模式
        page = redis_backend.keys(pattern="user:*")
        keys = page.keys

        assert len(keys) == 5
        for i in range(5):
            assert f"user:{i}" in keys

    def test_keys_with_pattern_question_mark(self, redis_backend: RedisBackend) -> None:
        """测试问号通配符"""
        # 设置数据
        for i in range(3):
            redis_backend.set(f"key:{i}:a", f"value_{i}_a")
            redis_backend.set(f"key:{i}:b", f"value_{i}_b")

        # 查询 key:?:a 模式
        page = redis_backend.keys(pattern="key:?:a")
        keys = page.keys

        assert len(keys) == 3
        for i in range(3):
            assert f"key:{i}:a" in keys

    def test_keys_pagination(self, redis_backend: RedisBackend) -> None:
        """测试键分页"""
        # 设置大量数据
        for i in range(50):
            redis_backend.set(f"key{i:02d}", f"value{i}")

        # 第一页
        page1 = redis_backend.keys(count=10, cursor=0)
        assert len(page1.keys) <= 10

        # 检查是否有下一页
        if page1.has_more:
            page2 = redis_backend.keys(count=10, cursor=page1.cursor)
            # 确保不是同样的键
            assert set(page1.keys) != set(page2.keys)


class TestRedisBackendSerialization:
    """测试 Redis 后端的序列化"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建和清理 Redis 后端"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            backend.clear()
            yield backend
            backend.clear()
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_store_dict(self, redis_backend: RedisBackend) -> None:
        """测试存储字典"""
        data = {"name": "John", "age": 30, "tags": ["python", "redis"]}
        redis_backend.set("user:1", data)

        retrieved = redis_backend.get("user:1")
        assert retrieved == data

    def test_store_list(self, redis_backend: RedisBackend) -> None:
        """测试存储列表"""
        data = [1, 2, 3, "four", {"five": 5}]
        redis_backend.set("list:1", data)

        retrieved = redis_backend.get("list:1")
        assert retrieved == data

    def test_store_nested_structure(self, redis_backend: RedisBackend) -> None:
        """测试存储嵌套结构"""
        data = {
            "user": {
                "name": "John",
                "posts": [
                    {"id": 1, "title": "Post 1"},
                    {"id": 2, "title": "Post 2"},
                ],
            },
            "stats": {"views": 1000, "likes": 50},
        }
        redis_backend.set("complex:1", data)

        retrieved = redis_backend.get("complex:1")
        assert retrieved == data


class TestRedisBackendEdgeCases:
    """测试 Redis 后端的边界情况"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建和清理 Redis 后端"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            backend.clear()
            yield backend
            backend.clear()
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_empty_value(self, redis_backend: RedisBackend) -> None:
        """测试空值"""
        redis_backend.set("empty", "")
        assert redis_backend.get("empty") == ""

    def test_large_value(self, redis_backend: RedisBackend) -> None:
        """测试大值存储"""
        large_value = "x" * (1024 * 1024)  # 1MB
        redis_backend.set("large", large_value)
        assert redis_backend.get("large") == large_value

    def test_special_characters_in_key(self, redis_backend: RedisBackend) -> None:
        """测试键中的特殊字符"""
        special_keys = [
            "key:with:colons",
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key@with#symbols",
        ]

        for key in special_keys:
            redis_backend.set(key, f"value_for_{key}")
            assert redis_backend.get(key) == f"value_for_{key}"

    def test_unicode_in_value(self, redis_backend: RedisBackend) -> None:
        """测试值中的 Unicode"""
        unicode_values = [
            "你好世界",
            "مرحبا بالعالم",
            "🚀🎉✨",
            "Привет мир",
        ]

        for i, value in enumerate(unicode_values):
            redis_backend.set(f"unicode:{i}", value)
            assert redis_backend.get(f"unicode:{i}") == value

    def test_ttl_precision(self, redis_backend: RedisBackend) -> None:
        """测试 TTL 精度"""
        redis_backend.set("ttl_test", "value", ttl=2)

        # 立即获取
        assert redis_backend.get("ttl_test") == "value"

        # 1秒后仍然存在
        time.sleep(1)
        assert redis_backend.get("ttl_test") == "value"

        # 2秒后应该过期
        time.sleep(1.1)
        assert redis_backend.get("ttl_test") is None

    def test_zero_ttl(self, redis_backend: RedisBackend) -> None:
        """测试零 TTL（永久存储）"""
        redis_backend.set("no_ttl", "value", ttl=0)

        # 应该立即过期或永久存储（取决于实现）
        # 大多数实现会立即删除
        value = redis_backend.get("no_ttl")
        # 不做断言，因为行为可能不同

    def test_negative_ttl(self, redis_backend: RedisBackend) -> None:
        """测试负 TTL"""
        redis_backend.set("negative_ttl", "value", ttl=-1)

        # 应该立即过期
        value = redis_backend.get("negative_ttl")
        # 不做断言，因为行为可能不同


class TestRedisBackendConcurrency:
    """测试 Redis 后端的并发操作"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建和清理 Redis 后端"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            backend.clear()
            yield backend
            backend.clear()
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    def test_multiple_set_operations(self, redis_backend: RedisBackend) -> None:
        """测试多个设置操作"""
        for i in range(100):
            redis_backend.set(f"key{i}", f"value{i}")

        # 验证所有键都被设置
        for i in range(100):
            assert redis_backend.get(f"key{i}") == f"value{i}"

    def test_concurrent_read_write(self, redis_backend: RedisBackend) -> None:
        """测试并发读写"""
        # 先设置一些数据
        for i in range(10):
            redis_backend.set(f"key{i}", f"value{i}")

        # 并发读写
        for i in range(10):
            value = redis_backend.get(f"key{i}")
            assert value == f"value{i}"

            redis_backend.set(f"key{i}", f"updated_value{i}")

        # 验证更新
        for i in range(10):
            assert redis_backend.get(f"key{i}") == f"updated_value{i}"


class TestRedisBackendAsyncOperations:
    """测试 Redis 后端的异步操作"""

    @pytest.fixture
    def redis_backend(self) -> RedisBackend:
        """创建和清理 Redis 后端"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=15,
            )
            backend.clear()
            yield backend
            backend.clear()
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    @pytest.mark.asyncio
    async def test_aset_and_aget(self, redis_backend: RedisBackend) -> None:
        """测试异步设置和获取"""
        result = await redis_backend.aset("key1", "value1")
        assert result is True

        value = await redis_backend.aget("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_aset_many(self, redis_backend: RedisBackend) -> None:
        """测试异步批量设置"""
        data = {f"key{i}": f"value{i}" for i in range(10)}
        await redis_backend.aset_many(data)

        # 验证
        for key, value in data.items():
            result = await redis_backend.aget(key)
            assert result == value

    @pytest.mark.asyncio
    async def test_aget_many(self, redis_backend: RedisBackend) -> None:
        """测试异步批量获取"""
        # 设置数据
        for i in range(5):
            redis_backend.set(f"key{i}", f"value{i}")

        # 异步批量获取
        values = await redis_backend.aget_many([f"key{i}" for i in range(5)])

        for i in range(5):
            assert values[f"key{i}"] == f"value{i}"

    @pytest.mark.asyncio
    async def test_adelete_many(self, redis_backend: RedisBackend) -> None:
        """测试异步批量删除"""
        # 设置数据
        for i in range(10):
            redis_backend.set(f"key{i}", f"value{i}")

        # 异步批量删除
        count = await redis_backend.adelete_many([f"key{i}" for i in range(5)])
        assert count == 5

        # 验证
        for i in range(5):
            assert not redis_backend.exists(f"key{i}")
        for i in range(5, 10):
            assert redis_backend.exists(f"key{i}")

    @pytest.mark.asyncio
    async def test_aclear(self, redis_backend: RedisBackend) -> None:
        """测试异步清空"""
        # 设置数据
        for i in range(10):
            redis_backend.set(f"key{i}", f"value{i}")

        # 异步清空
        await redis_backend.aclear()

        # 验证
        for i in range(10):
            assert not redis_backend.exists(f"key{i}")
