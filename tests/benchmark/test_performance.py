"""
性能基准测试

使用 pytest-benchmark 进行性能测试。
"""

import tempfile
from pathlib import Path

import pytest
from symphra_cache import CacheManager
from symphra_cache.backends import FileBackend, MemoryBackend


class TestMemoryBackendPerformance:
    """内存后端性能测试"""

    def test_set_performance(self, benchmark) -> None:
        """测试 set 操作性能"""
        cache = CacheManager(backend=MemoryBackend())

        def set_operation():
            cache.set("key", "value")

        result = benchmark(set_operation)
        assert result is None or result is True

    def test_get_performance(self, benchmark) -> None:
        """测试 get 操作性能"""
        cache = CacheManager(backend=MemoryBackend())
        cache.set("key", "value")

        def get_operation():
            return cache.get("key")

        result = benchmark(get_operation)
        assert result == "value"

    def test_batch_set_performance(self, benchmark) -> None:
        """测试批量 set 性能"""
        cache = CacheManager(backend=MemoryBackend())

        data = {f"key{i}": f"value{i}" for i in range(100)}

        def batch_set():
            cache.set_many(data)

        benchmark(batch_set)

    def test_batch_get_performance(self, benchmark) -> None:
        """测试批量 get 性能"""
        cache = CacheManager(backend=MemoryBackend())

        # 预设数据
        data = {f"key{i}": f"value{i}" for i in range(100)}
        cache.set_many(data)

        keys = list(data.keys())

        def batch_get():
            return cache.get_many(keys)

        result = benchmark(batch_get)
        assert len(result) == 100


class TestFileBackendPerformance:
    """文件后端性能测试"""

    def test_set_performance(self, benchmark) -> None:
        """测试 set 操作性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(backend=FileBackend(db_path=Path(tmpdir) / "cache.db"))

            def set_operation():
                cache.set("key", "value")

            benchmark(set_operation)

    def test_get_performance(self, benchmark) -> None:
        """测试 get 操作性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(backend=FileBackend(db_path=Path(tmpdir) / "cache.db"))
            cache.set("key", "value")

            def get_operation():
                return cache.get("key")

            result = benchmark(get_operation)
            assert result == "value"


class TestSerializationPerformance:
    """序列化性能测试"""

    def test_pickle_serialization(self, benchmark) -> None:
        """测试 Pickle 序列化性能"""
        from symphra_cache.serializers import PickleSerializer

        serializer = PickleSerializer()
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        def serialize():
            return serializer.serialize(data)

        benchmark(serialize)

    def test_json_serialization(self, benchmark) -> None:
        """测试 JSON 序列化性能"""
        from symphra_cache.serializers import JSONSerializer

        serializer = JSONSerializer()
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        def serialize():
            return serializer.serialize(data)

        benchmark(serialize)


@pytest.mark.parametrize("size", [10, 100, 1000])
class TestScalability:
    """可扩展性测试"""

    def test_memory_backend_scalability(self, benchmark, size) -> None:
        """测试内存后端可扩展性"""
        cache = CacheManager(backend=MemoryBackend(max_size=size * 2))

        data = {f"key{i}": f"value{i}" for i in range(size)}

        def operations():
            cache.set_many(data)
            cache.get_many(list(data.keys()))

        benchmark(operations)
