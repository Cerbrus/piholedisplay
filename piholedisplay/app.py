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

log = logging.getLogger(__name__)

FALLBACK_PHRASE = 'Blocked'
SETTLE_SECONDS = 600


def pick_phrase(phrases, blocked, rng=random):
    fitting = [phrase for phrase in phrases if phrase_fits(blocked, phrase)]
    return rng.choice(fitting) if fitting else FALLBACK_PHRASE


class App:
    def __init__(
        self,
        config_dir,
        display,
        once=False,
        client_factory=PiholeClient,
        system_reader=read_system,
        clock=datetime.now,
        stop=None,
        rng=random,
    ):
        self.config_dir = config_dir
        self.display = display
        self.once = once
        self.client_factory = client_factory
        self.system_reader = system_reader
        self.clock = clock
        self.stop = stop or threading.Event()
        self.rng = rng
        self.client = None
        self.client_key = None
        self.stats = None
        self.last_success = None
        self.blocking_off_since = None
        self.refreshes = 0
        self.frame = None
        self.config = None

    def run(self):
        next_render = None
        was_ok = None
        self.last_success = self.clock()
        try:
            while not self.stop.is_set():
                self.config = load_config(self.config_dir)
                logging.getLogger().setLevel(self.config.log_level)
                now = self.clock()
                ok = self._fetch(now)
                if next_render is None or now >= next_render or ok != was_ok:
                    self._show(self._frame(now, ok))
                    next_render = self._next_render(now, ok)
                was_ok = ok
                if self.once or self.config.interval_minutes <= 0:
                    return
                wait = (next_render - self.clock()).total_seconds()
                if not ok:
                    wait = min(wait, self.config.retry_seconds)
                self.stop.wait(max(wait, 1))
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

    def _frame(self, now, ok):
        return Frame(
            system=self.system_reader(),
            refreshed=now,
            pihole=self.stats,
            phrase=pick_phrase(self.config.phrases, self.stats.blocked, self.rng) if self.stats else FALLBACK_PHRASE,
            alternate=bool(self.refreshes % 2),
            overlay=self._overlay(ok),
        )

    def _show(self, frame):
        self.display.show(render(frame), self.config.draw_inverted)
        self.frame = frame
        self.refreshes += 1
        log.info('Rendered at %s', frame.refreshed.strftime('%H:%M:%S'))

    def _shutdown(self):
        if self.frame and not self.once and self.config.interval_minutes > 0:
            stopped = Overlay('pause', 'Stopped', self.clock().strftime('%d-%m %H:%M'))
            try:
                self.display.show(render(replace(self.frame, overlay=stopped)), self.config.draw_inverted)
            except Exception:
                log.exception('Could not draw the stopped frame')
        if self.client:
            self.client.close()
