"""
类型定义模块

本模块定义了缓存库的核心类型、枚举和类型别名。
所有类型定义都支持完整的类型检查（Mypy strict 模式）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

# ========== 类型别名定义 ==========

CacheKey = str | int | bytes
"""缓存键类型：支持字符串、整数和字节"""

CacheValue = Any
"""缓存值类型：支持任何 Python 对象"""

# ========== 类型变量定义 ==========

T = TypeVar("T")  # 泛型类型变量
K = TypeVar("K")  # 键类型变量
V = TypeVar("V")  # 值类型变量


# ========== 数据类定义 ==========


@dataclass
class KeysPage:
    """
    缓存键分页信息

    用于 keys() 方法返回分页结果。

    Attributes:
        keys: 当前页的缓存键列表
        cursor: 下一页的游标 (0 表示没有更多数据)
        has_more: 是否还有更多数据
        total_scanned: 总扫描数量
    """

    keys: list[str]  # 当前页的缓存键列表
    cursor: int  # 下一页的游标
    has_more: bool  # 是否还有更多数据
    total_scanned: int  # 总扫描数量


# ========== 枚举定义 ==========


class SerializationMode(str, Enum):
    """
    序列化模式枚举

    定义缓存值的序列化方式：
    - JSON: JSON 序列化，跨语言兼容，但类型支持有限
    - PICKLE: Python 原生序列化，支持所有 Python 对象
    - MSGPACK: MessagePack 序列化，紧凑高效
    """

    JSON = "json"  # JSON 序列化
    PICKLE = "pickle"  # Pickle 序列化
    MSGPACK = "msgpack"  # MessagePack 序列化


class EvictionPolicy(str, Enum):
    """
    缓存淘汰策略枚举

    定义缓存满时的淘汰规则：
    - LRU: Least Recently Used（最近最少使用），淘汰最久未访问的项
    - LFU: Least Frequently Used（最不经常使用），淘汰访问次数最少的项
    - FIFO: First In First Out（先进先出），淘汰最早插入的项
    """

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    FIFO = "fifo"  # 先进先出


class BackendType(str, Enum):
    """
    后端类型枚举

    定义支持的缓存后端类型：
    - MEMORY: 内存后端，高性能，进程重启数据丢失
    - FILE: 文件后端，持久化，支持热重载
    - REDIS: Redis 后端，分布式，高可用
    """

    MEMORY = "memory"  # 内存后端
    FILE = "file"  # 文件后端
    REDIS = "redis"  # Redis 后端


__all__ = [
    "KeysPage",
    "CacheKey",
    "CacheValue",
    "SerializationMode",
    "EvictionPolicy",
    "BackendType",
]
