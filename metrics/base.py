from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time
import secrets

SESSION_ID: str = secrets.token_urlsafe(16)

@dataclass(frozen=True, slots=True)
class NetworkRate:
    bytes_sent_per_s: float
    bytes_recv_per_s: float
    packets_sent_per_s: Optional[float] = None
    packets_recv_per_s: Optional[float] = None
    err_in_per_s: Optional[float] = None
    err_out_per_s: Optional[float] = None
    drop_in_per_s: Optional[float] = None
    drop_out_per_s: Optional[float] = None


@dataclass(frozen=True, slots=True)
class DiskRate:
    read_bytes_per_s: float
    write_bytes_per_s: float
    read_ops_per_s: Optional[float] = None
    write_ops_per_s: Optional[float] = None


@dataclass(frozen=True, slots=True)
class Metric:
    ts: float
    interval_s: int
    cpu_pct: float
    ram_pct: float
    hostname: str
    os: str
    os_v: str
    arch: str
    node_role: str
    env: str = "dev"
    net: Optional[NetworkRate] = None
    session_id: str = SESSION_ID
    disk: Optional[DiskRate] = None


def now(
    *,
    cpu_pct: float,
    ram_pct: float,
    net: Optional[NetworkRate] = None,
    disk: Optional[DiskRate] = None,
    hostname: str,
    os: str,
    os_v: str,
    arch: str,
    node_role: str,
    env: str = "dev",
    interval_s: int = 240,
) -> "Metric":
    return Metric(
        ts=time.time(),
        interval_s=interval_s,
        cpu_pct=cpu_pct,
        ram_pct=ram_pct,
        net=net,
        disk=disk,
        hostname=hostname,
        os=os,
        os_v=os_v,
        arch=arch,
        node_role = node_role,
        env=env,
        session_id=SESSION_ID
    )
