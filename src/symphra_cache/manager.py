"""
缓存管理器模块

本模块提供统一的缓存管理接口，屏蔽底层后端差异。
支持后端动态切换、配置文件加载和高级功能。

特性：
- 统一的同步/异步 API
- 后端自动实例化（从配置文件/环境变量）
- 键前缀支持（命名空间隔离）
- 统计信息和性能监控
- get_or_set 模式（缓存穿透优化）
- 批量操作优化

设计模式：
- 外观模式（Facade）：为复杂的后端系统提供简单接口
- 策略模式（Strategy）：后端可动态切换
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .backends.base import BaseBackend
    from .config import CacheConfig
    from .types import CacheKey, CacheValue, KeysPage

# 类型别名：用于装饰器的键生成函数类型
KeyBuilder = Callable[[Callable[..., Any], tuple[Any, ...], dict[str, Any]], str]


class CacheManager:
    """
    缓存管理器

    提供统一的缓存操作接口，屏蔽底层后端差异。
    支持后端动态切换和配置管理。

    核心功能：
    - 统一的同步/异步 API
    - 后端动态切换
    - 批量操作支持
    - 类型安全（完整类型注解）

    使用示例：
        >>> from symphra_cache import CacheManager
        >>> from symphra_cache.backends import MemoryBackend
        >>>
        >>> # 创建缓存管理器
        >>> cache = CacheManager(backend=MemoryBackend())
        >>>
        >>> # 基础操作
        >>> cache.set("user:123", {"name": "Alice"}, ttl=3600)
        >>> user = cache.get("user:123")
        >>>
        >>> # 异步操作
        >>> await cache.aset("product:456", {"name": "Laptop"})
        >>> product = await cache.aget("product:456")
        >>>
        >>> # 批量操作
        >>> cache.set_many({"key1": "value1", "key2": "value2"}, ttl=300)
        >>> results = cache.get_many(["key1", "key2"])
    """

    def __init__(self, backend: BaseBackend) -> None:
        """
        初始化缓存管理器

        Args:
            backend: 缓存后端实例（Memory/File/Redis）

        示例:
            >>> backend = MemoryBackend(max_size=10000)
            >>> cache = CacheManager(backend=backend)
        """
        self._backend = backend

    # ========== 同步基础操作 ==========

    def get(self, key: CacheKey) -> CacheValue | None:
        """
        获取缓存值（同步）

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期则返回 None

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> user = cache.get("user:123")
            >>> if user is None:
            ...     print("缓存未命中")
        """
        return self._backend.get(key)

    def set(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> bool:
        """
        设置缓存值(同步)

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒),None 表示永不过期
            ex: 如果为 True,ttl 表示相对过期时间;False 表示绝对时间戳
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            是否设置成功(nx=True 时可能失败)

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败

        示例:
            >>> # 设置 1 小时过期
            >>> cache.set("session:xyz", {"user_id": 123}, ttl=3600)
            >>>
            >>> # 仅当不存在时设置(类似 Redis SETNX)
            >>> success = cache.set("lock:resource", "owner_id", ttl=10, nx=True)
        """
        return self._backend.set(key, value, ttl=ttl, ex=ex, nx=nx)

    def delete(self, key: CacheKey) -> bool:
        """
        删除缓存（同步）

        Args:
            key: 缓存键

        Returns:
            如果键存在并成功删除返回 True，否则返回 False

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> if cache.delete("user:123"):
            ...     print("缓存已删除")
        """
        return self._backend.delete(key)

    def exists(self, key: CacheKey) -> bool:
        """
        检查键是否存在（同步）

        Args:
            key: 缓存键

        Returns:
            如果键存在且未过期返回 True，否则返回 False

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> if cache.exists("user:123"):
            ...     print("缓存存在")
        """
        return self._backend.exists(key)

    def clear(self) -> None:
        """
        清空所有缓存（同步）

        警告:
            此操作不可逆，会删除所有缓存数据

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> cache.clear()  # 删除所有缓存
        """
        self._backend.clear()

    async def aclear(self) -> None:
        """
        清空所有缓存（异步）

        警告:
            此操作不可逆，会删除所有缓存数据

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> await cache.aclear()  # 异步删除所有缓存
        """
        await self._backend.aclear()

    # ========== 异步基础操作 ==========

    async def aget(self, key: CacheKey) -> CacheValue | None:
        """
        获取缓存值（异步）

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期则返回 None

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> user = await cache.aget("user:123")
        """
        return await self._backend.aget(key)

    async def aset(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> bool:
        """
        设置缓存值(异步)

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒),None 表示永不过期
            ex: 如果为 True,ttl 表示相对过期时间
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            是否设置成功

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败

        示例:
            >>> await cache.aset("product:456", {"name": "Laptop"}, ttl=1800)
        """
        return await self._backend.aset(key, value, ttl=ttl, ex=ex, nx=nx)

    async def adelete(self, key: CacheKey) -> bool:
        """
        删除缓存（异步）

        Args:
            key: 缓存键

        Returns:
            如果键存在并成功删除返回 True，否则返回 False

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> deleted = await cache.adelete("user:123")
        """
        return await self._backend.adelete(key)

    # ========== 批量操作 ==========

    def get_many(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取缓存值（同步）

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典，不存在的键不包含在结果中

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> results = cache.get_many(["user:1", "user:2", "user:3"])
            >>> for key, value in results.items():
            ...     print(f"{key}: {value}")
        """
        return self._backend.get_many(keys)

    async def aget_many(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取缓存值（异步）

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典，不存在的键不包含在结果中

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> results = await cache.aget_many(["user:1", "user:2"])
        """
        return await self._backend.aget_many(keys)

    def set_many(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置缓存值（同步）

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None 表示永不过期

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败

        示例:
            >>> cache.set_many(
            ...     {
            ...         "user:1": {"name": "Alice"},
            ...         "user:2": {"name": "Bob"},
            ...     },
            ...     ttl=600,
            ... )
        """
        self._backend.set_many(mapping, ttl=ttl)

    async def aset_many(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置缓存值（异步）

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None 表示永不过期

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败

        示例:
            >>> await cache.aset_many(
            ...     {
            ...         "product:1": {"name": "Phone"},
            ...         "product:2": {"name": "Tablet"},
            ...     }
            ... )
        """
        await self._backend.aset_many(mapping, ttl=ttl)

    def delete_many(self, keys: list[CacheKey]) -> int:
        """
        批量删除缓存（同步）

        Args:
            keys: 缓存键列表

        Returns:
            成功删除的键数量

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> count = cache.delete_many(["user:1", "user:2", "user:3"])
            >>> print(f"删除了 {count} 个键")
        """
        return self._backend.delete_many(keys)

    async def adelete_many(self, keys: list[CacheKey]) -> int:
        """
        批量删除缓存（异步）

        Args:
            keys: 缓存键列表

        Returns:
            成功删除的键数量

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> count = await cache.adelete_many(["user:1", "user:2"])
        """
        return await self._backend.adelete_many(keys)

    # ========== 后端管理 ==========

    @property
    def backend(self) -> BaseBackend:
        """
        获取当前后端实例

        Returns:
            当前使用的后端实例

        示例:
            >>> backend = cache.backend
            >>> print(type(backend).__name__)  # "MemoryBackend"
        """
        return self._backend

    def switch_backend(self, backend: BaseBackend) -> None:
        """
        切换缓存后端

        注意:
            切换后端不会迁移现有数据，新后端从空白状态开始

        Args:
            backend: 新的后端实例

        示例:
            >>> # 从内存后端切换到 Redis 后端
            >>> from symphra_cache.backends import RedisBackend
            >>> cache.switch_backend(RedisBackend())
        """
        self._backend = backend

    # ========== 高级功能 ==========

    def get_or_set(
        self,
        key: CacheKey,
        default_factory: Callable[[], CacheValue],
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> CacheValue:
        """
        获取缓存值,如果不存在则调用 default_factory 计算并缓存

        这是防止缓存穿透的推荐模式。

        Args:
            key: 缓存键
            default_factory: 不存在时调用的工厂函数
            ttl: 过期时间(秒),None 表示永不过期
            ex: 如果为 True,ttl 表示相对过期时间
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            缓存值或计算的新值

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> def expensive_compute():
            ...     return sum(range(1000000))
            >>> result = cache.get_or_set("sum", expensive_compute, ttl=300)
        """
        value = self._backend.get(key)
        if value is not None:
            return value

        # 缓存未命中,计算新值
        value = default_factory()
        self._backend.set(key, value, ttl=ttl, ex=ex, nx=nx)
        return value

    async def aget_or_set(
        self,
        key: CacheKey,
        default_factory: Callable[[], CacheValue],
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> CacheValue:
        """
        获取缓存值,如果不存在则调用 default_factory 计算并缓存(异步)

        Args:
            key: 缓存键
            default_factory: 不存在时调用的工厂函数
            ttl: 过期时间(秒),None 表示永不过期
            ex: 如果为 True,ttl 表示相对过期时间
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            缓存值或计算的新值

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> async def fetch_data():
            ...     return await client.get("/api/data")
            >>> result = await cache.aget_or_set("data", fetch_data)
        """
        value = await self._backend.aget(key)
        if value is not None:
            return value

        # 缓存未命中,计算新值
        value = default_factory()
        await self._backend.aset(key, value, ttl=ttl, ex=ex, nx=nx)
        return value

    def increment(self, key: CacheKey, delta: int = 1) -> int:
        """
        原子递增计数器(同步)

        Args:
            key: 缓存键
            delta: 增量,默认为 1

        Returns:
            递增后的值

        Raises:
            ValueError: 当前值不是整数
            CacheBackendError: 后端操作失败

        示例:
            >>> cache.set("counter", 10)
            >>> new_value = cache.increment("counter", 5)
            >>> print(new_value)  # 15
        """
        current = self._backend.get(key)
        if current is None:
            current = 0

        if not isinstance(current, int):
            msg = f"键 {key} 的值不是整数类型: {type(current)}"
            raise ValueError(msg)

        new_value = current + delta
        self._backend.set(key, new_value)
        return new_value

    async def aincrement(self, key: CacheKey, delta: int = 1) -> int:
        """
        原子递增计数器(异步)

        Args:
            key: 缓存键
            delta: 增量,默认为 1

        Returns:
            递增后的值

        Raises:
            ValueError: 当前值不是整数
            CacheBackendError: 后端操作失败

        示例:
            >>> await cache.aset("counter", 10)
            >>> new_value = await cache.aincrement("counter", 5)
        """
        current = await self._backend.aget(key)
        if current is None:
            current = 0

        if not isinstance(current, int):
            msg = f"键 {key} 的值不是整数类型: {type(current)}"
            raise ValueError(msg)

        new_value = current + delta
        await self._backend.aset(key, new_value)
        return new_value

    def decrement(self, key: CacheKey, delta: int = 1) -> int:
        """
        原子递减计数器(同步)

        Args:
            key: 缓存键
            delta: 减量,默认为 1

        Returns:
            递减后的值

        Raises:
            ValueError: 当前值不是整数
            CacheBackendError: 后端操作失败

        示例:
            >>> cache.set("counter", 10)
            >>> new_value = cache.decrement("counter", 3)
            >>> print(new_value)  # 7
        """
        return self.increment(key, -delta)

    async def adecrement(self, key: CacheKey, delta: int = 1) -> int:
        """
        原子递减计数器(异步)

        Args:
            key: 缓存键
            delta: 减量,默认为 1

        Returns:
            递减后的值

        Raises:
            ValueError: 当前值不是整数
            CacheBackendError: 后端操作失败

        示例:
            >>> new_value = await cache.adecrement("counter", 3)
        """
        return await self.aincrement(key, -delta)

    def ttl(self, key: CacheKey) -> int | None:
        """
        获取键的剩余生存时间(同步)

        Args:
            key: 缓存键

        Returns:
            剩余秒数,如果键不存在或永不过期返回 None

        Raises:
            CacheBackendError: 后端操作失败

        注意:
            不同后端的实现精度可能不同

        示例:
            >>> cache.set("temp", "value", ttl=60)
            >>> remaining = cache.ttl("temp")
            >>> print(f"剩余 {remaining} 秒")
        """
        # 默认实现:检查是否存在,但无法获取精确 TTL
        # 子类可以重写此方法提供更精确的实现
        if not self._backend.exists(key):
            return None

        # 对于 MemoryBackend,可以访问内部数据
        if hasattr(self._backend, "_cache"):
            cache_data = self._backend._cache.get(key)
            if cache_data is None:
                return None
            _, expires_at = cache_data
            if expires_at is None:
                return None
            remaining = int(expires_at - time.time())
            return remaining if remaining > 0 else None

        # 其他后端无法精确获取,返回 None
        return None

    # ========== 便捷别名 ==========

    def mget(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取(get_many 的别名)

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典

        示例:
            >>> results = cache.mget(["key1", "key2", "key3"])
        """
        return self.get_many(keys)

    async def amget(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取(aget_many 的别名)(异步)

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典

        示例:
            >>> results = await cache.amget(["key1", "key2"])
        """
        return await self.aget_many(keys)

    def mset(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置(set_many 的别名)

        Args:
            mapping: 键值对字典
            ttl: 过期时间(秒)

        示例:
            >>> cache.mset({"key1": "val1", "key2": "val2"}, ttl=300)
        """
        self.set_many(mapping, ttl=ttl)

    async def amset(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置(aset_many 的别名)(异步)

        Args:
            mapping: 键值对字典
            ttl: 过期时间(秒)

        示例:
            >>> await cache.amset({"key1": "val1", "key2": "val2"})
        """
        await self.aset_many(mapping, ttl=ttl)

    # ========== 统计与健康检查 ==========

    def __len__(self) -> int:
        """
        获取缓存条目数量

        Returns:
            缓存中的键数量

        示例:
            >>> print(f"缓存中有 {len(cache)} 个条目")
        """
        if hasattr(self._backend, "_cache"):
            return len(self._backend._cache)
        return 0

    def check_health(self) -> bool:
        """
        检查后端健康状态

        Returns:
            True 表示健康,False 表示异常

        示例:
            >>> if cache.check_health():
            ...     print("缓存服务正常")
        """
        try:
            # 尝试设置和获取测试键
            test_key = "__health_check__"
            test_value = "ok"
            self._backend.set(test_key, test_value, ttl=1)
            result = self._backend.get(test_key)
            self._backend.delete(test_key)
            return result == test_value
        except Exception:
            return False

    async def acheck_health(self) -> bool:
        """
        检查后端健康状态(异步)

        Returns:
            True 表示健康,False 表示异常

        示例:
            >>> is_healthy = await cache.acheck_health()
        """
        try:
            test_key = "__health_check__"
            test_value = "ok"
            await self._backend.aset(test_key, test_value, ttl=1)
            result = await self._backend.aget(test_key)
            await self._backend.adelete(test_key)
            return result == test_value
        except Exception:
            return False

    def keys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """
        扫描缓存键(同步)

        支持模式匹配和分页。

        Args:
            pattern: 匹配模式(支持通配符 * 和 ?)
            cursor: 游标位置(0 表示开始)
            count: 每页返回的键数量
            max_keys: 最多返回的键数量

        Returns:
            KeysPage 对象

        示例:
            >>> page = cache.keys(pattern="user:*", count=100)
            >>> print(f"找到 {len(page.keys)} 个键")
            >>> if page.has_more:
            ...     next_page = cache.keys(cursor=page.cursor)
        """

        return self._backend.keys(pattern=pattern, cursor=cursor, count=count, max_keys=max_keys)

    async def akeys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """
        扫描缓存键(异步)

        Args:
            pattern: 匹配模式
            cursor: 游标位置
            count: 每页返回的键数量
            max_keys: 最多返回的键数量

        Returns:
            KeysPage 对象

        示例:
            >>> page = await cache.akeys(pattern="session:*")
        """
        return await self._backend.akeys(
            pattern=pattern, cursor=cursor, count=count, max_keys=max_keys
        )

    def close(self) -> None:
        """
        关闭后端连接(同步)

        释放所有资源,关闭网络连接等。

        示例:
            >>> cache.close()
        """
        self._backend.close()

    async def aclose(self) -> None:
        """
        关闭后端连接(异步)

        示例:
            >>> await cache.aclose()
        """
        await self._backend.aclose()

    # ========== 工厂方法 ==========

    # ========== 装饰器方法 ==========

    def cache(
        self,
        ttl: int | None = None,
        key_builder: KeyBuilder | None = None,
        key_prefix: str = "",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        缓存装饰器（绑定到此管理器实例）

        提供更便利的装饰器方式，无需每次都传入 manager 参数。

        Args:
            ttl: 缓存过期时间（秒），None 表示永不过期
            key_builder: 自定义键生成函数
            key_prefix: 键前缀（用于命名空间隔离）

        Returns:
            装饰器函数

        示例：
            >>> cache = CacheManager(backend=MemoryBackend())
            >>>
            >>> @cache.cache(ttl=3600, key_prefix="user:")
            >>> def get_user(user_id: int):
            ...     return db.query(User).get(user_id)
            >>>
            >>> user = get_user(123)  # 缓存 1 小时
        """
        from .decorators import cache as cache_decorator

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return cache_decorator(
                self,
                ttl=ttl,
                key_builder=key_builder,
                key_prefix=key_prefix,
            )(func)

        return decorator

    def acache(
        self,
        ttl: int | None = None,
        key_builder: KeyBuilder | None = None,
        key_prefix: str = "",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        异步缓存装饰器（绑定到此管理器实例）

        提供更便利的装饰器方式，无需每次都传入 manager 参数。

        Args:
            ttl: 缓存过期时间（秒），None 表示永不过期
            key_builder: 自定义键生成函数
            key_prefix: 键前缀

        Returns:
            装饰器函数

        示例：
            >>> cache = CacheManager(backend=MemoryBackend())
            >>>
            >>> @cache.acache(ttl=600)
            >>> async def fetch_data(api_url: str):
            ...     async with httpx.AsyncClient() as client:
            ...         response = await client.get(api_url)
            ...         return response.json()
            >>>
            >>> data = await fetch_data("https://api.example.com/users")
        """
        from .decorators import acache as acache_decorator

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return acache_decorator(
                self,
                ttl=ttl,
                key_builder=key_builder,
                key_prefix=key_prefix,
            )(func)

        return decorator

    def cache_invalidate(
        self,
        key_builder: KeyBuilder | None = None,
        key_prefix: str = "",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        缓存失效装饰器（绑定到此管理器实例）

        在函数执行后，删除对应的缓存。
        常用于更新操作（如 update_user 后清除 get_user 缓存）。

        Args:
            key_builder: 键生成函数（需与 @cache 一致）
            key_prefix: 键前缀

        Returns:
            装饰器函数

        示例：
            >>> cache = CacheManager(backend=MemoryBackend())
            >>>
            >>> @cache.cache(key_prefix="user:")
            >>> def get_user(user_id: int):
            ...     return db.query(User).get(user_id)
            >>>
            >>> @cache.cache_invalidate(key_prefix="user:")
            >>> def update_user(user_id: int, **updates):
            ...     db.query(User).filter_by(id=user_id).update(updates)
            ...     db.commit()
            >>>
            >>> get_user(123)  # 缓存结果
            >>> update_user(123, name="Bob")  # 清除缓存
            >>> get_user(123)  # 重新查询数据库
        """
        from .decorators import cache_invalidate as cache_invalidate_decorator

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return cache_invalidate_decorator(
                self,
                key_builder=key_builder,
                key_prefix=key_prefix,
            )(func)

        return decorator

    @classmethod
    def from_config(cls, config: CacheConfig | dict[str, Any] | str | Path) -> CacheManager:
        """
        从配置创建缓存管理器

        支持多种输入类型:
        - CacheConfig 对象
        - dict 配置字典
        - str/Path 配置文件路径

        Args:
            config: 配置对象、字典或文件路径

        Returns:
            配置好的 CacheManager 实例

        Raises:
            CacheConfigError: 配置验证失败
            ImportError: 缺少必需的依赖

        示例:
            >>> # 从字典创建
            >>> cache = CacheManager.from_config({"backend": "memory"})
            >>>
            >>> # 从文件创建
            >>> cache = CacheManager.from_config("config/cache.yaml")
            >>>
            >>> # 从 CacheConfig 对象创建
            >>> config = CacheConfig.from_file("cache.toml")
            >>> cache = CacheManager.from_config(config)
        """
        from .config import CacheConfig

        # 统一转换为 CacheConfig 对象
        if isinstance(config, dict):
            config_obj = CacheConfig(**config)
        elif isinstance(config, str | Path):
            config_obj = CacheConfig.from_file(config)
        elif isinstance(config, CacheConfig):
            config_obj = config
        else:
            msg = f"不支持的配置类型: {type(config)}"
            raise TypeError(msg)

        # 创建后端
        backend = config_obj.create_backend()

        # 创建管理器
        return cls(backend=backend)

    @classmethod
    def from_env(cls, prefix: str = "SYMPHRA_CACHE_") -> CacheManager:
        """
        从环境变量创建缓存管理器

        环境变量命名规则:
        - SYMPHRA_CACHE_BACKEND=memory
        - SYMPHRA_CACHE_MAX_SIZE=10000
        - SYMPHRA_CACHE_REDIS_HOST=localhost
        - SYMPHRA_CACHE_REDIS_PORT=6379

        Args:
            prefix: 环境变量前缀,默认为 "SYMPHRA_CACHE_"

        Returns:
            配置好的 CacheManager 实例

        Raises:
            CacheConfigError: 配置验证失败

        示例:
            >>> # 设置环境变量
            >>> os.environ["SYMPHRA_CACHE_BACKEND"] = "redis"
            >>> os.environ["SYMPHRA_CACHE_REDIS_HOST"] = "localhost"
            >>>
            >>> # 从环境变量创建
            >>> cache = CacheManager.from_env()
        """
        from .config import CacheConfig

        config = CacheConfig.from_env(prefix=prefix)
        backend = config.create_backend()
        return cls(backend=backend)

    @classmethod
    def from_file(cls, file_path: str | Path) -> CacheManager:
        """
        从配置文件创建缓存管理器

        支持的格式:
        - YAML (.yaml, .yml)
        - TOML (.toml)
        - JSON (.json)

        Args:
            file_path: 配置文件路径

        Returns:
            配置好的 CacheManager 实例

        Raises:
            CacheConfigError: 文件读取或解析失败

        示例:
            >>> # 从 YAML 文件创建
            >>> cache = CacheManager.from_file("config/cache.yaml")
            >>>
            >>> # 从 TOML 文件创建
            >>> cache = CacheManager.from_file("config/cache.toml")
        """
        from .config import CacheConfig

        config = CacheConfig.from_file(file_path)
        backend = config.create_backend()
        return cls(backend=backend)


# ========== 便利工厂函数 ==========


def create_memory_cache(
    max_size: int = 10000,
    cleanup_interval: int = 300,
) -> CacheManager:
    """
    创建内存缓存管理器的便利函数

    这是最常见的使用方式，适合开发和测试环境。
    使用 LRU（最近最少使用）作为默认淘汰策略。

    Args:
        max_size: 最大缓存项数量（默认 10000）
        cleanup_interval: TTL 清理间隔秒数（默认 300 秒）

    Returns:
        配置好的 CacheManager 实例

    示例：
        >>> cache = create_memory_cache(max_size=5000)
        >>> cache.set("key", "value", ttl=3600)
        >>> value = cache.get("key")
    """
    from .backends import MemoryBackend

    backend = MemoryBackend(
        max_size=max_size,
        cleanup_interval=cleanup_interval,
    )
    return CacheManager(backend=backend)


def create_file_cache(
    db_path: str | Path = "cache.db",
    max_size: int = 100000,
) -> CacheManager:
    """
    创建文件缓存管理器的便利函数

    适合单机部署，需要持久化缓存的场景。

    Args:
        db_path: SQLite 数据库文件路径（默认为 'cache.db'）
        max_size: 最大缓存项数量（默认 100000）

    Returns:
        配置好的 CacheManager 实例

    示例：
        >>> from pathlib import Path
        >>> cache = create_file_cache(db_path=Path("./data/cache.db"))
        >>> cache.set("key", "value", ttl=86400)
    """
    from pathlib import Path

    from .backends import FileBackend

    db_path = Path(db_path) if isinstance(db_path, str) else db_path
    backend = FileBackend(db_path=db_path, max_size=max_size)
    return CacheManager(backend=backend)


def create_redis_cache(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> CacheManager:
    """
    创建 Redis 缓存管理器的便利函数

    适合分布式部署，需要多实例共享缓存的场景。

    Args:
        host: Redis 服务器地址（默认 'localhost'）
        port: Redis 服务器端口（默认 6379）
        db: Redis 数据库编号（默认 0）
        password: Redis 密码（可选）

    Returns:
        配置好的 CacheManager 实例

    Raises:
        ImportError: 如果 redis 库未安装

    示例：
        >>> cache = create_redis_cache(host="redis.example.com", port=6379)
        >>> cache.set("key", "value", ttl=3600)
    """
    from .backends import RedisBackend

    backend = RedisBackend(host=host, port=port, db=db, password=password)
    return CacheManager(backend=backend)
