from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PiholeStats:
    blocked: int
    total: int
    percent_blocked: float
    clients: int
    blocklist_size: int
    blocklist_updated: datetime | None
    queries_per_minute: int
    history: tuple[tuple[int, int], ...]
    blocking: bool
    blocking_until: datetime | None
    messages: int
    update: str | None


@dataclass(frozen=True)
class SystemStats:
    host: str
    ip_address: str
    memory_percent: int | None
    disk_percent: int | None
    temperature: int | None
    uptime_seconds: int | None
    wifi_percent: int | None
    under_voltage: bool


@dataclass(frozen=True)
class Overlay:
    icon: str
    title: str
    detail: str


@dataclass(frozen=True)
class Frame:
    system: SystemStats
    refreshed: datetime
    pihole: PiholeStats | None = None
    phrase: str = 'Blocked'
    alternate: bool = False
    overlay: Overlay | None = None
