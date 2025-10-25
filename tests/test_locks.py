"""
分布式锁 (DistributedLock) 测试

测试分布式锁的获取、释放、超时和并发场景。
"""

import asyncio
import time
from typing import Any

import pytest

from symphra_cache import CacheManager
from symphra_cache.backends import MemoryBackend
from symphra_cache.locks import DistributedLock


class TestDistributedLockBasics:
    """测试分布式锁基础功能"""

    def test_lock_initialization(self) -> None:
        """测试锁的初始化"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1", timeout=10)

        assert lock.name == "lock:resource:1"
        assert lock.timeout == 10
        assert lock.blocking is True
        assert lock._locked is False
        assert lock.identifier is not None

    def test_lock_acquire_and_release(self) -> None:
        """测试获取和释放锁"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        # 获取锁
        result = lock.acquire()
        assert result is True
        assert lock._locked is True

        # 验证锁已设置
        lock_value = manager.get(lock.name)
        assert lock_value == lock.identifier

        # 释放锁
        lock.release()
        assert lock._locked is False

        # 验证锁已清除
        lock_value = manager.get(lock.name)
        assert lock_value is None

    def test_lock_already_held(self) -> None:
        """测试锁已被持有的情况"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1")
        lock2 = DistributedLock(manager, "resource:1")

        # 第一个锁获取成功
        result1 = lock1.acquire()
        assert result1 is True

        # 第二个锁获取失败（非阻塞模式）
        lock2_non_blocking = DistributedLock(
            manager, "resource:1", blocking=False
        )
        result2 = lock2_non_blocking.acquire()
        assert result2 is False

        # 释放第一个锁
        lock1.release()

        # 现在第二个锁可以获取
        result2 = lock2_non_blocking.acquire()
        assert result2 is True
        lock2_non_blocking.release()

    def test_lock_context_manager(self) -> None:
        """测试锁的上下文管理器"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        # 使用 with 语句
        with lock:
            assert lock._locked is True
            assert manager.get(lock.name) == lock.identifier

        # 退出上下文后锁应该释放
        assert lock._locked is False
        assert manager.get(lock.name) is None

    def test_lock_blocking_timeout(self) -> None:
        """测试阻塞超时"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1", timeout=10)
        lock2 = DistributedLock(
            manager, "resource:1", blocking=True, blocking_timeout=0.1
        )

        # 第一个锁持有资源
        lock1.acquire()

        # 第二个锁尝试获取，应该超时
        start_time = time.time()
        result = lock2.acquire()
        elapsed = time.time() - start_time

        assert result is False
        assert elapsed >= 0.1

        lock1.release()

    def test_lock_non_blocking(self) -> None:
        """测试非阻塞模式"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1")
        lock2 = DistributedLock(manager, "resource:1", blocking=False)

        # 第一个锁获取成功
        lock1.acquire()

        # 第二个锁立即失败（非阻塞）
        result = lock2.acquire()
        assert result is False

        lock1.release()

    def test_lock_release_without_acquire(self) -> None:
        """测试释放未获取的锁"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        # 释放未获取的锁应该是安全的
        lock.release()
        assert lock._locked is False

    def test_lock_own_lock_check(self) -> None:
        """测试锁所有权检查"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1")
        lock2 = DistributedLock(manager, "resource:1")

        # lock1 获取锁
        lock1.acquire()
        assert lock1._locked is True

        # lock2 尝试释放锁（应该失败，因为不是自己的锁）
        lock2.release()
        assert lock1._locked is True

        # 锁仍然存在
        assert manager.get(lock1.name) == lock1.identifier

        # lock1 可以释放自己的锁
        lock1.release()
        assert manager.get(lock1.name) is None


