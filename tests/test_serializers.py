"""
序列化器单元测试

测试所有序列化器的正确性。
"""

from __future__ import annotations

import datetime

import pytest

from symphra_cache.exceptions import CacheSerializationError
from symphra_cache.serializers import (
    JSONSerializer,
    PickleSerializer,
    get_serializer,
)
from symphra_cache.types import SerializationMode


class TestJSONSerializer:
    """测试 JSON 序列化器"""

    def test_basic_types(self) -> None:
        """测试基本类型"""
        serializer = JSONSerializer()

        # 字典
        data = {"name": "Alice", "age": 30}
        serialized = serializer.serialize(data)
        assert serializer.deserialize(serialized) == data

        # 列表
        data_list = [1, 2, 3, "four"]
        serialized = serializer.serialize(data_list)
        assert serializer.deserialize(serialized) == data_list

        # 字符串
        data_str = "hello world"
        serialized = serializer.serialize(data_str)
        assert serializer.deserialize(serialized) == data_str

    def test_unicode(self) -> None:
        """测试 Unicode 支持"""
        serializer = JSONSerializer()

        data = {"message": "你好世界", "emoji": "🎉"}
        serialized = serializer.serialize(data)
        assert serializer.deserialize(serialized) == data

    def test_invalid_data(self) -> None:
        """测试无效数据"""
        serializer = JSONSerializer()

        # JSON 不支持复杂对象
        with pytest.raises(CacheSerializationError):
            serializer.serialize(datetime.datetime.now())


class TestPickleSerializer:
    """测试 Pickle 序列化器"""

    def test_basic_types(self) -> None:
        """测试基本类型"""
        serializer = PickleSerializer()

        data = {"name": "Bob", "count": 123}
        serialized = serializer.serialize(data)
        assert serializer.deserialize(serialized) == data

    def test_complex_objects(self) -> None:
        """测试复杂对象"""
        serializer = PickleSerializer()

        # datetime 对象
        now = datetime.datetime.now()
        serialized = serializer.serialize(now)
        result = serializer.deserialize(serialized)
        assert result == now

        # 复杂嵌套结构
        data = {
            "timestamp": datetime.datetime(2024, 1, 1, 12, 0, 0),
            "nested": {"items": [1, 2, 3], "metadata": {"count": 42}},
        }
        serialized = serializer.serialize(data)
        result = serializer.deserialize(serialized)
        assert result == data


class TestGetSerializer:
    """测试序列化器工厂函数"""

    def test_get_json_serializer(self) -> None:
        """测试获取 JSON 序列化器"""
        serializer = get_serializer(SerializationMode.JSON)
        assert isinstance(serializer, JSONSerializer)

        # 使用字符串
        serializer = get_serializer("json")
        assert isinstance(serializer, JSONSerializer)

    def test_get_pickle_serializer(self) -> None:
        """测试获取 Pickle 序列化器"""
        serializer = get_serializer(SerializationMode.PICKLE)
        assert isinstance(serializer, PickleSerializer)

    def test_invalid_mode(self) -> None:
        """测试无效的序列化模式"""
        with pytest.raises(ValueError):
            get_serializer("invalid_mode")  # type: ignore[arg-type]
