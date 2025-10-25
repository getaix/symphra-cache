# 监控和指标

Symphra Cache 提供了全面的监控和指标功能，支持 Prometheus、StatsD 等主流监控系统，帮助您实时了解缓存系统的性能和健康状况。

## 概述

监控功能提供以下能力：

- **性能指标**：命中率、延迟、吞吐量等关键性能指标
- **健康检查**：缓存连接状态和系统健康度
- **多格式导出**：支持 Prometheus、StatsD 等多种监控格式
- **实时监控**：实时收集和展示缓存性能数据
- **自定义指标**：支持添加业务相关的自定义指标

## 基础监控

### 创建监控器

```python
from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.monitoring import CacheMonitor

# 创建缓存管理器
cache = CacheManager(backend=MemoryBackend())

# 创建监控器
monitor = CacheMonitor(cache)

# 收集指标
metrics = await monitor.collect_metrics()
print(f"缓存大小: {len(cache)}")
print(f"命中率: {metrics.get_hit_rate():.4f}")
print(f"总操作数: {metrics.get_total_operations()}")
```

### 健康检查

```python
# 检查缓存健康状态
health = monitor.get_health_status()
print(f"健康状态: {health['status']}")
print(f"缓存大小: {health['cache_size']}")
print(f"运行时间: {health['uptime_seconds']:.2f}秒")

# 异步健康检查
is_healthy = await cache.acheck_health()
print(f"异步健康检查: {'健康' if is_healthy else '不健康'}")
```

## Prometheus 监控

### 创建 Prometheus 导出器

```python
from symphra_cache.monitoring.prometheus import PrometheusExporter

# 创建 Prometheus 导出器
exporter = PrometheusExporter(
    monitor,
    namespace="myapp",
    subsystem="cache",
    labels={"instance": "web-server-01", "environment": "production"}
)

# 生成 Prometheus 格式指标
metrics_text = exporter.generate_metrics()
print(metrics_text)
```

### Prometheus 指标示例

```python
# 生成的 Prometheus 指标格式
"""
# HELP myapp_cache_size Current cache size
# TYPE myapp_cache_size gauge
myapp_cache_size{instance="web-server-01",environment="production"} 1024

# HELP myapp_cache_hit_rate Cache hit rate
# TYPE myapp_cache_hit_rate gauge
myapp_cache_hit_rate{instance="web-server-01",environment="production"} 0.95

# HELP myapp_cache_get_duration_seconds Time spent on GET operations
# TYPE myapp_cache_get_duration_seconds histogram
myapp_cache_get_duration_seconds_bucket{le="0.001",instance="web-server-01",environment="production"} 1000
myapp_cache_get_duration_seconds_bucket{le="0.005",instance="web-server-01",environment="production"} 1500
myapp_cache_get_duration_seconds_count{instance="web-server-01",environment="production"} 2000
myapp_cache_get_duration_seconds_sum{instance="web-server-01",environment="production"} 1.5
"""
```

### Pushgateway 集成

```python
# 创建 Pushgateway 客户端
pushgateway_client = exporter.create_pushgateway_client(
    gateway_url="http://pushgateway.example.com:9091",
    job_name="cache_monitoring",
    instance="web-server-01"
)

# 推送指标到 Pushgateway
success = await pushgateway_client.push_metrics()
print(f"推送成功: {success}")

# 获取推送 URL
push_url = pushgateway_client.get_push_url()
print(f"推送地址: {push_url}")
```

## StatsD 监控

### 创建 StatsD 导出器

```python
from symphra_cache.monitoring.statsd import StatsDExporter

# 创建 StatsD 导出器
statsd_exporter = StatsDExporter(
    monitor,
    host="statsd.example.com",
    port=8125,
    prefix="myapp.cache",
    sample_rate=1.0,  # 100% 采样
    protocol="udp",
    batch_size=100
)

# 生成 StatsD 格式指标
statsd_metrics = statsd_exporter.generate_all_metrics()
for metric in statsd_metrics:
    print(metric)
```

### StatsD 指标示例

