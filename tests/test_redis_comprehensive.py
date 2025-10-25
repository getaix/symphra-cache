"""
Redis 后端的全面测试（支持 mock 和真实 Redis）

提供完整的 Redis 后端测试覆盖。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from symphra_cache.backends import RedisBackend
from symphra_cache.serializers import PickleSerializer


class TestRedisBackendBasics:
    """Redis 后端基础测试"""

    def test_redis_backend_initialization(self) -> None:
        """测试 Redis 后端初始化"""
        try:
            # 创建后端
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=0,
                key_prefix="test:",
            )

            # 验证初始化成功
            assert backend._key_prefix == "test:"
            assert backend is not None
        except ImportError:
            # 如果 redis 未安装，跳过
            pytest.skip("redis 未安装")

    def test_redis_backend_default_prefix(self) -> None:
        """测试 Redis 后端的默认前缀"""
        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 验证默认前缀
            assert backend._key_prefix == "symphra:"
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_custom_serializer(self) -> None:
        """测试 Redis 后端的自定义序列化器"""
        try:
            serializer = PickleSerializer()
            backend = RedisBackend(
                host="localhost",
                port=6379,
                serialization_mode="pickle"
            )
            # 验证后端被初始化
            assert backend is not None
            assert backend._serializer is not None
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_repr(self) -> None:
        """测试 Redis 后端的字符串表示"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="app:")
            repr_str = repr(backend)
            # 验证 repr 包含关键信息
            assert "RedisBackend" in repr_str
            assert "app:" in repr_str
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendWithMockBasics:
    """使用 Mock 进行基础测试"""

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_initialization_with_mock(self, mock_aioredis, mock_redis) -> None:
        """测试 Redis 后端初始化 (使用 Mock)"""
        # Mock 返回值
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            # 创建后端
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=0,
                key_prefix="test:",
            )

            # 验证初始化成功
            assert backend._key_prefix == "test:"
            assert backend is not None
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_make_key(self, mock_aioredis, mock_redis) -> None:
        """测试 Redis 后端的键生成"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="app:")
            # 测试 _make_key 方法
            full_key = backend._make_key("mykey")
            assert full_key == "app:mykey"
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_multiple_prefixes(self, mock_aioredis, mock_redis) -> None:
        """测试 Redis 后端的多个前缀"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            # 创建多个后端，使用不同的前缀
            backend1 = RedisBackend(host="localhost", port=6379, key_prefix="cache1:")
            backend2 = RedisBackend(host="localhost", port=6379, key_prefix="cache2:")

            # 验证前缀不同
            assert backend1._key_prefix != backend2._key_prefix
            assert backend1._make_key("key") != backend2._make_key("key")
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendAsync:
    """Redis 后端的异步操作测试"""

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    @pytest.mark.asyncio
    async def test_redis_backend_async_client_creation(self, mock_aioredis, mock_redis) -> None:
        """测试 Redis 后端的异步客户端创建"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 验证异步客户端被创建
            assert backend._async_client is not None
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    @pytest.mark.asyncio
    async def test_redis_backend_both_clients(self, mock_aioredis, mock_redis) -> None:
        """测试 Redis 后端的同步和异步客户端"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 验证两个客户端都被创建
            assert backend._client is not None
            assert backend._async_client is not None
            # 验证它们是不同的对象
            assert backend._client != backend._async_client
        except ImportError:
            pytest.skip("redis 未安装")
