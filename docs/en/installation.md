# Installation

Install the core library:

```bash
pip install symphra-cache
```

Optional extras:

- Monitoring exporters:
  ```bash
  pip install "symphra-cache[monitoring]"
  ```
- Docs tooling (to build this site locally):
  ```bash
  pip install "symphra-cache[docs]"
  ```
- Redis performance acceleration (C extension):
  ```bash
  pip install "symphra-cache[hiredis]"
  ```

Python requirements: `>= 3.11`.

## Verify Installation

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

cache = CacheManager(backend=MemoryBackend())
cache.set("hello", "world", ttl=60)
assert cache.get("hello") == "world"
```
