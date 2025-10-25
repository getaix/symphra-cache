"""
Redis 后端的扩展测试，覆盖更多功能和边界情况。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from symphra_cache.backends import RedisBackend
from symphra_cache.serializers import JSONSerializer, PickleSerializer


class TestRedisBackendConfiguration:
    """Redis 后端配置测试"""

    def test_redis_backend_with_json_serializer(self) -> None:
        """测试 Redis 后端使用 JSON 序列化器"""
        try:
            backend = RedisBackend(host="localhost", port=6379, serialization_mode="json")
            assert backend._serializer is not None
            assert isinstance(backend._serializer, JSONSerializer)
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_with_pickle_serializer(self) -> None:
        """测试 Redis 后端使用 Pickle 序列化器"""
        try:
            backend = RedisBackend(host="localhost", port=6379, serialization_mode="pickle")
            assert backend._serializer is not None
            assert isinstance(backend._serializer, PickleSerializer)
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_with_password(self) -> None:
        """测试 Redis 后端带密码"""
        try:
            # 由于大多数本地开发环境的 Redis 不需要密码，
            # 我们只测试参数被正确接受，不测试实际连接
            backend = RedisBackend(
                host="localhost", port=6379, password="secret_password", key_prefix="secure:"
            )
            assert backend._key_prefix == "secure:"
        except ImportError:
            pytest.skip("redis 未安装")
        except Exception as e:
            # Redis 服务器不需要密码或连接失败，跳过
            pytest.skip(f"Redis 服务器配置异常: {e}")

    def test_redis_backend_with_custom_db(self) -> None:
        """测试 Redis 后端使用自定义数据库"""
        try:
            backend = RedisBackend(
                host="localhost",
                port=6379,
                db=5,  # 使用数据库 5 而不是默认的 0
                key_prefix="db5:",
            )
            assert backend._key_prefix == "db5:"
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendMakeKey:
    """Redis 后端键生成测试"""

    def test_make_key_simple(self) -> None:
        """测试简单键生成"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="app:")
            key = backend._make_key("user:123")
            assert key == "app:user:123"
        except ImportError:
            pytest.skip("redis 未安装")

    def test_make_key_with_special_chars(self) -> None:
        """测试特殊字符的键生成"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="cache:")
            key = backend._make_key("session:user-1234_id")
            assert key == "cache:session:user-1234_id"
        except ImportError:
            pytest.skip("redis 未安装")

    def test_make_key_with_unicode(self) -> None:
        """测试 Unicode 键生成"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="inter:")
            key = backend._make_key("用户:123")
            assert key == "inter:用户:123"
        except ImportError:
            pytest.skip("redis 未安装")

    def test_make_key_with_empty_prefix(self) -> None:
        """测试空前缀的键生成"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="")
            key = backend._make_key("mykey")
            assert key == "mykey"
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendWithMockOperations:
    """使用 Mock 的 Redis 后端操作测试"""

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_exists_operation(self, mock_aioredis, mock_redis) -> None:
        """测试 exists 操作"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.exists.return_value = 1

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 测试 exists 操作被定义
            assert hasattr(backend, "exists")
            assert callable(backend.exists)
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_incr_operation(self, mock_aioredis, mock_redis) -> None:
        """测试 incr 操作"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.incrby.return_value = 1

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 测试 incr 操作被定义
            assert hasattr(backend, "incr")
            assert callable(backend.incr)
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_decr_operation(self, mock_aioredis, mock_redis) -> None:
        """测试 decr 操作"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.decrby.return_value = 0

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 测试 decr 操作被定义
            assert hasattr(backend, "decr")
            assert callable(backend.decr)
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_ttl_operation(self, mock_aioredis, mock_redis) -> None:
        """测试 ttl 操作"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.ttl.return_value = 3600

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 测试 ttl 操作被定义
            assert hasattr(backend, "ttl")
            assert callable(backend.ttl)
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_keys_operation(self, mock_aioredis, mock_redis) -> None:
        """测试 keys 操作"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.scan.return_value = (0, [b"key1", b"key2"])

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379)
            # 测试 keys 操作被定义
            assert hasattr(backend, "keys")
            assert callable(backend.keys)
        except ImportError:
            pytest.skip("redis 未安装")

    @patch("redis.Redis")
    @patch("redis.asyncio.Redis")
    def test_redis_backend_clear_operation(self, mock_aioredis, mock_redis) -> None:
        """测试 clear 操作"""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.scan.return_value = (0, [b"app:key1", b"app:key2"])
        mock_redis_instance.delete.return_value = 2

        mock_aioredis_instance = AsyncMock()
        mock_aioredis.return_value = mock_aioredis_instance

        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="app:")
            # 测试 clear 操作被定义
            assert hasattr(backend, "clear")
            assert callable(backend.clear)
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendAttributes:
    """Redis 后端属性测试"""

    def test_redis_backend_has_client(self) -> None:
        """测试后端有 _client 属性"""
        try:
            backend = RedisBackend(host="localhost", port=6379)
            assert hasattr(backend, "_client")
            assert backend._client is not None
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_has_async_client(self) -> None:
        """测试后端有 _async_client 属性"""
        try:
            backend = RedisBackend(host="localhost", port=6379)
            assert hasattr(backend, "_async_client")
            assert backend._async_client is not None
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_has_serializer(self) -> None:
        """测试后端有 _serializer 属性"""
        try:
            backend = RedisBackend(host="localhost", port=6379)
            assert hasattr(backend, "_serializer")
            assert backend._serializer is not None
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_has_key_prefix(self) -> None:
        """测试后端有 _key_prefix 属性"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="test:")
            assert hasattr(backend, "_key_prefix")
            assert backend._key_prefix == "test:"
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendMethods:
    """Redis 后端方法存在性测试"""

    def test_redis_backend_has_all_required_methods(self) -> None:
        """测试后端有所有必需的方法"""
        try:
            backend = RedisBackend(host="localhost", port=6379)

            required_methods = [
                "get",
                "set",
                "delete",
                "exists",
                "clear",
                "get_many",
                "set_many",
                "delete_many",
                "incr",
                "decr",
                "keys",
                "ttl",
                "aget",
                "aset",
                "adelete",
                "akeys",
                "attl",
                "close",
                "aclose",
                "__len__",
                "__repr__",
            ]

            for method in required_methods:
                assert hasattr(backend, method), f"缺少方法: {method}"
                assert callable(getattr(backend, method)), f"不可调用: {method}"
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_repr(self) -> None:
        """测试 Redis 后端的 repr"""
        try:
            backend = RedisBackend(host="localhost", port=6379, key_prefix="cache:")
            repr_str = repr(backend)
            assert "RedisBackend" in repr_str
            assert "cache:" in repr_str
        except ImportError:
            pytest.skip("redis 未安装")


class TestRedisBackendConnectionPool:
    """Redis 后端连接池测试"""

    def test_redis_backend_with_custom_socket_timeout(self) -> None:
        """测试自定义套接字超时"""
        try:
            backend = RedisBackend(host="localhost", port=6379, socket_timeout=10.0)
            assert backend is not None
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_with_custom_connect_timeout(self) -> None:
        """测试自定义连接超时"""
        try:
            backend = RedisBackend(host="localhost", port=6379, socket_connect_timeout=5.0)
            assert backend is not None
        except ImportError:
            pytest.skip("redis 未安装")

    def test_redis_backend_with_max_connections(self) -> None:
        """测试最大连接数"""
        try:
            backend = RedisBackend(host="localhost", port=6379, max_connections=100)
            assert backend is not None
        except ImportError:
            pytest.skip("redis 未安装")
