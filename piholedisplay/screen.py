import math

from .canvas import WIDTH, Canvas, text_width

DIVIDER_X = 99
HERO_WIDTH = DIVIDER_X - 6
GRID_LEFT = 105
GRID_RIGHT = 161
GRID_ROWS = (1, 13, 25, 37)
ICON_GAP = 13
CHART_LEFT = 2
CHART_TOP = 53
CHART_HEIGHT = 36
CHART_WIDTH = WIDTH - 4
BAR_STEP = 3
BAR_WIDTH = 2
FOOTER_Y = 94
STAMP_RIGHT = WIDTH - 2
OVERLAY_TOP = 63
OVERLAY_BOTTOM = 79
OVERLAY_MARGIN = 1
MISSING = '-'


def thousands(value):
    return f'{value:,}'.replace(',', '.')


def compact(value):
    if value >= 1_000_000:
        return f'{value / 1_000_000:.2f}M'
    if value >= 10_000:
        return f'{value // 1000}k'
    return thousands(value)


def percent(value):
    return MISSING if value is None else f'{value}%'


def duration(seconds):
    if seconds is None:
        return MISSING
    minutes = int(seconds) // 60
    days, hours = minutes // 1440, minutes % 1440 // 60
    if days:
        return f'{days}d {hours}h'
    if hours:
        return f'{hours}h {minutes % 60}m'
    return f'{minutes}m'


def blocked_share(value):
    return f'{value:.0f}%' if value >= 99.95 else f'{value:.1f}%'


def phrase_fits(blocked, phrase):
    return text_width(f'{thousands(blocked)} {phrase}', 9) <= HERO_WIDTH


def fit(message, width, size=10):
    while message and text_width(message, size) > width:
        message = message[:-1]
    return message


def chart_columns(history, count):
    count = min(count, len(history))
    columns = []
    for column in range(count):
        start, end = column * len(history) / count, (column + 1) * len(history) / count
        buckets = range(int(start), min(math.ceil(end), len(history)))
        shares = [(min(end, index + 1) - max(start, index), history[index]) for index in buckets]
        columns.append(tuple(sum(share * entry[part] for share, entry in shares) for part in (0, 1)))
    return columns


def render(frame, corner_padding=0):
    canvas = Canvas()
    _hero(canvas, frame)
    canvas.line((DIVIDER_X, 2), (DIVIDER_X, 48))
    _grid(canvas, frame)
    canvas.line((CHART_LEFT, CHART_TOP - 2), (CHART_LEFT + CHART_WIDTH - 1, CHART_TOP - 2))
    hours = _chart(canvas, frame.pihole.history if frame.pihole else ())
    canvas.line((CHART_LEFT, CHART_TOP + CHART_HEIGHT + 2), (CHART_LEFT + CHART_WIDTH - 1, CHART_TOP + CHART_HEIGHT + 2))
    _footer(canvas, frame, hours, STAMP_RIGHT - corner_padding)
    if frame.overlay:
        _overlay(canvas, frame.overlay)
    return canvas


def _hero(canvas, frame):
    pihole = frame.pihole
    canvas.icon(3, 6, 'shield', 'red')
    canvas.text(16, 0, blocked_share(pihole.percent_blocked) if pihole else MISSING, 'red', size=24, bold=True)
    if pihole:
        canvas.text(3, 28, fit(f'{thousands(pihole.blocked)} {frame.phrase}', HERO_WIDTH, 9), size=9)
        canvas.text(3, 39, f'of {thousands(pihole.total)}', size=9)

    edge = DIVIDER_X - 3
    if frame.system.under_voltage:
        canvas.icon(edge - 8, 40, 'bolt', 'red')
        edge -= 13
    if pihole and pihole.messages:
        count = str(pihole.messages)
        canvas.text(edge, 39, count, 'red', size=9, align='right')
        canvas.icon(int(edge - text_width(count, 9)) - 12, 40, 'warning', 'red')


def _stat(canvas, x, y, icon, value, width):
    canvas.icon(x, y + 2, icon)
    canvas.text(x + ICON_GAP, y, fit(value, width - ICON_GAP))


