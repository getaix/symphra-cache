"""
后端抽象基类模块

本模块定义了所有缓存后端必须实现的接口。
遵循 SOLID 原则中的接口隔离和依赖倒置原则。

设计原则：
- 单一职责：每个方法只负责一个操作
- 开闭原则：子类可扩展，但基类接口稳定
- 里氏替换：所有后端可无缝替换
- 接口隔离：基础接口 + 可选批量操作
- 依赖倒置：依赖抽象而非具体实现
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import CacheKey, CacheValue, KeysPage


class BaseBackend(ABC):
    """
    缓存后端抽象基类

    所有缓存后端（Memory、File、Redis）都必须继承此类并实现所有抽象方法。
    遵循里氏替换原则，所有子类可以无缝替换使用。

    核心方法分为三类：
    1. 基础操作：get/set/delete/exists/clear（必须实现）
    2. 异步操作：aget/aset/adelete（必须实现）
    3. 批量操作：get_many/set_many/delete_many（可选，有默认实现）

    使用示例：
        >>> backend = MemoryBackend()
        >>> backend.set("user:123", {"name": "Alice"}, ttl=3600)
        >>> user = backend.get("user:123")
    """

    # ========== 同步基础操作（必须实现）==========

    @abstractmethod
    def get(self, key: CacheKey) -> CacheValue | None:
        """
        同步获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None

        Raises:
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    @abstractmethod
    def set(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> bool:
        """
        同步设置缓存值

        Args:
            key: 缓存键
            value: 缓存值（任意可序列化对象）
            ttl: 过期时间（秒），None 表示永不过期
            ex: 如果为 True,ttl 表示相对过期时间;否则表示绝对过期时间戳
            nx: 如果为 True,仅当键不存在时才设置(SET NX)

        Returns:
            是否设置成功(nx=True 时可能返回 False)

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: CacheKey) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            如果键存在并成功删除返回 True，否则返回 False

        Raises:
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: CacheKey) -> bool:
        """
        检查键是否存在

        Args:
            key: 缓存键

        Returns:
            如果键存在且未过期返回 True，否则返回 False

        Raises:
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        清空所有缓存

        警告:
            此操作不可逆，会删除所有缓存数据

        Raises:
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    async def aclear(self) -> None:
        """
        清空所有缓存（异步）

        警告:
            此操作不可逆，会删除所有缓存数据

        Raises:
            CacheBackendError: 后端操作失败
        """
        # 默认实现：调用同步版本
        self.clear()

    # ========== 异步基础操作（必须实现）==========

    @abstractmethod
    async def aget(self, key: CacheKey) -> CacheValue | None:
        """
        异步获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None

        Raises:
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    @abstractmethod
    async def aset(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> bool:
        """
        异步设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 表示永不过期
            ex: 如果为 True,ttl 表示相对过期时间;否则表示绝对过期时间戳
            nx: 如果为 True,仅当键不存在时才设置(SET NX)

        Returns:
            是否设置成功

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    @abstractmethod
    async def adelete(self, key: CacheKey) -> bool:
        """
        异步删除缓存

        Args:
            key: 缓存键

        Returns:
            如果键存在并成功删除返回 True，否则返回 False

        Raises:
            CacheBackendError: 后端操作失败
        """
        raise NotImplementedError

    # ========== 批量操作（可选实现，提供默认实现）==========

    def get_many(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取缓存值（同步）

        默认实现：循环调用 get() 方法
        子类可覆盖此方法以提供更高效的批量实现（如 Redis MGET）

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典，不存在的键不包含在结果中

        Raises:
            CacheBackendError: 后端操作失败
        """
        result: dict[CacheKey, CacheValue] = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def aget_many(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取缓存值（异步）

        默认实现：循环调用 aget() 方法
        子类可覆盖此方法以提供更高效的批量实现（如 Redis MGET）

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典，不存在的键不包含在结果中

        Raises:
            CacheBackendError: 后端操作失败
        """
        result: dict[CacheKey, CacheValue] = {}
        for key in keys:
            value = await self.aget(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置缓存值（同步）

        默认实现：循环调用 set() 方法
        子类可覆盖此方法以提供更高效的批量实现（如 Redis MSET）

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None 表示永不过期

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败
        """
        for key, value in mapping.items():
            self.set(key, value, ttl=ttl)

    async def aset_many(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置缓存值（异步）

        默认实现：循环调用 aset() 方法
        子类可覆盖此方法以提供更高效的批量实现（如 Redis MSET）

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None 表示永不过期

        Raises:
            CacheSerializationError: 序列化失败
            CacheBackendError: 后端操作失败
        """
        for key, value in mapping.items():
            await self.aset(key, value, ttl=ttl)

    def delete_many(self, keys: list[CacheKey]) -> int:
        """
        批量删除缓存（同步）

        默认实现：循环调用 delete() 方法
        子类可覆盖此方法以提供更高效的批量实现（如 Redis DEL）

        Args:
            keys: 缓存键列表

        Returns:
            成功删除的键数量

        Raises:
            CacheBackendError: 后端操作失败
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    async def adelete_many(self, keys: list[CacheKey]) -> int:
        """
        批量删除缓存（异步）

        默认实现：循环调用 adelete() 方法
        子类可覆盖此方法以提供更高效的批量实现（如 Redis DEL）

        Args:
            keys: 缓存键列表

        Returns:
            成功删除的键数量

        Raises:
            CacheBackendError: 后端操作失败
        """
        count = 0
        for key in keys:
            if await self.adelete(key):
                count += 1
        return count

    # ========== 扩展操作 ==========

    def keys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """
        扫描缓存键(同步)

        支持模式匹配和分页,避免一次性返回所有键导致内存问题。

        Args:
            pattern: 匹配模式(支持通配符 * 和 ?)
            cursor: 游标位置(0 表示开始)
            count: 每页返回的键数量建议值
            max_keys: 最多返回的键数量(None 表示不限制)

        Returns:
            KeysPage 对象,包含键列表、下一页游标等信息

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> page = backend.keys(pattern="user:*", count=100)
            >>> print(page.keys)
            >>> if page.has_more:
            ...     next_page = backend.keys(cursor=page.cursor)
        """
        from ..types import KeysPage

        # 默认实现:返回空结果
        # 子类应该重写此方法提供实际实现
        return KeysPage(keys=[], cursor=0, has_more=False, total_scanned=0)

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
            >>> page = await backend.akeys(pattern="session:*")
        """
        # 默认实现:调用同步版本
        # 子类可以重写提供真正的异步实现
        return self.keys(pattern=pattern, cursor=cursor, count=count, max_keys=max_keys)

    def ttl(self, key: CacheKey) -> int:
        """
        获取键的剩余生存时间(同步)

        Args:
            key: 缓存键

        Returns:
            剩余秒数,-1 表示永不过期,-2 表示键不存在

        Raises:
            CacheBackendError: 后端操作失败

        示例:
            >>> remaining = backend.ttl("session:123")
            >>> if remaining > 0:
            ...     print(f"还剩 {remaining} 秒过期")
        """
        # 默认实现:返回 -2(键不存在)
        # 子类应该重写此方法
        return -2 if not self.exists(key) else -1

    async def attl(self, key: CacheKey) -> int:
        """
        获取键的剩余生存时间(异步)

        Args:
            key: 缓存键

        Returns:
            剩余秒数,-1 表示永不过期,-2 表示键不存在

        示例:
            >>> remaining = await backend.attl("user:456")
        """
        # 默认实现:调用同步版本
        return self.ttl(key)

    @abstractmethod
    def close(self) -> None:
        """
        关闭后端连接(同步)

        释放所有资源,关闭网络连接、文件句柄等。
        调用此方法后,后端实例不应再被使用。

        示例:
            >>> backend.close()
        """
        # 子类必须实现
        ...

    async def aclose(self) -> None:
        """
        关闭后端连接(异步)

        示例:
            >>> await backend.aclose()
        """
        # 默认实现:调用同步版本
        self.close()

    def check_health(self) -> bool:
        """
        检查后端健康状态(同步)

        Returns:
            True 表示健康,False 表示异常

        示例:
            >>> if backend.check_health():
            ...     print("后端正常")
        """
        try:
            # 默认实现:尝试设置和获取测试键
            test_key = "__health_check__"
            test_value = "ok"
            self.set(test_key, test_value, ttl=1)
            result = self.get(test_key)
            self.delete(test_key)
            return result == test_value
        except Exception:
            return False

    async def acheck_health(self) -> bool:
        """
        检查后端健康状态(异步)

        Returns:
            True 表示健康,False 表示异常

        示例:
            >>> is_healthy = await backend.acheck_health()
        """
        try:
            test_key = "__health_check__"
            test_value = "ok"
            await self.aset(test_key, test_value, ttl=1)
            result = await self.aget(test_key)
            await self.adelete(test_key)
            return result == test_value
        except Exception:
            return False
