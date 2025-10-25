# 变更日志

本页展示项目的发布与变更记录。仓库内的权威版本请参见 [`CHANGELOG.md`](https://github.com/getaix/symphra-cache/blob/main/CHANGELOG.md)。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 并遵循 [语义化版本](https://semver.org/lang/zh-CN/spec/v2.0.0.html)。

## [未发布]

### 计划特性
- Prometheus/StatsD 监控导出器
- 高级缓存预热策略
- 缓存失效通知
- 性能基准测试

## [0.1.1] - 2025-10-25

### 修复
- 修正 `pyproject.toml` 中 `all` 可选依赖定义，避免 CI 安装失败。
- 文档工作流：补充 `pull_request` 触发、纳入 `README.zh.md`、增加并发取消策略、禁止 PR 部署 Pages。

### 文档
- README 与中文 README 增加监控快速上手示例，完善监控 API 文档。

## [0.1.0] - 2025-10-25

### 新增 - 核心后端
- **MemoryBackend**: 高性能内存缓存
  - LRU 淘汰策略（基于 OrderedDict, O(1) 复杂度）
  - 后台 TTL 清理（守护线程）
  - 线程安全（RLock 保护）
  - 批量操作优化

- **FileBackend**: 持久化文件缓存
  - 基于 SQLite WAL 模式
  - 热重载支持（开发模式）
  - LRU 淘汰（基于 last_access 字段）
  - 完整的异步支持（aiosqlite）

- **RedisBackend**: 分布式缓存
  - redis-py 4.x+ 支持
  - 连接池优化
  - 批量操作（MGET/MSET 管道）
  - 原子操作（incr/decr）

### 新增 - 核心功能
- 统一的缓存管理器 (`CacheManager`)
- 同步和异步双 API（get/aget, set/aset, 等）
- TTL 过期控制（秒级精度）
- 批量操作（get_many, set_many, delete_many）
- 异常层次结构（8 个自定义异常类）

### 新增 - 装饰器
- `@cache`: 同步函数缓存装饰器
- `@acache`: 异步函数缓存装饰器
- `@cache_invalidate`: 缓存失效装饰器
- `CachedProperty`: 缓存属性装饰器
- 自定义键生成策略

### 新增 - 序列化
- JSON 序列化器（跨语言兼容）
- Pickle 序列化器（支持复杂对象）
- MessagePack 序列化器（高性能）
- 可扩展的序列化器注册机制

### 新增 - 高级特性
- 分布式锁（DistributedLock）
- 唯一标识符防止锁冲突
- 阻塞和非阻塞模式
- 自动超时释放

### 新增 - 测试
- 73 个单元测试，全部通过
- 测试覆盖所有核心功能
- 内存后端：27 个测试
- 文件后端：16 个测试
- 序列化器：8 个测试
- 装饰器：5 个测试
- 异常和类型：17 个测试

### 新增 - 文档
- 完整的中文代码注释（2000+ 行）
- 3 个使用示例（basic_usage, decorator_usage, file_backend_usage）
- 双语 README（English + 中文）
- 实现遵循 SOLID 原则

### 技术细节
- Python 3.11+ 支持
- 基于 uv 包管理器
- Mypy 严格模式通过
- Ruff 格式化和 Lint
- GitHub Actions CI/CD

[未发布]: https://github.com/getaix/symphra-cache/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/getaix/symphra-cache/releases/tag/v0.1.1
[0.1.0]: https://github.com/getaix/symphra-cache/releases/tag/v0.1.0
