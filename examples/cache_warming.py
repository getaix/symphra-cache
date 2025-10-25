"""
缓存预热示例

演示如何使用 CacheWarmer 进行缓存预热，避免缓存冷启动问题。
"""

import asyncio
import time
from typing import Any

from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.warming import CacheWarmer, SmartCacheWarmer, create_warmer


def load_user_data() -> dict[str, Any]:
    """
    模拟从数据库加载用户数据
    """
    print("  [数据源] 正在从数据库加载用户数据...")
    time.sleep(0.5)  # 模拟数据库查询延迟

    return {
        "user:1": {"id": 1, "name": "Alice", "email": "alice@example.com"},
        "user:2": {"id": 2, "name": "Bob", "email": "bob@example.com"},
        "user:3": {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
        "user:4": {"id": 4, "name": "Diana", "email": "diana@example.com"},
        "user:5": {"id": 5, "name": "Eve", "email": "eve@example.com"},
    }


def load_product_data() -> dict[str, Any]:
    """
    模拟从数据库加载商品数据
    """
    print("  [数据源] 正在从数据库加载商品数据...")
    time.sleep(0.3)

    return {
        "product:101": {"id": 101, "name": "笔记本电脑", "price": 5999},
        "product:102": {"id": 102, "name": "智能手机", "price": 2999},
        "product:103": {"id": 103, "name": "平板电脑", "price": 1999},
        "product:104": {"id": 104, "name": "智能手表", "price": 999},
    }


async def demonstrate_manual_warming():
    """演示手动缓存预热"""
    print("=== 手动缓存预热示例 ===\n")

    # 创建缓存管理器
    cache = CacheManager(backend=MemoryBackend())
    warmer = CacheWarmer(cache, strategy="manual", ttl=3600)

    # 预热用户数据
    print("1. 预热用户数据...")
    start_time = time.time()
    await warmer.warm_up(load_user_data(), ttl=7200)  # 2小时过期
    elapsed = time.time() - start_time
    print(f"  预热完成，耗时: {elapsed:.3f}秒")

    # 预热商品数据
    print("\n2. 预热商品数据...")
    start_time = time.time()
    await warmer.warm_up(load_product_data(), ttl=3600)  # 1小时过期
    elapsed = time.time() - start_time
    print(f"  预热完成，耗时: {elapsed:.3f}秒")

    # 验证预热结果
    print("\n3. 验证预热结果:")
    user = cache.get("user:1")
    product = cache.get("product:101")
    print(f"  user:1 = {user}")
    print(f"  product:101 = {product}")

    # 查看缓存统计
    stats = warmer.get_warming_stats()
    print(f"\n4. 预热统计: {stats}")


async def demonstrate_auto_warming():
    """演示自动缓存预热"""
    print("\n=== 自动缓存预热示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    warmer = CacheWarmer(cache, strategy="auto", ttl=1800)

    print("1. 启动自动预热...")
    start_time = time.time()
    await warmer.auto_warm_up(load_user_data)
    elapsed = time.time() - start_time
    print(f"  自动预热完成，耗时: {elapsed:.3f}秒")

    # 验证数据
    user = cache.get("user:2")
    print(f"  user:2 = {user}")

    print("\n2. 启动后台自动预热任务...")
    # 启动后台预热（这里只是演示，不会真正运行）
    await warmer.start_background_warming(load_product_data, interval=3600)  # 每小时预热一次
    print("  后台预热任务已启动")

    # 停止后台任务
    warmer.stop_background_warming()
    print("  后台预热任务已停止")


async def demonstrate_incremental_warming():
    """演示增量缓存预热"""
    print("\n=== 增量缓存预热示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    warmer = CacheWarmer(cache, strategy="incremental", batch_size=2)

    # 先预热一些基础数据
    base_data = {"user:1": "data1", "user:2": "data2"}
    await warmer.warm_up(base_data)

    # 增量预热热点数据
    hot_keys = [f"user:{i}" for i in range(3, 8)]  # user:3 到 user:7

    def load_hot_data(keys):
        """模拟加载热点数据"""
        print(f"  [增量加载] 正在加载 {len(keys)} 个热点键...")
        return {key: f"hot_data_for_{key}" for key in keys}

    print("1. 执行增量预热...")
    start_time = time.time()
    await warmer.incremental_warm_up(hot_keys, load_hot_data)
    elapsed = time.time() - start_time
    print(f"  增量预热完成，耗时: {elapsed:.3f}秒")

    # 验证增量预热结果
    print("\n2. 验证增量预热结果:")
    for key in hot_keys[:3]:
        value = cache.get(key)
        print(f"  {key} = {value}")


async def demonstrate_smart_warming():
    """演示智能缓存预热"""
    print("\n=== 智能缓存预热示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    smart_warmer = SmartCacheWarmer(cache, prediction_window=24)

    # 预热一些基础数据
    base_data = {f"user:{i}": f"profile_{i}" for i in range(1, 11)}
    await smart_warmer.warm_up(base_data)

    # 模拟用户访问，记录访问模式
    print("1. 模拟用户访问模式...")
    for i in range(5):
        key = f"user:{i + 1}"
        value = cache.get(key)
        if value:
            smart_warmer.record_cache_miss(key)  # 记录访问

    # 智能预热
    def predict_and_load(hot_keys):
        """预测并加载数据"""
        print(f"  [智能预测] 预热 {len(hot_keys)} 个热点键...")
        return {key: f"predicted_{key}" for key in hot_keys}

    print("\n2. 执行智能预热...")
    start_time = time.time()
    await smart_warmer.smart_warm_up(predict_and_load, top_k=3)
    elapsed = time.time() - start_time
    print(f"  智能预热完成，耗时: {elapsed:.3f}秒")

    # 查看预测准确率
    accuracy = smart_warmer.get_prediction_accuracy()
    print(f"\n3. 预测准确率: {accuracy:.3f}")


async def demonstrate_warming_from_file():
    """演示从文件预热缓存"""
    print("\n=== 从文件预热缓存示例 ===\n")

    import json
    import tempfile
    from pathlib import Path

    cache = CacheManager(backend=MemoryBackend())
    warmer = CacheWarmer(cache)

    # 创建临时 JSON 文件
    temp_data = {
        "config:app_name": "MyApp",
        "config:version": "1.0.0",
        "config:debug": False,
        "feature:dark_mode": True,
        "feature:notifications": False,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(temp_data, f)
        temp_file = f.name

    try:
        print("1. 从 JSON 文件预热缓存...")
        start_time = time.time()
        await warmer.warm_up_from_file(temp_file, format="json", ttl=3600)
        elapsed = time.time() - start_time
        print(f"  文件预热完成，耗时: {elapsed:.3f}秒")

        # 验证文件预热结果
        print("\n2. 验证文件预热结果:")
        for key in ["config:app_name", "feature:dark_mode"]:
            value = cache.get(key)
            print(f"  {key} = {value}")

    finally:
        # 清理临时文件
        Path(temp_file).unlink()


async def demonstrate_ttl_map_warming():
    """演示使用 TTL 映射预热"""
    print("\n=== TTL 映射预热示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    warmer = CacheWarmer(cache)

    # 不同类型的数据，不同的过期时间
    data = {
        "session:user123": "session_data",
        "token:api456": "api_token",
        "config:app": "app_config",
        "feature:flag1": True,
    }

    # 为不同键设置不同的 TTL
    ttl_map = {
        "session:user123": 1800,  # 会话数据：30分钟
        "token:api456": 3600,  # API 令牌：1小时
        "config:app": 7200,  # 配置数据：2小时
        "feature:flag1": 14400,  # 功能标志：4小时
    }

    print("1. 使用 TTL 映射预热缓存...")
    start_time = time.time()
    await warmer.warm_up_with_ttl_map(data, ttl_map)
    elapsed = time.time() - start_time
    print(f"  TTL 映射预热完成，耗时: {elapsed:.3f}秒")

    # 验证不同 TTL 的设置
    print("\n2. 验证 TTL 设置:")
    for key in data:
        ttl = cache.ttl(key)
        expected_ttl = ttl_map[key]
        print(f"  {key}: 实际 TTL = {ttl}, 期望 TTL = {expected_ttl}")


async def demonstrate_factory_pattern():
    """演示工厂模式创建预热器"""
    print("\n=== 工厂模式示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())

    # 使用工厂函数创建不同类型的预热器
    manual_warmer = create_warmer(cache, strategy="manual", ttl=3600)
    smart_warmer = create_warmer(cache, strategy="smart", prediction_window=12)

    print("1. 手动预热器:", type(manual_warmer).__name__)
    print("2. 智能预热器:", type(smart_warmer).__name__)

    # 使用智能预热器
    data = {"key1": "value1", "key2": "value2"}
    await smart_warmer.warm_up(data)
    print("3. 智能预热器预热完成")


async def main():
    """主函数"""
    print("🚀 Symphra Cache 缓存预热示例\n")

    # 演示各种预热功能
    await demonstrate_manual_warming()
    await demonstrate_auto_warming()
    await demonstrate_incremental_warming()
    await demonstrate_smart_warming()
    await demonstrate_warming_from_file()
    await demonstrate_ttl_map_warming()
    await demonstrate_factory_pattern()

    print("\n✅ 所有缓存预热示例完成！")
    print("\n缓存预热功能特点:")
    print("  • 支持手动、自动、增量、智能等多种预热策略")
    print("  • 支持从文件、数据库等多种数据源预热")
    print("  • 支持批量操作和 TTL 映射")
    print("  • 提供详细的统计和监控信息")
    print("  • 支持后台定时预热任务")


if __name__ == "__main__":
    asyncio.run(main())
