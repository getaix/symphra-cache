# Getting Started

This quickstart shows the core usage patterns: basic operations, decorators, async flows, and configuration.

## Basic Usage

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

cache = CacheManager(backend=MemoryBackend())
cache.set("user:123", {"name": "Alice"}, ttl=3600)
user = cache.get("user:123")
print(user)
```

## Decorators (sync)

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.decorators import cache, cache_invalidate

cache_mgr = CacheManager(backend=MemoryBackend())

@cache(cache_mgr, ttl=600, key_prefix="user:")
def get_user(user_id: int):
    # Simulate DB query
    return {"id": user_id, "name": "Alice"}

@cache_invalidate(cache_mgr, key_prefix="user:")
def update_user(user_id: int, **updates):
    # Simulate DB update
    return True

get_user(123)
update_user(123, name="Bob")
get_user(123)  # refreshed
```

## Decorators (async)

```python
import httpx
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.decorators import acache

cache_mgr = CacheManager(backend=MemoryBackend())

@acache(cache_mgr, ttl=300)
async def fetch_json(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.json()
```

## Configuration

Create from a file:

```python
from symphra_cache import CacheManager
from symphra_cache.config import CacheConfig

config = CacheConfig.from_file("config/cache.yaml")
cache = CacheManager.from_config(config)
```

See `examples/` for more usage: `basic_usage.py`, `decorator_usage.py`, `config_usage.py`.
