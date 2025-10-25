"""
缓存预热模块测试

测试 CacheWarmer 和相关功能的完整测试套件。
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path

import pytest
from symphra_cache import CacheManager, MemoryBackend
from symphra_cache.warming import (
    CacheWarmer,
    SmartCacheWarmer,
    create_warmer,
)


class TestCacheWarmerBasics:
    """测试 CacheWarmer 基础功能"""

    def test_initialization(self) -> None:
        """测试初始化"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        assert warmer.cache is cache
        assert warmer.strategy == "manual"
        assert warmer.batch_size == 100
        assert warmer.ttl is None

    def test_initialization_with_custom_params(self) -> None:
        """测试自定义参数初始化"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, strategy="auto", batch_size=50, ttl=3600)

        assert warmer.strategy == "auto"
        assert warmer.batch_size == 50
        assert warmer.ttl == 3600

    @pytest.mark.asyncio
    async def test_warm_up_basic(self) -> None:
        """测试基础预热功能"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, ttl=7200)

        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

        await warmer.warm_up(data)

        # 验证数据已预热
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # 验证 TTL 设置
        ttl = cache.ttl("key1")
        assert ttl > 0 and ttl <= 7200

    @pytest.mark.asyncio
    async def test_warm_up_with_custom_ttl(self) -> None:
        """测试自定义 TTL 预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, ttl=3600)

        data = {"key1": "value1", "key2": "value2"}

        await warmer.warm_up(data, ttl=1800)

        # 验证使用了自定义 TTL
        ttl = cache.ttl("key1")
        assert ttl > 0 and ttl <= 1800

    @pytest.mark.asyncio
    async def test_warm_up_empty_data(self) -> None:
        """测试空数据预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        await warmer.warm_up({})

        # 应该不抛出异常
        assert len(cache) == 0

    @pytest.mark.asyncio
    async def test_warm_up_with_batch_size(self) -> None:
        """测试批量预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, batch_size=2)

        # 创建大量数据
        data = {f"key_{i}": f"value_{i}" for i in range(5)}

        await warmer.warm_up(data)

        # 验证所有数据都已预热
        for key, value in data.items():
            assert cache.get(key) == value


class TestCacheWarmerAuto:
    """测试自动预热功能"""

    @pytest.mark.asyncio
    async def test_auto_warm_up(self) -> None:
        """测试自动预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        def data_source():
            return {"auto_key1": "auto_value1", "auto_key2": "auto_value2"}

        await warmer.auto_warm_up(data_source)

        assert cache.get("auto_key1") == "auto_value1"
        assert cache.get("auto_key2") == "auto_value2"

    @pytest.mark.asyncio
    async def test_background_warming(self) -> None:
        """测试后台预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        call_count = 0

        def data_source():
            nonlocal call_count
            call_count += 1
            return {f"bg_key_{call_count}": f"bg_value_{call_count}"}

        # 启动后台预热
        await warmer.start_background_warming(data_source, interval=0.1)

        # 等待两次执行
        await asyncio.sleep(0.3)

        # 停止后台预热
        warmer.stop_background_warming()

        # 验证执行了多次
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_auto_warm_up_with_error(self) -> None:
        """测试自动预热错误处理"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        def failing_data_source():
            raise ValueError("模拟数据源错误")

        # 应该不抛出异常
        await warmer.auto_warm_up(failing_data_source)

        # 缓存应该为空
        assert len(cache) == 0