```python
# 生成的 StatsD 指标格式
"""
myapp.cache.size:1024|g
myapp.cache.hit_rate:0.95|g
myapp.cache.operations.total:2000|g
myapp.cache.get.latency.avg:0.5|ms
myapp.cache.get.latency.min:0.1|ms
myapp.cache.get.latency.max:2.0|ms
myapp.cache.set.latency.avg:0.8|ms
myapp.cache.set.latency.min:0.2|ms
myapp.cache.set.latency.max:3.0|ms
"""
```

### 异步发送指标

```python
# 异步发送指标到 StatsD
success = await statsd_exporter.send_metrics()
print(f"发送成功: {success}")

# 使用连接池
async with statsd_exporter:
    await statsd_exporter.send_metrics()
```

## 实时监控

### 定时监控

```python
import asyncio

async def real_time_monitoring(monitor, interval=60):
    """实时监控缓存性能"""
    while True:
        try:
            # 收集指标
            metrics = await monitor.collect_metrics()

            # 记录关键指标
            hit_rate = metrics.get_hit_rate()
            cache_size = len(monitor.cache)
            total_ops = metrics.get_total_operations()

            print(f"[{time.strftime('%H:%M:%S')}] "
                  f"命中率: {hit_rate:.4f}, "
                  f"缓存大小: {cache_size}, "
                  f"总操作: {total_ops}")

            # 发送到监控系统
            await send_to_monitoring_system(hit_rate, cache_size, total_ops)

        except Exception as e:
            print(f"监控错误: {e}")

        await asyncio.sleep(interval)

# 启动实时监控
monitoring_task = asyncio.create_task(real_time_monitoring(monitor, interval=30))
```

### 指标聚合

```python
class MetricsAggregator:
    def __init__(self):
        self.metrics_history = []
        self.window_size = 10  # 保留最近10个采样点

    def add_metrics(self, metrics):
        """添加新的指标数据"""
        self.metrics_history.append({
            'timestamp': time.time(),
            'hit_rate': metrics.get_hit_rate(),
            'cache_size': len(metrics.cache),
            'get_latency': metrics.get_latency_stats('get'),
            'set_latency': metrics.get_latency_stats('set')
        })

        # 限制历史记录大小
        if len(self.metrics_history) > self.window_size:
            self.metrics_history.pop(0)

    def get_average_hit_rate(self):
        """获取平均命中率"""
        if not self.metrics_history:
            return 0.0

        total = sum(m['hit_rate'] for m in self.metrics_history)
        return total / len(self.metrics_history)

    def get_p95_latency(self, operation='get'):
        """获取 P95 延迟"""
        latencies = []
        for m in self.metrics_history:
            latency_stats = m.get(f'{operation}_latency', {})
            if latency_stats.get('avg'):
                latencies.append(latency_stats['avg'])

        if not latencies:
            return 0.0

        # 简单的 P95 计算
        latencies.sort()
        index = int(len(latencies) * 0.95)
        return latencies[min(index, len(latencies) - 1)]
```

## 自定义指标

### 添加业务指标

```python
# 添加自定义业务指标
monitor.create_custom_metric("user_cache_hit_rate", 0.95,
                           {"service": "user_service"})
monitor.create_custom_metric("product_cache_size", 500,
                           {"service": "product_service"})

# StatsD 自定义指标
statsd_exporter.add_custom_metric("custom_metric", 42.5, "g")
statsd_exporter.add_custom_metric("operation_count", 100, "c")
```

### 业务场景监控

```python
class BusinessMetricsMonitor:
    def __init__(self, monitor):
        self.monitor = monitor

    async def track_user_cache_performance(self):
        """跟踪用户缓存性能"""
        # 模拟业务指标收集
        user_cache_hit = self.calculate_user_cache_hit_rate()
        user_cache_size = self.get_user_cache_size()

        # 添加自定义指标
        self.monitor.create_custom_metric(
            "user_cache_hit_rate",
            user_cache_hit,
            {"business_area": "user_service"}
        )
        self.monitor.create_custom_metric(
            "user_cache_size",
            user_cache_size,
            {"business_area": "user_service"}
        )

    def calculate_user_cache_hit_rate(self):
        """计算用户缓存命中率"""
        # 实现业务逻辑
        pass

    def get_user_cache_size(self):
        """获取用户缓存大小"""
        # 实现业务逻辑
        pass
```

## 告警和通知

### 命中率告警

