# Changelog

All notable changes to this project will be documented here. For the canonical changelog in the repository, see [`CHANGELOG.md`](https://github.com/getaix/symphra-cache/blob/main/CHANGELOG.md).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- Prometheus/StatsD monitoring exporters
- Advanced cache warming strategies
- Cache invalidation notifications
- Performance benchmarks

## [0.1.1] - 2025-10-25

### Fixed
- Correct `all` optional dependencies in `pyproject.toml` to avoid CI install failure.
- Docs workflow: add `pull_request` triggers, include `README.zh.md`, add concurrency to cancel duplicate builds, and prevent Pages deployment on PRs.

### Documentation
- Add monitoring quick-start examples to READMEs; improve monitoring API docs.

## [0.1.0] - 2025-10-25

### Added - Core Backends
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

### Added - Core Features
- 统一的缓存管理器 (`CacheManager`)
- 同步和异步双 API（get/aget, set/aset, etc.)
- TTL 过期控制（秒级精度）
- 批量操作（get_many, set_many, delete_many）
- 异常层次结构（8 个自定义异常类）

### Added - Decorators
- `@cache`: 同步函数缓存装饰器
- `@acache`: 异步函数缓存装饰器
- `@cache_invalidate`: 缓存失效装饰器
- `CachedProperty`: 缓存属性装饰器
- 自定义键生成策略

### Added - Serialization
- JSON 序列化器（跨语言兼容）
- Pickle 序列化器（支持复杂对象）
- MessagePack 序列化器（高性能）
- 可扩展的序列化器注册机制

### Added - Advanced Features
- 分布式锁（DistributedLock）
- 唯一标识符防止锁冲突
- 阻塞和非阻塞模式
- 自动超时释放

### Added - Testing
- 73 个单元测试，全部通过
- 测试覆盖所有核心功能
- 内存后端：27 个测试
- 文件后端：16 个测试
- 序列化器：8 个测试
- 装饰器：5 个测试
- 异常和类型：17 个测试

### Added - Documentation
- 完整的中文代码注释（2000+ 行）
- 3 个使用示例（basic_usage, decorator_usage, file_backend_usage）
- 双语 README（English + 中文）
- SOLID 原则贯穿实现

### Technical Details
- Python 3.11+ 支持
- 基于 uv 包管理器
- Mypy 严格模式通过
- Ruff 格式化和 Lint
- GitHub Actions CI/CD

[Unreleased]: https://github.com/getaix/symphra-cache/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/getaix/symphra-cache/releases/tag/v0.1.1
[0.1.0]: https://github.com/getaix/symphra-cache/releases/tag/v0.1.0
