"""
配置系统测试

测试 CacheConfig 和配置加载功能。
"""

import os
import tempfile
from pathlib import Path

import pytest
import toml
import yaml

from symphra_cache.backends import MemoryBackend
from symphra_cache.config import CacheConfig
from symphra_cache.exceptions import CacheConfigError


class TestCacheConfig:
    """测试 CacheConfig 类"""

    def test_default_config(self) -> None:
        """测试默认配置"""
        config = CacheConfig()

        assert config.backend == "memory"
        assert config.options == {}

    def test_custom_backend(self) -> None:
        """测试自定义后端"""
        config = CacheConfig(backend="file")

        assert config.backend == "file"

    def test_with_options(self) -> None:
        """测试带选项的配置"""
        config = CacheConfig(backend="memory", options={"max_size": 5000})

        assert config.backend == "memory"
        assert config.options["max_size"] == 5000

    def test_create_backend(self) -> None:
        """测试创建后端实例"""
        config = CacheConfig(backend="memory", options={"max_size": 1000})
        backend = config.create_backend()

        assert isinstance(backend, MemoryBackend)
        assert backend._max_size == 1000

    def test_create_backend_invalid(self) -> None:
        """测试创建无效后端"""
        # Pydantic 会在构造时验证
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CacheConfig(backend="invalid")

    def test_from_dict(self) -> None:
        """测试从字典创建配置"""
        config_dict = {"backend": "memory", "options": {"max_size": 2000}}

        config = CacheConfig(**config_dict)

        assert config.backend == "memory"
        assert config.options["max_size"] == 2000

    def test_to_dict(self) -> None:
        """测试转换为字典"""
        config = CacheConfig(backend="file", options={"db_path": "/tmp/cache.db"})

        config_dict = config.model_dump()

        assert config_dict["backend"] == "file"
        assert config_dict["options"]["db_path"] == "/tmp/cache.db"


