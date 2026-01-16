import time
import threading
import platform
import socket
from typing import Optional, Callable
from config.logging_config import get_logger

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from metrics.base import Metric, NetworkRate, DiskRate, now

logger = get_logger(__name__)


class MetricsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self._running = False
        self._thread = None
        self._last_net_io = None
        self._last_disk_io = None
        self._last_net_time = None
        self._last_disk_time = None

    def _get_hostname(self) -> str:
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"

    def _get_cpu_percent(self) -> float:
        if PSUTIL_AVAILABLE:
            return psutil.cpu_percent(interval=1)
        return 0.0

    def _get_ram_percent(self) -> float:
        if PSUTIL_AVAILABLE:
            return psutil.virtual_memory().percent
        return 0.0

    def _get_network_rate(self, interval_s: float) -> Optional[NetworkRate]:
        if not PSUTIL_AVAILABLE:
            return None

        try:
            net_io = psutil.net_io_counters()
            current_time = time.time()

            if self._last_net_io is None or self._last_net_time is None:
                self._last_net_io = net_io
                self._last_net_time = current_time
                return None

            time_diff = current_time - self._last_net_time
            if time_diff <= 0:
                return None

            bytes_sent_per_s = (
                net_io.bytes_sent - self._last_net_io.bytes_sent
            ) / time_diff
            bytes_recv_per_s = (
                net_io.bytes_recv - self._last_net_io.bytes_recv
            ) / time_diff
            packets_sent_per_s = (
                net_io.packets_sent - self._last_net_io.packets_sent
            ) / time_diff
            packets_recv_per_s = (
                net_io.packets_recv - self._last_net_io.packets_recv
            ) / time_diff
            err_in_per_s = (net_io.errin - self._last_net_io.errin) / time_diff
            err_out_per_s = (net_io.errout - self._last_net_io.errout) / time_diff
            drop_in_per_s = (net_io.dropin - self._last_net_io.dropin) / time_diff
            drop_out_per_s = (net_io.dropout - self._last_net_io.dropout) / time_diff

            self._last_net_io = net_io
            self._last_net_time = current_time

            return NetworkRate(
                bytes_sent_per_s=bytes_sent_per_s,
                bytes_recv_per_s=bytes_recv_per_s,
                packets_sent_per_s=packets_sent_per_s,
                packets_recv_per_s=packets_recv_per_s,
                err_in_per_s=err_in_per_s,
                err_out_per_s=err_out_per_s,
                drop_in_per_s=drop_in_per_s,
                drop_out_per_s=drop_out_per_s,
            )
        except Exception:
            return None

    def _get_disk_rate(self, interval_s: float) -> Optional[DiskRate]:
        if not PSUTIL_AVAILABLE:
            return None

        try:
            disk_io = psutil.disk_io_counters()
            current_time = time.time()

            if self._last_disk_io is None or self._last_disk_time is None:
                self._last_disk_io = disk_io
                self._last_disk_time = current_time
                return None

            time_diff = current_time - self._last_disk_time
            if time_diff <= 0:
                return None

            read_bytes_per_s = (
                disk_io.read_bytes - self._last_disk_io.read_bytes
            ) / time_diff
            write_bytes_per_s = (
                disk_io.write_bytes - self._last_disk_io.write_bytes
            ) / time_diff
            read_ops_per_s = (
                disk_io.read_count - self._last_disk_io.read_count
            ) / time_diff
            write_ops_per_s = (
                disk_io.write_count - self._last_disk_io.write_count
            ) / time_diff

            self._last_disk_io = disk_io
            self._last_disk_time = current_time

            return DiskRate(
                read_bytes_per_s=read_bytes_per_s,
                write_bytes_per_s=write_bytes_per_s,
                read_ops_per_s=read_ops_per_s,
                write_ops_per_s=write_ops_per_s,
            )
        except Exception:
            return None

    def collect_metric(
        self, node_role: str = "ingestion", env: str = "dev", interval_s: int = 10
    ) -> Metric:
        cpu_pct = self._get_cpu_percent()
        ram_pct = self._get_ram_percent()
        hostname = self._get_hostname()
        os_name = platform.system()
        os_version = platform.version()
        arch = platform.machine()

        net = self._get_network_rate(interval_s)
        disk = self._get_disk_rate(interval_s)

        metric = now(
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            net=net,
            disk=disk,
            hostname=hostname,
            os=os_name,
            os_v=os_version,
            arch=arch,
            node_role=node_role,
            env=env,
            interval_s=interval_s,
        )

        return metric


    def start_listener(
        self,
        interval_seconds: int = 10,
        node_role: str = "ingestion",
        env: str = "dev",
        on_metric_callback: Optional[Callable[[Metric], None]] = None,
    ):
        if self._running:
            return

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available. Install with: pip install psutil")
            logger.warning("Metrics collection will be limited (CPU/RAM will show 0.0)")

        self._running = True

        def _listen():
            while self._running:
                metric = self.collect_metric(
                    node_role=node_role, env=env, interval_s=interval_seconds
                )
                if on_metric_callback:
                    on_metric_callback(metric)
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=_listen, daemon=True)
        self._thread.start()
        logger.info(f"Metrics listener started (interval: {interval_seconds}s)")

    def stop_listener(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        logger.info("Metrics listener stopped")


_global_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def set_collector(collector: MetricsCollector):
    global _global_collector
    _global_collector = collector
