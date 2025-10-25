"""
缓存失效 (CacheInvalidator) 测试

测试缓存失效器的各种失效策略、模式匹配、条件失效等功能。
"""

import asyncio
from typing import Any

import pytest

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.invalidation import CacheInvalidator, CacheGroupInvalidator


class TestCacheInvalidatorBasics:
    """测试缓存失效器基础功能"""

    @pytest.mark.asyncio
    async def test_invalidator_initialization(self) -> None:
        """测试失效器初始化"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager, batch_size=50)

        assert invalidator.cache == manager
        assert invalidator.batch_size == 50
        assert invalidator.enable_distributed is False

    @pytest.mark.asyncio
    async def test_invalidate_single_key(self) -> None:
        """测试失效单个键"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        manager.set("key1", "value1")
        assert manager.exists("key1")

        # 失效键
        count = await invalidator.invalidate_keys(["key1"])
        assert count == 1
        assert not manager.exists("key1")

    @pytest.mark.asyncio
    async def test_invalidate_multiple_keys(self) -> None:
        """测试失效多个键"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置多个键
        for i in range(10):
            manager.set(f"key{i}", f"value{i}")

        # 失效所有键
        keys = [f"key{i}" for i in range(10)]
        count = await invalidator.invalidate_keys(keys)
        assert count == 10

        # 验证所有键都被删除
        for i in range(10):
            assert not manager.exists(f"key{i}")

    @pytest.mark.asyncio
    async def test_invalidate_empty_keys(self) -> None:
        """测试失效空键列表"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        count = await invalidator.invalidate_keys([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_invalidate_pattern_wildcard(self) -> None:
        """测试模式匹配失效（通配符）"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(5):
            manager.set(f"user:{i}", f"user_data_{i}")
            manager.set(f"session:{i}", f"session_data_{i}")

        # 失效 user:* 模式
        count = await invalidator.invalidate_pattern("user:*")
        assert count == 5

        # user:* 应该被删除
        for i in range(5):
            assert not manager.exists(f"user:{i}")

        # session:* 应该保留
        for i in range(5):
            assert manager.exists(f"session:{i}")

    @pytest.mark.asyncio
    async def test_invalidate_pattern_question_mark(self) -> None:
        """测试模式匹配失效（问号通配符）"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(3):
            manager.set(f"key:{i}:a", f"value_{i}_a")
            manager.set(f"key:{i}:b", f"value_{i}_b")

        # 失效 key:?:a 模式
        count = await invalidator.invalidate_pattern("key:?:a")
        assert count == 3

        # key:?:a 应该被删除
        for i in range(3):
            assert not manager.exists(f"key:{i}:a")

        # key:?:b 应该保留
        for i in range(3):
            assert manager.exists(f"key:{i}:b")

    @pytest.mark.asyncio
    async def test_invalidate_prefix(self) -> None:
        """测试前缀失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(3):
            manager.set(f"cache:user:{i}", f"user_{i}")
            manager.set(f"cache:post:{i}", f"post_{i}")
            manager.set(f"data:{i}", f"data_{i}")

        # 失效 cache: 前缀
        count = await invalidator.invalidate_prefix("cache:")
        assert count == 6

        # cache: 前缀应该被删除
        for i in range(3):
            assert not manager.exists(f"cache:user:{i}")
            assert not manager.exists(f"cache:post:{i}")

        # data: 前缀应该保留
        for i in range(3):
            assert manager.exists(f"data:{i}")

    @pytest.mark.asyncio
    async def test_invalidate_all(self) -> None:
        """测试失效所有缓存"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置多个键
        for i in range(10):
            manager.set(f"key{i}", f"value{i}")

        # 失效所有键
        count = await invalidator.invalidate_all()
        assert count == 10

        # 验证所有键都被删除
        for i in range(10):
            assert not manager.exists(f"key{i}")


