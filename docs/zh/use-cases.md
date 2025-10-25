# 使用场景

展示 Symphra Cache 在应用中的典型使用方式。

## Web API 响应缓存

```python
from fastapi import FastAPI
from symphra_cache import CacheManager
from symphra_cache.backends import RedisBackend
from symphra_cache.decorators import cache

app = FastAPI()
cache = CacheManager(backend=RedisBackend(url="redis://localhost:6379"))

@cache(cache, ttl=60, key_prefix="api:v1:prod:")
async def fetch_products(category: str):
    return [{"id": 1, "name": "Keyboard"}]
```

## 特性开关与配置

```python
from symphra_cache.decorators import cache

@cache(cache, ttl=5, key_prefix="flags:")
async def get_flag(name: str) -> bool:
    return True
```

## 计算结果缓存

```python
@cache(cache, ttl=300, key_prefix="calc:")
async def expensive_fn(x: int, y: int):
    return x ** y
```

## 批处理作业
- 高峰前预热热门键
- 夜间 ETL 后按分组失效

## 可观测性
- 监控命中/未命中与延迟
- 导出至 Prometheus/StatsD 做看板
