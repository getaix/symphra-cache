# Use Cases

Practical scenarios showing how Symphra Cache fits into applications.

## Web API Response Caching

```python
from fastapi import FastAPI
from symphra_cache import CacheManager
from symphra_cache.backends import RedisBackend
from symphra_cache.decorators import cache

app = FastAPI()
cache = CacheManager(backend=RedisBackend(url="redis://localhost:6379"))

@cache(cache, ttl=60, key_prefix="api:v1:prod:")
async def fetch_products(category: str):
    # heavy DB query
    return [{"id": 1, "name": "Keyboard"}]
```

## Feature Flags and Config

```python
from symphra_cache.decorators import cache

@cache(cache, ttl=5, key_prefix="flags:")
async def get_flag(name: str) -> bool:
    # fetch from remote config store
    return True
```

## Computation Results

```python
@cache(cache, ttl=300, key_prefix="calc:")
async def expensive_fn(x: int, y: int):
    # CPU-bound logic
    return x ** y
```

## Batch Jobs

- Warm popular keys before traffic spikes
- Invalidate product group after nightly ETL

## Observability

- Monitor hit/miss rates and latency
- Export to Prometheus/StatsD for dashboards
