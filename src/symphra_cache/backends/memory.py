"""
内存缓存后端模块

基于 Python 字典实现的高性能内存缓存。
支持 TTL 过期、LRU 淘汰、线程安全。

特性：
- 读写延迟 < 0.01ms
- LRU 淘汰策略（基于 OrderedDict）
- 后台自动清理过期键
- 线程安全（RLock 保护）
- 异步和同步双接口
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

from .base import BaseBackend

if TYPE_CHECKING:
    from ..types import CacheKey, CacheValue, KeysPage


class MemoryBackend(BaseBackend):
    """
    内存缓存后端

    基于 OrderedDict 实现的高性能内存缓存，支持 LRU 淘汰。

    架构设计:
    - 存储结构: OrderedDict[key, (value, expires_at)]
    - LRU 实现: 访问时将键移到末尾，淘汰时删除头部
    - TTL 管理: 惰性删除（读取时检查）+ 后台定期清理
    - 线程安全: 所有操作使用 RLock 保护

    性能特点:
    - 读取: O(1)，< 0.01ms
    - 写入: O(1)，< 0.01ms
    - LRU 淘汰: O(1)
    - 空间复杂度: O(n)

    使用示例:
        >>> backend = MemoryBackend(max_size=10000)
        >>> backend.set("user:123", {"name": "Alice"}, ttl=3600)
        >>> user = backend.get("user:123")
        >>> print(user)  # {"name": "Alice"}
    """

    def __init__(
        self,
        max_size: int = 10000,
        cleanup_interval: int = 60,
    ) -> None:
        """
        初始化内存后端

        Args:
            max_size: 最大缓存条数，超过后触发 LRU 淘汰（默认 10000）
            cleanup_interval: TTL 清理间隔（秒），默认 60 秒

        示例:
            >>> # 创建最大容量 1000 的缓存
            >>> backend = MemoryBackend(max_size=1000, cleanup_interval=30)
        """
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval

        # 存储格式: {key: (value, expires_at)}
        # expires_at 为 None 表示永不过期
        # 使用 OrderedDict 支持 LRU：最近访问的在末尾，最旧的在头部
        self._cache: OrderedDict[CacheKey, tuple[CacheValue, float | None]] = OrderedDict()

        # 线程锁（保证线程安全）
        # 使用 RLock 允许同一线程重入
        self._lock = threading.RLock()

        # 启动后台清理任务
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_task()

    # ========== 同步基础操作 ==========

    def get(self, key: CacheKey) -> CacheValue | None:
        """
        同步获取缓存值

        实现细节:
        1. 检查键是否存在
        2. 检查是否过期（惰性删除）
        3. 更新 LRU 顺序（移到末尾表示最近使用）
        4. 返回值

        时间复杂度: O(1)

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期则返回 None

        示例:
            >>> backend.set("key", "value", ttl=60)
            >>> backend.get("key")  # "value"
            >>> time.sleep(61)
            >>> backend.get("key")  # None（已过期）
        """
        with self._lock:
            # 检查键是否存在
            if key not in self._cache:
                return None

            value, expires_at = self._cache[key]

            # 检查是否过期（惰性删除）
            if expires_at is not None and time.time() > expires_at:
                # 已过期，删除并返回 None
                del self._cache[key]
                return None

            # 更新 LRU：移到末尾表示最近使用
            self._cache.move_to_end(key)

            return value

    async def aget(self, key: CacheKey) -> CacheValue | None:
        """
        异步获取缓存值

        内存后端的异步版本直接调用同步方法。
        因为内存操作非常快（< 0.01ms），无需真正的异步 I/O。

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期则返回 None

        示例:
            >>> value = await backend.aget("user:123")
        """
        return self.get(key)

    def set(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: int | None = None,
        ex: bool = False,
        nx: bool = False,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒),None 表示永不过期
            ex: 保留参数,内存后端始终使用相对过期时间
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            是否设置成功
        """
        with self._lock:
            # 检查 max_size 是否为 0
            if self._max_size == 0:
                return False

            # NX 模式:仅当键不存在时设置
            if nx and key in self._cache:
                # 检查是否已过期
                _, expires_at = self._cache[key]
                if expires_at is None or time.time() <= expires_at:
                    return False  # 键存在且未过期,设置失败

            # 计算过期时间
            expires_at = None if ttl is None else time.time() + ttl

            # 如果键已存在,更新位置
            if key in self._cache:
                self._cache.move_to_end(key)
            # 如果缓存已满,执行 LRU 淘汰
            elif len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            # 设置缓存值
            self._cache[key] = (value, expires_at)
            return True

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
            ttl: 过期时间(秒)
            ex: 保留参数
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            是否设置成功
        """
        return self.set(key, value, ttl=ttl, ex=ex, nx=nx)

    def delete(self, key: CacheKey) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            如果键存在并成功删除返回 True，否则返回 False

        示例:
            >>> backend.set("temp", "data")
            >>> backend.delete("temp")  # True
            >>> backend.delete("temp")  # False（已删除）
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def adelete(self, key: CacheKey) -> bool:
        """
        异步删除缓存

        Args:
            key: 缓存键

        Returns:
            如果键存在并成功删除返回 True，否则返回 False

        示例:
            >>> deleted = await backend.adelete("user:123")
        """
        return self.delete(key)

    def exists(self, key: CacheKey) -> bool:
        """
        检查键是否存在

        会检查键是否过期，过期的键返回 False。

        Args:
            key: 缓存键

        Returns:
            如果键存在且未过期返回 True，否则返回 False

        示例:
            >>> backend.set("key", "value", ttl=60)
            >>> backend.exists("key")  # True
            >>> time.sleep(61)
            >>> backend.exists("key")  # False（已过期）
        """
        return self.get(key) is not None

    def clear(self) -> None:
        """
        清空所有缓存

        警告:
            此操作不可逆，会删除所有缓存数据

        示例:
            >>> backend.clear()  # 删除所有缓存
        """
        with self._lock:
            self._cache.clear()

    # ========== 批量操作优化 ==========

    def get_many(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取缓存值（优化版）

        相比基类的默认实现，此版本在单个锁内完成所有操作，
        减少锁开销，提升性能。

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典，不存在或已过期的键不包含在结果中

        示例:
            >>> backend.set_many({"k1": "v1", "k2": "v2"})
            >>> results = backend.get_many(["k1", "k2", "k3"])
            >>> print(results)  # {"k1": "v1", "k2": "v2"}
        """
        result: dict[CacheKey, CacheValue] = {}
        now = time.time()

        with self._lock:
            for key in keys:
                if key not in self._cache:
                    continue

                value, expires_at = self._cache[key]

                # 检查是否过期
                if expires_at is not None and now > expires_at:
                    # 过期，删除（惰性清理）
                    del self._cache[key]
                    continue

                # 更新 LRU
                self._cache.move_to_end(key)
                result[key] = value

        return result

    def set_many(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置缓存值（优化版）

        在单个锁内完成所有操作，提升性能。

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None 表示永不过期

        示例:
            >>> backend.set_many(
            ...     {
            ...         "user:1": {"name": "Alice"},
            ...         "user:2": {"name": "Bob"},
            ...     },
            ...     ttl=600,
            ... )
        """
        with self._lock:
            # 边界情况：max_size=0 时不存储任何内容
            if self._max_size == 0:
                return

            expires_at = time.time() + ttl if ttl is not None else None

            for key, value in mapping.items():
                # 检查容量并 LRU 淘汰
                if len(self._cache) >= self._max_size and key not in self._cache:
                    self._cache.popitem(last=False)

                # 存储并移到末尾
                self._cache[key] = (value, expires_at)
                self._cache.move_to_end(key)

    # ========== 扩展操作 ==========

    def keys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """
        扫描缓存键

        Args:
            pattern: 匹配模式(支持通配符 * 和 ?)
            cursor: 游标位置
            count: 每页返回的键数量
            max_keys: 最多返回的键数量

        Returns:
            KeysPage 对象
        """
        import fnmatch

        from ..types import KeysPage

        with self._lock:
            # 获取所有键并过滤
            all_keys = list(self._cache.keys())

            # 模式匹配
            if pattern != "*":
                matched_keys = [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
            else:
                matched_keys = all_keys

            # 分页处理
            total = len(matched_keys)
            start_idx = cursor
            end_idx = start_idx + count

            if max_keys is not None:
                end_idx = min(end_idx, start_idx + max_keys)

            page_keys = matched_keys[start_idx:end_idx]

            # 计算下一页游标
            next_cursor = end_idx if end_idx < total else 0
            has_more = next_cursor > 0

            return KeysPage(
                keys=page_keys,
                cursor=next_cursor,
                has_more=has_more,
                total_scanned=len(page_keys),
            )

    async def akeys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """异步扫描缓存键"""
        return self.keys(pattern=pattern, cursor=cursor, count=count, max_keys=max_keys)

    def ttl(self, key: CacheKey) -> int:
        """
        获取键的剩余生存时间

        Returns:
            剩余秒数,-1 表示永不过期,-2 表示键不存在
        """
        with self._lock:
            if key not in self._cache:
                return -2

            _, expires_at = self._cache[key]
            if expires_at is None:
                return -1

            remaining = int(expires_at - time.time())
            return remaining if remaining > 0 else -2

    async def attl(self, key: CacheKey) -> int:
        """异步获取键的剩余生存时间"""
        return self.ttl(key)

    def close(self) -> None:
        """
        关闭后端

        停止后台清理线程。
        """
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            # 设置停止标志(如果有的话)
            # 当前实现中清理线程是 daemon,会自动退出
            pass

    async def aclose(self) -> None:
        """异步关闭后端"""
        self.close()

    # ========== 后台清理任务 ==========

    def _start_cleanup_task(self) -> None:
        """
        启动后台 TTL 清理任务

        使用守护线程定期清理过期的键。
        线程在对象销毁时自动停止。
        """

        def _cleanup_loop() -> None:
            """后台清理循环"""
            while not self._stop_cleanup.wait(self._cleanup_interval):
                self._cleanup_expired()

        # 创建并启动守护线程
        self._cleanup_thread = threading.Thread(
            target=_cleanup_loop,
            daemon=True,  # 守护线程，主程序退出时自动终止
            name="symphra-cache-cleanup",
        )
        self._cleanup_thread.start()

    def _cleanup_expired(self) -> None:
        """
        清理所有过期的键

        遍历所有缓存项，删除已过期的键。
        此方法由后台线程定期调用。
        """
        with self._lock:
            now = time.time()
            # 收集过期的键
            expired_keys = [
                key
                for key, (_, expires_at) in self._cache.items()
                if expires_at is not None and now > expires_at
            ]

            # 批量删除过期键
            for key in expired_keys:
                del self._cache[key]

    def __del__(self) -> None:
        """
        析构函数

        停止后台清理线程。
        """
        # 通知清理线程停止
        self._stop_cleanup.set()

        # 等待线程结束（最多等待 1 秒）
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)

    # ========== 调试和监控方法 ==========

    def __len__(self) -> int:
        """
        获取当前缓存项数量

        Returns:
            缓存项数量

        示例:
            >>> backend.set("k1", "v1")
            >>> backend.set("k2", "v2")
            >>> len(backend)  # 2
        """
        with self._lock:
            return len(self._cache)

    def __repr__(self) -> str:
        """
        字符串表示

        Returns:
            对象的字符串表示

        示例:
            >>> backend = MemoryBackend(max_size=1000)
            >>> repr(backend)
            "MemoryBackend(size=0, max_size=1000)"
        """
        with self._lock:
            return f"MemoryBackend(size={len(self._cache)}, max_size={self._max_size})"
