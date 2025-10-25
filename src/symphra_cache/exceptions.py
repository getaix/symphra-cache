"""
异常定义模块

本模块定义了缓存库的所有自定义异常类。
所有异常都继承自 CacheError 基类，便于统一捕获。
"""

from __future__ import annotations


class CacheError(Exception):
    """
    缓存操作基础异常

    所有缓存相关的异常都继承自此类。
    用于统一捕获所有缓存操作错误。

    示例:
        >>> try:
        ...     cache.get("key")
        ... except CacheError as e:
        ...     print(f"缓存错误: {e}")
    """

    pass


class CacheConfigError(CacheError):
    """
    缓存配置错误

    当配置验证失败或配置文件解析失败时抛出。
    包括配置格式错误、参数不合法等。

    示例:
        >>> # 配置文件不存在
        >>> raise CacheConfigError("配置文件不存在: cache.yaml")
        >>>
        >>> # 配置参数不合法
        >>> raise CacheConfigError("不支持的后端类型: custom")
    """

    pass


class CacheConnectionError(CacheError):
    """
    缓存连接错误

    当无法连接到缓存后端时抛出。
    主要用于 Redis 后端连接失败的场景。

    示例:
        >>> # Redis 连接失败
        >>> raise CacheConnectionError("无法连接到 Redis 服务器 localhost:6379")
    """

    pass


class CacheLockError(CacheError):
    """
    缓存锁操作错误

    当分布式锁操作失败时抛出。
    包括获取锁超时、释放锁失败等场景。

    示例:
        >>> # 获取锁超时
        >>> raise CacheLockError("获取锁超时: resource_key")
    """

    pass


class CacheSerializationError(CacheError):
    """
    缓存序列化/反序列化错误

    当序列化或反序列化缓存值失败时抛出。
    可能原因包括对象不可序列化、数据损坏等。

    示例:
        >>> # 对象无法序列化
        >>> raise CacheSerializationError("无法序列化对象: <lambda>")
    """

    pass


class CacheBackendError(CacheError):
    """
    后端操作错误

    当后端执行操作失败时抛出。
    包括文件操作失败、Redis 命令执行失败等。

    示例:
        >>> # 文件后端写入失败
        >>> raise CacheBackendError("无法写入缓存文件: cache.db")
    """

    pass


class CacheKeyError(CacheError):
    """
    缓存键错误

    当缓存键格式无效或操作失败时抛出。
    包括键名过长、包含非法字符等。

    示例:
        >>> # 键名过长
        >>> raise CacheKeyError("键名长度超过限制: 1024 字符")
    """

    pass


class CacheValueError(CacheError):
    """
    缓存值错误

    当缓存值无效时抛出。
    包括值过大、类型不支持等。

    示例:
        >>> # 值过大
        >>> raise CacheValueError("缓存值大小超过限制: 1MB")
    """

    pass


class CacheTimeoutError(CacheError):
    """
    缓存操作超时错误

    当缓存操作超时时抛出。
    包括读取超时、写入超时等。

    示例:
        >>> # 读取超时
        >>> raise CacheTimeoutError("读取缓存超时: 5秒")
    """

    pass
