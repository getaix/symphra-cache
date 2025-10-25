# CacheManager

High-level facade managing cache operations across backends.

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

cache = CacheManager(backend=MemoryBackend())
cache.set("k", "v", ttl=60)
assert cache.get("k") == "v"
```

::: symphra_cache.manager.CacheManager
