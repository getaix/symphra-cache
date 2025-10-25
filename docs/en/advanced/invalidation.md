# Cache Invalidation (Advanced)

Cache invalidation ensures data consistency by removing stale entries. Symphra Cache provides programmatic invalidation, pattern-based invalidation, and group invalidation utilities.

## When to Invalidate

- After write operations that change authoritative data
- When background jobs refresh datasets
- On scheduled intervals for time-sensitive data

## Programmatic Invalidation

Use the decorator to invalidate a matching cached key after a function completes.

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.decorators import cache, cache_invalidate

cache = CacheManager(backend=MemoryBackend())

@cache(cache, ttl=600, key_prefix="user:")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

@cache_invalidate(cache, key_prefix="user:")
def update_user(user_id: int, **updates):
    # mutate authoritative store
    return True
```

## Group Invalidation

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.invalidation import CacheInvalidator

cache = CacheManager(backend=MemoryBackend())
invalidator = CacheInvalidator(cache)

# Invalidate all keys with prefix
group = invalidator.create_cache_group_invalidator("user:")
await group.invalidate_all()
await group.invalidate_pattern("user:*:profile")
```

## Pattern Invalidation

```python
await invalidator.invalidate_pattern("product:*:price")
```

## Best Practices

- Keep prefixes consistent across `cache` and `cache_invalidate`
- Prefer targeted invalidation over global clears
- Use group invalidation for coherent datasets (e.g., all keys for a user)
- Combine TTL with invalidation for defense-in-depth
