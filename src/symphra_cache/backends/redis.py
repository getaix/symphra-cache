"""
Redis 缓存后端模块

基于 redis-py 实现的分布式缓存后端。
支持集群、哨兵、持久化、原子操作。

特性：
- 分布式缓存（多进程/多机器共享）
- 高可用（Redis 哨兵/集群）
- 原子操作（Lua 脚本）
- 高性能（内存存储 + 管道优化）

使用示例：
    >>> backend = RedisBackend(host="localhost", port=6379, db=0)
    >>> backend.set("key", "value", ttl=3600)
    >>> value = backend.get("key")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import CacheBackendError, CacheConnectionError
from ..serializers import get_serializer
from ..types import SerializationMode
from .base import BaseBackend

if TYPE_CHECKING:
    from ..types import CacheKey, CacheValue, KeysPage


class RedisBackend(BaseBackend):
    """
    Redis 缓存后端

    基于 redis-py 实现的分布式缓存，支持集群和哨兵。

    架构设计：
    - 连接：ConnectionPool 复用连接
    - 序列化：可配置（JSON/Pickle/MessagePack）
    - TTL：Redis 原生 SETEX/EXPIRE
    - 原子性：Lua 脚本保证

    性能特点：
    - 读取：~0.1-1ms（网络延迟）
    - 写入：~0.1-1ms
    - 批量操作：MGET/MSET 管道优化

    使用示例：
        >>> # 单机模式
        >>> backend = RedisBackend(host="localhost", port=6379)
        >>>
        >>> # 连接池模式
        >>> from redis import ConnectionPool
        >>> pool = ConnectionPool(host="localhost", port=6379, db=0)
        >>> backend = RedisBackend(connection_pool=pool)
        >>>
        >>> # 哨兵模式
        >>> from redis.sentinel import Sentinel
        >>> sentinel = Sentinel([("sentinel1", 26379), ("sentinel2", 26379)])
        >>> backend = RedisBackend(sentinel=sentinel, service_name="mymaster")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        key_prefix: str = "symphra:",
        serialization_mode: SerializationMode | str = SerializationMode.PICKLE,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        connection_pool: Any = None,
        max_connections: int = 50,
        decode_responses: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        初始化 Redis 后端

        Args:
            host: Redis 主机地址
            port: Redis 端口
            db: 数据库编号（0-15）
            password: Redis 密码
            key_prefix: 键前缀（避免冲突）
            serialization_mode: 序列化模式
            socket_timeout: 套接字超时（秒）
            socket_connect_timeout: 连接超时（秒）
            connection_pool: 自定义连接池
            max_connections: 最大连接数
            decode_responses: 是否解码响应为字符串
            **kwargs: 其他 redis.Redis 参数

        示例：
            >>> backend = RedisBackend(
            ...     host="redis.example.com",
            ...     port=6379,
            ...     password="secret",
            ...     key_prefix="myapp:",
            ... )
        """
        try:
            import redis
            import redis.asyncio as aioredis
        except ImportError as e:
            msg = "Redis 后端需要安装 redis: pip install redis"
            raise ImportError(msg) from e

        self._key_prefix = key_prefix
        self._serializer = get_serializer(serialization_mode)

        # 创建同步客户端
        if connection_pool is not None:
            self._client = redis.Redis(connection_pool=connection_pool)
        else:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                max_connections=max_connections,
                decode_responses=decode_responses,
                **kwargs,
            )

        # 创建异步客户端
        self._async_client = aioredis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            max_connections=max_connections,
            decode_responses=decode_responses,
            **kwargs,
        )

        # 测试连接
        self._test_connection()

    # ========== 连接管理 ==========

    def _test_connection(self) -> None:
        """测试 Redis 连接"""
        try:
            self._client.ping()
        except Exception as e:
            msg = f"无法连接到 Redis 服务器: {e}"
            raise CacheConnectionError(msg) from e

    def _make_key(self, key: CacheKey) -> str:
        """生成带前缀的完整键名"""
        return f"{self._key_prefix}{key}"

    # ========== 同步基础操作 ==========

    def get(self, key: CacheKey) -> CacheValue | None:
        """
        同步获取缓存值

        使用 Redis GET 命令，自动处理 TTL 过期。

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或已过期返回 None
        """
        try:
            full_key = self._make_key(key)
            value_bytes = self._client.get(full_key)

            if value_bytes is None:
                return None

            # 反序列化
            return self._serializer.deserialize(value_bytes)

        except Exception as e:
            msg = f"Redis GET 失败: {e}"
            raise CacheBackendError(msg) from e

    async def aget(self, key: CacheKey) -> CacheValue | None:
        """异步获取缓存值"""
        try:
            full_key = self._make_key(key)
            value_bytes = await self._async_client.get(full_key)

            if value_bytes is None:
                return None

            return self._serializer.deserialize(value_bytes)

        except Exception as e:
            msg = f"Redis AGET 失败: {e}"
            raise CacheBackendError(msg) from e

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
            value: 缓存值
            ttl: 过期时间(秒)
            ex: 保留参数,Redis 始终使用相对过期时间
            nx: 如果为 True,仅当键不存在时才设置(SET NX)

        Returns:
            是否设置成功
        """
        try:
            full_key = self._make_key(key)
            value_bytes = self._serializer.serialize(value)

            # 当 ttl <= 0 或 None 时，不设置过期时间，避免 Redis invalid expire time 错误
            if ttl is not None and ttl > 0:
                result = self._client.set(
                    full_key,
                    value_bytes,
                    ex=ttl,  # 过期时间(秒)
                    nx=nx,  # 仅当不存在时设置
                )
            else:
                result = self._client.set(
                    full_key,
                    value_bytes,
                    nx=nx,
                )

            # nx=True 时,如果键已存在则返回 None
            return result is not False and result is not None

        except Exception as e:
            msg = f"Redis SET 失败: {e}"
            raise CacheBackendError(msg) from e

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
        try:
            full_key = self._make_key(key)
            value_bytes = self._serializer.serialize(value)

            if ttl is not None and ttl > 0:
                result = await self._async_client.set(
                    full_key,
                    value_bytes,
                    ex=ttl,
                    nx=nx,
                )
            else:
                result = await self._async_client.set(
                    full_key,
                    value_bytes,
                    nx=nx,
                )

            return result is not False and result is not None

        except Exception as e:
            msg = f"Redis ASET 失败: {e}"
            raise CacheBackendError(msg) from e

    def delete(self, key: CacheKey) -> bool:
        """删除缓存"""
        try:
            full_key = self._make_key(key)
            count = self._client.delete(full_key)
            return count > 0
        except Exception as e:
            msg = f"Redis DELETE 失败: {e}"
            raise CacheBackendError(msg) from e

    async def adelete(self, key: CacheKey) -> bool:
        """异步删除缓存"""
        try:
            full_key = self._make_key(key)
            count = await self._async_client.delete(full_key)
            return count > 0
        except Exception as e:
            msg = f"Redis ADELETE 失败: {e}"
            raise CacheBackendError(msg) from e

    def exists(self, key: CacheKey) -> bool:
        """检查键是否存在"""
        try:
            full_key = self._make_key(key)
            return self._client.exists(full_key) > 0
        except Exception as e:
            msg = f"Redis EXISTS 失败: {e}"
            raise CacheBackendError(msg) from e

    def clear(self) -> None:
        """
        清空所有缓存

        警告：这会删除所有带前缀的键
        """
        try:
            # 使用 SCAN 遍历所有匹配的键
            pattern = f"{self._key_prefix}*"
            cursor = 0

            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=100)

                if keys:
                    self._client.delete(*keys)

                if cursor == 0:
                    break

        except Exception as e:
            msg = f"Redis CLEAR 失败: {e}"
            raise CacheBackendError(msg) from e

    # ========== 批量操作优化 ==========

    def get_many(self, keys: list[CacheKey]) -> dict[CacheKey, CacheValue]:
        """
        批量获取（使用 MGET 优化）

        相比循环调用 get()，MGET 只需一次网络往返。
        """
        if not keys:
            return {}

        try:
            full_keys = [self._make_key(k) for k in keys]

            # 使用 MGET 批量获取
            values_bytes = self._client.mget(full_keys)

            result: dict[CacheKey, CacheValue] = {}
            for key, value_bytes in zip(keys, values_bytes, strict=False):
                if value_bytes is not None:
                    result[key] = self._serializer.deserialize(value_bytes)

            return result

        except Exception as e:
            msg = f"Redis MGET 失败: {e}"
            raise CacheBackendError(msg) from e

    def set_many(
        self,
        mapping: dict[CacheKey, CacheValue],
        ttl: int | None = None,
    ) -> None:
        """
        批量设置（使用管道优化）

        使用 Pipeline 批量提交命令，减少网络往返。
        """
        if not mapping:
            return

        try:
            # 使用 Pipeline 批量执行
            pipe = self._client.pipeline()

            for key, value in mapping.items():
                full_key = self._make_key(key)
                value_bytes = self._serializer.serialize(value)

                if ttl is not None and ttl > 0:
                    pipe.setex(full_key, ttl, value_bytes)
                else:
                    pipe.set(full_key, value_bytes)

            pipe.execute()

        except Exception as e:
            msg = f"Redis MSET 失败: {e}"
            raise CacheBackendError(msg) from e

    def delete_many(self, keys: list[CacheKey]) -> int:
        """批量删除"""
        if not keys:
            return 0

        try:
            full_keys = [self._make_key(k) for k in keys]
            return self._client.delete(*full_keys)

        except Exception as e:
            msg = f"Redis DEL 失败: {e}"
            raise CacheBackendError(msg) from e

    # ========== 高级功能 ==========

    def incr(self, key: CacheKey, delta: int = 1) -> int:
        """
        原子自增

        Args:
            key: 缓存键
            delta: 增量（默认 1）

        Returns:
            自增后的值
        """
        try:
            full_key = self._make_key(key)
            return self._client.incrby(full_key, delta)
        except Exception as e:
            msg = f"Redis INCR 失败: {e}"
            raise CacheBackendError(msg) from e

    def decr(self, key: CacheKey, delta: int = 1) -> int:
        """
        原子自减

        Args:
            key: 缓存键
            delta: 减量（默认 1）

        Returns:
            自减后的值
        """
        try:
            full_key = self._make_key(key)
            return self._client.decrby(full_key, delta)
        except Exception as e:
            msg = f"Redis DECR 失败: {e}"
            raise CacheBackendError(msg) from e

    # ========== 扩展操作 ==========

    def keys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """
        扫描缓存键(使用 SCAN)

        Args:
            pattern: 匹配模式
            cursor: 游标位置
            count: 每页返回的键数量建议值
            max_keys: 最多返回的键数量

        Returns:
            KeysPage 对象
        """
        from ..types import KeysPage

        try:
            # 添加键前缀到模式
            full_pattern = f"{self._key_prefix}{pattern}"

            # 使用 SCAN 命令
            next_cursor, keys_found = self._client.scan(
                cursor=cursor,
                match=full_pattern,
                count=count,
            )

            # 移除键前缀
            prefix_len = len(self._key_prefix)
            clean_keys = [k.decode() if isinstance(k, bytes) else k for k in keys_found]
            clean_keys = [k[prefix_len:] for k in clean_keys]

            # 限制返回数量，优先遵循 count（分页大小）
            if count is not None and count > 0:
                clean_keys = clean_keys[:count]
            # 进一步限制到 max_keys（如果提供）
            if max_keys is not None:
                clean_keys = clean_keys[:max_keys]

            return KeysPage(
                keys=clean_keys,
                cursor=next_cursor,
                has_more=next_cursor != 0,
                total_scanned=len(clean_keys),
            )

        except Exception as e:
            msg = f"Redis SCAN 失败: {e}"
            raise CacheBackendError(msg) from e

    async def akeys(
        self,
        pattern: str = "*",
        cursor: int = 0,
        count: int = 100,
        max_keys: int | None = None,
    ) -> KeysPage:
        """异步扫描缓存键"""
        from ..types import KeysPage

        try:
            full_pattern = f"{self._key_prefix}{pattern}"

            next_cursor, keys_found = await self._async_client.scan(
                cursor=cursor,
                match=full_pattern,
                count=count,
            )

            prefix_len = len(self._key_prefix)
            clean_keys = [k.decode() if isinstance(k, bytes) else k for k in keys_found]
            clean_keys = [k[prefix_len:] for k in clean_keys]

            if count is not None and count > 0:
                clean_keys = clean_keys[:count]
            if max_keys is not None:
                clean_keys = clean_keys[:max_keys]

            return KeysPage(
                keys=clean_keys,
                cursor=next_cursor,
                has_more=next_cursor != 0,
                total_scanned=len(clean_keys),
            )

        except Exception as e:
            msg = f"Redis ASCAN 失败: {e}"
            raise CacheBackendError(msg) from e

    def ttl(self, key: CacheKey) -> int:
        """
        获取键的剩余生存时间

        Returns:
            剩余秒数,-1 表示永不过期,-2 表示键不存在
        """
        try:
            full_key = self._make_key(key)
            return self._client.ttl(full_key)
        except Exception as e:
            msg = f"Redis TTL 失败: {e}"
            raise CacheBackendError(msg) from e

    async def attl(self, key: CacheKey) -> int:
        """异步获取键的剩余生存时间"""
        try:
            full_key = self._make_key(key)
            return await self._async_client.ttl(full_key)
        except Exception as e:
            msg = f"Redis ATTL 失败: {e}"
            raise CacheBackendError(msg) from e

    # ========== 调试和监控 ==========

    def __len__(self) -> int:
        """
        获取缓存键数量

        注意：使用 SCAN 遍历，大数据集可能较慢
        """
        try:
            pattern = f"{self._key_prefix}*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=100)
                count += len(keys)

                if cursor == 0:
                    break

            return count

        except Exception as e:
            msg = f"Redis 计数失败: {e}"
            raise CacheBackendError(msg) from e

    def __repr__(self) -> str:
        """字符串表示"""
        return f"RedisBackend(prefix={self._key_prefix}, client={self._client})"

    def close(self) -> None:
        """关闭 Redis 连接"""
        self._client.close()

    async def aclose(self) -> None:
        """异步关闭 Redis 连接"""
        await self._async_client.close()

    def __del__(self) -> None:
        """析构函数"""
        import contextlib

        with contextlib.suppress(Exception):
            self.close()
