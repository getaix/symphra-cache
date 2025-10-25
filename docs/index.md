# Symphra Cache 文档

欢迎使用 **Symphra Cache** - 生产级 Python 异步缓存库!

## 🚀 核心特性

- **全异步支持** - 完整的 async/await 支持，高效处理并发
- **多后端支持** - 内存、文件、Redis 多种后端可选
- **分布式特性** - 内置分布式锁、缓存失效通知
- **灵活的装饰器** - 支持同步和异步装饰器
- **监控导出** - Prometheus 和 StatsD 监控支持
- **配置灵活** - 支持 YAML、TOML、JSON 等多种配置格式
- **生产就绪** - 完整的错误处理、日志记录、性能优化

## 📦 快速开始

### 安装

```bash
pip install symphra-cache
```

### 基础使用

```python
from symphra_cache import CacheManager, create_memory_cache

# 创建缓存
cache = create_memory_cache()

# 设置值
cache.set("key", "value", ttl=3600)

# 获取值
value = cache.get("key")
```

### 使用装饰器

```python
@cache.cache(ttl=3600)
def expensive_function(arg):
    return compute_something(arg)

# 异步版本
@cache.acache(ttl=3600)
async def async_expensive_function(arg):
    return await compute_something_async(arg)
```

## 📚 文档导航

- **[快速开始](getting-started/installation.md)** - 安装和基础配置
- **[用户指南](guide/backends.md)** - 详细的功能说明
- **[API 参考](api/cache-manager.md)** - 完整的 API 文档
- **[最佳实践](best-practices/performance.md)** - 性能优化和最佳实践
- **[常见问题](faq.md)** - FAQ 和故障排除

## 🎯 主要优势

### 性能优异
- 内存后端采用 LRU 淘汰策略
- Redis 后端支持分布式缓存
- 异步操作无阻塞

### 易于使用
- 统一的 API 接口
- 装饰器简化使用
- 便利工厂函数

### 功能完整
- 支持多种序列化方式
- 灵活的缓存失效策略
- 分布式锁并发控制

### 生产级质量
- 完整的类型注解
- 100% 的文档覆盖
- 高代码质量评分

## 💡 使用示例

### 选择后端

```python
from symphra_cache import create_memory_cache, create_redis_cache, create_file_cache

# 内存缓存 - 适合单机应用
memory_cache = create_memory_cache(max_size=5000)

# Redis 缓存 - 适合分布式应用
redis_cache = create_redis_cache(host="localhost", port=6379)

# 文件缓存 - 适合持久化需求
file_cache = create_file_cache(db_path="./cache.db")
```

### 缓存失效

```python
from symphra_cache.invalidation import CacheInvalidator

invalidator = CacheInvalidator(cache)

# 失效特定键
await invalidator.invalidate_keys(["key1", "key2"])

# 使用模式匹配失效
await invalidator.invalidate_pattern("user:*")

# 失效所有缓存
await invalidator.invalidate_all()
```

### 分布式锁

```python
from symphra_cache.locks import DistributedLock

lock = DistributedLock(cache, "resource:1", timeout=10)

with lock:
    # 临界区代码，保证一次只有一个实例执行
    process_shared_resource()
```

## 🔧 配置

支持多种配置方式:

```python
# YAML 配置
cache = CacheManager.from_file("config.yaml")

# 字典配置
cache = CacheManager.from_config({
    "backend": "redis",
    "options": {
        "host": "localhost",
        "port": 6379,
    }
})
```

## 📊 监控

集成 Prometheus 和 StatsD 监控:

```python
from symphra_cache.monitoring.prometheus import PrometheusExporter

monitor = CacheMonitor(cache)
exporter = PrometheusExporter(monitor)

# 获取 Prometheus 格式指标
metrics = exporter.generate_metrics()
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📄 许可证

MIT License

---

**最后更新**: 2024-10-25
**版本**: 1.0.0
