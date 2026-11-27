import io
import logging
import random
import threading
from dataclasses import replace
from datetime import datetime, timedelta

from .config import load_config
from .model import Frame, Overlay
from .pihole import PiholeClient, PiholeError
from .screen import phrase_fits, render
from .system import read_system
from .web import FrameServer

log = logging.getLogger(__name__)

FALLBACK_PHRASE = 'Blocked'
SETTLE_SECONDS = 600
SNAPSHOT_SCALE = 4


def pick_phrase(phrases, blocked, rng=random):
    fitting = [phrase for phrase in phrases if phrase_fits(blocked, phrase)]
    return rng.choice(fitting) if fitting else FALLBACK_PHRASE


class Signals:
    def __init__(self):
        self.stopping = False
        self.redraw = False
        self.wake = threading.Event()

    def stop(self, *_):
        self.stopping = True
        self.wake.set()

    def request_redraw(self, *_):
        self.redraw = True
        self.wake.set()

    def take_redraw(self):
        requested, self.redraw = self.redraw, False
        return requested

    def wait(self, seconds):
        self.wake.wait(seconds)
        self.wake.clear()


class App:
    def __init__(
        self,
        config_dir,
        display,
        once=False,
        client_factory=PiholeClient,
        system_reader=read_system,
        server_factory=FrameServer,
        clock=datetime.now,
        signals=None,
        rng=random,
    ):
        self.config_dir = config_dir
        self.display = display
        self.once = once
        self.client_factory = client_factory
        self.system_reader = system_reader
        self.server_factory = server_factory
        self.clock = clock
        self.signals = signals or Signals()
        self.rng = rng
        self.client = None
        self.client_key = None
        self.stats = None
        self.last_success = None
        self.blocking_off_since = None
        self.refreshes = 0
        self.frame = None
        self.config = None
        self.lock = threading.Lock()
        self.server = None
        self.snapshot = None
        self.snapshot_taken = None
        self.snapshots = 0

    def run(self):
        next_render = None
        was_ok = None
        self.last_success = self.clock()
        try:
            while not self.signals.stopping:
                self.config = load_config(self.config_dir)
                logging.getLogger().setLevel(self.config.log_level)
                now = self.clock()
                with self.lock:
                    ok = self._fetch(now)
                    requested = self.signals.take_redraw()
                    due = next_render is None or now >= next_render or ok != was_ok or requested
                    frame = self._frame(now, ok, bool(self.refreshes % 2)) if due else None
                    if due:
                        next_render = self._next_render(now, ok)
                if frame:
                    self._show(frame)
                was_ok = ok
                if self.once or self.config.interval_minutes <= 0:
                    return
                self._serve()
                wait = (next_render - self.clock()).total_seconds()
                if not ok:
                    wait = min(wait, self.config.retry_seconds)
                self.signals.wait(max(wait, 1))
        finally:
            self._shutdown()

    def _next_render(self, now, ok):
        scheduled = now + timedelta(minutes=self.config.interval_minutes)
        settling = SETTLE_SECONDS - self.stats.uptime_seconds if ok else 0
        if settling > 0:
            return min(scheduled, now + timedelta(seconds=settling))
        return scheduled

    def _fetch(self, now):
        key = (self.config.api_url, self.config.password_file)
        if key != self.client_key:
            if self.client:
                self.client.close()
            self.client = self.client_factory(*key)
            self.client_key = key
        try:
            self.stats = self.client.fetch(now)
        except PiholeError as error:
            log.error('No data from Pi-hole: %s', error)
            return False
        self.last_success = now
        if self.stats.blocking:
            self.blocking_off_since = None
        elif not self.blocking_off_since:
            self.blocking_off_since = now
        return True

    def _overlay(self, ok):
        if not ok:
            return Overlay('warning', 'No data', f'since {self.last_success:%H:%M}')
        if not self.stats.blocking:
            until = self.stats.blocking_until
            detail = f'until {until:%H:%M}' if until else f'since {self.blocking_off_since:%H:%M}'
            return Overlay('shield', 'Blocking off', detail)
        return None

    def _frame(self, now, ok, alternate):
        return Frame(
            system=self.system_reader(),
            refreshed=now,
            pihole=self.stats,
            phrase=pick_phrase(self.config.phrases, self.stats.blocked, self.rng) if self.stats else FALLBACK_PHRASE,
            alternate=alternate,
            overlay=self._overlay(ok),
        )

    def _show(self, frame):
        self.display.show(render(frame, self.config.corner_padding), self.config.draw_inverted)
        self.frame = frame
        self.refreshes += 1
        log.info('Rendered at %s', frame.refreshed.strftime('%H:%M:%S'))

    def png(self):
        with self.lock:
            now = self.clock()
            if not self.snapshot or (now - self.snapshot_taken).total_seconds() >= self.config.http_max_age_seconds:
                frame = self._frame(now, self._fetch(now), bool(self.snapshots % 2))
                buffer = io.BytesIO()
                render(frame).to_rgb(SNAPSHOT_SCALE).save(buffer, 'PNG')
                self.snapshot = buffer.getvalue()
                self.snapshot_taken = now
                self.snapshots += 1
            return self.snapshot

    def _serve(self):
        port = self.config.http_port
        if self.server and self.server.port != port:
            self.server.close()
            self.server = None
        if port and not self.server:
            try:
                self.server = self.server_factory(port, self.png)
            except OSError as error:
                log.error('Cannot serve the screen on port %s: %s', port, error)

    def _shutdown(self):
        if self.server:
            self.server.close()
        if self.frame and not self.once and self.config.interval_minutes > 0:
            stopped = Overlay('pause', 'Stopped', self.clock().strftime('%d-%m %H:%M'))
            try:
                canvas = render(replace(self.frame, overlay=stopped), self.config.corner_padding)
                self.display.show(canvas, self.config.draw_inverted)
            except Exception:
                log.exception('Could not draw the stopped frame')
        if self.client:
            self.client.close()