class TestConfigFileLoading:
    """测试配置文件加载"""

    def test_load_from_yaml(self) -> None:
        """测试从 YAML 文件加载"""
        config_data = {"backend": "memory", "options": {"max_size": 3000}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = CacheConfig.from_file(config_path)

            assert config.backend == "memory"
            assert config.options["max_size"] == 3000
        finally:
            Path(config_path).unlink()

    def test_load_from_yml(self) -> None:
        """测试从 .yml 文件加载"""
        config_data = {"backend": "memory", "options": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = CacheConfig.from_file(config_path)

            assert config.backend == "memory"
        finally:
            Path(config_path).unlink()

    def test_load_from_toml(self) -> None:
        """测试从 TOML 文件加载"""
        config_data = {"backend": "file", "options": {"db_path": "/tmp/test.db"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            toml.dump(config_data, f)
            config_path = f.name

        try:
            config = CacheConfig.from_file(config_path)

            assert config.backend == "file"
            assert config.options["db_path"] == "/tmp/test.db"
        finally:
            Path(config_path).unlink()

    def test_load_from_json(self) -> None:
        """测试从 JSON 文件加载"""
        import json

        config_data = {"backend": "memory", "options": {"max_size": 4000}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            config = CacheConfig.from_file(config_path)

            assert config.backend == "memory"
            assert config.options["max_size"] == 4000
        finally:
            Path(config_path).unlink()

    def test_load_nonexistent_file(self) -> None:
        """测试加载不存在的文件"""
        with pytest.raises(CacheConfigError, match="配置文件不存在"):
            CacheConfig.from_file("/nonexistent/config.yaml")

    def test_load_unsupported_format(self) -> None:
        """测试加载不支持的格式"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("backend: memory")
            config_path = f.name

        try:
            with pytest.raises(CacheConfigError, match="不支持的配置文件格式"):
                CacheConfig.from_file(config_path)
        finally:
            Path(config_path).unlink()


class TestEnvironmentVariableLoading:
    """测试环境变量加载"""

    def test_load_from_env_basic(self) -> None:
        """测试从环境变量加载基础配置"""
        os.environ["SYMPHRA_CACHE_BACKEND"] = "memory"

        try:
            config = CacheConfig.from_env()

            assert config.backend == "memory"
        finally:
            del os.environ["SYMPHRA_CACHE_BACKEND"]

    def test_load_from_env_with_options(self) -> None:
        """测试从环境变量加载带选项的配置"""
        os.environ["SYMPHRA_CACHE_BACKEND"] = "memory"
        os.environ["SYMPHRA_CACHE_OPTIONS__MAX_SIZE"] = "5000"
        os.environ["SYMPHRA_CACHE_OPTIONS__CLEANUP_INTERVAL"] = "60"

        try:
            config = CacheConfig.from_env()

            assert config.backend == "memory"
            assert config.options["max_size"] == 5000
            assert config.options["cleanup_interval"] == 60
        finally:
            del os.environ["SYMPHRA_CACHE_BACKEND"]
            del os.environ["SYMPHRA_CACHE_OPTIONS__MAX_SIZE"]
            del os.environ["SYMPHRA_CACHE_OPTIONS__CLEANUP_INTERVAL"]

    def test_load_from_env_no_backend(self) -> None:
        """测试环境变量中没有 backend 时使用默认值"""
        # 确保没有设置环境变量
        if "SYMPHRA_CACHE_BACKEND" in os.environ:
            del os.environ["SYMPHRA_CACHE_BACKEND"]

        config = CacheConfig.from_env()

        assert config.backend == "memory"  # 默认值

    def test_load_from_env_boolean_values(self) -> None:
        """测试布尔值解析"""
        os.environ["SYMPHRA_CACHE_BACKEND"] = "file"
        os.environ["SYMPHRA_CACHE_OPTIONS__ENABLE_HOT_RELOAD"] = "true"

        try:
            config = CacheConfig.from_env()

            assert config.options["enable_hot_reload"] is True
        finally:
            del os.environ["SYMPHRA_CACHE_BACKEND"]
            del os.environ["SYMPHRA_CACHE_OPTIONS__ENABLE_HOT_RELOAD"]

    def test_load_from_env_path_values(self) -> None:
        """测试路径值解析"""
        os.environ["SYMPHRA_CACHE_BACKEND"] = "file"
        os.environ["SYMPHRA_CACHE_OPTIONS__DB_PATH"] = "/tmp/cache.db"

        try:
            config = CacheConfig.from_env()

            assert config.options["db_path"] == "/tmp/cache.db"
        finally:
            del os.environ["SYMPHRA_CACHE_BACKEND"]
            del os.environ["SYMPHRA_CACHE_OPTIONS__DB_PATH"]


class TestConfigValidation:
    """测试配置验证"""

    def test_empty_backend_name(self) -> None:
        """测试空后端名称"""
        with pytest.raises(ValueError):
            CacheConfig(backend="")

    def test_backend_case_insensitive(self) -> None:
        """测试后端名称大小写不敏感"""
        config1 = CacheConfig(backend="MEMORY")
        config2 = CacheConfig(backend="memory")
        config3 = CacheConfig(backend="Memory")

        backend1 = config1.create_backend()
        backend2 = config2.create_backend()
        backend3 = config3.create_backend()

        assert isinstance(backend1, MemoryBackend)
        assert isinstance(backend2, MemoryBackend)
        assert isinstance(backend3, MemoryBackend)

    def test_options_defaults_to_empty_dict(self) -> None:
        """测试 options 默认为空字典"""
        config = CacheConfig(backend="memory")

        assert config.options == {}
        assert isinstance(config.options, dict)


class TestConfigIntegration:
    """测试配置与其他组件的集成"""

    def test_create_file_backend(self) -> None:
        """测试创建文件后端"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                backend="file", options={"db_path": f"{tmpdir}/cache.db", "max_size": 1000}
            )

            backend = config.create_backend()

            assert backend._db_path == Path(f"{tmpdir}/cache.db")
            assert backend._max_size == 1000

    def test_create_memory_backend(self) -> None:
        """测试创建内存后端"""
        config = CacheConfig(backend="memory", options={"max_size": 2000, "cleanup_interval": 120})

        backend = config.create_backend()

        assert backend._max_size == 2000
        assert backend._cleanup_interval == 120

    def test_repr(self) -> None:
        """测试字符串表示"""
        config = CacheConfig(backend="memory", options={"max_size": 1000})

        repr_str = repr(config)

        assert "CacheConfig" in repr_str or "memory" in repr_str
