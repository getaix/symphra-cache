"""
配置管理模块

使用 Pydantic 进行配置验证和管理,支持从配置文件、环境变量、字典自动加载。

使用示例:
    >>> # 从字典创建
    >>> config = CacheConfig(backend="memory", options={"max_size": 10000})
    >>>
    >>> # 从 YAML 文件创建
    >>> config = CacheConfig.from_file("cache.yaml")
    >>>
    >>> # 从环境变量创建
    >>> config = CacheConfig.from_env()
    >>>
    >>> # 自动实例化后端
    >>> backend = config.create_backend()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from .exceptions import CacheConfigError

if TYPE_CHECKING:
    from .backends import BaseBackend


class CacheConfig(BaseModel):
    """
    缓存配置类

    使用 Pydantic 进行自动验证,采用 backend + options 的扩展模式。

    支持从多种来源加载:
    - 字典
    - YAML 文件
    - TOML 文件
    - JSON 文件
    - 环境变量

    配置示例:
        ```python
        # 方式1: 使用默认内存后端
        config = CacheConfig()

        # 方式2: 指定后端名称
        config = CacheConfig(backend="memory")

        # 方式3: 指定后端和参数
        config = CacheConfig(backend="redis", options={"host": "localhost", "port": 6379})

        # 实例化后端
        backend = config.create_backend()
        ```

    属性:
        backend: 已注册的后端名称(如 memory、file、redis)
        options: 传递给后端构造函数的参数字典
    """

    backend: str = Field(
        default="memory",
        description="后端名称,对应已注册的 backend 标识(如 memory、file、redis)",
    )

    options: dict[str, Any] = Field(
        default_factory=dict,
        description="后端构造参数,会在实例化时传递给具体后端实现",
    )

    # ========== Pydantic 配置 ==========

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",  # 禁止额外字段
        "str_strip_whitespace": True,
    }

    # ========== 验证器 ==========

    @model_validator(mode="after")
    def validate_backend(self) -> CacheConfig:
        """验证后端配置"""
        from .backends import get_registered_backends

        # 验证后端类型
        available_backends = get_registered_backends()
        if self.backend.lower() not in available_backends:
            valid_backends = ", ".join(available_backends)
            msg = f"不支持的后端类型: {self.backend}。支持的类型: {valid_backends}"
            raise ValueError(msg)

        return self

    # ========== 后端实例化 ==========

    def create_backend(self) -> BaseBackend:
        """
        根据配置创建后端实例

        Returns:
            配置好的后端实例

        Raises:
            CacheConfigError: 后端创建失败

        示例:
            >>> config = CacheConfig(backend="memory", options={"max_size": 1000})
            >>> backend = config.create_backend()
        """
        from .backends import create_backend

        try:
            return create_backend(self.backend, **self.options)
        except Exception as e:
            msg = f"创建 {self.backend} 后端失败: {e}"
            raise CacheConfigError(msg) from e

    # ========== 工厂方法 ==========

    @classmethod
    def from_file(cls, file_path: str | Path) -> CacheConfig:
        """
        从配置文件创建配置

        支持的格式:
        - YAML (.yaml, .yml)
        - TOML (.toml)
        - JSON (.json)

        Args:
            file_path: 配置文件路径

        Returns:
            CacheConfig 实例

        Raises:
            CacheConfigError: 文件读取或解析失败

        示例:
            >>> config = CacheConfig.from_file("config/cache.yaml")
        """
        file_path = Path(file_path)

        if not file_path.exists():
            msg = f"配置文件不存在: {file_path}"
            raise CacheConfigError(msg)

        suffix = file_path.suffix.lower()

        try:
            if suffix in {".yaml", ".yml"}:
                return cls._from_yaml(file_path)
            if suffix == ".toml":
                return cls._from_toml(file_path)
            if suffix == ".json":
                return cls._from_json(file_path)
            msg = f"不支持的配置文件格式: {suffix}"
            raise CacheConfigError(msg)
        except Exception as e:
            if isinstance(e, CacheConfigError):
                raise
            msg = f"读取配置文件失败: {file_path}"
            raise CacheConfigError(msg) from e

    @classmethod
    def _from_yaml(cls, file_path: Path) -> CacheConfig:
        """从 YAML 文件加载"""
        try:
            import yaml
        except ImportError as e:
            msg = "YAML 支持需要安装 PyYAML: pip install pyyaml"
            raise ImportError(msg) from e

        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            msg = "YAML 配置文件必须是字典格式"
            raise CacheConfigError(msg)

        return cls(**data)

    @classmethod
    def _from_toml(cls, file_path: Path) -> CacheConfig:
        """从 TOML 文件加载"""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # Python < 3.11
            except ImportError as e:
                msg = "TOML 支持需要安装 tomli: pip install tomli"
                raise ImportError(msg) from e

        with file_path.open("rb") as f:
            data = tomllib.load(f)

        if not isinstance(data, dict):
            msg = "TOML 配置文件必须是字典格式"
            raise CacheConfigError(msg)

        return cls(**data)

    @classmethod
    def _from_json(cls, file_path: Path) -> CacheConfig:
        """从 JSON 文件加载"""
        import json

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            msg = "JSON 配置文件必须是字典格式"
            raise CacheConfigError(msg)

        return cls(**data)

    @classmethod
    def from_env(cls, prefix: str = "SYMPHRA_CACHE_") -> CacheConfig:
        """
        从环境变量创建配置

        环境变量命名规则:
        - SYMPHRA_CACHE_BACKEND=memory
        - SYMPHRA_CACHE_OPTIONS__MAX_SIZE=10000  (options 使用双下划线)
        - SYMPHRA_CACHE_OPTIONS__HOST=localhost

        Args:
            prefix: 环境变量前缀

        Returns:
            CacheConfig 实例

        示例:
            >>> import os
            >>> os.environ["SYMPHRA_CACHE_BACKEND"] = "redis"
            >>> os.environ["SYMPHRA_CACHE_OPTIONS__HOST"] = "localhost"
            >>> config = CacheConfig.from_env()
        """
        backend = os.environ.get(f"{prefix}BACKEND", "memory")
        options: dict[str, Any] = {}

        # 收集 options
        options_prefix = f"{prefix}OPTIONS__"
        for key, value in os.environ.items():
            if key.startswith(options_prefix):
                # 移除前缀并转为小写
                option_key = key[len(options_prefix) :].lower()
                # 类型转换
                options[option_key] = cls._convert_env_value(value)

        return cls(backend=backend, options=options)

    @staticmethod
    def _convert_env_value(value: str) -> Any:
        """转换环境变量值类型"""
        # 布尔值
        if value.lower() in {"true", "1", "yes", "on"}:
            return True
        if value.lower() in {"false", "0", "no", "off"}:
            return False

        # None/null
        if value.lower() in {"none", "null", ""}:
            return None

        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 字符串
        return value

    def __repr__(self) -> str:
        """字符串表示"""
        return f"CacheConfig(backend={self.backend!r}, options={self.options!r})"
