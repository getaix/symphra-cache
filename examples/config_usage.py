"""
配置文件使用示例

演示如何使用配置文件、环境变量和字典来创建缓存管理器。
"""

import os
import tempfile
from pathlib import Path

from symphra_cache import CacheManager
from symphra_cache.config import CacheConfig


def example_from_dict() -> None:
    """从字典创建缓存管理器"""
    print("=== 从字典创建缓存管理器 ===\n")

    # 方式1: 使用 CacheConfig
    config = CacheConfig(backend="memory", options={"max_size": 1000})
    cache = CacheManager.from_config(config)

    # 方式2: 直接传递字典
    CacheManager.from_config({"backend": "memory", "options": {"max_size": 2000}})

    # 测试缓存功能
    cache.set("user:123", {"name": "Alice"}, ttl=60)
    user = cache.get("user:123")
    print(f"用户数据: {user}\n")


def example_from_yaml() -> None:
    """从 YAML 配置文件创建缓存管理器"""
    print("=== 从 YAML 文件创建缓存管理器 ===\n")

    # 使用项目自带的示例配置
    config_path = Path(__file__).parent.parent / "config" / "cache.yaml"

    if config_path.exists():
        cache = CacheManager.from_file(config_path)
        print(f"从 {config_path} 加载配置成功")
        print(f"后端类型: {cache.backend.__class__.__name__}\n")
    else:
        print(f"配置文件不存在: {config_path}\n")


def example_from_toml() -> None:
    """从 TOML 配置文件创建缓存管理器"""
    print("=== 从 TOML 文件创建缓存管理器 ===\n")

    # 创建临时 TOML 配置文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
# 缓存配置
backend = "file"

[options]
db_path = "/tmp/cache_example.db"
max_size = 5000
serialization_mode = "json"
enable_hot_reload = true
"""
        )
        toml_path = f.name

    try:
        cache = CacheManager.from_file(toml_path)
        print(f"从 {toml_path} 加载配置成功")
        print(f"后端类型: {cache.backend.__class__.__name__}")

        # 测试持久化
        cache.set("config", {"debug": True})
        config_data = cache.get("config")
        print(f"配置数据: {config_data}\n")
    finally:
        os.unlink(toml_path)


def example_from_env() -> None:
    """从环境变量创建缓存管理器"""
    print("=== 从环境变量创建缓存管理器 ===\n")

    # 设置环境变量
    os.environ["SYMPHRA_CACHE_BACKEND"] = "memory"
    os.environ["SYMPHRA_CACHE_OPTIONS__MAX_SIZE"] = "8000"
    os.environ["SYMPHRA_CACHE_OPTIONS__CLEANUP_INTERVAL"] = "30"

    # 从环境变量创建
    cache = CacheManager.from_env()
    print("从环境变量加载配置成功")
    print(f"后端类型: {cache.backend.__class__.__name__}")
    print(
        f"最大条目数: {cache.backend._max_size if hasattr(cache.backend, '_max_size') else 'N/A'}\n"
    )

    # 清理环境变量
    del os.environ["SYMPHRA_CACHE_BACKEND"]
    del os.environ["SYMPHRA_CACHE_OPTIONS__MAX_SIZE"]
    del os.environ["SYMPHRA_CACHE_OPTIONS__CLEANUP_INTERVAL"]


def example_backend_registry() -> None:
    """演示后端注册系统"""
    print("=== 后端注册系统 ===\n")

    from symphra_cache.backends import (
        create_backend,
        get_registered_backends,
        register_backend,
    )
    from symphra_cache.backends.base import BaseBackend

    # 查看已注册的后端
    print(f"可用后端: {', '.join(get_registered_backends())}")

    # 注册自定义后端(示例)
    class CustomBackend(BaseBackend):
        """自定义后端示例"""

        def __init__(self, custom_param: str = "default") -> None:
            self.custom_param = custom_param

        def get(self, key):
            return None

        def set(self, key, value, ttl=None):
            pass

        def delete(self, key):
            return False

        def exists(self, key):
            return False

        def clear(self):
            pass

        async def aget(self, key):
            return None

        async def aset(self, key, value, ttl=None):
            pass

        async def adelete(self, key):
            return False

    # 注册自定义后端
    register_backend("custom", lambda **opts: CustomBackend(**opts))

    # 创建自定义后端实例
    backend = create_backend("custom", custom_param="test_value")
    print(f"\n自定义后端创建成功: {backend.custom_param}\n")


def main() -> None:
    """配置示例主函数"""
    print("=" * 60)
    print("缓存配置使用示例".center(60))
    print("=" * 60 + "\n")

    example_from_dict()
    example_from_yaml()
    example_from_toml()
    example_from_env()
    example_backend_registry()

    print("=" * 60)
    print("所有示例运行完成!".center(60))
    print("=" * 60)


if __name__ == "__main__":
    main()
