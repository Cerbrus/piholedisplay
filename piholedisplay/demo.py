import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from .canvas import Canvas
from .icons import ICONS, SIZE
from .model import Frame, Overlay, PiholeStats, SystemStats
from .screen import render

NOW = datetime(2026, 11, 27, 12, 0)
SCREEN_SCALE = 4
ICON_SCALE = 6


def demo_history(buckets=144):
    rng = random.Random(7)
    history = []
    for index in range(buckets):
        total = int(max(60, 400 + 350 * math.sin(index / buckets * math.pi * 2 - 1.2) + rng.randint(0, 250)))
        history.append((total, int(total * rng.uniform(0.1, 0.3))))
    return tuple(history)


def demo_pihole(**changes):
    values = {
        'blocked': 12431,
        'total': 67512,
        'percent_blocked': 18.4,
        'clients': 23,
        'blocklist_size': 1243118,
        'blocklist_updated': NOW - timedelta(days=3, hours=4),
        'queries_per_minute': 47,
        'history': demo_history(),
        'blocking': True,
        'blocking_until': None,
        'messages': 0,
        'update': None,
        'uptime_seconds': 12 * 86400,
    }
    return PiholeStats(**{**values, **changes})


def demo_system(**changes):
    values = {
        'host': 'pi-hole.local',
        'ip_address': '192.168.1.104',
        'memory_percent': 36,
        'disk_percent': 37,
        'temperature': 46,
        'uptime_seconds': 12 * 86400 + 4 * 3600,
        'wifi_percent': 72,
        'under_voltage': False,
    }
    return SystemStats(**{**values, **changes})


def demo_frames():
    def frame(pihole=None, system=None, **changes):
        return Frame(system=system or demo_system(), refreshed=NOW, pihole=pihole or demo_pihole(), phrase='Yeeted', **changes)

    return {
        'normal-1': frame(),
        'normal-2': frame(alternate=True),
        'markers': frame(demo_pihole(messages=2, update='v6.7'), demo_system(under_voltage=True)),
        'stopped': frame(overlay=Overlay('pause', 'Stopped', '27-11 11:47')),
        'blocking-off': frame(
            demo_pihole(blocking=False, blocking_until=NOW + timedelta(minutes=15)),
            alternate=True,
            overlay=Overlay('shield', 'Blocking off', 'until 12:15'),
        ),
        'no-data': frame(overlay=Overlay('warning', 'No data', 'since 11:50')),
    }


def icons_markdown():
    lines = [
        '# Icons',
        '',
        'Every icon on the screen is a 9 x 9 pixel bitmap from `piholedisplay/icons.py`.',
        'This page is generated: run `python -m piholedisplay --demo docs` after changing an icon.',
        '',
        '| Icon | Name | Meaning |',
        '|---|---|---|',
    ]
    lines += [f'| ![{name}](icons/{name}.png) | `{name}` | {icon.meaning} |' for name, icon in ICONS.items()]
    return '\n'.join(lines) + '\n'


def icon_image(name):
    canvas = Canvas(SIZE + 2, SIZE + 2)
    canvas.icon(1, 1, name)
    return canvas.to_rgb(ICON_SCALE)


def write_demo(directory):
    directory = Path(directory)
    screens, icons = directory / 'screens', directory / 'icons'
    screens.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    for name, frame in demo_frames().items():
        render(frame).to_rgb(SCREEN_SCALE).save(screens / f'{name}.png')
    for name in ICONS:
        icon_image(name).save(icons / f'{name}.png')
    (directory / 'icons.md').write_text(icons_markdown(), encoding='utf-8', newline='\n')