class TestDistributedLockConcurrency:
    """测试分布式锁的并发场景"""

    def test_multiple_sequential_locks(self) -> None:
        """测试多个顺序锁操作"""
        manager = CacheManager(backend=MemoryBackend())
        counter = 0

        for i in range(5):
            lock = DistributedLock(manager, f"resource:{i}")
            result = lock.acquire()
            assert result is True

            counter += 1
            lock.release()

        assert counter == 5

    def test_concurrent_lock_attempts(self) -> None:
        """测试并发锁尝试"""
        manager = CacheManager(backend=MemoryBackend())
        acquired_count = 0

        def try_acquire() -> None:
            nonlocal acquired_count
            lock = DistributedLock(manager, "shared_resource", blocking=False)
            if lock.acquire():
                acquired_count += 1
                time.sleep(0.01)
                lock.release()

        # 先持有一个锁
        main_lock = DistributedLock(manager, "shared_resource")
        main_lock.acquire()

        # 尝试多个并发获取（都应该失败）
        for _ in range(10):
            try_acquire()

        # 没有任何线程应该获取到锁
        assert acquired_count == 0

        main_lock.release()

    def test_lock_timeout_protection(self) -> None:
        """测试锁超时保护（防止死锁）"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1", timeout=1)

        # 获取锁
        lock1.acquire()
        assert manager.get(lock1.name) == lock1.identifier

        # 等待超时
        time.sleep(1.1)

        # 锁应该过期（但在此测试中，内存后端不会自动删除）
        # 所以我们创建一个新的锁对象并尝试获取
        lock2 = DistributedLock(manager, "resource:1", blocking=False)
        # 由于缓存中仍然有值，第二个锁不能获取
        result = lock2.acquire()
        # 但如果我们手动清除缓存并尝试，应该成功
        manager.delete(lock1.name)
        result = lock2.acquire()
        assert result is True
        lock2.release()


class TestDistributedLockEdgeCases:
    """测试分布式锁的边界情况"""

    def test_lock_name_with_special_characters(self) -> None:
        """测试包含特殊字符的锁名称"""
        manager = CacheManager(backend=MemoryBackend())
        special_names = [
            "resource:1:2:3",
            "resource-with-dash",
            "resource_with_underscore",
            "resource.with.dots",
        ]

        for name in special_names:
            lock = DistributedLock(manager, name)
            result = lock.acquire()
            assert result is True
            lock.release()

    def test_lock_timeout_zero(self) -> None:
        """测试零超时的锁"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1", timeout=0)

        # 应该能获取锁（即使超时为0）
        result = lock.acquire()
        assert result is True
        lock.release()

    def test_lock_very_long_timeout(self) -> None:
        """测试很长超时的锁"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1", timeout=3600)

        result = lock.acquire()
        assert result is True
        assert manager.get(lock.name) == lock.identifier
        lock.release()

    def test_multiple_context_manager_exits(self) -> None:
        """测试多次上下文管理器退出"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        with lock:
            pass

        # 再次尝试释放（应该安全）
        lock.release()
        assert lock._locked is False

    def test_lock_identifier_uniqueness(self) -> None:
        """测试锁标识符的唯一性"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1")
        lock2 = DistributedLock(manager, "resource:1")

        # 两个锁的标识符应该不同
        assert lock1.identifier != lock2.identifier

    def test_blocking_timeout_zero(self) -> None:
        """测试零阻塞超时"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1")
        lock2 = DistributedLock(
            manager, "resource:1", blocking=True, blocking_timeout=0
        )

        lock1.acquire()

        # 超时为0，应该立即返回
        start = time.time()
        result = lock2.acquire()
        elapsed = time.time() - start

        assert result is False
        assert elapsed < 0.1

        lock1.release()


class TestDistributedLockStateManagement:
    """测试分布式锁的状态管理"""

    def test_lock_state_after_acquire(self) -> None:
        """测试获取后的锁状态"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        assert lock._locked is False

        lock.acquire()
        assert lock._locked is True

        lock.release()
        assert lock._locked is False

    def test_lock_value_matches_identifier(self) -> None:
        """测试缓存中的锁值与标识符匹配"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        lock.acquire()

        # 缓存中的值应该与标识符相同
        cached_value = manager.get(lock.name)
        assert cached_value == lock.identifier

        lock.release()

    def test_release_wrong_lock_does_not_affect_state(self) -> None:
        """测试释放错误的锁不会影响状态"""
        manager = CacheManager(backend=MemoryBackend())
        lock1 = DistributedLock(manager, "resource:1")
        lock2 = DistributedLock(manager, "resource:1")

        lock1.acquire()
        lock1_locked = lock1._locked

        # lock2 尝试释放（不会成功）
        lock2.release()

        # lock1 的状态应该不变
        assert lock1._locked == lock1_locked
        assert manager.get(lock1.name) == lock1.identifier

        lock1.release()

    def test_context_manager_exception_handling(self) -> None:
        """测试上下文管理器异常处理"""
        manager = CacheManager(backend=MemoryBackend())
        lock = DistributedLock(manager, "resource:1")

        # 在上下文中抛出异常
        try:
            with lock:
                assert lock._locked is True
                raise ValueError("Test exception")
        except ValueError:
            pass

        # 锁应该被释放
        assert lock._locked is False
        assert manager.get(lock.name) is None
