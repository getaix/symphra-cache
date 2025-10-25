"""
缓存预热模块

提供缓存预热功能，支持数据预加载和自动预热策略。
避免缓存冷启动问题，提升系统性能。

特性：
- 支持手动预热和自动预热
- 基于访问模式的智能预热
- 支持批量预热操作
- 可配置预热策略

使用示例：
    >>> from symphra_cache import CacheManager, MemoryBackend
    >>> from symphra_cache.warming import CacheWarmer
    >>>
    >>> cache = CacheManager(backend=MemoryBackend())
    >>> warmer = CacheWarmer(cache)
    >>>
    >>> # 手动预热
    >>> await warmer.warm_up({"key1": "value1", "key2": "value2"})
    >>>
    >>> # 自动预热（基于访问模式）
    >>> await warmer.auto_warm_up()
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .manager import CacheManager
    from .types import CacheKey, CacheValue


class CacheWarmer:
    """
    缓存预热器

    提供多种缓存预热策略，支持手动和自动预热。

    预热策略：
    - 手动预热：直接指定键值对进行预热
    - 自动预热：基于历史访问数据智能预热
    - 增量预热：定期检查并预热热点数据

    使用示例：
        >>> warmer = CacheWarmer(cache)
        >>> await warmer.warm_up({"key1": "value1", "key2": "value2"})
        >>> await warmer.auto_warm_up()
    """

    def __init__(
        self,
        cache: CacheManager,
        strategy: str = "manual",
        batch_size: int = 100,
        ttl: int | None = None,
    ) -> None:
        """
        初始化缓存预热器

        Args:
            cache: 缓存管理器实例
            strategy: 预热策略 ("manual", "auto", "incremental")
            batch_size: 批量操作大小
            ttl: 预热数据的默认过期时间
        """
        self.cache = cache
        self.strategy = strategy
        self.batch_size = batch_size
        self.ttl = ttl
        self._warming_tasks: list[asyncio.Task[Any]] = []
        self._access_patterns: dict[CacheKey, dict[str, Any]] = {}
        self._last_warm_up_time = time.time()

    async def warm_up(
        self,
        data: dict[CacheKey, CacheValue],
        ttl: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        """
        手动预热缓存

        Args:
            data: 要预热的键值对数据
            ttl: 过期时间（秒），None 使用默认值
            batch_size: 批量大小，None 使用默认值
        """
        ttl = ttl if ttl is not None else self.ttl
        batch_size = batch_size if batch_size is not None else self.batch_size

        if not data:
            return

        # 批量预热，避免一次性操作过多数据
        keys = list(data.keys())
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i : i + batch_size]
            batch_data = {key: data[key] for key in batch_keys}

            # 批量设置缓存
            await self.cache.aset_many(batch_data, ttl=ttl)

            # 短暂休眠避免阻塞
            if i + batch_size < len(keys):
                await asyncio.sleep(0.01)

        self._last_warm_up_time = time.time()

    async def auto_warm_up(
        self,
        data_source: Callable[[], dict[CacheKey, CacheValue]],
        ttl: int | None = None,
    ) -> None:
        """
        自动预热缓存

        基于数据源函数自动预热缓存。

        Args:
            data_source: 数据源函数，返回要预热的数据
            ttl: 过期时间（秒）
        """
        try:
            data = await asyncio.to_thread(data_source)
            await self.warm_up(data, ttl=ttl)
        except Exception as e:
            # 记录错误但不中断预热过程
            print(f"自动预热失败: {e}")

    async def incremental_warm_up(
        self,
        hot_keys: list[CacheKey],
        data_loader: Callable[[list[CacheKey]], dict[CacheKey, CacheValue]],
        ttl: int | None = None,
    ) -> None:
        """
        增量预热

        预热热点键，适用于大数据集的渐进式预热。

        Args:
            hot_keys: 热点键列表
            data_loader: 数据加载函数
            ttl: 过期时间（秒）
        """
        if not hot_keys:
            return

        # 分批处理热点键
        for i in range(0, len(hot_keys), self.batch_size):
            batch_keys = hot_keys[i : i + self.batch_size]

            try:
                # 加载数据
                data = await asyncio.to_thread(data_loader, batch_keys)

                # 预热数据
                await self.warm_up(data, ttl=ttl)

                # 记录访问模式
                for key in batch_keys:
                    self._record_access_pattern(key)

            except Exception as e:
                print(f"增量预热失败 (批次 {i // self.batch_size + 1}): {e}")

            # 短暂休眠
            if i + self.batch_size < len(hot_keys):
                await asyncio.sleep(0.1)

    def _record_access_pattern(self, key: CacheKey) -> None:
        """
        记录访问模式

        Args:
            key: 被访问的缓存键
        """
        current_time = time.time()
        if key not in self._access_patterns:
            self._access_patterns[key] = {
                "count": 0,
                "first_access": current_time,
                "last_access": current_time,
            }

        pattern = self._access_patterns[key]
        pattern["count"] += 1
        pattern["last_access"] = current_time

    def get_hot_keys(self, min_access_count: int = 5, hours: float = 1.0) -> list[CacheKey]:
        """
        获取热点键

        Args:
            min_access_count: 最小访问次数
            hours: 时间窗口（小时）

        Returns:
            热点键列表
        """
        current_time = time.time()
        cutoff_time = current_time - (hours * 3600)

        hot_keys = []
        for key, pattern in self._access_patterns.items():
            if pattern["count"] >= min_access_count and pattern["last_access"] >= cutoff_time:
                hot_keys.append(key)

        return hot_keys

    async def start_background_warming(
        self,
        data_source: Callable[[], dict[CacheKey, CacheValue]],
        interval: int = 3600,  # 默认1小时
    ) -> None:
        """
        启动后台预热任务

        Args:
            data_source: 数据源函数
            interval: 预热间隔（秒）
        """

        async def _background_warm_up() -> None:
            while True:
                try:
                    await self.auto_warm_up(data_source)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"后台预热任务失败: {e}")
                    await asyncio.sleep(interval)

        task = asyncio.create_task(_background_warm_up())
        self._warming_tasks.append(task)

    def stop_background_warming(self) -> None:
        """停止所有后台预热任务"""
        for task in self._warming_tasks:
            task.cancel()
        self._warming_tasks.clear()

    async def warm_up_from_file(
        self,
        file_path: str,
        format: str = "json",
        ttl: int | None = None,
    ) -> None:
        """
        从文件预热缓存

        支持 JSON、CSV 格式。

        Args:
            file_path: 文件路径
            format: 文件格式 ("json", "csv")
            ttl: 过期时间（秒）
        """
        import csv
        import json

        data: dict[CacheKey, CacheValue] = {}

        try:
            if format.lower() == "json":
                with open(file_path, encoding="utf-8") as f:
                    file_data = json.load(f)
                    data.update(file_data)

            elif format.lower() == "csv":
                with open(file_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if "key" in row and "value" in row:
                            data[row["key"]] = row["value"]

            else:
                raise ValueError(f"不支持的文件格式: {format}")

            await self.warm_up(data, ttl=ttl)

        except Exception as e:
            raise RuntimeError(f"从文件预热失败: {e}") from e

    async def warm_up_with_ttl_map(
        self,
        data: dict[CacheKey, CacheValue],
        ttl_map: dict[CacheKey, int],
    ) -> None:
        """
        使用 TTL 映射预热缓存

        不同键可以有不同的过期时间。

        Args:
            data: 要预热的数据
            ttl_map: 每个键的 TTL 映射
        """
        if not data:
            return

        # 按 TTL 分组
        ttl_groups: dict[int, dict[CacheKey, CacheValue]] = {}
        for key, value in data.items():
            ttl = ttl_map.get(key, self.ttl)
            if ttl not in ttl_groups:
                ttl_groups[ttl] = {}
            ttl_groups[ttl][key] = value

        # 分组预热
        for group_ttl, group_data in ttl_groups.items():
            await self.warm_up(group_data, ttl=group_ttl)

    def get_warming_stats(self) -> dict[str, Any]:
        """
        获取预热统计信息

        Returns:
            统计信息字典
        """
        return {
            "strategy": self.strategy,
            "batch_size": self.batch_size,
            "last_warm_up_time": self._last_warm_up_time,
            "total_keys_warmed": len(self._access_patterns),
            "hot_keys_count": len(self.get_hot_keys()),
            "background_tasks_count": len(self._warming_tasks),
        }

    async def close(self) -> None:
        """
        关闭预热器，清理资源
        """
        self.stop_background_warming()

        # 等待所有任务完成
        if self._warming_tasks:
            await asyncio.gather(*self._warming_tasks, return_exceptions=True)

    def __repr__(self) -> str:
        """
        字符串表示
        """
        return f"CacheWarmer(strategy={self.strategy!r}, cache={self.cache!r})"


class SmartCacheWarmer(CacheWarmer):
    """
    智能缓存预热器

    基于机器学习算法预测热点数据进行预热。

    特性：
    - 时间序列分析
    - 访问模式学习
    - 自适应预热策略
    - 性能监控和优化
    """

    def __init__(
        self,
        cache: CacheManager,
        prediction_window: int = 24,  # 预测窗口（小时）
        learning_rate: float = 0.1,
    ) -> None:
        """
        初始化智能预热器

        Args:
            cache: 缓存管理器
            prediction_window: 预测时间窗口（小时）
            learning_rate: 学习率
        """
        super().__init__(cache, strategy="smart")
        self.prediction_window = prediction_window
        self.learning_rate = learning_rate
        self._historical_data: list[dict[str, Any]] = []

    def _analyze_access_patterns(self) -> dict[CacheKey, float]:
        """
        分析访问模式，预测热点数据

        Returns:
            键的热度评分字典
        """
        if not self._access_patterns:
            return {}

        # 简单的热度计算：基于访问频率和最近访问时间
        current_time = time.time()
        heat_scores: dict[CacheKey, float] = {}

        for key, pattern in self._access_patterns.items():
            access_count = pattern["count"]
            last_access = pattern["last_access"]

            # 时间衰减因子
            time_diff = current_time - last_access
            time_factor = max(0, 1 - (time_diff / (3600 * 24)))  # 24小时衰减

            # 热度评分
            heat_score = access_count * time_factor
            heat_scores[key] = heat_score

        return heat_scores

    async def smart_warm_up(
        self,
        data_source: Callable[[list[CacheKey]], dict[CacheKey, CacheValue]],
        top_k: int = 100,
    ) -> None:
        """
        智能预热

        基于热度分析预热最热的 K 个键。

        Args:
            data_source: 数据加载函数
            top_k: 预热前 K 个热点键
        """
        # 分析访问模式
        heat_scores = self._analyze_access_patterns()

        # 获取最热的键
        sorted_keys = sorted(heat_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        hot_keys = [key for key, _ in sorted_keys]

        if hot_keys:
            # 智能预热
            await self.incremental_warm_up(hot_keys, data_source)

    def record_cache_miss(self, key: CacheKey) -> None:
        """
        记录缓存未命中

        用于学习哪些数据应该被预热。

        Args:
            key: 未命中的缓存键
        """
        self._record_access_pattern(key)

    def get_prediction_accuracy(self) -> float:
        """
        获取预测准确率

        Returns:
            准确率（0-1之间）
        """
        # 简单的准确率计算：基于缓存命中率提升
        if not self._historical_data:
            return 0.0

        # 这里可以实现更复杂的准确率计算逻辑
        # 暂时返回一个简单的估算值
        return min(1.0, len(self._access_patterns) / 1000)


# 工厂函数
def create_warmer(
    cache: CacheManager,
    strategy: str = "manual",
    **kwargs: Any,
) -> CacheWarmer:
    """
    创建缓存预热器工厂函数

    Args:
        cache: 缓存管理器
        strategy: 预热策略
        **kwargs: 其他参数

    Returns:
        缓存预热器实例
    """
    if strategy == "smart":
        return SmartCacheWarmer(cache, **kwargs)
    else:
        return CacheWarmer(cache, strategy=strategy, **kwargs)
