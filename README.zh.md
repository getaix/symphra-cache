# Symphra Cache

[English](README.md) | [中文](README.zh.md)

> 🚀 生产级 Python 3.11+ 异步缓存库

[![CI](https://github.com/getaix/symphra-cache/workflows/CI/badge.svg)](https://github.com/getaix/symphra-cache/actions)
[![PyPI version](https://badge.fury.io/py/symphra-cache.svg)](https://pypi.org/project/symphra-cache/)
[![Python versions](https://img.shields.io/pypi/pyversions/symphra-cache.svg)](https://pypi.org/project/symphra-cache/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code coverage](https://codecov.io/gh/symphra/symphra-cache/branch/main/graph/badge.svg)](https://codecov.io/gh/symphra/symphra-cache)

## ✨ 核心特性

- **🎯 三种后端**
  - **内存**: 高性能内存缓存，支持 LRU 淘汰
  - **文件**: 基于 SQLite 的持久化缓存，支持**热重载**
  - **Redis**: 分布式缓存，支持集群和哨兵模式

- **⚡ 卓越性能**
  - 全异步支持（async/await）
  - 内存后端延迟 < 0.01ms
  - 文件后端热重载 10 万条数据 < 5 秒
  - Redis 后端支持连接池和 hiredis 加速

- **🔒 高级功能**
  - 分布式锁（基于 Redis）
  - 缓存预热和失效通知
  - Prometheus/StatsD 监控导出
  - 批量操作支持

- **🎨 开发友好**
  - 简洁的装饰器 API（`@cached`）
  - 上下文管理器支持（`async with cache.lock()`）
  - 完整的类型注解
  - 详尽的中文文档和注释

## 📦 安装

```bash
# 基础安装（内存 + 文件后端）
pip install symphra-cache

# 安装 Redis 加速（hiredis）
pip install symphra-cache[hiredis]

# 安装监控支持
pip install symphra-cache[monitoring]

# 完整安装（所有功能）
pip install symphra-cache[all]
```

## 🚀 快速开始

### 基础用法

```python
from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend

# 创建内存后端的缓存管理器
cache = CacheManager(backend=MemoryBackend())

# 基本操作
cache.set("user:123", {"name": "张三", "age": 30}, ttl=3600)
user = cache.get("user:123")

# 异步操作
await cache.aset("product:456", {"name": "笔记本电脑", "price": 6999})
product = await cache.aget("product:456")
```

### 文件后端（热重载）

```python
from symphra_cache.backends import FileBackend

# 创建文件后端（持久化到 SQLite）
backend = FileBackend(db_path="./cache.db")
cache = CacheManager(backend=backend)

# 设置缓存（立即持久化）
cache.set("session:xyz", {"user_id": 123}, ttl=1800)

# 重启进程... 缓存自动重新加载！
# 重启后数据仍然可用
session = cache.get("session:xyz")  # ✅ 可以正常获取！
```

### 装饰器 API

```python
@cache.cached(ttl=300)
async def get_user_profile(user_id: int):
    """获取用户资料（缓存 5 分钟）"""
    return await database.fetch_user(user_id)

# 第一次调用：查询数据库
profile = await get_user_profile(123)

# 第二次调用：从缓存返回
profile = await get_user_profile(123)  # ⚡ 极速！
```

### 分布式锁

```python
from symphra_cache.backends import RedisBackend

cache = CacheManager(backend=RedisBackend())

async with cache.lock("critical_resource", ttl=30):
    # 同一时间只有一个实例可以执行这段代码
    value = await cache.get("counter")
    await cache.set("counter", value + 1)
```

### 监控

```python
from symphra_cache import CacheManager, CacheMonitor
from symphra_cache.monitoring.prometheus import PrometheusExporter
from symphra_cache.monitoring.statsd import StatsDExporter

# 启用监控
cache = CacheManager.from_config({"backend": "memory"})
monitor = CacheMonitor(cache)

# 执行一些操作
cache.set("user:1", {"name": "张三"})
cache.get("user:1")

# 统一指标接口
metrics = monitor.metrics
print(metrics.get_latency_stats("get"))  # {"min": ..., "max": ..., "avg": ...}

# Prometheus 文本指标
prom = PrometheusExporter(monitor, namespace="myapp", subsystem="cache")
print(prom.generate_metrics())

# StatsD 导出器（发送需要可达的服务器）
statsd = StatsDExporter(monitor, prefix="myapp.cache")
# await statsd.send_metrics()  # 在异步上下文中调用
```

- 安装监控扩展：`pip install symphra-cache[monitoring]`
- 提供 Prometheus/StatsD 导出器，包含命中/未命中、计数与延迟统计。

## 📚 文档

- **English Docs**: [https://symphra-cache.readthedocs.io/en/](https://symphra-cache.readthedocs.io/en/)
- **中文文档**: [https://symphra-cache.readthedocs.io/zh/](https://symphra-cache.readthedocs.io/zh/)

### 主题

- [快速开始](docs/zh/quickstart.md)
- [后端详解](docs/zh/backends/)
  - [内存后端](docs/zh/backends/memory.md)
  - [文件后端（热重载）](docs/zh/backends/file.md)
  - [Redis 后端](docs/zh/backends/redis.md)
- [高级特性](docs/zh/advanced/)
  - [分布式锁](docs/zh/advanced/locks.md)
  - [缓存预热](docs/zh/advanced/warming.md)
  - [监控导出](docs/zh/advanced/monitoring.md)
- [API 参考](docs/zh/api/reference.md)

## 🏗️ 架构设计

```
┌──────────────────────────────────────┐
│      统一接口层 (CacheManager)        │
│  @cached | async with cache.lock()  │
└──────────┬───────────┬───────────────┘
           │           │
    ┌──────▼─────┐ ┌──▼────┐ ┌────────┐
    │   内存     │ │ 文件  │ │ Redis  │
    │   后端     │ │ 后端  │ │ 后端   │
    │            │ │       │ │        │
    │ - Dict     │ │SQLite │ │redis-py│
    │ - LRU      │ │+Memory│ │+hiredis│
    │ - TTL      │ │热重载 │ │ 集群   │
    └────────────┘ └───────┘ └────────┘
```

## 🔬 性能指标

| 后端 | 读取延迟 (P99) | 写入延迟 (P99) | 吞吐量 | 热重载 (10万条) |
|------|---------------|---------------|--------|----------------|
| 内存 | < 0.01ms      | < 0.01ms      | 20万 ops/s | N/A        |
| 文件 | < 0.1ms       | < 1ms         | 5万 ops/s  | < 5秒      |
| Redis | < 1ms        | < 2ms         | 10万 ops/s | N/A        |

## 🤝 贡献指南

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 开源协议

本项目采用 MIT 协议 - 详见 [LICENSE](LICENSE) 文件。

## 🔗 相关链接

- **GitHub**: [https://github.com/getaix/symphra-cache](https://github.com/getaix/symphra-cache)
- **PyPI**: [https://pypi.org/project/symphra-cache/](https://pypi.org/project/symphra-cache/)
- **文档**: [https://getaix.github.io/symphra-cache/](https://getaix.github.io/symphra-cache/)
- **问题反馈**: [https://github.com/getaix/symphra-cache/issues](https://github.com/getaix/symphra-cache/issues)
- **变更日志**: [CHANGELOG.md](CHANGELOG.md)

## 🌟 Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=symphra/symphra-cache&type=Date)](https://star-history.com/#symphra/symphra-cache&Date)

---

❤️ 由 Symphra 团队精心打造
