# 缓存预热

缓存预热是 Symphra Cache 提供的高级功能，用于在应用程序启动或运行时预先加载热点数据到缓存中，避免缓存冷启动问题，提升系统性能。

## 概述

缓存预热通过以下方式提升性能：

- **避免缓存雪崩**：在高并发场景下，大量请求同时访问未缓存的数据可能导致数据库压力过大
- **提升响应速度**：热点数据预先加载，减少首次访问延迟
- **优化用户体验**：关键数据始终可用，提供一致的响应时间

## 基础用法

### 手动预热

```python
from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.warming import CacheWarmer

# 创建缓存管理器
cache = CacheManager(backend=MemoryBackend())

# 创建预热器
warmer = CacheWarmer(cache, ttl=3600)

# 手动预热数据
data = {
    "user:1": {"name": "Alice", "age": 30},
    "user:2": {"name": "Bob", "age": 25},
    "config:app_name": "MyApp",
}

await warmer.warm_up(data)
```

### 自动预热

```python
# 定义数据源函数
def load_hot_data():
    return {
        "product:101": {"name": "笔记本电脑", "price": 5999},
        "product:102": {"name": "智能手机", "price": 2999},
    }

# 自动预热
await warmer.auto_warm_up(load_hot_data)
```

### 智能预热

```python
from symphra_cache.warming import SmartCacheWarmer

# 创建智能预热器
smart_warmer = SmartCacheWarmer(cache, prediction_window=24)

# 记录访问模式
smart_warmer.record_cache_miss("user:123")

# 智能预热热点数据
def predict_and_load(hot_keys):
    return {key: f"predicted_data_{key}" for key in hot_keys}

await smart_warmer.smart_warm_up(predict_and_load, top_k=10)
```

## 高级功能

### 增量预热

适用于大数据集的渐进式预热：

```python
# 大量热点键
hot_keys = [f"user:{i}" for i in range(1, 10001)]  # 1万用户

def load_user_batch(keys):
    """批量加载用户数据"""
    return {key: f"user_data_{key}" for key in keys}

# 增量预热，每次处理100个键
await warmer.incremental_warm_up(hot_keys, load_user_batch, batch_size=100)
```

### 文件预热

从文件预热缓存数据：

```python
import json

# JSON 文件预热
await warmer.warm_up_from_file("cache_data.json", format="json", ttl=7200)

# CSV 文件预热
await warmer.warm_up_from_file("cache_data.csv", format="csv", ttl=3600)
```

### TTL 映射预热

为不同键设置不同的过期时间：

```python
data = {
    "session:user123": "session_data",
    "token:api456": "api_token",
    "config:app": "app_config",
}

ttl_map = {
    "session:user123": 1800,    # 会话数据：30分钟
    "token:api456": 3600,       # API 令牌：1小时
    "config:app": 7200,         # 配置数据：2小时
}

await warmer.warm_up_with_ttl_map(data, ttl_map)
```

### 后台预热

启动后台定时预热任务：

```python
# 启动后台预热（每小时执行一次）
await warmer.start_background_warming(
    data_source=load_hot_data,
    interval=3600  # 1小时
)

# 停止后台预热
warmer.stop_background_warming()
```

## 缓存组管理

### 创建缓存组

```python
# 为用户数据创建专门的缓存组
user_group = warmer.create_cache_group_invalidator("user:")

# 预热整个用户组
await user_group.warm_up_all()

# 预热特定模式
await user_group.warm_up_pattern("*:profile")
```

## 统计和监控

### 获取预热统计

```python
stats = warmer.get_warming_stats()
print(f"策略: {stats['strategy']}")
print(f"最后预热时间: {stats['last_warm_up_time']}")
print(f"已预热键数量: {stats['total_keys_warmed']}")
print(f"热点键数量: {stats['hot_keys_count']}")
```

### 预热历史

```python
# 获取最近10次预热操作历史
history = warmer.get_invalidation_history(limit=10)
for record in history:
    print(f"时间: {record['timestamp']}")
    print(f"方法: {record['method']}")
    print(f"详情: {record['details']}")
```

## 工厂模式

使用工厂函数创建不同类型的预热器：

```python
from symphra_cache.warming import create_warmer

# 创建手动预热器
manual_warmer = create_warmer(cache, strategy="manual", ttl=3600)

# 创建智能预热器
smart_warmer = create_warmer(cache, strategy="smart", prediction_window=12)

# 创建自定义配置预热器
custom_warmer = create_warmer(
    cache,
    strategy="incremental",
    batch_size=50,
    ttl=1800
)
```

## 最佳实践

### 1. 预热时机

- **应用启动时**：预热核心配置和热点数据
- **低峰时段**：在业务低峰期执行大量预热操作
- **预测性预热**：基于历史访问模式预测热点数据

### 2. 数据选择

- **热点数据**：访问频率高的数据优先预热
- **关键数据**：对业务至关重要的数据
- **计算成本高**：生成成本高的数据适合预热

### 3. 性能优化

- **批量操作**：使用批量预热减少网络往返
- **分批处理**：大数据集分批预热，避免内存峰值
- **异步执行**：使用异步预热避免阻塞主线程

### 4. TTL 策略

- **动态 TTL**：根据数据类型设置不同过期时间
- **热点延长**：热点数据设置较长 TTL
- **冷数据短 TTL**：冷数据设置较短 TTL

### 5. 监控和调优

- **监控命中率**：跟踪预热效果
- **调整策略**：根据监控数据调整预热策略
- **容量规划**：合理设置缓存容量，避免内存溢出

## 错误处理

### 异常捕获

```python
try:
    await warmer.warm_up(large_data)
except Exception as e:
    print(f"预热失败: {e}")
    # 记录错误日志
    # 实施降级策略
```

### 降级策略

```python
def safe_warm_up(warmer, data):
    """安全预热，包含错误处理"""
    try:
        await warmer.warm_up(data)
        return True
    except Exception as e:
        # 记录错误但不中断应用
        print(f"预热警告: {e}")
        return False
```

## 性能调优

### 批量大小优化

```python
# 根据网络和内存情况调整批量大小
optimal_batch_size = 100  # 初始值
warmer = CacheWarmer(cache, batch_size=optimal_batch_size)
```

### 并发预热

```python
# 并发执行多个预热任务
tasks = []
for data_chunk in data_chunks:
    task = warmer.warm_up(data_chunk)
    tasks.append(task)

await asyncio.gather(*tasks)
```

## 实际应用场景

### 电商网站

```python
# 预热商品数据
product_warmer = CacheWarmer(cache, ttl=3600)
await product_warmer.warm_up_from_file("hot_products.json")

# 预热用户会话
session_warmer = CacheWarmer(cache, ttl=1800)
await session_warmer.warm_up(load_active_sessions())
```

### 社交媒体

```python
# 智能预热用户动态
social_warmer = SmartCacheWarmer(cache)
await social_warmer.smart_warm_up(load_user_feeds, top_k=50)

# 预热热门话题
trending_warmer = CacheWarmer(cache, ttl=600)  # 10分钟过期
await trending_warmer.warm_up(load_trending_topics())
```

### 内容管理系统

```python
# 预热热门文章
cms_warmer = CacheWarmer(cache, ttl=7200)
await cms_warmer.warm_up(load_popular_articles())

# 预热分类数据
category_warmer = CacheWarmer(cache, ttl=14400)
await category_warmer.warm_up(load_categories())
```

通过合理使用缓存预热功能，可以显著提升应用程序的性能和用户体验，特别是在高并发和大数据量的场景下。
