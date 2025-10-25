"""
StatsD 监控导出模块

提供 StatsD 指标导出功能，支持与 StatsD 服务器集成。
可以将缓存指标发送到 StatsD，进而存储到 Graphite、InfluxDB 等时序数据库。

特性：
- 支持 StatsD 协议（UDP/TCP）
- 多种指标类型（计数器、计时器、Gauge）
- 批量发送优化
- 错误处理和重试机制
- 与主流 APM 工具集成

使用示例：
    >>> from symphra_cache.monitoring.statsd import StatsDExporter
    >>> exporter = StatsDExporter(monitor, host="localhost", port=8125)
    >>> await exporter.send_metrics()
"""

from __future__ import annotations

import asyncio
import socket
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import CacheMonitor


class StatsDExporter:
    """
    StatsD 指标导出器

    将缓存监控指标转换为 StatsD 格式并通过 UDP 发送。

    支持的指标类型：
    - Counter: 计数器（操作次数）
    - Timer: 计时器（延迟）
    - Gauge: 瞬时值（缓存大小、命中率）

    使用示例：
        >>> exporter = StatsDExporter(monitor, host="localhost", port=8125)
        >>> await exporter.send_metrics()
    """

    def __init__(
        self,
        monitor: CacheMonitor,
        host: str = "localhost",
        port: int = 8125,
        prefix: str = "symphra.cache",
        sample_rate: float = 1.0,
        protocol: str = "udp",
        batch_size: int = 10,
    ) -> None:
        """
        初始化 StatsD 导出器

        Args:
            monitor: 缓存监控器
            host: StatsD 服务器主机
            port: StatsD 服务器端口
            prefix: 指标前缀
            sample_rate: 采样率 (0.0-1.0)
            protocol: 传输协议 ("udp", "tcp")
            batch_size: 批量发送大小
        """
        self.monitor = monitor
        self.host = host
        self.port = port
        self.prefix = prefix
        self.sample_rate = max(0.0, min(1.0, sample_rate))  # 确保在有效范围内
        self.protocol = protocol.lower()
        self.batch_size = batch_size
        self._socket: socket.socket | None = None
        self._tcp_writer: asyncio.StreamWriter | None = None
        self._tcp_reader: asyncio.StreamReader | None = None
        self._is_connected = False
        self._pending_metrics: list[str] = []
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """
        建立到 StatsD 服务器的连接
        """
        if self._is_connected:
            return

        try:
            if self.protocol == "udp":
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.setblocking(False)
            elif self.protocol == "tcp":
                reader, writer = await asyncio.open_connection(self.host, self.port)
                self._tcp_reader = reader
                self._tcp_writer = writer
            else:
                raise ValueError(f"不支持的协议: {self.protocol}")

            self._is_connected = True

        except Exception as e:
            print(f"连接 StatsD 服务器失败: {e}")
            self._is_connected = False

    async def disconnect(self) -> None:
        """
        断开连接
        """
        if self.protocol == "udp" and self._socket:
            self._socket.close()
        elif self.protocol == "tcp" and self._tcp_writer:
            self._tcp_writer.close()
            await self._tcp_writer.wait_closed()

        self._is_connected = False
        self._socket = None
        self._tcp_writer = None
        self._tcp_reader = None

    def _format_metric_name(self, name: str) -> str:
        """
        格式化指标名称

        Args:
            name: 原始指标名称

        Returns:
            格式化的指标名称
        """
        return f"{self.prefix}.{name}"

    def _generate_counter_metrics(self) -> list[str]:
        """
        生成计数器指标

        Returns:
            计数器指标列表
        """
        metrics = self.monitor.metrics
        metric_lines = []

        # 操作计数器
        operations = [
            ("get", metrics.get_count),
            ("set", metrics.set_count),
            ("delete", metrics.delete_count),
            ("hit", metrics.hit_count),
            ("miss", metrics.miss_count),
        ]

        for operation, count in operations:
            if count > 0:
                metric_name = self._format_metric_name(f"operations.{operation}")
                metric_lines.append(f"{metric_name}:{count}|c")

        return metric_lines

    def _generate_timer_metrics(self) -> list[str]:
        """
        生成计时器指标

        Returns:
            计时器指标列表
        """
        metrics = self.monitor.metrics
        metric_lines = []

        # GET 操作延迟
        if metrics.get_count > 0:
            avg_latency = metrics.get_average_latency("get")
            min_latency = metrics.get_latency_stats("get")["min"]
            max_latency = metrics.get_latency_stats("get")["max"]

            metric_lines.extend(
                [
                    f"{self._format_metric_name('get.latency.avg')}:{avg_latency:.3f}|ms",
                    f"{self._format_metric_name('get.latency.min')}:{min_latency:.3f}|ms",
                    f"{self._format_metric_name('get.latency.max')}:{max_latency:.3f}|ms",
                ]
            )

        # SET 操作延迟
        if metrics.set_count > 0:
            avg_latency = metrics.get_average_latency("set")
            min_latency = metrics.get_latency_stats("set")["min"]
            max_latency = metrics.get_latency_stats("set")["max"]

            metric_lines.extend(
                [
                    f"{self._format_metric_name('set.latency.avg')}:{avg_latency:.3f}|ms",
                    f"{self._format_metric_name('set.latency.min')}:{min_latency:.3f}|ms",
                    f"{self._format_metric_name('set.latency.max')}:{max_latency:.3f}|ms",
                ]
            )

        return metric_lines

    def _generate_gauge_metrics(self) -> list[str]:
        """
        生成 Gauge 指标

        Returns:
            Gauge 指标列表
        """
        metrics = self.monitor.metrics
        metric_lines = []

        # 缓存大小
        try:
            cache_size = len(self.monitor.cache)
            metric_lines.append(f"{self._format_metric_name('size')}:{cache_size}|g")
        except Exception:
            metric_lines.append(f"{self._format_metric_name('size')}:0|g")

        # 命中率
        hit_rate = metrics.get_hit_rate()
        metric_lines.append(f"{self._format_metric_name('hit_rate')}:{hit_rate:.3f}|g")

        # 总操作数
        total_ops = metrics.get_total_operations()
        metric_lines.append(f"{self._format_metric_name('operations.total')}:{total_ops}|g")

        return metric_lines

    async def _send_udp_metrics(self, metric_lines: list[str]) -> bool:
        """
        通过 UDP 发送指标

        Args:
            metric_lines: 指标行列表

        Returns:
            发送是否成功
        """
        if not self._socket or not self._is_connected:
            return False

        try:
            # 合并指标为单个数据报（注意 UDP 数据报大小限制）
            for i in range(0, len(metric_lines), 10):  # 每10个指标一个数据报
                batch = metric_lines[i : i + 10]
                if not batch:
                    continue

                message = "\n".join(batch).encode("utf-8")

                # 检查数据报大小（通常限制为 1500 字节）
                if len(message) > 1400:  # 留一些余量
                    # 分割大数据报
                    for line in batch:
                        if len(line.encode("utf-8")) <= 1400:
                            await asyncio.get_event_loop().sock_sendto(
                                self._socket, line.encode("utf-8"), (self.host, self.port)
                            )
                else:
                    await asyncio.get_event_loop().sock_sendto(
                        self._socket, message, (self.host, self.port)
                    )

            return True

        except Exception as e:
            print(f"UDP 发送失败: {e}")
            return False

    async def _send_tcp_metrics(self, metric_lines: list[str]) -> bool:
        """
        通过 TCP 发送指标

        Args:
            metric_lines: 指标行列表

        Returns:
            发送是否成功
        """
        if not self._tcp_writer or not self._is_connected:
            return False

        try:
            # 合并指标为单个消息
            message = "\n".join(metric_lines).encode("utf-8") + b"\n"
            self._tcp_writer.write(message)
            await self._tcp_writer.drain()
            return True

        except Exception as e:
            print(f"TCP 发送失败: {e}")
            return False

    async def send_metrics(self, metric_lines: list[str] | None = None) -> bool:
        """
        发送指标到 StatsD 服务器

        Args:
            metric_lines: 要发送的指标行列表，None 表示发送所有指标

        Returns:
            发送是否成功
        """
        if not self.monitor.is_enabled():
            return True

        if metric_lines is None:
            metric_lines = self.generate_all_metrics()

        if not metric_lines:
            return True

        # 建立连接
        if not self._is_connected:
            await self.connect()
            if not self._is_connected:
                return False

        # 应用采样率
        if self.sample_rate < 1.0:
            import random

            metric_lines = [line for line in metric_lines if random.random() < self.sample_rate]

        try:
            if self.protocol == "udp":
                return await self._send_udp_metrics(metric_lines)
            else:
                return await self._send_tcp_metrics(metric_lines)

        except Exception as e:
            print(f"发送指标失败: {e}")
            await self.disconnect()
            return False

    def generate_all_metrics(self) -> list[str]:
        """
        生成所有指标

        Returns:
            指标行列表
        """
        all_metrics = []
        all_metrics.extend(self._generate_counter_metrics())
        all_metrics.extend(self._generate_timer_metrics())
        all_metrics.extend(self._generate_gauge_metrics())
        return all_metrics

    async def schedule_periodic_send(self, interval: float = 30.0) -> None:
        """
        安排周期性发送指标

        Args:
            interval: 发送间隔（秒）
        """
        while True:
            try:
                await asyncio.sleep(interval)
                await self.send_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"周期性发送失败: {e}")

    def add_custom_metric(self, name: str, value: float, metric_type: str = "g") -> None:
        """
        添加自定义指标

        Args:
            name: 指标名称
            value: 指标值
            metric_type: 指标类型 ("c", "g", "ms")
        """
        metric_line = f"{self._format_metric_name(name)}:{value}|{metric_type}"
        self._pending_metrics.append(metric_line)

    async def flush_pending_metrics(self) -> bool:
        """
        刷新待发送的指标

        Returns:
            刷新是否成功
        """
        if not self._pending_metrics:
            return True

        success = await self.send_metrics(self._pending_metrics)
        if success:
            self._pending_metrics.clear()

        return success

    def get_connection_status(self) -> dict[str, Any]:
        """
        获取连接状态

        Returns:
            连接状态信息
        """
        return {
            "connected": self._is_connected,
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "pending_metrics": len(self._pending_metrics),
        }

    async def __aenter__(self) -> StatsDExporter:
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """异步上下文管理器出口"""
        await self.disconnect()

    def __del__(self) -> None:
        """析构函数"""
        if self._socket:
            self._socket.close()
