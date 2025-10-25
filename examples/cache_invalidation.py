"""
缓存失效通知示例

演示如何使用 CacheInvalidator 进行缓存失效管理，确保数据一致性。
"""

import asyncio
import time
from typing import Any

from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.invalidation import CacheInvalidator, create_invalidator


def setup_test_data(cache: CacheManager) -> None:
    """设置测试数据"""
    # 用户数据
    cache.set("user:1", {"id": 1, "name": "Alice", "email": "alice@example.com"}, ttl=3600)
    cache.set("user:2", {"id": 2, "name": "Bob", "email": "bob@example.com"}, ttl=3600)
    cache.set("user:3", {"id": 3, "name": "Charlie", "email": "charlie@example.com"}, ttl=3600)

    # 商品数据
    cache.set("product:101", {"id": 101, "name": "笔记本电脑", "price": 5999}, ttl=7200)
    cache.set("product:102", {"id": 102, "name": "智能手机", "price": 2999}, ttl=7200)
    cache.set("product:103", {"id": 103, "name": "平板电脑", "price": 1999}, ttl=7200)

    # 会话数据
    cache.set("session:user1", "session_data_1", ttl=1800)
    cache.set("session:user2", "session_data_2", ttl=1800)
    cache.set("session:user3", "session_data_3", ttl=1800)

    # 配置数据
    cache.set("config:app_name", "MyApp", ttl=14400)
    cache.set("config:version", "1.0.0", ttl=14400)
    cache.set("feature:dark_mode", True, ttl=14400)


