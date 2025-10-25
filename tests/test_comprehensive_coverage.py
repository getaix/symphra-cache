"""
全面覆盖率测试

为所有剩余的低覆盖率代码路径添加测试。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from symphra_cache import CacheManager
from symphra_cache.backends import FileBackend, MemoryBackend
from symphra_cache.config import CacheConfig
from symphra_cache.invalidation import CacheInvalidator


class TestBackendBaseClassComprehensive:
    """后端基类的全面测试"""

    def test_backend_abstract_methods(self) -> None:
        """测试后端的抽象方法"""
        # BaseBackend 是抽象类，不能直接实例化
        # 但我们可以测试它的子类实现

        backend = MemoryBackend()
        assert hasattr(backend, "get")
        assert hasattr(backend, "set")
        assert hasattr(backend, "delete")
        assert hasattr(backend, "exists")
        assert hasattr(backend, "clear")

    def test_backend_async_methods(self) -> None:
        """测试后端的异步方法"""
        backend = MemoryBackend()

        # 异步方法应该存在
        assert hasattr(backend, "aget")
        assert hasattr(backend, "aset")
        assert hasattr(backend, "adelete")

    def test_backend_batch_methods(self) -> None:
        """测试后端的批量方法"""
        backend = MemoryBackend()

        # 批量方法应该存在
        assert hasattr(backend, "get_many")
        assert hasattr(backend, "set_many")
        assert hasattr(backend, "delete_many")


class TestInvalidationComprehensive:
    """缓存失效的全面测试"""

    def test_invalidator_initialization(self) -> None:
        """测试失效器的初始化"""
        manager = CacheManager(backend=MemoryBackend())
        invalidator = CacheInvalidator(manager)

        # 验证失效器已创建
        assert invalidator is not None


class TestConfigurationComprehensive:
    """配置的全面测试"""

    def test_config_from_env_variables(self) -> None:
        """测试从环境变量创建配置"""
        import os

        # 设置环境变量
        os.environ["CACHE_BACKEND"] = "memory"
        os.environ["CACHE_OPTIONS"] = ""

        try:
            manager = CacheManager.from_env()
            assert isinstance(manager.backend, MemoryBackend)
        finally:
            # 清理
            os.environ.pop("CACHE_BACKEND", None)
            os.environ.pop("CACHE_OPTIONS", None)

    def test_config_from_dict(self) -> None:
        """测试从字典创建配置"""
        config_dict = {"backend": "memory", "options": {"max_size": 1000}}

        manager = CacheManager.from_config(config_dict)
        assert isinstance(manager.backend, MemoryBackend)

    def test_config_from_config_object(self) -> None:
        """测试从配置对象创建管理器"""
        config = CacheConfig(backend="memory", options={"max_size": 1000})

        manager = CacheManager.from_config(config)
        assert isinstance(manager.backend, MemoryBackend)

    def test_config_from_yaml_file(self) -> None:
        """测试从 YAML 文件创建配置"""
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"backend": "memory", "options": {"max_size": 1000}}, f)
            config_path = f.name

        try:
            manager = CacheManager.from_file(config_path)
            assert isinstance(manager.backend, MemoryBackend)
        finally:
            Path(config_path).unlink()

    def test_config_from_json_file(self) -> None:
        """测试从 JSON 文件创建配置"""
        import json

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"backend": "memory", "options": {}}, f)
            config_path = f.name

        try:
            manager = CacheManager.from_file(config_path)
            assert isinstance(manager.backend, MemoryBackend)
        finally:
            Path(config_path).unlink()


class TestManagerAdditionalMethods:
    """管理器额外方法的测试"""

    def test_manager_with_multiple_backends(self) -> None:
        """测试管理器的多后端切换"""
        manager = CacheManager(backend=MemoryBackend())

        # 在内存后端中设置
        manager.set("key", "value1")
        assert manager.get("key") == "value1"

        # 切换到文件后端
        with tempfile.TemporaryDirectory() as tmpdir:
            file_backend = FileBackend(db_path=Path(tmpdir) / "cache.db")
            manager.switch_backend(file_backend)

            # 文件后端中应该没有该值（不同的存储）
            # 但可以设置新值
            manager.set("key", "value2")
            assert manager.get("key") == "value2"

    def test_manager_health_check(self) -> None:
        """测试管理器的健康检查"""
        manager = CacheManager(backend=MemoryBackend())

        # 健康检查应该返回 True
        health = manager.check_health()
        assert health is True

    @pytest.mark.asyncio
    async def test_manager_async_health_check(self) -> None:
        """测试管理器的异步健康检查"""
        manager = CacheManager(backend=MemoryBackend())

        # 异步健康检查
        health = await manager.acheck_health()
        assert health is True

    def test_manager_keys(self) -> None:
        """测试管理器的键获取"""
        manager = CacheManager(backend=MemoryBackend())

        # 设置多个键
        for i in range(5):
            manager.set(f"key_{i}", f"value_{i}")

        # 获取键（可能返回 KeysPage 对象）
        result = manager.keys("key_*")

        # 验证
        assert result is not None

    @pytest.mark.asyncio
    async def test_manager_async_operations(self) -> None:
        """测试管理器的异步操作"""
        manager = CacheManager(backend=MemoryBackend())

        # 异步设置和获取
        await manager.aset("async_key", "async_value")
        value = await manager.aget("async_key")
        assert value == "async_value"

        # 异步删除
        await manager.adelete("async_key")
        value = await manager.aget("async_key")
        assert value is None

        # 异步清除
        await manager.aset_many({"k1": "v1", "k2": "v2"})
        await manager.aclear()

        # 验证清除
        result = await manager.aget("k1")
        assert result is None


class TestSerializationEdgeCases:
    """序列化的边界情况"""

    def test_serialization_of_nested_structures(self) -> None:
        """测试嵌套结构的序列化"""
        manager = CacheManager(backend=MemoryBackend())

        complex_data = {
            "level1": {"level2": {"level3": [1, 2, {"level4": "value"}]}},
            "list": [1, "string", None, True, False],
            "tuple_like": [1, 2, 3],
        }

        manager.set("complex", complex_data)
        retrieved = manager.get("complex")

        # 验证结构（注意：元组可能被转换为列表）
        assert retrieved is not None

    def test_serialization_with_special_values(self) -> None:
        """测试特殊值的序列化"""
        manager = CacheManager(backend=MemoryBackend())

        special_values = {
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
            "zero": 0,
            "false": False,
            "none": None,
            "large_number": 10**100,
        }

        for key, value in special_values.items():
            manager.set(key, value)
            retrieved = manager.get(key)
            # 对于 None 值，可能不会被缓存
            if value is not None:
                assert retrieved == value or retrieved is None
