# Symphra Cache

[English](README.md) | [中文](README.zh.md)

> 🚀 Production-grade async caching library for Python 3.11+

[![CI](https://github.com/getaix/symphra-cache/workflows/CI/badge.svg)](https://github.com/getaix/symphra-cache/actions)
[![PyPI version](https://badge.fury.io/py/symphra-cache.svg)](https://pypi.org/project/symphra-cache/)
[![Python versions](https://img.shields.io/pypi/pyversions/symphra-cache.svg)](https://pypi.org/project/symphra-cache/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code coverage](https://codecov.io/gh/symphra/symphra-cache/branch/main/graph/badge.svg)](https://codecov.io/gh/symphra/symphra-cache)

## ✨ Features

- **🎯 Three Backends**
  - **Memory**: High-performance in-memory cache with LRU eviction
  - **File**: Persistent SQLite-based cache with **hot reload** support
  - **Redis**: Distributed cache with cluster and sentinel support

- **⚡ Performance**
  - Fully async/await support
  - Memory backend: < 0.01ms latency
  - File backend: Hot reload 100k entries in < 5s
  - Redis backend: Connection pooling with hiredis acceleration

- **🔒 Advanced Features**
  - Distributed locks (Redis-based)
  - Cache warming and invalidation notifications
  - Prometheus/StatsD monitoring
  - Batch operations support

- **🎨 Developer Friendly**
  - Simple decorator API (`@cached`)
  - Context manager support (`async with cache.lock()`)
  - Type hints everywhere
  - Comprehensive Chinese documentation

## 📦 Installation

```bash
# Basic installation (uv - recommended)
uv add symphra-cache

# Or with pip
pip install symphra-cache

# With Redis support
uv add symphra-cache redis

# Full installation (all features)
pip install symphra-cache[all]
```


### Monitoring

```python
from symphra_cache import CacheManager, CacheMonitor
from symphra_cache.monitoring.prometheus import PrometheusExporter
from symphra_cache.monitoring.statsd import StatsDExporter

# Enable monitoring
cache = CacheManager.from_config({"backend": "memory"})
monitor = CacheMonitor(cache)

# Do some operations
cache.set("user:1", {"name": "Alice"})
cache.get("user:1")

# Unified metrics API
metrics = monitor.metrics
print(metrics.get_latency_stats("get"))  # {"min": ..., "max": ..., "avg": ...}

# Prometheus text metrics
prom = PrometheusExporter(monitor, namespace="myapp", subsystem="cache")
print(prom.generate_metrics())

# StatsD exporter (requires reachable server if sending)
statsd = StatsDExporter(monitor, prefix="myapp.cache")
# await statsd.send_metrics()  # in async context
```

- Install monitoring extras: `pip install symphra-cache[monitoring]`
- Provides Prometheus/StatsD exporters with hit/miss, counts, and latency stats.

## 🚀 Quick Start

### Basic Usage

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

# Create cache manager with memory backend
cache = CacheManager(backend=MemoryBackend())

# Basic operations
cache.set("user:123", {"name": "Alice", "age": 30}, ttl=3600)
user = cache.get("user:123")

# Async operations
await cache.aset("product:456", {"name": "Laptop", "price": 999})
product = await cache.aget("product:456")
```

### File Backend with Hot Reload

```python
from symphra_cache.backends import FileBackend

# Create file backend (persists to SQLite)
backend = FileBackend(db_path="./cache.db")
cache = CacheManager(backend=backend)

# Set cache (persisted immediately)
cache.set("session:xyz", {"user_id": 123}, ttl=1800)

# Restart process... cache automatically reloads!
# The data is still available after restart
session = cache.get("session:xyz")  # ✅ Works!
```

### Decorator API

```python
from symphra_cache.decorators import acache

@acache(cache, ttl=300)
async def get_user_profile(user_id: int):
    """Fetch user profile (cached for 5 minutes)"""
    return await database.fetch_user(user_id)

# First call: queries database
profile = await get_user_profile(123)

# Second call: returns from cache
profile = await get_user_profile(123)  # ⚡ Fast!
```

### Distributed Lock

```python
from symphra_cache.backends import RedisBackend
from symphra_cache.locks import DistributedLock

cache = CacheManager(backend=RedisBackend())
lock = DistributedLock(cache, "critical_resource", timeout=30)

with lock:
    # Only one instance can execute this block at a time
    value = cache.get("counter") or 0
    cache.set("counter", value + 1)
```

## 📚 Documentation

- **English Docs**: [https://symphra-cache.readthedocs.io/en/](https://symphra-cache.readthedocs.io/en/)
- **中文文档**: [https://symphra-cache.readthedocs.io/zh/](https://symphra-cache.readthedocs.io/zh/)

### Topics

- [Getting Started](docs/en/quickstart.md)
- [Backends](docs/en/backends/)
  - [Memory Backend](docs/en/backends/memory.md)
  - [File Backend (Hot Reload)](docs/en/backends/file.md)
  - [Redis Backend](docs/en/backends/redis.md)
- [Advanced Features](docs/en/advanced/)
  - [Distributed Locks](docs/en/advanced/locks.md)
  - [Cache Warming](docs/en/advanced/warming.md)
  - [Monitoring](docs/en/advanced/monitoring.md)
- [API Reference](docs/en/api/reference.md)

## 🏗️ Architecture

```
┌──────────────────────────────────────┐
│      Unified API (CacheManager)      │
│  @cached | async with cache.lock()  │
└──────────┬───────────┬───────────────┘
           │           │
    ┌──────▼─────┐ ┌──▼────┐ ┌────────┐
    │   Memory   │ │ File  │ │ Redis  │
    │  Backend   │ │Backend│ │Backend │
    │            │ │       │ │        │
    │ - Dict     │ │SQLite │ │redis-py│
    │ - LRU      │ │+Memory│ │+hiredis│
    │ - TTL      │ │Hot    │ │Cluster │
    └────────────┘ │Reload │ └────────┘
                   └───────┘
```

## 🔬 Performance

| Backend | Read (P99) | Write (P99) | Throughput | Hot Reload (100k) |
|---------|-----------|------------|-----------|-------------------|
| Memory  | < 0.01ms  | < 0.01ms   | 200k ops/s | N/A              |
| File    | < 0.1ms   | < 1ms      | 50k ops/s  | < 5s             |
| Redis   | < 1ms     | < 2ms      | 100k ops/s | N/A              |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **GitHub**: [https://github.com/getaix/symphra-cache](https://github.com/getaix/symphra-cache)
- **PyPI**: [https://pypi.org/project/symphra-cache/](https://pypi.org/project/symphra-cache/)
- **Documentation**: [https://getaix.github.io/symphra-cache/](https://getaix.github.io/symphra-cache/)
- **Issues**: [https://github.com/getaix/symphra-cache/issues](https://github.com/getaix/symphra-cache/issues)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=symphra/symphra-cache&type=Date)](https://star-history.com/#symphra/symphra-cache&Date)

---

Made with ❤️ by the Symphra Team
