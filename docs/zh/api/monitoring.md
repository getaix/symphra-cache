# 监控

指标采集与导出集成。

## 使用示例

```python
from symphra_cache import CacheManager, CacheMonitor
from symphra_cache.monitoring.prometheus import PrometheusExporter
from symphra_cache.monitoring.statsd import StatsDExporter

# 创建缓存与监控器
cache = CacheManager.from_config({"backend": "memory"})
monitor = CacheMonitor(cache)

# 执行一些操作
cache.set("user:1", {"name": "张三"})
cache.get("user:1")

# 统一指标接口
metrics = monitor.metrics
print(metrics.get_latency_stats("get"))  # {"min": ..., "max": ..., "avg": ...}

# Prometheus 导出（文本格式）
prom = PrometheusExporter(monitor, namespace="myapp", subsystem="cache")
print(prom.generate_metrics())

# StatsD 导出（发送到服务器）
# 注意：调用 send_metrics() 需要可达的 StatsD 服务器
statsd = StatsDExporter(monitor, prefix="myapp.cache")
# await statsd.send_metrics()  # 在异步上下文中调用
```

## 指标接口说明

- `CacheMonitor.is_enabled()` 控制监控开关（关闭时几乎零开销）。
- `CacheMonitor.metrics` 提供导出器期望的字段：`get_count`、`set_count`、`delete_count`、`hit_count`、`miss_count`。
- `get_hit_rate()` 与 `get_total_operations()` 返回命中率与总操作数。
- `get_average_latency(operation)` 返回 `get`/`set` 的平均延迟（毫秒）。
- `get_latency_stats(operation)` 返回 `{min, max, avg}` 的延迟统计（毫秒）。

::: symphra_cache.monitor.CacheMonitor

::: symphra_cache.monitor.CacheStats

::: symphra_cache.monitoring.prometheus.PrometheusExporter

::: symphra_cache.monitoring.statsd.StatsDExporter
