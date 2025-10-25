"""
类型系统单元测试

测试类型定义和枚举的正确性。
"""

from __future__ import annotations

from symphra_cache.types import BackendType, EvictionPolicy, SerializationMode


class TestSerializationMode:
    """测试序列化模式枚举"""

    def test_enum_values(self) -> None:
        """测试枚举值的正确性"""
        assert SerializationMode.JSON.value == "json"
        assert SerializationMode.PICKLE.value == "pickle"
        assert SerializationMode.MSGPACK.value == "msgpack"

    def test_enum_membership(self) -> None:
        """测试枚举成员检查"""
        assert "json" in [m.value for m in SerializationMode]
        assert "pickle" in [m.value for m in SerializationMode]
        assert "msgpack" in [m.value for m in SerializationMode]


class TestEvictionPolicy:
    """测试缓存淘汰策略枚举"""

    def test_enum_values(self) -> None:
        """测试枚举值的正确性"""
        assert EvictionPolicy.LRU.value == "lru"
        assert EvictionPolicy.LFU.value == "lfu"
        assert EvictionPolicy.FIFO.value == "fifo"

    def test_enum_count(self) -> None:
        """测试枚举成员数量"""
        assert len(EvictionPolicy) == 3


class TestBackendType:
    """测试后端类型枚举"""

    def test_enum_values(self) -> None:
        """测试枚举值的正确性"""
        assert BackendType.MEMORY.value == "memory"
        assert BackendType.FILE.value == "file"
        assert BackendType.REDIS.value == "redis"

    def test_string_representation(self) -> None:
        """测试字符串表示"""
        # 测试枚举值（.value 属性）
        assert BackendType.MEMORY.value == "memory"
        assert BackendType.FILE.value == "file"
        assert BackendType.REDIS.value == "redis"