class TestCacheWarmerIncremental:
    """测试增量预热功能"""

    @pytest.mark.asyncio
    async def test_incremental_warm_up(self) -> None:
        """测试增量预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, batch_size=2)

        # 先预热一些基础数据
        base_data = {"base_key1": "base_value1", "base_key2": "base_value2"}
        await warmer.warm_up(base_data)

        # 增量预热热点键
        hot_keys = ["hot_key1", "hot_key2", "hot_key3", "hot_key4", "hot_key5"]

        def data_loader(keys):
            return {key: f"hot_data_for_{key}" for key in keys}

        await warmer.incremental_warm_up(hot_keys, data_loader)

        # 验证基础数据仍在
        assert cache.get("base_key1") == "base_value1"
        assert cache.get("base_key2") == "base_value2"

        # 验证增量数据已加载
        for key in hot_keys:
            assert cache.get(key) == f"hot_data_for_{key}"


class TestCacheWarmerSmart:
    """测试智能预热功能"""

    @pytest.mark.asyncio
    async def test_smart_warmer_initialization(self) -> None:
        """测试智能预热器初始化"""
        cache = CacheManager(backend=MemoryBackend())
        smart_warmer = SmartCacheWarmer(cache, prediction_window=12, learning_rate=0.2)

        assert smart_warmer.prediction_window == 12
        assert smart_warmer.learning_rate == 0.2
        assert smart_warmer.strategy == "smart"

    @pytest.mark.asyncio
    async def test_record_cache_miss(self) -> None:
        """测试记录缓存未命中"""
        cache = CacheManager(backend=MemoryBackend())
        smart_warmer = SmartCacheWarmer(cache)

        # 记录一些访问
        smart_warmer.record_cache_miss("hot_key1")
        smart_warmer.record_cache_miss("hot_key1")  # 重复访问
        smart_warmer.record_cache_miss("hot_key2")

        # 获取热点键
        hot_keys = smart_warmer.get_hot_keys(min_access_count=1, hours=1.0)

        assert "hot_key1" in hot_keys
        assert "hot_key2" in hot_keys

    @pytest.mark.asyncio
    async def test_smart_warm_up(self) -> None:
        """测试智能预热"""
        cache = CacheManager(backend=MemoryBackend())
        smart_warmer = SmartCacheWarmer(cache)

        # 记录访问模式
        for _ in range(5):
            smart_warmer.record_cache_miss("key1")
        for _ in range(3):
            smart_warmer.record_cache_miss("key2")

        def data_loader(keys):
            return {key: f"smart_data_{key}" for key in keys}

        await smart_warmer.smart_warm_up(data_loader, top_k=2)

        # 验证热点键被预热
        hot_keys = smart_warmer.get_hot_keys(min_access_count=3, hours=1.0)
        for key in hot_keys:
            assert cache.get(key) == f"smart_data_{key}"


class TestCacheWarmerFile:
    """测试文件预热功能"""

    @pytest.mark.asyncio
    async def test_warm_up_from_json_file(self) -> None:
        """测试从 JSON 文件预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        # 创建临时 JSON 文件
        test_data = {
            "config:key1": "value1",
            "config:key2": "value2",
            "feature:flag1": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            await warmer.warm_up_from_file(temp_file, format="json", ttl=3600)

            # 验证数据已加载
            for key, value in test_data.items():
                assert cache.get(key) == value

        finally:
            Path(temp_file).unlink()

    @pytest.mark.asyncio
    async def test_warm_up_from_nonexistent_file(self) -> None:
        """测试从不存在文件预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        with pytest.raises(RuntimeError):
            await warmer.warm_up_from_file("/nonexistent/file.json", format="json")

    @pytest.mark.asyncio
    async def test_warm_up_with_ttl_map(self) -> None:
        """测试 TTL 映射预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        data = {
            "session:key1": "session_data",
            "token:key2": "token_data",
            "config:key3": "config_data",
        }

        ttl_map = {
            "session:key1": 1800,
            "token:key2": 3600,
            "config:key3": 7200,
        }

        await warmer.warm_up_with_ttl_map(data, ttl_map)

        # 验证不同 TTL
        session_ttl = cache.ttl("session:key1")
        token_ttl = cache.ttl("token:key2")
        config_ttl = cache.ttl("config:key3")

        assert session_ttl <= 1800
        assert token_ttl <= 3600
        assert config_ttl <= 7200


class TestCacheWarmerStats:
    """测试预热统计功能"""

    @pytest.mark.asyncio
    async def test_get_warming_stats(self) -> None:
        """测试获取预热统计"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, strategy="auto", batch_size=50)

        stats = warmer.get_warming_stats()

        assert stats["strategy"] == "auto"
        assert stats["batch_size"] == 50
        assert "last_warm_up_time" in stats
        assert "total_keys_warmed" in stats
        assert "hot_keys_count" in stats
        assert "background_tasks_count" in stats

    @pytest.mark.asyncio
    async def test_close_warmup(self) -> None:
        """测试关闭预热器"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        # 启动后台任务
        await warmer.start_background_warming(lambda: {}, interval=1.0)

        # 关闭应该停止任务
        await warmer.close()

        assert len(warmer._warming_tasks) == 0


class TestCacheWarmerFactory:
    """测试工厂模式"""

    def test_create_warmer_manual(self) -> None:
        """测试创建手动预热器"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = create_warmer(cache, strategy="manual")

        assert isinstance(warmer, CacheWarmer)
        assert warmer.strategy == "manual"

    def test_create_warmer_smart(self) -> None:
        """测试创建智能预热器"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = create_warmer(cache, strategy="smart")

        assert isinstance(warmer, SmartCacheWarmer)
        assert warmer.strategy == "smart"

    def test_create_warmer_invalid_strategy(self) -> None:
        """测试创建无效策略预热器"""
        cache = CacheManager(backend=MemoryBackend())
        # 默认应该返回 CacheWarmer
        warmer = create_warmer(cache, strategy="invalid")

        assert isinstance(warmer, CacheWarmer)


class TestCacheWarmerPerformance:
    """测试性能相关功能"""

    @pytest.mark.asyncio
    async def test_warm_up_performance(self) -> None:
        """测试预热性能"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, batch_size=100)

        # 创建大量数据
        large_data = {f"perf_key_{i}": f"perf_value_{i}" for i in range(1000)}

        start_time = time.time()
        await warmer.warm_up(large_data)
        elapsed = time.time() - start_time

        # 验证性能（应该在合理时间内完成）
        assert elapsed < 5.0  # 5秒内完成1000个键的预热

        # 验证所有数据都已预热
        assert len(cache) == 1000

    @pytest.mark.asyncio
    async def test_incremental_warm_up_performance(self) -> None:
        """测试增量预热性能"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache, batch_size=50)

        hot_keys = [f"hot_key_{i}" for i in range(500)]

        def data_loader(keys):
            return {key: f"hot_data_{key}" for key in keys}

        start_time = time.time()
        await warmer.incremental_warm_up(hot_keys, data_loader)
        elapsed = time.time() - start_time

        # 验证性能
        assert elapsed < 3.0
        assert len(cache) == 500


class TestCacheWarmerEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_warm_up_with_none_values(self) -> None:
        """测试预热包含 None 值的数据"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        data = {"key1": None, "key2": "value2"}

        # 应该不抛出异常
        await warmer.warm_up(data)

        assert cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_warm_up_with_complex_objects(self) -> None:
        """测试预热复杂对象"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        complex_data = {
            "user:1": {"id": 1, "name": "Alice", "tags": ["admin", "user"]},
            "product:101": {"id": 101, "price": 99.99, "in_stock": True},
        }

        await warmer.warm_up(complex_data)

        user = cache.get("user:1")
        assert user["id"] == 1
        assert user["name"] == "Alice"
        assert user["tags"] == ["admin", "user"]

    @pytest.mark.asyncio
    async def test_concurrent_warm_up(self) -> None:
        """测试并发预热"""
        cache = CacheManager(backend=MemoryBackend())
        warmer = CacheWarmer(cache)

        data1 = {f"concurrent_key_{i}": f"value_{i}" for i in range(100)}
        data2 = {f"concurrent_key_{i + 100}": f"value_{i + 100}" for i in range(100)}

        # 并发执行预热
        await asyncio.gather(warmer.warm_up(data1), warmer.warm_up(data2))

        # 验证所有数据都已预热
        assert len(cache) == 200
