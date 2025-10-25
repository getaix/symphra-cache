"""
Prometheus 监控导出模块

提供 Prometheus 指标导出功能，支持标准的 Prometheus 指标格式。
可以与 Prometheus 服务器集成，实现缓存性能的可视化监控。

特性：
- 标准 Prometheus 指标格式
- 自动指标发现
- 支持 Gauge、Counter、Histogram
- 可配置的指标标签
- 与 Prometheus Pushgateway 集成

使用示例：
    >>> from symphra_cache.monitoring.prometheus import PrometheusExporter
    >>> exporter = PrometheusExporter(monitor)
    >>> metrics_text = exporter.generate_metrics()
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .base import CacheMonitor


class PrometheusExporter:
    """
    Prometheus 指标导出器

    将缓存监控指标转换为 Prometheus 格式。

    支持的指标类型：
    - Counter: 累积计数器（操作次数）
    - Gauge: 瞬时值（缓存大小、命中率）
    - Histogram: 分布统计（延迟分布）

    使用示例：
        >>> exporter = PrometheusExporter(monitor)
        >>> metrics_text = exporter.generate_metrics()
    """

    def __init__(
        self,
        monitor: CacheMonitor,
        namespace: str = "symphra_cache",
        subsystem: str = "cache",
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        初始化 Prometheus 导出器

        Args:
            monitor: 缓存监控器
            namespace: 指标命名空间
            subsystem: 子系统名称
            labels: 全局标签
        """
        self.monitor = monitor
        self.namespace = namespace
        self.subsystem = subsystem
        self.labels = labels or {}
        self._start_time = time.time()

    def _format_labels(self, extra_labels: dict[str, str] | None = None) -> str:
        """
        格式化标签

        Args:
            extra_labels: 额外标签

        Returns:
            格式化的标签字符串
        """
        all_labels = self.labels.copy()
        if extra_labels:
            all_labels.update(extra_labels)

        if not all_labels:
            return ""

        label_strs = []
        for key, value in all_labels.items():
            # 转义特殊字符
            escaped_value = str(value).replace('"', '\\"').replace("\n", "\\n")
            label_strs.append(f'{key}="{escaped_value}"')

        return "{" + ",".join(label_strs) + "}"

    def _generate_counter_metrics(self) -> str:
        """
        生成 Counter 指标

        Returns:
            Counter 指标文本
        """
        metrics = self.monitor.metrics
        lines = []

        # 操作计数器
        lines.append(f"# HELP {self._metric_name('operations_total')} Total cache operations")
        lines.append(f"# TYPE {self._metric_name('operations_total')} counter")

        operations = [
            ("get", metrics.get_count),
            ("set", metrics.set_count),
            ("delete", metrics.delete_count),
            ("hit", metrics.hit_count),
            ("miss", metrics.miss_count),
        ]

        for operation, count in operations:
            if count > 0:
                labels = self._format_labels({"operation": operation})
                lines.append(f"{self._metric_name('operations_total')}{labels} {count}")

        return "\n".join(lines)

    def _generate_gauge_metrics(self) -> str:
        """
        生成 Gauge 指标

        Returns:
            Gauge 指标文本
        """
        metrics = self.monitor.metrics
        lines = []

        # 缓存大小
        lines.append(f"# HELP {self._metric_name('size')} Current cache size")
        lines.append(f"# TYPE {self._metric_name('size')} gauge")
        try:
            cache_size = len(self.monitor.cache)
            lines.append(f"{self._metric_name('size')}{self._format_labels()} {cache_size}")
        except Exception:
            lines.append(f"{self._metric_name('size')}{self._format_labels()} 0")

        # 命中率
        lines.append(f"# HELP {self._metric_name('hit_rate')} Cache hit rate")
        lines.append(f"# TYPE {self._metric_name('hit_rate')} gauge")
        hit_rate = metrics.get_hit_rate()
        lines.append(f"{self._metric_name('hit_rate')}{self._format_labels()} {hit_rate}")

        # 运行时间
        lines.append(f"# HELP {self._metric_name('uptime_seconds')} Cache uptime in seconds")
        lines.append(f"# TYPE {self._metric_name('uptime_seconds')} gauge")
        uptime = time.time() - self._start_time
        lines.append(f"{self._metric_name('uptime_seconds')}{self._format_labels()} {uptime}")

        return "\n".join(lines)

    def _generate_histogram_metrics(self) -> str:
        """
        生成 Histogram 指标

        Returns:
            Histogram 指标文本
        """
        metrics = self.monitor.metrics
        lines = []

        # GET 操作延迟分布
        lines.append(
            f"# HELP {self._metric_name('get_duration_seconds')} Time spent on GET operations"
        )
        lines.append(f"# TYPE {self._metric_name('get_duration_seconds')} histogram")

        # Prometheus histogram buckets (秒)
        buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

        get_count = metrics.get_count
        if get_count > 0:
            avg_latency = metrics.get_average_latency("get") / 1000  # 转换为秒

            # 生成 bucket 计数（简化实现）
            for bucket in buckets:
                # 假设正态分布，计算 bucket 内的请求数
                bucket_count = int(
                    get_count * self._normal_cdf(bucket, avg_latency, avg_latency * 0.5)
                )
                labels = self._format_labels({"le": str(bucket)})
                lines.append(
                    f"{self._metric_name('get_duration_seconds')}_bucket{labels} {bucket_count}"
                )

            # 总计数和总和
            lines.append(
                f"{self._metric_name('get_duration_seconds')}_count{self._format_labels()} {get_count}"
            )
            lines.append(
                f"{self._metric_name('get_duration_seconds')}_sum{self._format_labels()} {avg_latency * get_count}"
            )

        # SET 操作延迟分布
        lines.append(
            f"# HELP {self._metric_name('set_duration_seconds')} Time spent on SET operations"
        )
        lines.append(f"# TYPE {self._metric_name('set_duration_seconds')} histogram")

        set_count = metrics.set_count
        if set_count > 0:
            avg_latency = metrics.get_average_latency("set") / 1000

            for bucket in buckets:
                bucket_count = int(
                    set_count * self._normal_cdf(bucket, avg_latency, avg_latency * 0.5)
                )
                labels = self._format_labels({"le": str(bucket)})
                lines.append(
                    f"{self._metric_name('set_duration_seconds')}_bucket{labels} {bucket_count}"
                )

            lines.append(
                f"{self._metric_name('set_duration_seconds')}_count{self._format_labels()} {set_count}"
            )
            lines.append(
                f"{self._metric_name('set_duration_seconds')}_sum{self._format_labels()} {avg_latency * set_count}"
            )

        return "\n".join(lines)

    def _normal_cdf(self, x: float, mean: float, std: float) -> float:
        """
        正态分布累积分布函数（简化实现）

        Args:
            x: 输入值
            mean: 均值
            std: 标准差

        Returns:
            CDF 值
        """
        import math

        return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))

    def _metric_name(self, name: str) -> str:
        """
        生成完整的指标名称

        Args:
            name: 指标名称

        Returns:
            完整的指标名称
        """
        parts = []
        if self.namespace:
            parts.append(self.namespace)
        if self.subsystem:
            parts.append(self.subsystem)
        parts.append(name)
        return "_".join(parts)

    def generate_metrics(self) -> str:
        """
        生成 Prometheus 格式的指标文本

        Returns:
            Prometheus 指标文本
        """
        if not self.monitor.is_enabled():
            return "# Cache monitoring is disabled"

        lines = []

        # 添加元信息
        lines.append(f"# Symphra Cache Metrics - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("# Generated by PrometheusExporter")
        lines.append("")

        # 生成不同类型的指标
        lines.append(self._generate_counter_metrics())
        lines.append("")
        lines.append(self._generate_gauge_metrics())
        lines.append("")
        lines.append(self._generate_histogram_metrics())

        return "\n".join(lines)

    def get_metrics_handler(self) -> Callable[[], str]:
        """
        获取指标处理器函数

        Returns:
            返回指标文本的函数
        """
        return self.generate_metrics

    def create_pushgateway_client(
        self,
        gateway_url: str,
        job_name: str,
        instance: str = "",
    ) -> PrometheusPushgatewayClient:
        """
        创建 Pushgateway 客户端

        Args:
            gateway_url: Pushgateway URL
            job_name: 作业名称
            instance: 实例标识符

        Returns:
            Pushgateway 客户端
        """
        return PrometheusPushgatewayClient(
            exporter=self,
            gateway_url=gateway_url,
            job_name=job_name,
            instance=instance or self._get_default_instance(),
        )

    def _get_default_instance(self) -> str:
        """
        获取默认实例标识符

        Returns:
            实例标识符
        """
        import os
        import socket

        hostname = socket.gethostname()
        pid = os.getpid()
        return f"{hostname}:{pid}"

    def update_labels(self, labels: dict[str, str]) -> None:
        """
        更新全局标签

        Args:
            labels: 新的标签字典
        """
        self.labels.update(labels)


class PrometheusPushgatewayClient:
    """
    Prometheus Pushgateway 客户端

    将指标推送到 Prometheus Pushgateway。
    """

    def __init__(
        self,
        exporter: PrometheusExporter,
        gateway_url: str,
        job_name: str,
        instance: str = "",
    ) -> None:
        """
        初始化 Pushgateway 客户端

        Args:
            exporter: Prometheus 导出器
            gateway_url: Pushgateway URL
            job_name: 作业名称
            instance: 实例标识符
        """
        self.exporter = exporter
        self.gateway_url = gateway_url.rstrip("/")
        self.job_name = job_name
        self.instance = instance or self.exporter._get_default_instance()

    async def push_metrics(self) -> bool:
        """
        推送指标到 Pushgateway

        Returns:
            推送是否成功
        """
        try:
            import aiohttp

            metrics_text = self.exporter.generate_metrics()

            # 构建 Pushgateway URL
            url = f"{self.gateway_url}/metrics/job/{self.job_name}/instance/{self.instance}"

            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url,
                    data=metrics_text,
                    headers={
                        "Content-Type": "text/plain",
                    },
                ) as response,
            ):
                return response.status == 200

        except Exception:
            return False

    def get_push_url(self) -> str:
        """
        获取推送 URL

        Returns:
            完整的推送 URL
        """
        return f"{self.gateway_url}/metrics/job/{self.job_name}/instance/{self.instance}"
