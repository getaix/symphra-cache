# 缓存失效通知

缓存失效通知是 Symphra Cache 提供的高级功能，用于在数据更新时主动清除或更新缓存中的过期数据，确保数据一致性。

## 概述

缓存失效通过以下方式确保数据一致性：

- **主动失效**：在数据更新时主动清除相关缓存
- **模式匹配**：基于键模式批量清除缓存
- **依赖管理**：清除主键时同时清除相关依赖键
- **延迟失效**：在指定时间后自动清除缓存

## 基础用法

### 键级失效

```python
from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.invalidation import CacheInvalidator

# 创建缓存管理器
cache = CacheManager(backend=MemoryBackend())

# 创建失效器
invalidator = CacheInvalidator(cache)

# 失效特定键
keys_to_invalidate = ["user:123", "user:456", "user:789"]
await invalidator.invalidate_keys(keys_to_invalidate)
```

### 模式匹配失效

```python
# 失效所有用户数据
await invalidator.invalidate_pattern("user:*")

# 失效特定前缀的数据
await invalidator.invalidate_prefix("session:")

# 使用通配符模式
await invalidator.invalidate_pattern("product:*:price")
```

### 条件失效

```python
# 基于条件失效数据
def should_invalidate(key, value):
    """检查是否应该失效该键值对"""
    return "temp" in key or value is None

await invalidator.invalidate_by_condition(should_invalidate)
```

## 高级功能

### 缓存组管理

```python
# 创建用户组失效器
user_group = invalidator.create_cache_group_invalidator("user:")

# 失效整个用户组
await user_group.invalidate_all()

# 失效用户组中的特定模式
await user_group.invalidate_pattern("*:profile")

# 失效用户组中的特定键
await user_group.invalidate_keys(["profile", "settings"])
```

### 依赖失效

```python
# 定义依赖解析函数
def resolve_user_dependencies(user_keys):
    """解析用户相关的所有依赖键"""
    dependencies = []
    for key in user_keys:
        if key.startswith("user:profile:"):
            user_id = key.split(":")[-1]
            dependencies.extend([
                f"user:posts:{user_id}",
                f"user:followers:{user_id}",
                f"user:following:{user_id}",
                f"stats:user:{user_id}",
            ])
    return dependencies

# 失效用户及其所有依赖
primary_keys = ["user:profile:123"]
await invalidator.invalidate_with_dependencies(
    primary_keys,
    resolve_user_dependencies
)
```

### 延迟失效

```python
# 2秒后失效特定键
keys_to_delay = ["temp:data1", "temp:data2"]
task = await invalidator.schedule_invalidation(keys_to_delay, delay=2.0)

# 等待延迟失效完成
await task
```

### 条件延迟失效

```python
# 当条件满足时才失效
def check_condition():
    return some_global_flag is True

task = await invalidator.conditional_invalidation(
    condition=check_condition,
    keys=["conditional:key"],
    check_interval=1.0  # 每秒检查一次
)
```

## 批量操作优化

### 大数据集失效

```python
# 大量键的分批失效
all_keys = [f"key:{i}" for i in range(10000)]

# 使用自定义批量大小
invalidator = CacheInvalidator(cache, batch_size=500)
await invalidator.invalidate_keys(all_keys)
```

### 性能监控

```python
# 监控失效操作性能
start_time = time.time()
invalidated_count = await invalidator.invalidate_pattern("temp:*")
elapsed = time.time() - start_time

print(f"失效 {invalidated_count} 个键，耗时 {elapsed:.3f} 秒")
```

## 统计和监控

### 失效统计

```python
stats = invalidator.get_invalidation_stats()
print(f"总操作数: {stats['total_operations']}")
print(f"总失效键数: {stats['total_invalidated_keys']}")
print(f"最后操作时间: {stats['last_invalidation_time']}")
print(f"最后操作详情: {stats['last_operation']}")
```

### 失效历史

```python
# 获取最近10次失效操作历史
history = invalidator.get_invalidation_history(limit=10)
for i, record in enumerate(history, 1):
    print(f"操作 {i}:")
    print(f"  时间: {record['timestamp']}")
    print(f"  方法: {record['method']}")
    print(f"  详情: {record['details']}")
    print(f"  失效键数: {record['invalidated_count']}")
```

## 实际应用场景

### 用户数据更新

```python
async def update_user_profile(user_id, profile_data):
    """更新用户资料并失效相关缓存"""
    # 1. 更新数据库
    await database.update_user(user_id, profile_data)

    # 2. 失效用户相关缓存
    invalidator = CacheInvalidator(cache)

    # 失效用户资料缓存
    await invalidator.invalidate_keys([f"user:profile:{user_id}"])

    # 失效用户统计缓存
    await invalidator.invalidate_pattern(f"user:stats:{user_id}:*")

    # 失效用户动态缓存
    await invalidator.invalidate_pattern(f"feed:user:{user_id}:*")

# 使用示例
await update_user_profile(123, {"name": "New Name", "avatar": "new_avatar.jpg"})
```

