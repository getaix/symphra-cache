"""
文件缓存后端模块

基于 SQLite 实现的持久化缓存后端。
支持热重载、TTL 过期、LRU 淘汰。

特性：
- 持久化存储（进程重启后数据保留）
- 热重载（开发环境下自动加载磁盘更新）
- 高性能（SQLite WAL 模式 + 索引优化）
- 多进程安全（SQLite 文件锁）

使用示例：
    >>> from pathlib import Path
    >>> backend = FileBackend(db_path=Path("./cache.db"), max_size=10000)
    >>> backend.set("key", "value", ttl=3600)
    >>> value = backend.get("key")
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

from ..exceptions import CacheBackendError
from ..serializers import get_serializer
from ..types import SerializationMode
from .base import BaseBackend

if TYPE_CHECKING:
    from ..types import CacheKey, CacheValue, KeysPage


class FileBackend(BaseBackend):
    """
    文件缓存后端

    基于 SQLite 实现的持久化缓存，支持热重载和 LRU 淘汰。

    架构设计：
    - 存储引擎：SQLite（WAL 模式，高并发）
    - 表结构：cache_entries(key PRIMARY KEY, value BLOB, expires_at REAL, last_access REAL)
    - LRU 实现：基于 last_access 字段，定期清理
    - 序列化：可配置（JSON/Pickle/MessagePack）

    性能特点：
    - 读取：~1-5ms（取决于磁盘性能）
    - 写入：~1-5ms（WAL 模式异步）
    - 热重载：文件 mtime 检测，增量加载

    使用示例：
        >>> backend = FileBackend(
        ...     db_path=Path("./cache.db"),
        ...     max_size=10000,
        ...     serialization_mode=SerializationMode.PICKLE,
        ... )
        >>> backend.set("user:123", {"name": "Alice"}, ttl=3600)
    """

    def __init__(
        self,
        db_path: Path | str = "./symphra_cache.db",
        max_size: int = 10000,
        serialization_mode: SerializationMode | str = SerializationMode.PICKLE,
        cleanup_interval: int = 300,  # 5 分钟
        enable_hot_reload: bool = False,
    ) -> None:
        """
        初始化文件后端

        Args:
            db_path: SQLite 数据库文件路径
            max_size: 最大缓存条数（超过触发 LRU 淘汰）
            serialization_mode: 序列化模式
            cleanup_interval: 清理间隔（秒）
            enable_hot_reload: 是否启用热重载（开发模式）

        示例：
            >>> backend = FileBackend(
            ...     db_path="./dev_cache.db",
            ...     enable_hot_reload=True,  # 开发环境
            ... )
        """
        self._db_path = Path(db_path)
        self._max_size = max_size
        self._serializer = get_serializer(serialization_mode)
        self._cleanup_interval = cleanup_interval
        self._enable_hot_reload = enable_hot_reload

        # 线程锁（保护同步操作）
        self._lock = threading.RLock()

        # 初始化数据库
        self._init_database()

        # 启动后台清理任务
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_task()

        # 热重载相关
        self._last_reload_time = time.time()
        self._db_mtime = self._get_db_mtime()

    # ========== 数据库初始化 ==========

    def _init_database(self) -> None:
        """
        初始化 SQLite 数据库

        创建表结构和索引，启用 WAL 模式。
        """
        # 确保父目录存在
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            # 启用 WAL 模式（Write-Ahead Logging）
            # 提升并发性能，允许读写并行
            conn.execute("PRAGMA journal_mode=WAL")

            # 启用外键约束
            conn.execute("PRAGMA foreign_keys=ON")

            # 创建缓存表
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    expires_at REAL,  -- NULL 表示永不过期
                    last_access REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """
            )

            # 创建索引（优化 TTL 清理和 LRU 淘汰）
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache_entries(expires_at)
                WHERE expires_at IS NOT NULL
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_last_access
                ON cache_entries(last_access)
            """
            )

            conn.commit()

    # ========== 同步基础操作 ==========

    def get(self, key: CacheKey) -> CacheValue | None:
        """
        同步获取缓存值

        实现细节：
        1. 查询数据库
        2. 检查 TTL 是否过期
        3. 更新 last_access（LRU）
        4. 反序列化返回

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期返回 None
        """
        # 热重载检测
        if self._enable_hot_reload:
            self._check_hot_reload()

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute(
                    "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                    (str(key),),
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                value_bytes, expires_at = row

                # 检查是否过期
                if expires_at is not None and time.time() > expires_at:
                    # 已过期，删除
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (str(key),))
                    conn.commit()
                    return None

                # 更新 last_access（LRU）
                conn.execute(
                    "UPDATE cache_entries SET last_access = ? WHERE key = ?",
                    (time.time(), str(key)),
                )
                conn.commit()

                # 反序列化
                return self._serializer.deserialize(value_bytes)

            finally:
                conn.close()

    async def aget(self, key: CacheKey) -> CacheValue | None:
        """
        异步获取缓存值

        使用 aiosqlite 实现真正的异步 I/O。
        """
        # 热重载检测
        if self._enable_hot_reload:
            self._check_hot_reload()

        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                (str(key),),
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            value_bytes, expires_at = row

            # 检查过期
            if expires_at is not None and time.time() > expires_at:
                await conn.execute("DELETE FROM cache_entries WHERE key = ?", (str(key),))
                await conn.commit()
                return None

            # 更新 last_access
            await conn.execute(
                "UPDATE cache_entries SET last_access = ? WHERE key = ?",
                (time.time(), str(key)),
            )
            await conn.commit()

            return self._serializer.deserialize(value_bytes)

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
            ttl: 过期时间(秒)
            ex: 保留参数
            nx: 如果为 True,仅当键不存在时才设置

        Returns:
            是否设置成功
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                # 序列化值
                serialized_value = self._serializer.serialize(value)

                # 计算过期时间
                now = time.time()
                expires_at = None if ttl is None else now + ttl

                # NX 模式检查
                if nx:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM cache_entries WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                        (key, now),
                    )
                    if cursor.fetchone()[0] > 0:
                        return False  # 键已存在且未过期

                # 使用 INSERT OR REPLACE
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (key, value, expires_at, last_access, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, serialized_value, expires_at, now, now),
                )

                # LRU 淘汰检查
                self._evict_if_needed(conn)

                # 统一提交所有变更
                conn.commit()

                return True

            except Exception as e:
                conn.rollback()
                msg = f"设置缓存失败: {key}"
                raise CacheBackendError(msg) from e
            finally:
                conn.close()

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
        async with aiosqlite.connect(self._db_path) as conn:
            try:
                # 序列化值
                serialized_value = self._serializer.serialize(value)

                # 计算过期时间
                now = time.time()
                expires_at = None if ttl is None else now + ttl

                # NX 模式检查
                if nx:
                    cursor = await conn.execute(
                        "SELECT COUNT(*) FROM cache_entries WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                        (key, now),
                    )
                    row = await cursor.fetchone()
                    if row[0] > 0:
                        return False

                # 插入或替换
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (key, value, expires_at, last_access, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, serialized_value, expires_at, now, now),
                )

                # LRU 淘汰
                await self._aevict_if_needed(conn)

                # 统一提交所有变更
                await conn.commit()

                return True

            except Exception as e:
                await conn.rollback()
                msg = f"异步设置缓存失败: {key}"
                raise CacheBackendError(msg) from e

    def delete(self, key: CacheKey) -> bool:
        """删除缓存"""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute(
                    "DELETE FROM cache_entries WHERE key = ?",
                    (str(key),),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    async def adelete(self, key: CacheKey) -> bool:
        """异步删除缓存"""
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM cache_entries WHERE key = ?",
                (str(key),),
            )
            await conn.commit()
            return cursor.rowcount > 0

    def exists(self, key: CacheKey) -> bool:
        """检查键是否存在（未过期）"""
        return self.get(key) is not None

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute("DELETE FROM cache_entries")
                conn.commit()
            finally:
                conn.close()

    # ========== LRU 淘汰 ==========

    def _evict_if_needed(self, conn: sqlite3.Connection) -> None:
        """
        LRU 淘汰(同步版本)

        当缓存数量超过 max_size 时,删除最旧的条目。
        """
        # 获取当前条目数
        cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
        count = cursor.fetchone()[0]

        if count > self._max_size:
            # 计算需要删除的数量
            to_delete = count - self._max_size

            # 删除最旧的条目(last_access 最小)
            conn.execute(
                """
                DELETE FROM cache_entries
                WHERE key IN (
                    SELECT key FROM cache_entries
                    ORDER BY last_access ASC
                    LIMIT ?
                )
                """,
                (to_delete,),
            )

    async def _aevict_if_needed(self, conn: aiosqlite.Connection) -> None:
        """LRU 淘汰(异步版本)"""
        cursor = await conn.execute("SELECT COUNT(*) FROM cache_entries")
        row = await cursor.fetchone()
        count = row[0] if row else 0

        if count > self._max_size:
            to_delete = count - self._max_size

            await conn.execute(
                """
                DELETE FROM cache_entries
                WHERE key IN (
                    SELECT key FROM cache_entries
                    ORDER BY last_access ASC
                    LIMIT ?
                )
                """,
                (to_delete,),
            )

    # ========== 后台清理任务 ==========

    def _start_cleanup_task(self) -> None:
        """启动后台清理任务"""

        def _cleanup_loop() -> None:
            while not self._stop_cleanup.wait(self._cleanup_interval):
                self._cleanup_expired()

        self._cleanup_thread = threading.Thread(
            target=_cleanup_loop,
            daemon=True,
            name="symphra-file-cache-cleanup",
        )
        self._cleanup_thread.start()

    def _cleanup_expired(self) -> None:
        """清理过期的缓存条目"""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                now = time.time()
                conn.execute(
                    "DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at < ?",
                    (now,),
                )
                conn.commit()
            finally:
                conn.close()

    # ========== 热重载 ==========

    def _get_db_mtime(self) -> float:
        """获取数据库文件的修改时间"""
        if self._db_path.exists():
            return self._db_path.stat().st_mtime
        return 0.0

    def _check_hot_reload(self) -> None:
        """
        检查数据库文件是否被外部修改，触发热重载

        适用于开发环境，多进程共享缓存时自动同步。
        """
        current_mtime = self._get_db_mtime()
        if current_mtime > self._db_mtime:
            # 文件已更新，重新加载（这里实际上是透明的，SQLite 自动同步）
            self._db_mtime = current_mtime
            self._last_reload_time = time.time()

    # ========== 调试和监控 ==========

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
            pattern: 匹配模式（支持通配符 * 和 ?）
            cursor: 游标位置（用于分页，此实现中基于索引）
            count: 每页返回的键数量
            max_keys: 最多返回的键数量

        Returns:
            KeysPage 对象
        """
        import fnmatch

        from ..types import KeysPage

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                # 获取所有未过期的键
                now = time.time()
                cursor_obj = conn.execute(
                    "SELECT key FROM cache_entries WHERE expires_at IS NULL OR expires_at > ? ORDER BY key",
                    (now,),
                )
                all_keys = [row[0] for row in cursor_obj.fetchall()]

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

            finally:
                conn.close()

    async def akeys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """异步扫描缓存键"""
        return self.keys(pattern=pattern, cursor=cursor, count=count, max_keys=max_keys)

    def close(self) -> None:
        """
        关闭后端连接（同步）

        停止后台清理线程。
        """
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)

    async def aclose(self) -> None:
        """
        关闭后端连接（异步）
        """
        self.close()

    def __len__(self) -> int:
        """获取当前缓存条目数"""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
                return cursor.fetchone()[0]
            finally:
                conn.close()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"FileBackend(db_path={self._db_path}, size={len(self)}, max_size={self._max_size})"

    def __del__(self) -> None:
        """析构函数"""
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)