```python
class CacheAlertManager:
    def __init__(self, monitor, thresholds):
        self.monitor = monitor
        self.thresholds = thresholds  # 告警阈值配置
        self.alert_history = []

    async def check_alerts(self):
        """检查是否需要告警"""
        metrics = await self.monitor.collect_metrics()
        hit_rate = metrics.get_hit_rate()

        # 检查命中率告警
        if hit_rate < self.thresholds['hit_rate_min']:
            await self.send_alert(
                'cache_hit_rate_low',
                f'缓存命中率过低: {hit_rate:.4f} (阈值: {self.thresholds["hit_rate_min"]})'
            )

        # 检查缓存大小告警
        cache_size = len(self.monitor.cache)
        if cache_size > self.thresholds['cache_size_max']:
            await self.send_alert(
                'cache_size_too_large',
                f'缓存大小过大: {cache_size} (阈值: {self.thresholds["cache_size_max"]})'
            )

    async def send_alert(self, alert_type, message):
        """发送告警"""
        alert = {
            'timestamp': time.time(),
            'type': alert_type,
            'message': message,
            'severity': 'warning' if alert_type == 'cache_hit_rate_low' else 'critical'
        }

        self.alert_history.append(alert)

        # 发送到告警系统
        await self.send_to_alert_system(alert)

    async def send_to_alert_system(self, alert):
        """发送到实际的告警系统"""
        # 实现发送到钉钉、企业微信、邮件等
        pass
```

### 延迟告警

```python
async def monitor_latency_alerts(monitor, thresholds):
    """监控延迟告警"""
    while True:
        try:
            metrics = await monitor.collect_metrics()
            latency_stats = metrics.get_latency_stats('get')

            if latency_stats['avg'] > thresholds['get_latency_max']:
                await send_latency_alert(
                    'get_latency_high',
                    f'GET 操作平均延迟过高: {latency_stats["avg"]:.3f}ms'
                )

            if latency_stats['max'] > thresholds['get_latency_critical']:
                await send_latency_alert(
                    'get_latency_critical',
                    f'GET 操作最大延迟过高: {latency_stats["max"]:.3f}ms'
                )

        except Exception as e:
            print(f'延迟监控错误: {e}')

        await asyncio.sleep(60)  # 每分钟检查一次
```

## 监控最佳实践

### 1. 指标选择

- **核心指标**：命中率、延迟、缓存大小
- **业务指标**：按业务模块分类监控
- **错误指标**：缓存操作失败率
- **容量指标**：内存使用、连接数

### 2. 采样频率

- **高频采样**：关键指标每秒采样
- **低频采样**：聚合指标每分钟采样
- **按需采样**：特定场景下手动触发

### 3. 告警配置

- **合理阈值**：根据历史数据设置阈值
- **分级告警**：不同严重程度不同处理
- **避免噪音**：设置告警抑制规则

### 4. 数据保留

- **短期数据**：高精度数据保留较短时间
- **长期数据**：聚合数据保留较长时间
- **关键事件**：重要事件永久保留

### 5. 可视化

- **实时仪表盘**：关键指标实时展示
- **趋势分析**：历史数据趋势分析
- **异常检测**：自动识别异常模式

## 性能优化

### 监控开销控制

```python
# 控制监控开销
monitor = CacheMonitor(cache, enabled=True)

# 在高负载时临时禁用监控
if system_load_is_high():
    monitor.disable()
else:
    monitor.enable()

# 批量收集指标减少开销
async def batch_collect_metrics(monitor, keys):
    """批量收集多个缓存的指标"""
    tasks = [monitor.collect_metrics() for _ in keys]
    return await asyncio.gather(*tasks)
```

### 异步监控

```python
# 使用异步监控避免阻塞
async def async_monitoring_task(monitor):
    """异步监控任务"""
    while True:
        # 异步收集指标
        metrics = await monitor.collect_metrics()

        # 异步发送到监控系统
        await asyncio.gather(
            send_to_prometheus(metrics),
            send_to_statsd(metrics),
            check_alerts(metrics)
        )

        await asyncio.sleep(30)

# 启动异步监控
monitoring_task = asyncio.create_task(async_monitoring_task(monitor))
```

通过完善的监控和指标系统，您可以全面了解缓存系统的运行状态，及时发现和解决问题，确保系统的稳定性和高性能。
