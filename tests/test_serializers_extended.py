"""
序列化模块的扩展测试，覆盖错误处理和边界情况。
"""

from __future__ import annotations

import pytest
from symphra_cache.exceptions import CacheSerializationError
from symphra_cache.serializers import (
    JSONSerializer,
    MessagePackSerializer,
    PickleSerializer,
    get_serializer,
)
from symphra_cache.types import SerializationMode


class TestJSONSerializerErrors:
    """测试 JSON 序列化器的错误处理"""

    def test_json_deserialize_invalid_json(self) -> None:
        """测试无效的 JSON 数据反序列化"""
        serializer = JSONSerializer()

        # 无效的 JSON 数据
        invalid_data = b"invalid json {]["

        with pytest.raises(CacheSerializationError):
            serializer.deserialize(invalid_data)

    def test_json_deserialize_invalid_utf8(self) -> None:
        """测试无效的 UTF-8 数据"""
        serializer = JSONSerializer()

        # 无效的 UTF-8 字节
        invalid_utf8 = b"\xff\xfe"

        with pytest.raises(CacheSerializationError):
            serializer.deserialize(invalid_utf8)

    def test_json_serialize_custom_object(self) -> None:
        """测试序列化自定义对象"""
        serializer = JSONSerializer()

        class CustomClass:
            pass

        # 自定义对象不能被 JSON 序列化
        with pytest.raises(CacheSerializationError):
            serializer.serialize(CustomClass())

    def test_json_roundtrip_with_unicode(self) -> None:
        """测试 Unicode 数据的往返"""
        serializer = JSONSerializer()

        data = {
            "chinese": "你好世界",
            "emoji": "😀🎉",
            "symbols": "™®©",
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_json_roundtrip_with_numbers(self) -> None:
        """测试各种数字类型"""
        serializer = JSONSerializer()

        data = {
            "int": 42,
            "float": 3.14,
            "negative": -100,
            "zero": 0,
            "large": 10**100,
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data


class TestPickleSerializerErrors:
    """测试 Pickle 序列化器的错误处理"""

    def test_pickle_deserialize_invalid_data(self) -> None:
        """测试无效的 Pickle 数据"""
        serializer = PickleSerializer()

        # 无效的 Pickle 数据
        invalid_data = b"invalid pickle data"

        with pytest.raises(CacheSerializationError):
            serializer.deserialize(invalid_data)

    def test_pickle_roundtrip_with_complex_types(self) -> None:
        """测试复杂类型的往返"""
        serializer = PickleSerializer()

        import datetime

        data = {
            "date": datetime.date(2024, 1, 1),
            "datetime": datetime.datetime(2024, 1, 1, 12, 30, 45),
            "timedelta": datetime.timedelta(days=5),
            "complex": 3 + 4j,
            "set": {1, 2, 3},
            "frozenset": frozenset([1, 2, 3]),
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_pickle_serialize_empty_containers(self) -> None:
        """测试空容器的序列化"""
        serializer = PickleSerializer()

        data = {
            "empty_list": [],
            "empty_dict": {},
            "empty_tuple": (),
            "empty_set": set(),
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_pickle_serialize_nested_structures(self) -> None:
        """测试深度嵌套的结构"""
        serializer = PickleSerializer()

        # 深度嵌套
        data = {"level1": {"level2": {"level3": {"level4": "value"}}}}

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data


class TestMessagePackSerializer:
    """测试 MessagePack 序列化器"""

    def test_msgpack_serializer_import_available(self) -> None:
        """测试 MessagePack 是否可用"""
        try:
            serializer = MessagePackSerializer()
            assert serializer is not None
        except ImportError:
            pytest.skip("msgpack 未安装")

    def test_msgpack_roundtrip_basic(self) -> None:
        """测试基本类型的往返"""
        try:
            serializer = MessagePackSerializer()

            data = {
                "string": "hello",
                "number": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            }

            serialized = serializer.serialize(data)
            deserialized = serializer.deserialize(serialized)

            assert deserialized == data
        except ImportError:
            pytest.skip("msgpack 未安装")

    def test_msgpack_roundtrip_unicode(self) -> None:
        """测试 Unicode 数据"""
        try:
            serializer = MessagePackSerializer()

            data = {
                "chinese": "你好",
                "emoji": "😀",
            }

            serialized = serializer.serialize(data)
            deserialized = serializer.deserialize(serialized)

            assert deserialized == data
        except ImportError:
            pytest.skip("msgpack 未安装")

    def test_msgpack_deserialize_invalid_data(self) -> None:
        """测试无效的 MessagePack 数据"""
        try:
            serializer = MessagePackSerializer()

            # 无效的 MessagePack 数据
            invalid_data = b"\xff\xff\xff"

            with pytest.raises(CacheSerializationError):
                serializer.deserialize(invalid_data)
        except ImportError:
            pytest.skip("msgpack 未安装")


class TestSerializerFactory:
    """测试序列化器工厂函数"""

    def test_get_serializer_json(self) -> None:
        """测试获取 JSON 序列化器"""
        serializer = get_serializer(SerializationMode.JSON)
        assert isinstance(serializer, JSONSerializer)

    def test_get_serializer_pickle(self) -> None:
        """测试获取 Pickle 序列化器"""
        serializer = get_serializer(SerializationMode.PICKLE)
        assert isinstance(serializer, PickleSerializer)

    def test_get_serializer_msgpack(self) -> None:
        """测试获取 MessagePack 序列化器"""
        try:
            serializer = get_serializer(SerializationMode.MSGPACK)
            assert isinstance(serializer, MessagePackSerializer)
        except ImportError:
            pytest.skip("msgpack 未安装")

    def test_get_serializer_by_string(self) -> None:
        """测试使用字符串名称获取序列化器"""
        serializer = get_serializer("json")
        assert isinstance(serializer, JSONSerializer)

    def test_get_serializer_invalid_mode(self) -> None:
        """测试无效的序列化模式"""
        with pytest.raises(ValueError):
            get_serializer("invalid_mode")

    def test_get_serializer_cached_instances(self) -> None:
        """测试序列化器实例是否被正确创建"""
        # 多次获取应该返回不同的实例
        serializer1 = get_serializer(SerializationMode.JSON)
        serializer2 = get_serializer(SerializationMode.JSON)

        # 虽然是不同的对象，但都是 JSONSerializer 类型
        assert isinstance(serializer1, JSONSerializer)
        assert isinstance(serializer2, JSONSerializer)


class TestSerializerEdgeCases:
    """测试序列化器的边界情况"""

    def test_json_serializer_with_none_value(self) -> None:
        """测试序列化 None 值"""
        serializer = JSONSerializer()

        data = None
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized is None

    def test_pickle_serializer_with_bytes(self) -> None:
        """测试 Pickle 序列化字节数据"""
        serializer = PickleSerializer()

        data = b"binary data"
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_json_serializer_with_list(self) -> None:
        """测试序列化列表"""
        serializer = JSONSerializer()

        data = [1, "two", 3.0, True, None]
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_json_serializer_preserves_types(self) -> None:
        """测试 JSON 保留基本类型"""
        serializer = JSONSerializer()

        data = {"int": 42, "float": 3.14, "bool": True}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert isinstance(deserialized["int"], int)
        assert isinstance(deserialized["float"], float)
        assert isinstance(deserialized["bool"], bool)

    def test_pickle_large_data(self) -> None:
        """测试 Pickle 大数据"""
        serializer = PickleSerializer()

        # 创建大数据
        large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

        serialized = serializer.serialize(large_data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == large_data
        assert len(deserialized) == 1000
