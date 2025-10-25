"""
文件后端单元测试

测试 FileBackend 的所有功能：
- 基础 CRUD 操作
- TTL 过期验证
- 持久化验证
- 异步操作
- LRU 淘汰
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from symphra_cache.backends.file import FileBackend
from symphra_cache.types import SerializationMode


class TestFileBackendBasics:
    """测试基础功能"""

    def test_set_and_get(self) -> None:
        """测试基础 set/get 操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            backend.set("key1", "value1")
            assert backend.get("key1") == "value1"

            # 不存在的键返回 None
            assert backend.get("nonexistent") is None

    def test_persistence(self) -> None:
        """测试持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cache.db"

            # 第一个实例：写入数据
            backend1 = FileBackend(db_path=db_path)
            backend1.set("persistent_key", "persistent_value")
            del backend1

            # 第二个实例：读取数据
            backend2 = FileBackend(db_path=db_path)
            assert backend2.get("persistent_key") == "persistent_value"

    def test_different_types(self) -> None:
        """测试不同类型的值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            # 字符串
            backend.set("str", "hello")
            assert backend.get("str") == "hello"

            # 数字
            backend.set("int", 123)
            assert backend.get("int") == 123

            # 字典
            backend.set("dict", {"name": "Alice", "age": 30})
            assert backend.get("dict") == {"name": "Alice", "age": 30}

            # 列表
            backend.set("list", [1, 2, 3])
            assert backend.get("list") == [1, 2, 3]

    def test_delete(self) -> None:
        """测试删除操作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            backend.set("key", "value")
            assert backend.delete("key") is True
            assert backend.get("key") is None

            # 删除不存在的键返回 False
            assert backend.delete("nonexistent") is False

    def test_exists(self) -> None:
        """测试 exists 方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            assert backend.exists("key") is False

            backend.set("key", "value")
            assert backend.exists("key") is True

            backend.delete("key")
            assert backend.exists("key") is False

    def test_clear(self) -> None:
        """测试清空所有缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            backend.set("key1", "value1")
            backend.set("key2", "value2")
            backend.set("key3", "value3")

            backend.clear()

            assert backend.get("key1") is None
            assert backend.get("key2") is None
            assert backend.get("key3") is None


class TestFileBackendTTL:
    """测试 TTL 过期功能"""

    def test_ttl_expiration(self) -> None:
        """测试 TTL 过期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            backend.set("key", "value", ttl=1)
            assert backend.get("key") == "value"

            time.sleep(1.1)
            assert backend.get("key") is None

    def test_no_ttl(self) -> None:
        """测试无 TTL（永不过期）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            backend.set("key", "value")
            time.sleep(0.5)
            assert backend.get("key") == "value"


class TestFileBackendAsync:
    """测试异步操作"""

    @pytest.mark.asyncio
    async def test_async_get_set(self) -> None:
        """测试异步 get/set"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            await backend.aset("key", "value")
            assert await backend.aget("key") == "value"

    @pytest.mark.asyncio
    async def test_async_delete(self) -> None:
        """测试异步删除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            await backend.aset("key", "value")
            assert await backend.adelete("key") is True
            assert await backend.aget("key") is None

    @pytest.mark.asyncio
    async def test_async_with_ttl(self) -> None:
        """测试异步操作的 TTL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            await backend.aset("key", "value", ttl=1)
            assert await backend.aget("key") == "value"

            await asyncio.sleep(1.1)
            assert await backend.aget("key") is None


class TestFileBackendSerialization:
    """测试序列化模式"""

    def test_json_serialization(self) -> None:
        """测试 JSON 序列化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(
                db_path=Path(tmpdir) / "cache.db",
                serialization_mode=SerializationMode.JSON,
            )

            data = {"name": "Alice", "items": [1, 2, 3]}
            backend.set("key", data)
            assert backend.get("key") == data

    def test_pickle_serialization(self) -> None:
        """测试 Pickle 序列化（默认）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(
                db_path=Path(tmpdir) / "cache.db",
                serialization_mode=SerializationMode.PICKLE,
            )

            import datetime

            data = {"time": datetime.datetime(2024, 1, 1), "count": 123}
            backend.set("key", data)
            result = backend.get("key")

            assert result["count"] == 123
            assert isinstance(result["time"], datetime.datetime)


class TestFileBackendLRU:
    """测试 LRU 淘汰"""

    def test_lru_eviction(self) -> None:
        """测试 LRU 淘汰"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(
                db_path=Path(tmpdir) / "cache.db",
                max_size=3,
            )

            backend.set("key1", "value1")
            backend.set("key2", "value2")
            backend.set("key3", "value3")

            # 添加第 4 个键，应淘汰 key1
            backend.set("key4", "value4")

            assert backend.get("key1") is None
            assert backend.get("key2") == "value2"
            assert backend.get("key3") == "value3"
            assert backend.get("key4") == "value4"


class TestFileBackendEdgeCases:
    """测试边界条件"""

    def test_len_method(self) -> None:
        """测试 len() 方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileBackend(db_path=Path(tmpdir) / "cache.db")

            assert len(backend) == 0

            backend.set("key1", "value1")
            assert len(backend) == 1

            backend.set("key2", "value2")
            assert len(backend) == 2

            backend.delete("key1")
            assert len(backend) == 1

    def test_repr_method(self) -> None:
        """测试 repr() 方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cache.db"
            backend = FileBackend(db_path=db_path, max_size=100)

            backend.set("key1", "value1")

            repr_str = repr(backend)
            assert "FileBackend" in repr_str
            assert str(db_path) in repr_str
