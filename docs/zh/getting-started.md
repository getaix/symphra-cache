# 快速入门

## 基础示例

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

cache = CacheManager(backend=MemoryBackend())

result = await cache.get_or_set("hello", ttl=60, func=lambda: "world")
print(result)
```

## 装饰器（同步 / 异步）

```python
from symphra_cache.decorators import cache, acache

@cache(cache, ttl=120, key_prefix="sync:")
def add(x: int, y: int):
    return x + y

@acache(cache, ttl=120, key_prefix="async:")
async def fetch_user(uid: int):
    return {"id": uid}
```

## 从配置文件加载

```python
from symphra_cache.config import CacheConfig
from symphra_cache import CacheManager

conf = CacheConfig.from_yaml("config/cache.yaml")
manager = CacheManager.from_config(conf)
```
