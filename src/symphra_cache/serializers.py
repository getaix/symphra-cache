"""
序列化工具模块

提供多种序列化方式：
- JSON：适合简单数据类型，可读性好
- Pickle：支持任意 Python 对象，性能较好
- MessagePack：高性能二进制序列化（可选）

使用示例：
    >>> serializer = get_serializer(SerializationMode.JSON)
    >>> data = {"name": "Alice", "age": 30}
    >>> serialized = serializer.serialize(data)
    >>> deserialized = serializer.deserialize(serialized)
"""

from __future__ import annotations

import json
import pickle
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .exceptions import CacheSerializationError
from .types import SerializationMode

if TYPE_CHECKING:
    from .types import CacheValue


class BaseSerializer(ABC):
    """
    序列化器抽象基类

    定义序列化和反序列化接口。
    """

    @abstractmethod
    def serialize(self, value: CacheValue) -> bytes:
        """
        序列化值为字节

        Args:
            value: 要序列化的值

        Returns:
            序列化后的字节数据

        Raises:
            CacheSerializationError: 序列化失败
        """
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> CacheValue:
        """
        反序列化字节为值

        Args:
            data: 要反序列化的字节数据

        Returns:
            反序列化后的值

        Raises:
            CacheSerializationError: 反序列化失败
        """
        raise NotImplementedError


class JSONSerializer(BaseSerializer):
    """
    JSON 序列化器

    优点：
    - 可读性好
    - 跨语言兼容
    - 适合简单数据结构

    缺点：
    - 不支持复杂 Python 对象（如 datetime、bytes）
    - 性能相对较低

    示例：
        >>> serializer = JSONSerializer()
        >>> data = {"key": "value", "count": 123}
        >>> bytes_data = serializer.serialize(data)
        >>> original = serializer.deserialize(bytes_data)
    """

    def serialize(self, value: CacheValue) -> bytes:
        """将值序列化为 JSON 字节"""
        try:
            # 使用 ensure_ascii=False 支持中文等 Unicode 字符
            json_str = json.dumps(value, ensure_ascii=False)
            return json_str.encode("utf-8")
        except (TypeError, ValueError) as e:
            msg = f"JSON 序列化失败: {e}"
            raise CacheSerializationError(msg) from e

    def deserialize(self, data: bytes) -> CacheValue:
        """从 JSON 字节反序列化值"""
        try:
            json_str = data.decode("utf-8")
            return json.loads(json_str)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            msg = f"JSON 反序列化失败: {e}"
            raise CacheSerializationError(msg) from e


class PickleSerializer(BaseSerializer):
    """
    Pickle 序列化器

    优点：
    - 支持几乎所有 Python 对象
    - 性能较好
    - Python 标准库内置

    缺点：
    - 不跨语言
    - 安全风险（不要反序列化不可信数据）
    - 二进制格式，不可读

    警告：
        仅反序列化可信来源的数据，避免代码注入风险

    示例：
        >>> serializer = PickleSerializer()
        >>> import datetime
        >>> data = {"time": datetime.datetime.now(), "items": [1, 2, 3]}
        >>> bytes_data = serializer.serialize(data)
        >>> original = serializer.deserialize(bytes_data)
    """

    def serialize(self, value: CacheValue) -> bytes:
        """将值序列化为 Pickle 字节"""
        try:
            # 使用协议 5（Python 3.8+，性能最优）
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except (pickle.PicklingError, TypeError) as e:
            msg = f"Pickle 序列化失败: {e}"
            raise CacheSerializationError(msg) from e

    def deserialize(self, data: bytes) -> CacheValue:
        """从 Pickle 字节反序列化值"""
        try:
            return pickle.loads(data)  # noqa: S301
        except (pickle.UnpicklingError, AttributeError, EOFError) as e:
            msg = f"Pickle 反序列化失败: {e}"
            raise CacheSerializationError(msg) from e


class MessagePackSerializer(BaseSerializer):
    """
    MessagePack 序列化器

    优点：
    - 高性能（比 JSON 快 2-5 倍）
    - 紧凑的二进制格式
    - 跨语言兼容

    缺点：
    - 需要额外依赖 msgpack
    - 对复杂 Python 对象支持有限

    示例：
        >>> serializer = MessagePackSerializer()
        >>> data = {"users": [{"id": 1}, {"id": 2}], "total": 2}
        >>> bytes_data = serializer.serialize(data)
        >>> original = serializer.deserialize(bytes_data)
    """

    def __init__(self) -> None:
        """初始化 MessagePack 序列化器"""
        try:
            import msgpack

            self._msgpack = msgpack
        except ImportError as e:
            msg = "MessagePack 序列化需要安装 msgpack: pip install msgpack"
            raise ImportError(msg) from e

    def serialize(self, value: CacheValue) -> bytes:
        """将值序列化为 MessagePack 字节"""
        try:
            return self._msgpack.packb(value, use_bin_type=True)
        except (self._msgpack.PackException, TypeError) as e:
            msg = f"MessagePack 序列化失败: {e}"
            raise CacheSerializationError(msg) from e

    def deserialize(self, data: bytes) -> CacheValue:
        """从 MessagePack 字节反序列化值"""
        try:
            return self._msgpack.unpackb(data, raw=False)
        except (self._msgpack.UnpackException, ValueError) as e:
            msg = f"MessagePack 反序列化失败: {e}"
            raise CacheSerializationError(msg) from e


# 全局序列化器注册表
_SERIALIZERS: dict[SerializationMode, type[BaseSerializer]] = {
    SerializationMode.JSON: JSONSerializer,
    SerializationMode.PICKLE: PickleSerializer,
    SerializationMode.MSGPACK: MessagePackSerializer,
}


def get_serializer(mode: SerializationMode | str) -> BaseSerializer:
    """
    获取指定模式的序列化器实例

    Args:
        mode: 序列化模式（SerializationMode 枚举或字符串）

    Returns:
        序列化器实例

    Raises:
        ValueError: 不支持的序列化模式

    示例:
        >>> serializer = get_serializer(SerializationMode.JSON)
        >>> # 或使用字符串
        >>> serializer = get_serializer("json")
    """
    # 支持字符串参数
    if isinstance(mode, str):
        try:
            mode = SerializationMode(mode)
        except ValueError as e:
            msg = f"不支持的序列化模式: {mode}"
            raise ValueError(msg) from e

    # 获取序列化器类
    serializer_cls = _SERIALIZERS.get(mode)
    if serializer_cls is None:
        msg = f"未注册的序列化模式: {mode}"
        raise ValueError(msg)

    # 返回实例
    return serializer_cls()


def register_serializer(
    mode: SerializationMode,
    serializer_cls: type[BaseSerializer],
) -> None:
    """
    注册自定义序列化器

    允许用户扩展支持的序列化格式。

    Args:
        mode: 序列化模式
        serializer_cls: 序列化器类（必须继承 BaseSerializer）

    Raises:
        TypeError: serializer_cls 不是 BaseSerializer 的子类

    示例:
        >>> class CustomSerializer(BaseSerializer):
        ...     def serialize(self, value):
        ...         ...
        ...
        ...     def deserialize(self, data):
        ...         ...
        >>>
        >>> register_serializer(SerializationMode.CUSTOM, CustomSerializer)
    """
    if not issubclass(serializer_cls, BaseSerializer):
        msg = f"序列化器类必须继承 BaseSerializer: {serializer_cls}"
        raise TypeError(msg)

    _SERIALIZERS[mode] = serializer_cls