async def demonstrate_key_invalidation():
    """演示键级失效"""
    print("=== 键级失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    setup_test_data(cache)
    print(f"1. 初始缓存大小: {len(cache)}")

    # 失效特定键
    keys_to_invalidate = ["user:1", "user:2"]
    print(f"\n2. 失效键: {keys_to_invalidate}")
    start_time = time.time()
    invalidated_count = await invalidator.invalidate_keys(keys_to_invalidate)
    elapsed = time.time() - start_time
    print(f"  失效完成，耗时: {elapsed:.3f}秒")
    print(f"  实际失效键数量: {invalidated_count}")
    print(f"  当前缓存大小: {len(cache)}")

    # 验证失效结果
    print("\n3. 验证失效结果:")
    for key in keys_to_invalidate:
        value = cache.get(key)
        print(f"  {key}: {value}")  # 应该为 None

    # 检查未失效的键
    remaining_keys = ["user:3", "product:101"]
    print("\n4. 验证未失效键:")
    for key in remaining_keys:
        value = cache.get(key)
        print(f"  {key}: {value is not None}")


async def demonstrate_pattern_invalidation():
    """演示模式匹配失效"""
    print("\n=== 模式匹配失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    setup_test_data(cache)
    print(f"1. 初始缓存大小: {len(cache)}")

    # 模式匹配失效 - 失效所有用户数据
    print("\n2. 失效所有用户数据 (user:*)")
    start_time = time.time()
    invalidated_count = await invalidator.invalidate_pattern("user:*")
    elapsed = time.time() - start_time
    print(f"  失效完成，耗时: {elapsed:.3f}秒")
    print(f"  实际失效键数量: {invalidated_count}")
    print(f"  当前缓存大小: {len(cache)}")

    # 验证用户数据已失效
    print("\n3. 验证用户数据失效:")
    for i in range(1, 4):
        key = f"user:{i}"
        value = cache.get(key)
        print(f"  {key}: {value is None}")

    # 验证其他数据仍在
    print("\n4. 验证其他数据仍在:")
    other_keys = ["product:101", "config:app_name", "session:user1"]
    for key in other_keys:
        value = cache.get(key)
        print(f"  {key}: {value is not None}")


async def demonstrate_prefix_invalidation():
    """演示前缀失效"""
    print("\n=== 前缀失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    setup_test_data(cache)
    print(f"1. 初始缓存大小: {len(cache)}")

    # 前缀失效 - 失效所有会话数据
    print("\n2. 失效所有会话数据 (session:*)")
    start_time = time.time()
    invalidated_count = await invalidator.invalidate_prefix("session:")
    elapsed = time.time() - start_time
    print(f"  失效完成，耗时: {elapsed:.3f}秒")
    print(f"  实际失效键数量: {invalidated_count}")
    print(f"  当前缓存大小: {len(cache)}")

    # 验证会话数据已失效
    print("\n3. 验证会话数据失效:")
    for i in range(1, 4):
        key = f"session:user{i}"
        value = cache.get(key)
        print(f"  {key}: {value is None}")


async def demonstrate_condition_invalidation():
    """演示条件失效"""
    print("\n=== 条件失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    cache.set("temp:high:1", "value1", ttl=3600)
    cache.set("temp:low:2", "value2", ttl=3600)
    cache.set("temp:high:3", "value3", ttl=3600)
    cache.set("temp:normal:4", "value4", ttl=3600)
    cache.set("temp:high:5", "value5", ttl=3600)

    print(f"1. 初始缓存大小: {len(cache)}")

    # 条件失效 - 失效包含 "high" 的键
    def should_invalidate(key: str, value: Any) -> bool:
        return "high" in key

    print("\n2. 失效包含 'high' 的键")
    start_time = time.time()
    invalidated_count = await invalidator.invalidate_by_condition(should_invalidate)
    elapsed = time.time() - start_time
    print(f"  失效完成，耗时: {elapsed:.3f}秒")
    print(f"  实际失效键数量: {invalidated_count}")
    print(f"  当前缓存大小: {len(cache)}")

    # 验证条件失效结果
    print("\n3. 验证条件失效结果:")
    all_keys = ["temp:high:1", "temp:low:2", "temp:high:3", "temp:normal:4", "temp:high:5"]
    for key in all_keys:
        value = cache.get(key)
        should_be_invalid = "high" in key
        is_invalid = value is None
        print(
            f"  {key}: 应失效={should_be_invalid}, 已失效={is_invalid}, 匹配={should_be_invalid == is_invalid}"
        )


async def demonstrate_group_invalidation():
    """演示缓存组失效"""
    print("\n=== 缓存组失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    setup_test_data(cache)
    print(f"1. 初始缓存大小: {len(cache)}")

    # 创建用户组失效器
    user_group_invalidator = invalidator.create_cache_group_invalidator("user:")
    print("\n2. 创建用户组失效器 (user:*)")

    # 失效用户组所有数据
    start_time = time.time()
    invalidated_count = await user_group_invalidator.invalidate_all()
    elapsed = time.time() - start_time
    print(f"  用户组失效完成，耗时: {elapsed:.3f}秒")
    print(f"  实际失效键数量: {invalidated_count}")

    # 使用模式匹配验证
    pattern_invalidated = await invalidator.invalidate_pattern("product:*")
    print(f"\n3. 失效商品组，失效键数量: {pattern_invalidated}")

    print(f"4. 最终缓存大小: {len(cache)}")

    # 验证组失效
    print("\n5. 验证组失效结果:")
    remaining_keys = ["config:app_name", "config:version", "feature:dark_mode"]
    for key in remaining_keys:
        value = cache.get(key)
        print(f"  {key}: {value is not None}")


async def demonstrate_dependency_invalidation():
    """演示依赖失效"""
    print("\n=== 依赖失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据（模拟依赖关系）
    cache.set("user:profile:123", {"name": "Alice", "age": 30}, ttl=3600)
    cache.set("user:posts:123", [{"id": 1, "title": "Post 1"}], ttl=3600)
    cache.set("user:followers:123", [1, 2, 3], ttl=3600)
    cache.set("user:following:123", [4, 5, 6], ttl=3600)
    cache.set("stats:user:123", {"posts": 1, "followers": 3}, ttl=3600)

    print(f"1. 初始缓存大小: {len(cache)}")

    # 依赖解析函数
    def resolve_user_dependencies(user_keys: list[str]) -> list[str]:
        """解析用户相关的所有依赖键"""
        dependencies = []
        for key in user_keys:
            if key.startswith("user:profile:"):
                user_id = key.split(":")[-1]
                # 添加所有相关的用户数据键
                dependencies.extend(
                    [
                        f"user:posts:{user_id}",
                        f"user:followers:{user_id}",
                        f"user:following:{user_id}",
                        f"stats:user:{user_id}",
                    ]
                )
        return dependencies

    # 失效用户及其依赖
    primary_keys = ["user:profile:123"]
    print(f"\n2. 失效用户及其依赖: {primary_keys}")
    start_time = time.time()
    invalidated_count = await invalidator.invalidate_with_dependencies(
        primary_keys, resolve_user_dependencies
    )
    elapsed = time.time() - start_time
    print(f"  依赖失效完成，耗时: {elapsed:.3f}秒")
    print(f"  实际失效键数量: {invalidated_count}")
    print(f"  当前缓存大小: {len(cache)}")


async def demonstrate_delayed_invalidation():
    """演示延迟失效"""
    print("\n=== 延迟失效示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    cache.set("delayed:key1", "value1", ttl=3600)
    cache.set("delayed:key2", "value2", ttl=3600)
    cache.set("delayed:key3", "value3", ttl=3600)

    print(f"1. 初始缓存大小: {len(cache)}")

    # 延迟失效
    keys_to_delay = ["delayed:key1", "delayed:key2"]
    delay_seconds = 2.0

    print(f"\n2. 设置 {delay_seconds} 秒后失效键: {keys_to_delay}")
    task = await invalidator.schedule_invalidation(keys_to_delay, delay_seconds)

    # 等待一段时间后检查
    await asyncio.sleep(1.0)
    print(f"3. 1秒后缓存大小: {len(cache)}")

    # 等待失效完成
    await task
    print(f"4. 失效完成后缓存大小: {len(cache)}")

    # 验证延迟失效结果
    print("\n5. 验证延迟失效结果:")
    for key in keys_to_delay:
        value = cache.get(key)
        print(f"  {key}: {value is None}")


async def demonstrate_invalidation_stats():
    """演示失效统计功能"""
    print("\n=== 失效统计示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    invalidator = CacheInvalidator(cache)

    # 设置测试数据
    setup_test_data(cache)

    # 执行几种不同的失效操作
    await invalidator.invalidate_keys(["user:1"])
    await invalidator.invalidate_pattern("product:*")
    await invalidator.invalidate_prefix("session:")

    # 获取统计信息
    stats = invalidator.get_invalidation_stats()
    print("1. 失效统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 获取失效历史
    history = invalidator.get_invalidation_history()
    print("\n2. 失效历史记录:")
    for i, record in enumerate(history):
        print(f"  记录 {i + 1}: {record}")


async def demonstrate_factory_pattern():
    """演示工厂模式"""
    print("\n=== 工厂模式示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())

    # 使用工厂函数创建失效器
    invalidator = create_invalidator(cache, strategy="default", batch_size=50)

    print("1. 工厂创建的失效器:", type(invalidator).__name__)
    print("2. 配置参数:")
    print(f"  批量大小: {invalidator.batch_size}")
    print(f"  启用分布式: {invalidator.enable_distributed}")


async def main():
    """主函数"""
    print("🗑️ Symphra Cache 缓存失效通知示例\n")

    # 演示各种失效功能
    await demonstrate_key_invalidation()
    await demonstrate_pattern_invalidation()
    await demonstrate_prefix_invalidation()
    await demonstrate_condition_invalidation()
    await demonstrate_group_invalidation()
    await demonstrate_dependency_invalidation()
    await demonstrate_delayed_invalidation()
    await demonstrate_invalidation_stats()
    await demonstrate_factory_pattern()

    print("\n✅ 所有缓存失效示例完成！")
    print("\n缓存失效功能特点:")
    print("  • 支持键级、模式、前缀、条件等多种失效策略")
    print("  • 提供缓存组管理，简化批量操作")
    print("  • 支持依赖失效，维护数据一致性")
    print("  • 支持延迟失效和条件失效")
    print("  • 提供详细的失效统计和历史记录")
    print("  • 支持分布式失效通知")


if __name__ == "__main__":
    asyncio.run(main())
