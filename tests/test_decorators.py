"""
装饰器单元测试

测试缓存装饰器的功能。
"""

from __future__ import annotations

import pytest

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.decorators import acache, cache


class TestCacheDecorator:
    """测试同步缓存装饰器"""

    def test_basic_caching(self) -> None:
        """测试基础缓存功能"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @cache(manager)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用：执行函数
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用：从缓存获取
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 未增加

        # 不同参数：重新执行
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_cache_with_ttl(self) -> None:
        """测试带 TTL 的缓存"""
        import time

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @cache(manager, ttl=1)
        def timed_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        # 第一次调用
        result1 = timed_function(5)
        assert result1 == 15
        assert call_count == 1

        # 立即调用：从缓存
        result2 = timed_function(5)
        assert result2 == 15
        assert call_count == 1

        # 等待过期后调用
        time.sleep(1.1)
        result3 = timed_function(5)
        assert result3 == 15
        assert call_count == 2

    def test_cache_with_prefix(self) -> None:
        """测试键前缀"""
        manager = CacheManager(backend=MemoryBackend())

        @cache(manager, key_prefix="user:")
        def get_user(user_id: int) -> dict[str, object]:
            return {"id": user_id, "name": "Alice"}

        result = get_user(123)
        assert result["id"] == 123

        # 验证键前缀生效（通过直接访问后端）
        # 键格式: user:module.function:hash


class TestAsyncCacheDecorator:
    """测试异步缓存装饰器"""

    @pytest.mark.asyncio
    async def test_basic_async_caching(self) -> None:
        """测试异步缓存"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @acache(manager)
        async def async_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = await async_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用：从缓存
        result2 = await async_function(5)
        assert result2 == 10
        assert call_count == 1


