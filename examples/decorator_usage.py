"""
装饰器使用示例

演示缓存装饰器的使用。
"""

import time

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.decorators import cache

# 创建全局缓存管理器
cache_manager = CacheManager(backend=MemoryBackend())


@cache(cache_manager, ttl=3600)
def get_user_profile(user_id: int) -> dict[str, object]:
    """
    获取用户资料（模拟数据库查询）

    使用 @cache 装饰器自动缓存结果。
    """
    print(f"  [数据库查询] 正在获取用户 {user_id} 的资料...")
    time.sleep(0.5)  # 模拟数据库延迟

    return {
        "id": user_id,
        "name": f"User_{user_id}",
        "email": f"user{user_id}@example.com",
    }


@cache(cache_manager, ttl=60, key_prefix="stats:")
def get_user_statistics(user_id: int) -> dict[str, int]:
    """
    获取用户统计信息

    使用键前缀进行命名空间隔离。
    """
    print(f"  [计算统计] 正在计算用户 {user_id} 的统计信息...")
    time.sleep(0.3)

    return {
        "posts_count": 42,
        "followers_count": 1337,
        "following_count": 256,
    }


def main() -> None:
    """装饰器示例"""
    print("=== 缓存装饰器示例 ===\n")

    # 第一次调用：执行函数（缓存未命中）
    print("1. 第一次调用 get_user_profile(123):")
    start = time.time()
    profile1 = get_user_profile(123)
    elapsed1 = time.time() - start
    print(f"  结果: {profile1}")
    print(f"  耗时: {elapsed1:.3f}秒\n")

    # 第二次调用：从缓存获取（缓存命中）
    print("2. 第二次调用 get_user_profile(123):")
    start = time.time()
    profile2 = get_user_profile(123)
    elapsed2 = time.time() - start
    print(f"  结果: {profile2}")
    print(f"  耗时: {elapsed2:.3f}秒 (快 {elapsed1 / elapsed2:.1f}x)\n")

    # 不同参数：重新执行
    print("3. 调用 get_user_profile(456) (不同参数):")
    start = time.time()
    profile3 = get_user_profile(456)
    elapsed3 = time.time() - start
    print(f"  结果: {profile3}")
    print(f"  耗时: {elapsed3:.3f}秒\n")

    # 使用键前缀
    print("4. 调用 get_user_statistics(123) (带键前缀):")
    stats = get_user_statistics(123)
    print(f"  结果: {stats}\n")

    # 缓存统计
    print("5. 缓存统计:")
    print(f"  缓存条目数: {len(cache_manager)}")


if __name__ == "__main__":
    main()
