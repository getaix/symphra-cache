# Symphra Cache

A production-grade Python async cache library with unified APIs and pluggable backends. It supports in-memory, SQLite file, and Redis storage, with decorators, distributed locks, warming, invalidation, and monitoring built-in.

- Fully async and sync APIs
- Drop-in decorators for caching and invalidation
- Backends: Memory, File (SQLite, hot reload), Redis
- Distributed lock helper
- Cache warming and group invalidation
- Monitoring exporters: Prometheus, StatsD

## Architecture

- `CacheManager`: Facade providing consistent cache operations
- Backends: `MemoryBackend`, `FileBackend`, `RedisBackend`
- Decorators: `cache`, `acache`, `cache_invalidate`, `CachedProperty`
- Utilities: `DistributedLock`, `CacheWarmer`, `CacheInvalidator`
- Monitoring: `CacheMonitor`, `PrometheusExporter`, `StatsDExporter`

## Links

- Installation: [installation.md](installation.md)
- Getting Started: [getting-started.md](getting-started.md)
- API Reference: [api/index.md](api/index.md)
