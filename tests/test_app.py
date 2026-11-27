import io
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image

from piholedisplay import screen
from piholedisplay.app import FALLBACK_PHRASE, SNAPSHOT_SCALE, App, Signals, pick_phrase
from piholedisplay.canvas import HEIGHT, WIDTH
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


class FakeSignals:
    def __init__(self, clock, rounds, redraws=(), wake_after=None):
        self.clock = clock
        self.rounds = rounds
        self.redraws = list(redraws)
        self.wake_after = wake_after
        self.waits = []

    @property
    def stopping(self):
        return self.rounds <= 0

    def take_redraw(self):
        return self.redraws.pop(0) if self.redraws else False

    def wait(self, seconds):
        self.waits.append(seconds)
        self.clock.now += timedelta(seconds=min(seconds, self.wake_after or seconds))
        self.rounds -= 1


class Display:
    def __init__(self):
        self.shown = 0

    def show(self, canvas, inverted):
        self.shown += 1
        self.canvas = canvas


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


class Server:
    def __init__(self, port, produce):
        self.port = port
        self.produce = produce
        self.closed = False

    def close(self):
        self.closed = True


@pytest.fixture
def config_dir(tmp_path):
    (tmp_path / 'config.json').write_text((ROOT / 'config.json').read_text())
    return tmp_path


def run(config_dir, results, rounds, redraws=(), wake_after=None, **options):
    clock = Clock()
    frames = []
    client = Client(results)
    app = App(
        config_dir,
        Display(),
        client_factory=lambda *_: client,
        system_reader=demo_system,
        server_factory=Server,
        clock=clock,
        signals=FakeSignals(clock, rounds, redraws, wake_after),
        rng=random.Random(1),
        **options,
    )
    show = app._show
    app._show = lambda frame: (frames.append(frame), show(frame))
    app.run()
    return app, client, frames


def test_renders_every_interval_and_alternates(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=3)

    assert [frame.refreshed for frame in frames] == [START + timedelta(minutes=30 * index) for index in range(3)]
    assert [frame.alternate for frame in frames] == [False, True, False]
    assert all(frame.overlay is None for frame in frames)
    assert app.signals.waits == [1800, 1800, 1800]


def test_stop_draws_the_stopped_frame_and_logs_out(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=1)

    assert app.display.shown == len(frames) + 1
    assert client.closed


def test_failure_shows_no_data_once_and_retries_every_minute(config_dir):
    app, client, frames = run(config_dir, [demo_pihole(), PiholeError('down')], rounds=4)

    assert [frame.overlay.title if frame.overlay else None for frame in frames] == [None, 'No data']
    assert frames[1].overlay.detail == 'since 12:00'
    assert frames[1].pihole == demo_pihole()
    assert app.signals.waits == [1800, 60, 60, 60]


def test_recovery_redraws_without_waiting_for_the_interval(config_dir):
    app, client, frames = run(config_dir, [PiholeError('down'), demo_pihole()], rounds=2)

    assert [frame.overlay.title if frame.overlay else None for frame in frames] == ['No data', None]
    assert frames[0].pihole is None
    assert frames[1].refreshed == START + timedelta(seconds=60)


def test_redraws_early_while_pihole_is_still_loading_its_history(config_dir):
    app, client, frames = run(config_dir, [demo_pihole(uptime_seconds=120), demo_pihole()], rounds=2)

    assert [frame.refreshed for frame in frames] == [START, START + timedelta(seconds=480)]
    assert app.signals.waits == [480, 1800]


def test_redraw_request_draws_without_waiting_for_the_interval(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=2, redraws=[False, True], wake_after=100)

    assert [frame.refreshed for frame in frames] == [START, START + timedelta(seconds=100)]
    assert all(frame.overlay is None for frame in frames)


def test_signals_keep_a_redraw_request_until_it_is_taken():
    signals = Signals()

    signals.request_redraw()
    signals.wait(60)

    assert signals.take_redraw()
    assert not signals.take_redraw()
    assert not signals.stopping

    signals.stop()
    signals.wait(60)

    assert signals.stopping


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
    assert config.interval_minutes == 30


def test_shipped_phrases_are_unique_and_fit_a_six_digit_count():
    phrases = load_config(ROOT).phrases

    assert len(set(phrases)) == len(phrases)
    assert all(pick_phrase([phrase], 12431) == phrase for phrase in phrases)
    assert len([phrase for phrase in phrases if pick_phrase([phrase], 123456) == phrase]) >= 40


def test_pick_phrase_falls_back_when_nothing_fits():
    assert pick_phrase(['Defenestrated with prejudice'], 12431) == FALLBACK_PHRASE
    assert pick_phrase([], 12431) == FALLBACK_PHRASE


def test_serves_the_screen_on_the_configured_port_until_it_stops(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=2)

    assert app.server.port == 8081
    assert app.server.produce == app.png
    assert app.server.closed


def test_port_zero_serves_nothing(config_dir):
    (config_dir / 'config.local.json').write_text(json.dumps({'http': {'port': 0}}))

    app, client, frames = run(config_dir, [demo_pihole()], rounds=2)

    assert app.server is None


def test_changed_port_moves_the_server(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=1)
    first = app.server
    (config_dir / 'config.local.json').write_text(json.dumps({'http': {'port': 8082}}))
    app.config = load_config(config_dir)

    app._serve()

    assert first.closed
    assert app.server.port == 8082


def test_corner_padding_applies_to_the_panel_and_not_to_the_png(config_dir):
    (config_dir / 'config.local.json').write_text(json.dumps({'corner_padding': 6}))
    box = (screen.STAMP_RIGHT - 6, screen.FOOTER_Y, WIDTH, HEIGHT)

    app, client, frames = run(config_dir, [demo_pihole()], rounds=1)

    assert app.display.canvas.black.crop(box).getextrema() == (255, 255)
    with Image.open(io.BytesIO(app.png())) as image:
        assert image.crop(tuple(SNAPSHOT_SCALE * edge for edge in box)).getextrema() != ((255, 255), (255, 255), (255, 255))


def test_png_is_a_fresh_frame_at_four_times_the_panel_size(config_dir):
    app, client, frames = run(config_dir, [demo_pihole(), demo_pihole(clients=99)], rounds=1)
    app.clock.now += timedelta(minutes=7)

    with Image.open(io.BytesIO(app.png())) as image:
        assert image.size == (WIDTH * SNAPSHOT_SCALE, HEIGHT * SNAPSHOT_SCALE)
    assert app.stats.clients == 99
    assert app.refreshes == 1


def test_png_is_rendered_again_only_after_the_maximum_age(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=1)

    first = app.png()
    app.clock.now += timedelta(seconds=119)
    second = app.png()
    app.clock.now += timedelta(seconds=1)
    third = app.png()

    assert second is first
    assert third is not first
    assert app.snapshots == 2


def test_png_is_rendered_again_at_once_on_refresh(config_dir):
    app, client, frames = run(config_dir, [demo_pihole()], rounds=1)

    first = app.png()
    second = app.png(refresh=True)

    assert second is not first
    assert app.png() is second
    assert app.snapshots == 2


def test_png_shows_no_data_while_pihole_is_down(config_dir):
    app, client, frames = run(config_dir, [demo_pihole(), PiholeError('down')], rounds=1)

    app.png()

    assert app._overlay(False).title == 'No data'
    assert app.stats == demo_pihole()


def test_signals_default_to_real_ones(config_dir):
    assert isinstance(App(config_dir, Display()).signals, Signals)
