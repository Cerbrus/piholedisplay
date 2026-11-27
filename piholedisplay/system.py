import shutil
import socket
import subprocess
from pathlib import Path

from .model import SystemStats

THROTTLED_FILE = 'sys/devices/platform/soc/soc:firmware/get_throttled'
UNDER_VOLTAGE_SINCE_BOOT = 1 << 16
WIRELESS_MAX_QUALITY = 70


def read_text(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def memory_percent(root):
    text = read_text(root / 'proc/meminfo')
    if not text:
        return None
    values = {line.split(':')[0]: int(line.split()[1]) for line in text.splitlines() if ':' in line}
    total, available = values.get('MemTotal'), values.get('MemAvailable')
    if not total or available is None:
        return None
    return round((total - available) * 100 / total)


def disk_percent(root):
    try:
        usage = shutil.disk_usage(root)
    except OSError:
        return None
    return round(usage.used * 100 / usage.total)


def temperature(root):
    text = read_text(root / 'sys/class/thermal/thermal_zone0/temp')
    return round(int(text) / 1000) if text else None


def uptime_seconds(root):
    text = read_text(root / 'proc/uptime')
    return int(float(text.split()[0])) if text else None


def wifi_percent(root):
    text = read_text(root / 'proc/net/wireless')
    for line in (text or '').splitlines()[2:]:
        fields = line.split()
        if len(fields) > 2:
            quality = float(fields[2].rstrip('.'))
            return min(100, round(quality * 100 / WIRELESS_MAX_QUALITY))
    return None


def vcgencmd_throttled():
    try:
        output = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return output.strip().partition('=')[2] or None


def under_voltage(throttled_file, fallback=vcgencmd_throttled):
    text = read_text(throttled_file) or fallback()
    try:
        return bool(int(text, 16) & UNDER_VOLTAGE_SINCE_BOOT)
    except (TypeError, ValueError):
        return False


def ip_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('192.0.2.1', 80))
            return probe.getsockname()[0]
    except OSError:
        return '-'


def read_system(root=Path('/'), throttled_fallback=vcgencmd_throttled):
    return SystemStats(
        host=socket.gethostname().lower() + '.local',
        ip_address=ip_address(),
        memory_percent=memory_percent(root),
        disk_percent=disk_percent(root),
        temperature=temperature(root),
        uptime_seconds=uptime_seconds(root),
        wifi_percent=wifi_percent(root),
        under_voltage=under_voltage(root / THROTTLED_FILE, throttled_fallback),
    )
