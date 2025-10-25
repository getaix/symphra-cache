# Monitoring

Metrics collection and exporter integrations.

## Usage

```python
from symphra_cache import CacheManager, CacheMonitor
from symphra_cache.monitoring.prometheus import PrometheusExporter
from symphra_cache.monitoring.statsd import StatsDExporter

# Create cache and monitor
cache = CacheManager.from_config({"backend": "memory"})
monitor = CacheMonitor(cache)

# Do some operations
cache.set("user:1", {"name": "Alice"})
cache.get("user:1")

# Unified metrics interface
metrics = monitor.metrics
print(metrics.get_latency_stats("get"))  # {"min": ..., "max": ..., "avg": ...}

# Prometheus exporter (text format)
prom = PrometheusExporter(monitor, namespace="myapp", subsystem="cache")
print(prom.generate_metrics())

# StatsD exporter (send to server)
# Note: requires a reachable StatsD server if you call send_metrics()
statsd = StatsDExporter(monitor, prefix="myapp.cache")
# await statsd.send_metrics()  # in an async context
```

## Metrics Interface

- `CacheMonitor.is_enabled()` toggles monitoring overhead on/off.
- `CacheMonitor.metrics` provides adapter fields: `get_count`, `set_count`, `delete_count`, `hit_count`, `miss_count`.
- `get_hit_rate()` and `get_total_operations()` return hit rate and total operations.
- `get_average_latency(operation)` returns average latency in milliseconds for `get`/`set`.
- `get_latency_stats(operation)` returns `{min, max, avg}` in milliseconds for `get`/`set`.

::: symphra_cache.monitor.CacheMonitor

::: symphra_cache.monitor.CacheStats

::: symphra_cache.monitoring.prometheus.PrometheusExporter

::: symphra_cache.monitoring.statsd.StatsDExporter
