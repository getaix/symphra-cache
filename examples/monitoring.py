"""
监控示例

演示如何使用 CacheMonitor 和各种监控导出器来监控缓存性能。
"""

import asyncio
import time

from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.monitoring import CacheMonitor, PrometheusExporter, StatsDExporter


def simulate_cache_operations(cache: CacheManager, operations: int = 100) -> None:
    """模拟缓存操作以生成监控数据"""
    print(f"  正在模拟 {operations} 次缓存操作...")

    # 模拟混合的读写操作
    for i in range(operations):
        key = f"test:key:{i % 10}"  # 重复使用10个键以产生命中

        if i % 3 == 0:
            # 30% 的写操作
            cache.set(key, f"value_{i}", ttl=3600)
        else:
            # 70% 的读操作
            cache.get(key)

        # 每10次操作休息一下
        if i % 10 == 0:
            time.sleep(0.001)  # 1ms 休息


async def demonstrate_basic_monitoring():
    """演示基础监控功能"""
    print("=== 基础监控示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)

    # 模拟一些缓存操作
    simulate_cache_operations(cache, 50)

    # 收集指标
    print("1. 收集缓存指标...")
    metrics = await monitor.collect_metrics()

    # 显示指标
    print("2. 缓存指标:")
    metrics_dict = metrics.to_dict()
    for key, value in metrics_dict.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # 显示健康状态
    print("\n3. 健康状态:")
    health = monitor.get_health_status()
    for key, value in health.items():
        print(f"  {key}: {value}")


async def demonstrate_prometheus_export():
    """演示 Prometheus 指标导出"""
    print("\n=== Prometheus 导出示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)
    exporter = PrometheusExporter(
        monitor,
        namespace="myapp",
        subsystem="cache",
        labels={"instance": "test-instance", "environment": "development"},
    )

    # 模拟缓存操作
    simulate_cache_operations(cache, 100)

    # 生成 Prometheus 格式指标
    print("1. 生成 Prometheus 格式指标...")
    metrics_text = exporter.generate_metrics()

    print("2. Prometheus 指标输出:")
    print("-" * 50)
    print(metrics_text)
    print("-" * 50)

    # 演示 Pushgateway 集成
    print("\n3. Pushgateway 集成演示:")
    try:
        # 注意：这里只是演示客户端创建，不实际连接
        pushgateway_client = exporter.create_pushgateway_client(
            gateway_url="http://localhost:9091",
            job_name="cache_monitoring",
            instance="test-instance",
        )
        print(f"  Pushgateway URL: {pushgateway_client.get_push_url()}")
        print("  Pushgateway 客户端已创建（需要实际的 Pushgateway 服务器）")
    except Exception as e:
        print(f"  Pushgateway 集成失败: {e}")


async def demonstrate_statsd_export():
    """演示 StatsD 指标导出"""
    print("\n=== StatsD 导出示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)

    # 创建 StatsD 导出器（使用本地模式，不实际发送）
    exporter = StatsDExporter(
        monitor, host="localhost", port=8125, prefix="myapp.cache", sample_rate=1.0, protocol="udp"
    )

    # 模拟缓存操作
    simulate_cache_operations(cache, 50)

    # 生成 StatsD 格式指标
    print("1. 生成 StatsD 格式指标...")
    statsd_metrics = exporter.generate_all_metrics()

    print("2. StatsD 指标输出:")
    for metric in statsd_metrics:
        print(f"  {metric}")

    # 演示连接状态
    print("\n3. 连接状态:")
    status = exporter.get_connection_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    # 演示自定义指标
    print("\n4. 添加自定义指标:")
    exporter.add_custom_metric("custom_metric", 42.5, "g")
    exporter.add_custom_metric("operation_count", 100, "c")

    custom_metrics = exporter.generate_all_metrics()
    print("  包含自定义指标的输出:")
    for metric in custom_metrics:
        if "custom" in metric:
            print(f"  {metric}")


async def demonstrate_real_time_monitoring():
    """演示实时监控"""
    print("\n=== 实时监控示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)

    print("1. 开始实时监控（5秒）...")
    print("  每秒显示一次指标快照")
    print("-" * 60)

    for i in range(5):
        # 模拟一些操作
        simulate_cache_operations(cache, 20)

        # 收集并显示指标
        metrics = await monitor.collect_metrics()
        metrics_dict = metrics.to_dict()

        timestamp = time.strftime("%H:%M:%S")
        print(f"\n  [{timestamp}] 第 {i + 1} 次采样:")
        print(f"    操作总数: {metrics_dict.get('total_operations', 0)}")
        print(f"    命中率: {metrics_dict.get('hit_rate', 0):.4f}")
        print(f"    缓存大小: {metrics_dict.get('cache_size', 0)}")
        print(f"    GET 平均延迟: {metrics_dict.get('get_latency', {}).get('avg', 0):.3f}ms")
        print(f"    SET 平均延迟: {metrics_dict.get('set_latency', {}).get('avg', 0):.3f}ms")

        # 等待1秒
        await asyncio.sleep(1)

    print("-" * 60)
    print("2. 实时监控完成")


async def demonstrate_metric_types():
    """演示不同类型的监控指标"""
    print("\n=== 指标类型示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)

    # 模拟不同类型的操作
    print("1. 模拟各种缓存操作...")

    # 大量读操作
    for i in range(50):
        cache.get(f"read:key:{i % 5}")

    # 一些写操作
    for i in range(20):
        cache.set(f"write:key:{i}", f"value_{i}", ttl=3600)

    # 一些删除操作
    for i in range(10):
        cache.delete(f"delete:key:{i}")

    # 收集详细指标
    print("\n2. 详细指标分析:")
    metrics = monitor.metrics

    print(f"  GET 操作: {metrics.get_count}")
    print(f"  SET 操作: {metrics.set_count}")
    print(f"  DELETE 操作: {metrics.delete_count}")
    print(f"  命中次数: {metrics.hit_count}")
    print(f"  未命中次数: {metrics.miss_count}")
    print(f"  命中率: {metrics.get_hit_rate():.4f}")

    # 延迟统计
    print("\n3. 延迟统计:")
    get_latency = metrics.get_latency_stats("get")
    set_latency = metrics.get_latency_stats("set")

    print(
        f"  GET 延迟 - 最小: {get_latency['min'] or 0:.3f}ms, 最大: {get_latency['max'] or 0:.3f}ms, 平均: {get_latency['avg']:.3f}ms"
    )
    print(
        f"  SET 延迟 - 最小: {set_latency['min'] or 0:.3f}ms, 最大: {set_latency['max'] or 0:.3f}ms, 平均: {set_latency['avg']:.3f}ms"
    )


async def demonstrate_monitoring_lifecycle():
    """演示监控器的生命周期管理"""
    print("\n=== 监控生命周期示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)

    print("1. 初始状态:")
    print(f"  监控启用: {monitor.is_enabled()}")

    # 启用监控
    monitor.enable()
    print("\n2. 启用监控后:")
    print(f"  监控启用: {monitor.is_enabled()}")

    # 执行一些操作
    simulate_cache_operations(cache, 30)

    # 收集指标
    metrics1 = await monitor.collect_metrics()
    print(f"  操作前指标 - 总操作数: {metrics1.get_total_operations()}")

    # 重置指标
    monitor.reset_metrics()
    print("\n3. 重置指标后:")

    # 再执行一些操作
    simulate_cache_operations(cache, 20)

    metrics2 = await monitor.collect_metrics()
    print(f"  操作后指标 - 总操作数: {metrics2.get_total_operations()}")

    # 禁用监控
    monitor.disable()
    print("\n4. 禁用监控后:")
    print(f"  监控启用: {monitor.is_enabled()}")

    # 执行操作但不收集指标
    simulate_cache_operations(cache, 10)

    metrics3 = await monitor.collect_metrics()
    print(f"  禁用后指标 - 总操作数: {metrics3.get_total_operations()}")


async def demonstrate_exporter_configuration():
    """演示导出器配置选项"""
    print("\n=== 导出器配置示例 ===\n")

    cache = CacheManager(backend=MemoryBackend())
    monitor = CacheMonitor(cache)

    # Prometheus 导出器配置
    print("1. Prometheus 导出器配置:")
    prom_exporter = PrometheusExporter(
        monitor,
        namespace="production",
        subsystem="cache",
        labels={"service": "user-service", "version": "1.0.0"},
    )

    print(f"  命名空间: {prom_exporter.namespace}")
    print(f"  子系统: {prom_exporter.subsystem}")
    print(f"  标签: {prom_exporter.labels}")

    # 添加动态标签
    prom_exporter.update_labels({"region": "us-west-1", "zone": "a"})
    print(f"  更新后标签: {prom_exporter.labels}")

    # StatsD 导出器配置
    print("\n2. StatsD 导出器配置:")
    statsd_exporter = StatsDExporter(
        monitor,
        host="statsd.example.com",
        port=8125,
        prefix="production.user_service.cache",
        sample_rate=0.8,  # 80% 采样
        protocol="tcp",
        batch_size=20,
    )

    print(f"  主机: {statsd_exporter.host}")
    print(f"  端口: {statsd_exporter.port}")
    print(f"  前缀: {statsd_exporter.prefix}")
    print(f"  采样率: {statsd_exporter.sample_rate}")
    print(f"  协议: {statsd_exporter.protocol}")
    print(f"  批量大小: {statsd_exporter.batch_size}")


async def main():
    """主函数"""
    print("📊 Symphra Cache 监控示例\n")

    # 演示各种监控功能
    await demonstrate_basic_monitoring()
    await demonstrate_prometheus_export()
    await demonstrate_statsd_export()
    await demonstrate_real_time_monitoring()
    await demonstrate_metric_types()
    await demonstrate_monitoring_lifecycle()
    await demonstrate_exporter_configuration()

    print("\n✅ 所有监控示例完成！")
    print("\n监控功能特点:")
    print("  • 提供全面的缓存性能指标")
    print("  • 支持 Prometheus 和 StatsD 导出")
    print("  • 实时监控和历史数据分析")
    print("  • 灵活的配置和标签支持")
    print("  • 完整的生命周期管理")
    print("  • 支持自定义指标扩展")


if __name__ == "__main__":
    asyncio.run(main())
