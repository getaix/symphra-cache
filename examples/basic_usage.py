"""
基础使用示例

演示 Symphra Cache 的基本功能。
"""

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend


def main() -> None:
    """基础使用示例"""
    # 创建缓存管理器（使用内存后端）
    cache = CacheManager(backend=MemoryBackend())

    # 1. 基础 set/get
    print("=== 基础 Set/Get ===")
    cache.set("user:123", {"name": "Alice", "age": 30})
    user = cache.get("user:123")
    print(f"用户信息: {user}")

    # 2. 带 TTL 的缓存
    print("\n=== TTL 过期 ===")
    cache.set("temp_token", "abc123", ttl=10)  # 10 秒后过期
    print(f"临时令牌: {cache.get('temp_token')}")

    # 3. 批量操作
    print("\n=== 批量操作 ===")
    cache.set_many(
        {
            "product:1": {"name": "笔记本", "price": 5000},
            "product:2": {"name": "鼠标", "price": 99},
            "product:3": {"name": "键盘", "price": 299},
        }
    )

    products = cache.get_many(["product:1", "product:2", "product:3"])
    for key, value in products.items():
        print(f"{key}: {value}")

    # 4. 删除和清空
    print("\n=== 删除操作 ===")
    cache.delete("product:1")
    print(f"product:1 是否存在: {cache.exists('product:1')}")

    # 5. 统计信息
    print("\n=== 统计信息 ===")
    print(f"缓存条目数: {len(cache)}")

    # 清空所有缓存
    cache.clear()
    print(f"清空后条目数: {len(cache)}")


if __name__ == "__main__":
    main()
