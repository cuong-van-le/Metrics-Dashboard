from .blueprint import Pipeline
from metrics.agent import set_collector, MetricsCollector, get_collector
from metrics.base import Metric
from config.logging_config import get_logger
import json
import time

logger = get_logger(__name__)


class Ingestion(Pipeline):
    def __init__(self, config, client):
        self.config = config
        self.client = client
        collector = MetricsCollector()
        set_collector(collector)

    def _metric_to_dict(self, metric: Metric) -> dict:
        data = {
            "ts": metric.ts,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(metric.ts)),
            "interval_s": metric.interval_s,
            "cpu_pct": metric.cpu_pct,
            "ram_pct": metric.ram_pct,
            "hostname": metric.hostname,
            "os": metric.os,
            "os_v": metric.os_v,
            "arch": metric.arch,
            "node_role": metric.node_role,
            "env": metric.env,
            "session_id": metric.session_id,
        }

        if metric.net:
            data["net_bytes_sent_per_s"] = metric.net.bytes_sent_per_s
            data["net_bytes_recv_per_s"] = metric.net.bytes_recv_per_s
            data["net_packets_sent_per_s"] = metric.net.packets_sent_per_s
            data["net_packets_recv_per_s"] = metric.net.packets_recv_per_s
            data["net_err_in_per_s"] = metric.net.err_in_per_s
            data["net_err_out_per_s"] = metric.net.err_out_per_s
            data["net_drop_in_per_s"] = metric.net.drop_in_per_s
            data["net_drop_out_per_s"] = metric.net.drop_out_per_s

        if metric.disk:
            data["disk_read_bytes_per_s"] = metric.disk.read_bytes_per_s
            data["disk_write_bytes_per_s"] = metric.disk.write_bytes_per_s
            data["disk_read_ops_per_s"] = metric.disk.read_ops_per_s
            data["disk_write_ops_per_s"] = metric.disk.write_ops_per_s

        return data

    def send_message(self, metric: Metric):
        try:
            metric_dict = self._metric_to_dict(metric)
            payload = json.dumps(metric_dict) + "\n"
            print("Message will be sent")
            d = self.client.put_record(
                DeliveryStreamName=self.config.DELIVERY_STREAM_NAME,
                Record={"Data": payload.encode("utf-8")},
            )
            print(d)
            print("Message sent")

            logger.info(
                f"Sent metric to Firehose: {metric.hostname} - CPU: {metric.cpu_pct:.2f}%, RAM: {metric.ram_pct:.2f}%"
            )
        except Exception as e:
            logger.error(f"Failed to send metric to Firehose: {e}")

    def listen(self):
        collector = get_collector()
        collector.start_listener(
            interval_seconds=3, on_metric_callback=self.send_message
        )
        logger.info("Ingestion listener started with metrics collection")

        try:
            while True:
                pass
        except KeyboardInterrupt:
            logger.info("Ingestion listener stopped")
            collector.stop_listener()
