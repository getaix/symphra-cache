# FAQ

Answers to common questions.

## Does it support both sync and async?
Yes. Use `@cache` for sync functions and `@acache` for async.

## How to choose a backend?
- `MemoryBackend`: fastest, per-process
- `FileBackend`: simple persistence, hot reload
- `RedisBackend`: shared, durable, horizontal scale

## How do I invalidate a specific key?
Use `CacheInvalidator.invalidate_key("prefix:...:id")` or `@cache_invalidate`.

## Can I customize serialization?
Yes. Use `serializers.get_serializer(...)` or implement `BaseSerializer`.

## Does it provide metrics?
Yes. Use `CacheMonitor` and exporters for Prometheus or StatsD.

## How to configure from files?
Load `CacheConfig` from YAML/TOML/JSON and attach to `CacheManager`.
