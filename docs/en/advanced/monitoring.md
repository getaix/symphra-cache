# Monitoring (Advanced)

Measure cache effectiveness and latency, export metrics to Prometheus or StatsD.

## Built-in Metrics

```python
from symphra_cache.monitor import CacheMonitor

monitor = CacheMonitor()
# Attach monitor to manager
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

manager = CacheManager(backend=MemoryBackend(), monitor=monitor)
```

## Prometheus Exporter

```python
from symphra_cache.monitoring.prometheus import PrometheusExporter

exporter = PrometheusExporter(monitor)
exporter.start_http_server(port=8000)
```

## StatsD Exporter

```python
from symphra_cache.monitoring.statsd import StatsDExporter

exporter = StatsDExporter(monitor, host="127.0.0.1", port=8125)
exporter.start()
```

## Key Metrics

- Hit ratio, miss ratio
- Latency percentiles (p50/p90/p99)
- Backend errors and timeouts
- Evictions and invalidations

## Operability Tips

- Set alerts for miss spikes and error rates
- Track warming impact on tail latency
- Tag metrics by backend type and key namespaces
