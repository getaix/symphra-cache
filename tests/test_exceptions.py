"""
异常定义单元测试

测试自定义异常的继承关系和使用。
"""

from __future__ import annotations

import pytest
from symphra_cache import exceptions


class TestExceptionHierarchy:
    """测试异常继承关系"""

    def test_cache_error_is_base(self) -> None:
        """测试 CacheError 是基础异常"""
        assert issubclass(exceptions.CacheError, Exception)

    def test_all_exceptions_inherit_cache_error(self) -> None:
        """测试所有自定义异常都继承自 CacheError"""
        exception_classes = [
            exceptions.CacheConnectionError,
            exceptions.CacheLockError,
            exceptions.CacheSerializationError,
            exceptions.CacheBackendError,
            exceptions.CacheKeyError,
            exceptions.CacheValueError,
            exceptions.CacheTimeoutError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, exceptions.CacheError)

    def test_exception_can_be_raised(self) -> None:
        """测试异常可以正常抛出"""
        with pytest.raises(exceptions.CacheError):
            raise exceptions.CacheError("测试错误")

        with pytest.raises(exceptions.CacheConnectionError):
            raise exceptions.CacheConnectionError("连接失败")

    def test_catch_base_exception(self) -> None:
        """测试可以通过基类捕获所有异常"""
        try:
            raise exceptions.CacheSerializationError("序列化失败")
        except exceptions.CacheError as e:
            assert isinstance(e, exceptions.CacheSerializationError)
            assert str(e) == "序列化失败"


class TestSpecificExceptions:
    """测试特定异常"""

    def test_cache_connection_error(self) -> None:
        """测试连接错误异常"""
        error = exceptions.CacheConnectionError("无法连接到 Redis")
        assert str(error) == "无法连接到 Redis"
        assert isinstance(error, exceptions.CacheError)

    def test_cache_lock_error(self) -> None:
        """测试锁错误异常"""
        error = exceptions.CacheLockError("获取锁超时")
        assert str(error) == "获取锁超时"

    def test_cache_serialization_error(self) -> None:
        """测试序列化错误异常"""
        error = exceptions.CacheSerializationError("无法序列化对象")
        assert str(error) == "无法序列化对象"

    def test_cache_backend_error(self) -> None:
        """测试后端错误异常"""
        error = exceptions.CacheBackendError("后端操作失败")
        assert str(error) == "后端操作失败"

    def test_cache_key_error(self) -> None:
        """测试键错误异常"""
        error = exceptions.CacheKeyError("键名过长")
        assert str(error) == "键名过长"

    def test_cache_value_error(self) -> None:
        """测试值错误异常"""
        error = exceptions.CacheValueError("值过大")
        assert str(error) == "值过大"

    def test_cache_timeout_error(self) -> None:
        """测试超时错误异常"""
        error = exceptions.CacheTimeoutError("操作超时")
        assert str(error) == "操作超时"