class TestCacheInvalidatorCondition:
    """测试缓存失效器的条件失效"""

    @pytest.mark.asyncio
    async def test_invalidate_by_condition(self) -> None:
        """测试基于条件的失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键和值
        for i in range(10):
            manager.set(f"key{i}", i)

        # 定义条件：失效值 > 5 的键
        def condition(key: Any, value: Any) -> bool:
            return value > 5

        count = await invalidator.invalidate_by_condition(condition)
        assert count == 4  # 6, 7, 8, 9

        # 验证结果
        for i in range(6):
            assert manager.exists(f"key{i}")
        for i in range(6, 10):
            assert not manager.exists(f"key{i}")

    @pytest.mark.asyncio
    async def test_invalidate_by_condition_with_key_check(self) -> None:
        """测试基于键名和值的条件失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(5):
            manager.set(f"user:{i}", {"id": i, "name": f"user_{i}"})
            manager.set(f"post:{i}", {"id": i, "content": f"post_{i}"})

        # 定义条件：失效 user: 前缀的键
        def condition(key: Any, value: Any) -> bool:
            return isinstance(key, str) and key.startswith("user:")

        count = await invalidator.invalidate_by_condition(condition)
        assert count == 5

        # 验证 user: 键被删除
        for i in range(5):
            assert not manager.exists(f"user:{i}")

        # 验证 post: 键保留
        for i in range(5):
            assert manager.exists(f"post:{i}")

    @pytest.mark.asyncio
    async def test_invalidate_by_condition_with_max_keys(self) -> None:
        """测试有最大键限制的条件失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(20):
            manager.set(f"key{i}", i)

        # 定义条件：失效所有键，但限制最多10个
        def condition(key: Any, value: Any) -> bool:
            return True

        count = await invalidator.invalidate_by_condition(condition, max_keys=10)
        assert count <= 10


class TestCacheInvalidatorDependencies:
    """测试缓存失效器的依赖失效"""

    @pytest.mark.asyncio
    async def test_invalidate_with_dependencies(self) -> None:
        """测试失效键及其依赖项"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        manager.set("user:1", "user_data")
        manager.set("user:1:profile", "profile_data")
        manager.set("user:1:posts", "posts_data")
        manager.set("cache:other", "other_data")

        # 定义依赖解析函数
        def resolve_dependencies(keys: list[Any]) -> list[Any]:
            """获取相关的依赖键"""
            dependencies = []
            for key in keys:
                if key == "user:1":
                    dependencies.extend(["user:1:profile", "user:1:posts"])
            return dependencies

        # 失效主键及其依赖
        count = await invalidator.invalidate_with_dependencies(
            ["user:1"], resolve_dependencies
        )
        assert count == 3

        # 验证主键和依赖键都被删除
        assert not manager.exists("user:1")
        assert not manager.exists("user:1:profile")
        assert not manager.exists("user:1:posts")

        # 其他键保留
        assert manager.exists("cache:other")

    @pytest.mark.asyncio
    async def test_invalidate_with_multiple_dependencies(self) -> None:
        """测试多个主键的依赖失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(3):
            manager.set(f"user:{i}", f"user_{i}")
            manager.set(f"user:{i}:profile", f"profile_{i}")

        # 定义依赖解析函数
        def resolve_dependencies(keys: list[Any]) -> list[Any]:
            """获取所有相关的依赖键"""
            dependencies = []
            for key in keys:
                if isinstance(key, str) and key.startswith("user:"):
                    user_id = key.split(":")[1]
                    dependencies.append(f"user:{user_id}:profile")
            return dependencies

        # 失效多个主键及其依赖
        count = await invalidator.invalidate_with_dependencies(
            ["user:0", "user:1", "user:2"], resolve_dependencies
        )
        assert count == 6


class TestCacheInvalidatorScheduling:
    """测试缓存失效器的调度功能"""

    @pytest.mark.asyncio
    async def test_schedule_invalidation(self) -> None:
        """测试延迟失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        manager.set("key1", "value1")

        # 调度延迟失效
        task = await invalidator.schedule_invalidation(["key1"], delay=0.1)

        # 立即检查，键应该存在
        assert manager.exists("key1")

        # 等待失效完成
        count = await task
        assert count == 1
        assert not manager.exists("key1")

    @pytest.mark.asyncio
    async def test_conditional_invalidation(self) -> None:
        """测试条件失效任务"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        manager.set("key1", "value1")

        # 定义条件（延迟触发）
        condition_triggered = False

        def condition() -> bool:
            return condition_triggered

        # 启动条件失效任务
        task = await invalidator.conditional_invalidation(
            condition, ["key1"], check_interval=0.01
        )

        # 短暂等待
        await asyncio.sleep(0.05)

        # 条件未触发，键应该存在
        assert manager.exists("key1")

        # 触发条件
        condition_triggered = True

        # 等待失效完成
        count = await task
        assert count == 1
        assert not manager.exists("key1")


class TestCacheGroupInvalidator:
    """测试缓存组失效器"""

    @pytest.mark.asyncio
    async def test_group_invalidator_initialization(self) -> None:
        """测试组失效器初始化"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)
        group = invalidator.create_cache_group_invalidator("user:")

        assert isinstance(group, CacheGroupInvalidator)
        assert group.group_prefix == "user:"
        assert group.parent == invalidator

    @pytest.mark.asyncio
    async def test_group_invalidate_all(self) -> None:
        """测试组内全部失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)
        group = invalidator.create_cache_group_invalidator("user:")

        # 设置组内和组外的键
        for i in range(3):
            manager.set(f"user:{i}", f"user_{i}")
            manager.set(f"post:{i}", f"post_{i}")

        # 失效整个组
        count = await group.invalidate_all()
        assert count == 3

        # 验证组内键被删除
        for i in range(3):
            assert not manager.exists(f"user:{i}")

        # 验证组外键保留
        for i in range(3):
            assert manager.exists(f"post:{i}")

    @pytest.mark.asyncio
    async def test_group_invalidate_pattern(self) -> None:
        """测试组内模式失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)
        group = invalidator.create_cache_group_invalidator("cache:")

        # 设置键
        for i in range(3):
            manager.set(f"cache:user:{i}", f"user_{i}")
            manager.set(f"cache:post:{i}", f"post_{i}")

        # 失效 cache:user:* 模式
        count = await group.invalidate_pattern("user:*")
        assert count == 3

        # 验证 cache:user:* 被删除
        for i in range(3):
            assert not manager.exists(f"cache:user:{i}")

        # 验证 cache:post:* 保留
        for i in range(3):
            assert manager.exists(f"cache:post:{i}")

    @pytest.mark.asyncio
    async def test_group_invalidate_keys(self) -> None:
        """测试组内指定键失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)
        group = invalidator.create_cache_group_invalidator("cache:")

        # 设置键
        manager.set("cache:key1", "value1")
        manager.set("cache:key2", "value2")
        manager.set("cache:key3", "value3")

        # 失效相对于组前缀的键
        count = await group.invalidate_keys(["key1", "key3"])
        assert count == 2

        # 验证
        assert not manager.exists("cache:key1")
        assert manager.exists("cache:key2")
        assert not manager.exists("cache:key3")

    @pytest.mark.asyncio
    async def test_group_invalidator_stats(self) -> None:
        """测试组失效器统计"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)
        group = invalidator.create_cache_group_invalidator("user:")

        stats = group.get_stats()

        assert stats["group_prefix"] == "user:"
        assert "parent_stats" in stats
        assert stats["parent_stats"]["batch_size"] == invalidator.batch_size


