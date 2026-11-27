import json
from dataclasses import dataclass
from pathlib import Path

DEFAULTS = 'config.json'
OVERRIDES = 'config.local.json'


@dataclass(frozen=True)
class Config:
    interval_minutes: float
    retry_seconds: float
    draw_inverted: bool
    log_level: str
    api_url: str
    password_file: str | None
    phrases: tuple[str, ...]


def merge(base, overrides):
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(directory):
    directory = Path(directory)
    values = json.loads((directory / DEFAULTS).read_text(encoding='utf-8'))
    overrides = directory / OVERRIDES
    if overrides.exists():
        values = merge(values, json.loads(overrides.read_text(encoding='utf-8')))
    return Config(
        interval_minutes=values['interval_minutes'],
        retry_seconds=values['retry_seconds'],
        draw_inverted=values['draw_inverted'],
        log_level=values['log_level'],
        api_url=values['pihole']['api_url'],
        password_file=values['pihole']['password_file'],
        phrases=tuple(values['phrases']),
    )
