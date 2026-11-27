import json
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from piholedisplay.app import FALLBACK_PHRASE, App, pick_phrase
from piholedisplay.config import load_config
from piholedisplay.demo import demo_pihole, demo_system
from piholedisplay.pihole import PiholeError

ROOT = Path(__file__).parent.parent
START = datetime(2026, 11, 27, 12, 0)


class Clock:
    def __init__(self):
        self.now = START

    def __call__(self):
        return self.now


class Stop:
    def __init__(self, clock, rounds):
        self.clock = clock
        self.rounds = rounds
        self.waits = []

    def is_set(self):
        return self.rounds <= 0

    def wait(self, seconds):
        self.waits.append(seconds)
        self.clock.now += timedelta(seconds=seconds)
        self.rounds -= 1


class Display:
    def __init__(self):
        self.shown = 0

    def show(self, canvas, inverted):
        self.shown += 1


class Client:
    def __init__(self, results):
        self.results = list(results)
        self.closed = False

    def fetch(self, now):
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


@pytest.fixture
def config_dir(tmp_path):
    (tmp_path / 'config.json').write_text((ROOT / 'config.json').read_text())
    return tmp_path


def run(config_dir, results, rounds, **options):
    clock = Clock()
    frames = []
    client = Client(results)
    app = App(
        config_dir,
        Display(),
        client_factory=lambda *_: client,
        system_reader=demo_system,
        clock=clock,
        stop=Stop(clock, rounds),
        rng=random.Random(1),
        **options,
    )
    show = app._show
    app._show = lambda frame: (frames.append(frame), show(frame))
    app.run()
    return app, client, frames


def test_renders_every_interval_and_alternates(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=3)

    assert [frame.refreshed for frame in frames] == [START + timedelta(minutes=10 * index) for index in range(3)]
    assert [frame.alternate for frame in frames] == [False, True, False]
    assert all(frame.overlay is None for frame in frames)
    assert app.stop.waits == [600, 600, 600]


def test_stop_draws_the_stopped_frame_and_logs_out(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=1)

    assert app.display.shown == len(frames) + 1
    assert client.closed


def test_failure_shows_no_data_once_and_retries_every_minute(config_dir):
    app, client, frames = run(config_dir, [demo_pihole(), PiholeError('down')], rounds=4)

    assert [frame.overlay.title if frame.overlay else None for frame in frames] == [None, 'No data']
    assert frames[1].overlay.detail == 'since 12:00'
    assert frames[1].pihole == demo_pihole()
    assert app.stop.waits == [600, 60, 60, 60]


def test_recovery_redraws_without_waiting_for_the_interval(config_dir):
    app, client, frames = run(config_dir, [PiholeError('down'), demo_pihole()], rounds=2)

    assert [frame.overlay.title if frame.overlay else None for frame in frames] == ['No data', None]
    assert frames[0].pihole is None
    assert frames[1].refreshed == START + timedelta(seconds=60)


def test_blocking_off_shows_until_or_since(config_dir):
    timed = demo_pihole(blocking=False, blocking_until=START + timedelta(minutes=15))
    untimed = demo_pihole(blocking=False)

    assert run(config_dir, [timed], rounds=1)[2][0].overlay.detail == 'until 12:15'
    assert run(config_dir, [untimed], rounds=1)[2][0].overlay.detail == 'since 12:00'


def test_once_renders_a_single_frame_without_the_stopped_frame(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=5, once=True)

    assert app.display.shown == 1
    assert client.closed


def test_zero_interval_renders_once(config_dir):
    (config_dir / 'config.local.json').write_text(json.dumps({'interval_minutes': 0}))

    app, client, frames = run(config_dir, [demo_pihole()], rounds=5)

    assert app.display.shown == 1


def test_local_config_overrides_nested_values(config_dir):
    (config_dir / 'config.local.json').write_text(json.dumps({'pihole': {'api_url': 'http://other/api'}, 'draw_inverted': False}))

    config = load_config(config_dir)

    assert config.api_url == 'http://other/api'
    assert config.password_file == '/etc/pihole/cli_pw'
    assert not config.draw_inverted
    assert config.interval_minutes == 10


def test_shipped_phrases_are_unique_and_fit_a_six_digit_count():
    phrases = load_config(ROOT).phrases

    assert len(set(phrases)) == len(phrases)
    assert all(pick_phrase([phrase], 12431) == phrase for phrase in phrases)
    assert len([phrase for phrase in phrases if pick_phrase([phrase], 123456) == phrase]) >= 40


def test_pick_phrase_falls_back_when_nothing_fits():
    assert pick_phrase(['Defenestrated with prejudice'], 12431) == FALLBACK_PHRASE
    assert pick_phrase([], 12431) == FALLBACK_PHRASE


def test_stop_event_default_is_a_threading_event(config_dir):
    assert isinstance(App(config_dir, Display()).stop, threading.Event)