class TestCacheInvalidatorStats:
    """测试缓存失效器的统计功能"""

    @pytest.mark.asyncio
    async def test_invalidation_stats(self) -> None:
        """测试失效统计"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(5):
            manager.set(f"key{i}", f"value{i}")

        # 执行失效
        await invalidator.invalidate_keys([f"key{i}" for i in range(5)])

        # 获取统计
        stats = invalidator.get_invalidation_stats()

        assert stats["total_operations"] == 1
        assert stats["total_invalidated_keys"] == 5
        assert stats["batch_size"] == 100
        assert stats["enable_distributed"] is False

    @pytest.mark.asyncio
    async def test_invalidation_history(self) -> None:
        """测试失效历史"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        for i in range(3):
            manager.set(f"key{i}", f"value{i}")

        # 执行多次失效
        await invalidator.invalidate_keys(["key0"])
        await invalidator.invalidate_keys(["key1", "key2"])
        await invalidator.invalidate_pattern("key*")

        # 获取历史
        history = invalidator.get_invalidation_history(limit=10)

        assert len(history) == 3
        # 历史应该按时间倒序
        assert history[0]["method"] == "pattern"
        assert history[1]["method"] == "keys"
        assert history[2]["method"] == "keys"

    @pytest.mark.asyncio
    async def test_invalidation_log_limit(self) -> None:
        """测试失效日志的限制（最多100条）"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 执行超过100次的失效操作
        for i in range(120):
            manager.set(f"key{i}", f"value{i}")
            await invalidator.invalidate_keys([f"key{i}"])

        # 日志应该限制在100条
        stats = invalidator.get_invalidation_stats()
        assert stats["total_operations"] == 100


class TestCacheInvalidatorBatching:
    """测试缓存失效器的批处理"""

    @pytest.mark.asyncio
    async def test_batch_size_custom(self) -> None:
        """测试自定义批大小"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager, batch_size=10)

        # 设置键
        for i in range(35):
            manager.set(f"key{i}", f"value{i}")

        # 失效所有键（应该分成4个批）
        count = await invalidator.invalidate_keys([f"key{i}" for i in range(35)])
        assert count == 35

        # 验证所有键都被删除
        for i in range(35):
            assert not manager.exists(f"key{i}")

    @pytest.mark.asyncio
    async def test_batch_size_override(self) -> None:
        """测试批大小覆盖"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager, batch_size=100)

        # 设置键
        for i in range(50):
            manager.set(f"key{i}", f"value{i}")

        # 使用不同的批大小失效
        count = await invalidator.invalidate_keys([f"key{i}" for i in range(50)], batch_size=10)
        assert count == 50

        # 验证所有键都被删除
        for i in range(50):
            assert not manager.exists(f"key{i}")


class TestCacheInvalidatorEdgeCases:
    """测试缓存失效器的边界情况"""

    @pytest.mark.asyncio
    async def test_invalidate_non_existent_keys(self) -> None:
        """测试失效不存在的键"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 失效不存在的键（应该返回0）
        count = await invalidator.invalidate_keys(["non_existent"])
        assert count == 0

    @pytest.mark.asyncio
    async def test_invalidate_pattern_no_matches(self) -> None:
        """测试无匹配的模式失效"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 设置键
        manager.set("key1", "value1")

        # 失效不匹配的模式
        count = await invalidator.invalidate_pattern("nomatch:*")
        assert count == 0

        # 原有键应该保留
        assert manager.exists("key1")

    @pytest.mark.asyncio
    async def test_invalidator_cleanup(self) -> None:
        """测试失效器清理"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 执行一些失效操作
        for i in range(5):
            manager.set(f"key{i}", f"value{i}")
            await invalidator.invalidate_keys([f"key{i}"])

        # 清理失效器
        await invalidator.close()

        # 日志应该被清空
        assert len(invalidator._invalidation_log) == 0