class TestCacheInvalidateDecorator:
    """测试缓存失效装饰器"""

    def test_cache_invalidation(self) -> None:
        """测试缓存失效"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @cache(manager)
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用：缓存
        result1 = compute(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用：从缓存
        result2 = compute(5)
        assert result2 == 10
        assert call_count == 1

        # 手动清除缓存（模拟失效）
        # 这里直接使用 manager 清除所有缓存
        manager.clear()

        # 再次调用：重新执行
        result3 = compute(5)
        assert result3 == 10
        assert call_count == 2

    def test_cache_invalidate_decorator(self) -> None:
        """测试 cache_invalidate 装饰器"""
        from symphra_cache.decorators import cache_invalidate, default_key_builder

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0
        update_count = 0

        @cache(manager)
        def get_value(key: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"value_{key}"

        @cache_invalidate(manager, key_builder=default_key_builder)
        def update_value(key: str) -> None:
            nonlocal update_count
            update_count += 1

        # 缓存初始值
        result1 = get_value("test")
        assert result1 == "value_test"
        assert call_count == 1

        # 从缓存获取
        result2 = get_value("test")
        assert result2 == "value_test"
        assert call_count == 1

        # 构建和删除相同的缓存键
        cache_key = default_key_builder(get_value, ("test",), {})
        manager.delete(cache_key)

        # 重新缓存新值
        result3 = get_value("test")
        assert result3 == "value_test"
        assert call_count == 2

    def test_cache_with_none_value(self) -> None:
        """测试缓存不缓存 None 值"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @cache(manager)
        def may_return_none(should_return_value: bool) -> str | None:
            nonlocal call_count
            call_count += 1
            return "value" if should_return_value else None

        # 返回 None 的调用不应该被缓存
        result1 = may_return_none(False)
        assert result1 is None
        assert call_count == 1

        # 再次调用应该重新执行（因为没被缓存）
        result2 = may_return_none(False)
        assert result2 is None
        assert call_count == 2

        # 返回值的调用应该被缓存
        result3 = may_return_none(True)
        assert result3 == "value"
        assert call_count == 3

        # 再次调用应该从缓存获取
        result4 = may_return_none(True)
        assert result4 == "value"
        assert call_count == 3

    def test_cache_with_custom_key_builder(self) -> None:
        """测试自定义键生成函数"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        def custom_key_builder(func, args, kwargs):
            # 只使用第一个参数
            return f"custom_{args[0] if args else 'no_args'}"

        @cache(manager, key_builder=custom_key_builder)
        def compute(x: int, y: int = 10) -> int:
            nonlocal call_count
            call_count += 1
            return x + y

        # 相同的第一个参数应该使用缓存，即使其他参数不同
        result1 = compute(5, y=10)
        assert result1 == 15
        assert call_count == 1

        # 使用不同的 y，但 x 相同，应该使用缓存
        result2 = compute(5, y=20)
        assert result2 == 15  # 还是返回之前的缓存值
        assert call_count == 1

        # 不同的 x 应该重新计算
        result3 = compute(10, y=10)
        assert result3 == 20
        assert call_count == 2

    def test_cache_with_non_serializable_param(self) -> None:
        """测试不可序列化参数的处理"""
        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        @cache(manager)
        def compute(obj: object) -> str:
            nonlocal call_count
            call_count += 1
            return str(type(obj).__name__)

        class CustomObject:
            pass

        # 不可序列化的对象应该触发降级策略
        obj1 = CustomObject()
        result1 = compute(obj1)
        assert "CustomObject" in result1
        assert call_count == 1

        # 不同的对象应该生成不同的缓存键
        obj2 = CustomObject()
        result2 = compute(obj2)
        assert "CustomObject" in result2
        assert call_count == 2


class TestCachedProperty:
    """测试缓存属性装饰器"""

    def test_cached_property_basic(self) -> None:
        """测试缓存属性基本功能"""
        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        class User:
            def __init__(self, user_id: int) -> None:
                self.user_id = user_id

            @CachedProperty(manager)
            def profile(self) -> dict[str, object]:
                nonlocal call_count
                call_count += 1
                return {"id": self.user_id, "name": "Alice"}

        user = User(123)

        # 第一次访问：计算属性值
        profile1 = user.profile
        assert profile1["id"] == 123
        assert call_count == 1

        # 第二次访问：从缓存获取
        profile2 = user.profile
        assert profile2["id"] == 123
        assert call_count == 1

    def test_cached_property_with_ttl(self) -> None:
        """测试带 TTL 的缓存属性"""
        import time

        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        class User:
            def __init__(self, user_id: int) -> None:
                self.user_id = user_id

            @CachedProperty(manager, ttl=1)
            def profile(self) -> dict[str, object]:
                nonlocal call_count
                call_count += 1
                return {"id": self.user_id, "name": "Alice"}

        user = User(123)

        # 第一次访问
        profile1 = user.profile
        assert profile1["id"] == 123
        assert call_count == 1

        # 立即访问：从缓存
        profile2 = user.profile
        assert profile2["id"] == 123
        assert call_count == 1

        # 等待过期
        time.sleep(1.1)

        # 过期后访问：重新计算
        profile3 = user.profile
        assert profile3["id"] == 123
        assert call_count == 2

    def test_cached_property_with_prefix(self) -> None:
        """测试缓存属性键前缀"""
        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        class User:
            def __init__(self, user_id: int) -> None:
                self.user_id = user_id

            @CachedProperty(manager, key_prefix="user:")
            def profile(self) -> dict[str, object]:
                nonlocal call_count
                call_count += 1
                return {"id": self.user_id}

        user = User(123)

        # 访问属性
        profile = user.profile
        assert profile["id"] == 123
        assert call_count == 1

    def test_cached_property_different_instances(self) -> None:
        """测试不同实例有不同的缓存"""
        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        class User:
            def __init__(self, user_id: int) -> None:
                self.user_id = user_id

            @CachedProperty(manager)
            def profile(self) -> dict[str, object]:
                nonlocal call_count
                call_count += 1
                return {"id": self.user_id}

        user1 = User(123)
        user2 = User(456)

        # 不同实例的属性应该分别缓存
        profile1 = user1.profile
        assert profile1["id"] == 123
        assert call_count == 1

        profile2 = user2.profile
        assert profile2["id"] == 456
        assert call_count == 2

        # 再次访问应该使用各自的缓存
        profile1_again = user1.profile
        assert profile1_again["id"] == 123
        assert call_count == 2

        profile2_again = user2.profile
        assert profile2_again["id"] == 456
        assert call_count == 2

    def test_cached_property_on_class(self) -> None:
        """测试在类上访问缓存属性返回描述器本身"""
        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())

        class User:
            @CachedProperty(manager)
            def profile(self) -> dict[str, object]:
                return {}

        # 在类上访问应该返回描述器本身
        assert isinstance(User.profile, CachedProperty)

    def test_cached_property_with_none_value(self) -> None:
        """测试缓存属性不缓存 None 值"""
        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())
        call_count = 0

        class User:
            def __init__(self, has_profile: bool) -> None:
                self.has_profile = has_profile

            @CachedProperty(manager)
            def profile(self) -> dict[str, object] | None:
                nonlocal call_count
                call_count += 1
                return {"id": 123} if self.has_profile else None

        user = User(False)

        # 返回 None 的调用不应该被缓存
        profile1 = user.profile
        assert profile1 is None
        assert call_count == 1

        # 再次访问应该重新计算
        profile2 = user.profile
        assert profile2 is None
        assert call_count == 2

    def test_cached_property_uninitialized(self) -> None:
        """测试未初始化的缓存属性"""
        from symphra_cache.decorators import CachedProperty

        manager = CacheManager(backend=MemoryBackend())

        cached_prop = CachedProperty(manager)

        class User:
            pass

        # 未设置函数的情况
        user = User()
        with pytest.raises(RuntimeError, match="未正确初始化"):
            _ = cached_prop.__get__(user, User)
