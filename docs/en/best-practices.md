# Best Practices

Guidelines for robust, efficient caching with Symphra Cache.

## Keys and Namespaces

- Use consistent `key_prefix` naming by domain (e.g., `user:`)
- Avoid embedding volatile parameters directly; normalize where possible

## TTL and Freshness

- Choose TTLs based on data volatility and SLA
- Combine TTL with explicit invalidation for correctness

## Decorators

- Prefer `@cache` and `@acache` for simplicity
- Keep function arguments JSON-serializable or provide custom serializer

## Backends

- Use `MemoryBackend` for single-process speed
- Use `FileBackend` for hot-reload development flows
- Use `RedisBackend` for multi-instance sharing and persistence

## Monitoring and Ops

- Track hit/miss, latency percentiles, error rates
- Alert on miss spikes and backend timeouts
- Warm critical paths before peak traffic

## Testing

- Mock backends in unit tests for determinism
- Validate cache keys and invalidation paths