def _grid(canvas, frame):
    pihole, system = frame.pihole, frame.system
    half = GRID_RIGHT - GRID_LEFT
    full = WIDTH - GRID_LEFT - 2
    cells = [
        ('person', str(pihole.clients) if pihole else MISSING),
        ('pulse', f'{pihole.queries_per_minute}/m' if pihole else MISSING),
        ('list', compact(pihole.blocklist_size) if pihole else MISSING),
        ('thermometer', MISSING if system.temperature is None else f'{system.temperature}°'),
    ]
    if frame.alternate:
        age = None
        if pihole and pihole.blocklist_updated:
            age = max(0, (frame.refreshed - pihole.blocklist_updated).days)
        cells += [('calendar', MISSING if age is None else f'{age}d'), ('wifi', percent(system.wifi_percent))]
        address = ('home', system.host)
    else:
        cells += [('chip', percent(system.memory_percent)), ('floppy', percent(system.disk_percent))]
        address = ('network', system.ip_address)

    for index, (icon, value) in enumerate(cells):
        x = GRID_RIGHT if index % 2 else GRID_LEFT
        _stat(canvas, x, GRID_ROWS[index // 2], icon, value, half)
    _stat(canvas, GRID_LEFT, GRID_ROWS[3], *address, full)


def _chart(canvas, history):
    columns = chart_columns(history, CHART_WIDTH // BAR_STEP)
    peak = max((total for total, _ in columns), default=0)
    if not peak:
        return 0
    bottom = CHART_TOP + CHART_HEIGHT
    for index, (total, blocked) in enumerate(columns):
        left = CHART_LEFT + index * BAR_STEP
        total_height = int(total * CHART_HEIGHT / peak)
        blocked_height = int(blocked * CHART_HEIGHT / peak)
        if total_height > blocked_height:
            canvas.box((left, bottom - total_height, left + BAR_WIDTH - 1, bottom - blocked_height - 1))
        if blocked_height:
            canvas.box((left, bottom - blocked_height, left + BAR_WIDTH - 1, bottom), 'red')
        elif total_height:
            canvas.box((left, bottom, left + BAR_WIDTH - 1, bottom))
    return round(len(history) / 6)


def _footer(canvas, frame, hours, stamp_right):
    if hours:
        canvas.text(2, FOOTER_Y, f'-{hours}h', size=8)
    canvas.icon(34, FOOTER_Y, 'power')
    canvas.text(46, FOOTER_Y, duration(frame.system.uptime_seconds), size=8)
    if frame.pihole and frame.pihole.update:
        canvas.icon(88, FOOTER_Y, 'update', 'red')
        canvas.text(100, FOOTER_Y, fit(frame.pihole.update, 34, 8), 'red', size=8)
    stamp = frame.refreshed.strftime('%d-%m %H:%M')
    canvas.icon(int(stamp_right - text_width(stamp, 8)) - 12, FOOTER_Y, 'clock')
    canvas.text(stamp_right, FOOTER_Y, stamp, size=8, align='right')


def _overlay(canvas, overlay):
    title_width = text_width(overlay.title, 9, bold=True)
    detail_width = text_width(overlay.detail, 8)
    width = int(6 + 9 + 5 + title_width + 6 + detail_width + 6)
    left = (WIDTH - width) // 2
    canvas.clear((left - OVERLAY_MARGIN, OVERLAY_TOP - OVERLAY_MARGIN, left + width + OVERLAY_MARGIN, OVERLAY_BOTTOM + OVERLAY_MARGIN))
    canvas.box((left, OVERLAY_TOP, left + width, OVERLAY_BOTTOM), 'red')
    canvas.icon(left + 6, OVERLAY_TOP + 4, overlay.icon, 'red', fill=255)
    canvas.text(left + 20, OVERLAY_TOP + 3, overlay.title, 'red', size=9, bold=True, fill=255)
    canvas.text(left + 26 + title_width, OVERLAY_TOP + 4, overlay.detail, 'red', size=8, fill=255)