### 商品价格更新

```python
async def update_product_price(product_id, new_price):
    """更新商品价格并失效相关缓存"""
    # 1. 更新数据库
    await database.update_price(product_id, new_price)

    # 2. 失效价格相关缓存
    invalidator = CacheInvalidator(cache)

    # 失效商品价格缓存
    await invalidator.invalidate_keys([f"product:price:{product_id}"])

    # 失效商品详情缓存
    await invalidator.invalidate_keys([f"product:detail:{product_id}"])

    # 失效分类价格缓存
    category = await database.get_product_category(product_id)
    await invalidator.invalidate_pattern(f"category:{category}:products:*")

# 使用示例
await update_product_price(101, 2999.99)
```

### 配置更新

```python
async def update_app_config(config_key, config_value):
    """更新应用配置并失效相关缓存"""
    # 1. 更新配置
    await config_service.update(config_key, config_value)

    # 2. 失效配置缓存
    invalidator = CacheInvalidator(cache)

    # 失效特定配置
    await invalidator.invalidate_keys([f"config:{config_key}"])

    # 失效所有配置缓存
    await invalidator.invalidate_prefix("config:")

    # 失效依赖该配置的功能缓存
    await invalidator.invalidate_pattern("feature:*")

# 使用示例
await update_app_config("maintenance_mode", True)
```

### 会话管理

```python
async def logout_user(user_id):
    """用户登出并清理会话缓存"""
    # 1. 清理会话状态
    await session_service.clear_session(user_id)

    # 2. 失会话缓存
    invalidator = CacheInvalidator(cache)

    # 失效用户会话
    await invalidator.invalidate_pattern(f"session:user:{user_id}:*")

    # 失效用户权限缓存
    await invalidator.invalidate_keys([f"permissions:user:{user_id}"])

    # 失效用户状态缓存
    await invalidator.invalidate_keys([f"status:user:{user_id}"])

# 使用示例
await logout_user(123)
```

## 最佳实践

### 1. 失效策略

- **及时失效**：数据更新后立即失效相关缓存
- **精确失效**：只失效必要的键，避免过度清除
- **批量失效**：大量键使用批量操作提高效率
- **异步失效**：非关键失效使用异步操作避免阻塞

### 2. 依赖管理

- **建立依赖图**：明确数据间的依赖关系
- **级联失效**：主数据变更时自动失效依赖数据
- **避免循环**：防止依赖关系形成循环

### 3. 性能优化

- **批量操作**：使用批量失效减少网络往返
- **模式匹配**：利用模式匹配提高失效效率
- **延迟失效**：非紧急失效可以延迟执行

### 4. 错误处理

- **优雅降级**：失效失败时记录错误但不中断业务
- **重试机制**：重要失效操作实现重试逻辑
- **监控告警**：监控失效操作的成功率

### 5. 分布式考虑

- **一致性**：在分布式环境中确保所有实例的缓存一致性
- **通知机制**：使用消息队列通知其他实例
- **版本控制**：使用版本号避免并发更新问题

## 错误处理

### 异常捕获

```python
async def safe_invalidate(invalidator, keys):
    """安全失效，包含错误处理"""
    try:
        return await invalidator.invalidate_keys(keys)
    except Exception as e:
        print(f"失效失败: {e}")
        # 记录错误日志
        # 实施降级策略
        return 0
```

### 降级策略

```python
async def invalidate_with_fallback(invalidator, keys):
    """带降级策略的失效"""
    try:
        return await invalidator.invalidate_keys(keys)
    except Exception:
        # 降级：使用单个键失效
        invalidated = 0
        for key in keys:
            try:
                if await invalidator.invalidate_keys([key]):
                    invalidated += 1
            except Exception:
                continue
        return invalidated
```

## 性能监控

### 失效性能指标

```python
class InvalidationMonitor:
    def __init__(self, invalidator):
        self.invalidator = invalidator
        self.metrics = {}

    async def monitored_invalidate(self, method, *args, **kwargs):
        """监控失效操作性能"""
        start_time = time.time()

        if method == "keys":
            result = await self.invalidator.invalidate_keys(*args, **kwargs)
        elif method == "pattern":
            result = await self.invalidator.invalidate_pattern(*args, **kwargs)
        # ... 其他方法

        elapsed = time.time() - start_time

        # 记录性能指标
        self.metrics[method] = {
            "last_duration": elapsed,
            "last_result": result,
            "avg_duration": self._calculate_avg(method, elapsed)
        }

        return result
```

通过合理使用缓存失效通知功能，可以确保缓存数据的一致性，避免脏数据问题，提升系统的可靠性和用户体验。
