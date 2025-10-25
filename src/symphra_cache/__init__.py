"""
Symphra Cache - 生产级 Python 异步缓存库

本库提供统一的缓存接口，支持多种后端实现：
- Memory: 内存缓存（高性能、LRU 淘汰）
- File: 文件缓存（持久化、热重载）
- Redis: Redis 缓存（分布式、高可用）

主要特性：
- 全异步支持（async/await）
- 统一的装饰器和上下文管理器 API
- 分布式锁、缓存预热、失效通知
- Prometheus/StatsD 监控导出
- 中文文档和注释

示例：
    >>> from symphra_cache import CacheManager
    >>> from symphra_cache.backends import MemoryBackend
    >>>
    >>> cache = CacheManager(backend=MemoryBackend())
    >>> cache.set("key", "value", ttl=60)
    >>> cache.get("key")
    'value'
"""

from __future__ import annotations

from .__version__ import __version__
from .backends import BaseBackend, FileBackend, MemoryBackend, RedisBackend
from .decorators import CachedProperty, acache, cache, cache_invalidate
from .invalidation import CacheGroupInvalidator, CacheInvalidator, create_invalidator
from .locks import DistributedLock
from .manager import (
    CacheManager,
    create_file_cache,
    create_memory_cache,
    create_redis_cache,
)
from .monitor import CacheMonitor, CacheStats
from .monitoring import CacheMonitor as BaseCacheMonitor
from .monitoring.prometheus import PrometheusExporter, PrometheusPushgatewayClient
from .monitoring.statsd import StatsDExporter
from .serializers import (
    BaseSerializer,
    JSONSerializer,
    MessagePackSerializer,
    PickleSerializer,
    get_serializer,
)
from .types import BackendType, EvictionPolicy, SerializationMode
from .warming import CacheWarmer, SmartCacheWarmer, create_warmer

# 导出核心类和版本号
__all__ = [
    "__version__",
    # 管理器和便利函数
    "CacheManager",
    "create_memory_cache",
    "create_file_cache",
    "create_redis_cache",
    # 监控
    "CacheMonitor",
    "CacheStats",
    "BaseCacheMonitor",
    "PrometheusExporter",
    "PrometheusPushgatewayClient",
    "StatsDExporter",
    # 后端
    "BaseBackend",
    "MemoryBackend",
    "FileBackend",
    "RedisBackend",
    # 装饰器
    "cache",
    "acache",
    "cache_invalidate",
    "CachedProperty",
    # 锁
    "DistributedLock",
    # 序列化
    "BaseSerializer",
    "JSONSerializer",
    "PickleSerializer",
    "MessagePackSerializer",
    "get_serializer",
    # 缓存预热
    "CacheWarmer",
    "SmartCacheWarmer",
    "create_warmer",
    # 缓存失效
    "CacheInvalidator",
    "CacheGroupInvalidator",
    "create_invalidator",
    # 类型
    "SerializationMode",
    "EvictionPolicy",
    "BackendType",
]
