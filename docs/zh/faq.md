# 常见问题

## 是否同时支持同步与异步？
支持。同步用 `@cache`，异步用 `@acache`。

## 如何选择后端？
- `MemoryBackend`：最快，进程内
- `FileBackend`：简单持久化，热重载
- `RedisBackend`：共享、持久化、水平扩展

## 如何失效特定键？
使用 `CacheInvalidator.invalidate_key("prefix:...:id")` 或 `@cache_invalidate`。

## 可以自定义序列化吗？
可以。使用 `serializers.get_serializer(...)` 或实现 `BaseSerializer`。

## 是否提供监控指标？
提供。使用 `CacheMonitor`，并通过 Prometheus / StatsD 导出。

## 如何从文件配置？
从 YAML/TOML/JSON 加载 `CacheConfig`，再构造 `CacheManager`。
