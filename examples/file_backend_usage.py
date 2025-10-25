"""
文件后端使用示例

演示文件缓存后端的持久化功能。
"""

from pathlib import Path

from symphra_cache import CacheManager
from symphra_cache.backends import FileBackend


def main() -> None:
    """文件后端示例"""
    print("=== 文件缓存后端示例 ===\n")

    # 创建文件后端（数据持久化到 SQLite）
    cache_path = Path("./cache_example.db")
    backend = FileBackend(
        db_path=cache_path,
        max_size=1000,
        enable_hot_reload=True,  # 开发模式：启用热重载
    )

    cache = CacheManager(backend=backend)

    # 写入数据
    print("1. 写入缓存数据:")
    cache.set("config:app_name", "Symphra Cache Demo")
    cache.set("config:version", "1.0.0")
    cache.set("config:debug", True)
    print("  数据已写入\n")

    # 读取数据
    print("2. 读取缓存数据:")
    app_name = cache.get("config:app_name")
    version = cache.get("config:version")
    debug = cache.get("config:debug")
    print(f"  应用名称: {app_name}")
    print(f"  版本号: {version}")
    print(f"  调试模式: {debug}\n")

    # 持久化验证
    print("3. 验证持久化:")
    print(f"  数据库文件: {cache_path}")
    print(f"  文件大小: {cache_path.stat().st_size} 字节")
    print(f"  缓存条目数: {len(cache)}\n")

    print("4. 提示:")
    print("  - 进程重启后，数据仍然存在")
    print("  - 可用于开发环境的热重载场景")
    print("  - 支持 TTL 过期和 LRU 淘汰\n")

    # 清理示例文件（可选）
    # cache_path.unlink()


if __name__ == "__main__":
    main()
