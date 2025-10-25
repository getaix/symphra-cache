"""
缓存装饰器模块

提供易用的装饰器接口，自动缓存函数返回值。

特性：
- 支持同步和异步函数
- 自动生成缓存键
- 可自定义键生成策略
- 支持 TTL 过期
- 类型安全（泛型装饰器）

使用示例：
    >>> from symphra_cache import CacheManager, MemoryBackend
    >>> from symphra_cache.decorators import cache
    >>>
    >>> manager = CacheManager(backend=MemoryBackend())
    >>>
    >>> @cache(manager, ttl=3600)
    >>> def get_user(user_id: int):
    ...     # 数据库查询（只在缓存未命中时执行）
    ...     return {"id": user_id, "name": "Alice"}
    >>>
    >>> user = get_user(123)  # 第一次：查询数据库
    >>> user = get_user(123)  # 第二次：从缓存获取
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from .manager import CacheManager

# 泛型类型变量
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])


def default_key_builder(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """
    默认缓存键生成器

    生成策略：
    1. 函数全限定名（module.class.function）
    2. 位置参数序列化
    3. 关键字参数序列化（按键排序）
    4. MD5 哈希（避免键过长）

    Args:
        func: 被装饰的函数
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        缓存键字符串

    示例：
        >>> def get_user(user_id: int, include_posts: bool = False):
        ...     pass
        >>> key = default_key_builder(get_user, (123,), {"include_posts": True})
        >>> # 生成类似: "module.get_user:a1b2c3d4..."
    """
    # 函数全限定名
    module = func.__module__
    qualname = func.__qualname__

    # 序列化参数（使用 JSON 保证一致性）
    try:
        # 构建参数字典（包含位置参数和关键字参数）
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # 序列化为 JSON（按键排序保证一致性）
        args_json = json.dumps(
            bound_args.arguments,
            sort_keys=True,
            default=str,  # 不可序列化对象转为字符串
        )

    except Exception:
        # 降级策略：直接转字符串
        args_json = f"{args}:{sorted(kwargs.items())}"

    # 生成哈希（避免键过长）
    hash_obj = hashlib.md5(args_json.encode("utf-8"), usedforsecurity=False)
    args_hash = hash_obj.hexdigest()

    return f"{module}.{qualname}:{args_hash}"


def cache(
    manager: CacheManager,
    ttl: int | None = None,
    key_builder: Callable[[Callable[..., Any], tuple[Any, ...], dict[str, Any]], str] | None = None,
    key_prefix: str = "",
) -> Callable[[F], F]:
    """
    缓存装饰器（同步函数）

    自动缓存函数返回值，提升性能。

    Args:
        manager: 缓存管理器实例
        ttl: 缓存过期时间（秒），None 表示永不过期
        key_builder: 自定义键生成函数
        key_prefix: 键前缀（用于命名空间隔离）

    Returns:
        装饰后的函数

    示例：
        >>> @cache(manager, ttl=3600, key_prefix="user:")
        >>> def get_user(user_id: int):
        ...     return db.query(User).get(user_id)
        >>>
        >>> user = get_user(123)  # 缓存 1 小时
    """

    def decorator(func: F) -> F:
        # 使用默认键生成器
        nonlocal key_builder
        if key_builder is None:
            key_builder = default_key_builder

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            cache_key = key_prefix + key_builder(func, args, kwargs)

            # 尝试从缓存获取
            cached_value = manager.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            if result is not None:  # 不缓存 None 值
                manager.set(cache_key, result, ttl=ttl)

            return result

        return cast("F", wrapper)

    return decorator


def acache(
    manager: CacheManager,
    ttl: int | None = None,
    key_builder: Callable[[Callable[..., Any], tuple[Any, ...], dict[str, Any]], str] | None = None,
    key_prefix: str = "",
) -> Callable[[AsyncF], AsyncF]:
    """
    缓存装饰器（异步函数）

    异步版本的缓存装饰器，支持 async/await 函数。

    Args:
        manager: 缓存管理器实例
        ttl: 缓存过期时间（秒）
        key_builder: 自定义键生成函数
        key_prefix: 键前缀

    Returns:
        装饰后的异步函数

    示例：
        >>> @acache(manager, ttl=600)
        >>> async def fetch_data(api_url: str):
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get(api_url)
        ...         return response.json()
        >>>
        >>> data = await fetch_data("https://api.example.com/users")
    """

    def decorator(func: AsyncF) -> AsyncF:
        # 使用默认键生成器
        nonlocal key_builder
        if key_builder is None:
            key_builder = default_key_builder

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            cache_key = key_prefix + key_builder(func, args, kwargs)

            # 尝试从缓存获取
            cached_value = await manager.aget(cache_key)
            if cached_value is not None:
                return cached_value

            # 缓存未命中，执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            if result is not None:
                await manager.aset(cache_key, result, ttl=ttl)

            return result

        return cast("AsyncF", wrapper)

    return decorator


def cache_invalidate(
    manager: CacheManager,
    key_builder: Callable[[Callable[..., Any], tuple[Any, ...], dict[str, Any]], str] | None = None,
    key_prefix: str = "",
) -> Callable[[F], F]:
    """
    缓存失效装饰器

    在函数执行后，删除对应的缓存。
    常用于更新操作（如 update_user 后清除 get_user 缓存）。

    Args:
        manager: 缓存管理器
        key_builder: 键生成函数（需与 @cache 一致）
        key_prefix: 键前缀

    Returns:
        装饰后的函数

    示例：
        >>> @cache(manager, key_prefix="user:")
        >>> def get_user(user_id: int):
        ...     return db.query(User).get(user_id)
        >>>
        >>> @cache_invalidate(manager, key_prefix="user:")
        >>> def update_user(user_id: int, **updates):
        ...     db.query(User).filter_by(id=user_id).update(updates)
        ...     db.commit()
        >>>
        >>> get_user(123)  # 缓存结果
        >>> update_user(123, name="Bob")  # 清除缓存
        >>> get_user(123)  # 重新查询数据库
    """

    def decorator(func: F) -> F:
        nonlocal key_builder
        if key_builder is None:
            key_builder = default_key_builder

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 先执行函数
            result = func(*args, **kwargs)

            # 生成缓存键并删除
            cache_key = key_prefix + key_builder(func, args, kwargs)
            manager.delete(cache_key)

            return result

        return cast("F", wrapper)

    return decorator


class CachedProperty:
    """
    缓存属性装饰器

    类似于 functools.cached_property，但使用外部缓存后端。
    适用于需要在多个实例间共享缓存的场景。

    示例：
        >>> class User:
        ...     def __init__(self, user_id):
        ...         self.user_id = user_id
        ...
        ...     @CachedProperty(manager, ttl=600)
        ...     def profile(self):
        ...         # 数据库查询
        ...         return db.query(Profile).get(self.user_id)
        >>>
        >>> user = User(123)
        >>> profile = user.profile  # 第一次：查询数据库
        >>> profile = user.profile  # 第二次：从缓存获取
    """

    def __init__(
        self,
        manager: CacheManager,
        ttl: int | None = None,
        key_prefix: str = "",
    ) -> None:
        """
        初始化缓存属性

        Args:
            manager: 缓存管理器
            ttl: 缓存过期时间
            key_prefix: 键前缀
        """
        self.manager = manager
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.func: Callable[[Any], Any] | None = None

    def __call__(self, func: Callable[[Any], Any]) -> CachedProperty:
        """设置被装饰的方法"""
        self.func = func
        return self

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        """描述器协议：获取属性值"""
        if instance is None:
            return self

        if self.func is None:
            msg = "CachedProperty 未正确初始化"
            raise RuntimeError(msg)

        # 生成缓存键（基于类名、方法名、实例 ID）
        cache_key = f"{self.key_prefix}{owner.__name__}.{self.func.__name__}:{id(instance)}"

        # 尝试从缓存获取
        cached_value = self.manager.get(cache_key)
        if cached_value is not None:
            return cached_value

        # 缓存未命中，调用方法
        result = self.func(instance)

        # 存入缓存
        if result is not None:
            self.manager.set(cache_key, result, ttl=self.ttl)

        return result
