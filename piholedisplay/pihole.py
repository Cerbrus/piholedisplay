import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from .model import PiholeStats

log = logging.getLogger(__name__)

COMPONENTS = ('core', 'web', 'ftl')


class PiholeError(Exception):
    pass


def parse_update(version):
    for component in COMPONENTS:
        entry = version.get(component) or {}
        local = (entry.get('local') or {}).get('version')
        remote = (entry.get('remote') or {}).get('version')
        if local and remote and local != remote:
            return remote
    return None


def queries_per_minute(history):
    if len(history) < 2:
        return 0
    previous, current = history[-2], history[-1]
    minutes = (current['timestamp'] - previous['timestamp']) / 60
    return round(previous['total'] / minutes) if minutes > 0 else 0


def parse_stats(summary, history, blocking, messages, version, ftl, now):
    entries = sorted(history['history'], key=lambda entry: entry['timestamp'])
    queries, gravity = summary['queries'], summary['gravity']
    updated = gravity.get('last_update')
    timer = blocking.get('timer')
    return PiholeStats(
        blocked=queries['blocked'],
        total=queries['total'],
        percent_blocked=queries['percent_blocked'],
        clients=summary['clients']['active'],
        blocklist_size=gravity['domains_being_blocked'],
        blocklist_updated=datetime.fromtimestamp(updated) if updated else None,
        queries_per_minute=queries_per_minute(entries),
        history=tuple((entry['total'], entry['blocked']) for entry in entries),
        blocking=blocking['blocking'] != 'disabled',
        blocking_until=now + timedelta(seconds=timer) if timer else None,
        messages=messages['count'],
        update=parse_update(version['version']),
        uptime_seconds=ftl['ftl']['uptime'] / 1000,
    )


class PiholeClient:
    def __init__(self, api_url, password_file, timeout=10, opener=urllib.request.urlopen):
        self.api_url = api_url.rstrip('/')
        self.password_file = Path(password_file) if password_file else None
        self.timeout = timeout
        self.opener = opener
        self.sid = None

    def fetch(self, now):
        try:
            return parse_stats(
                self._get('stats/summary'),
                self._get('history'),
                self._get('dns/blocking'),
                self._get('info/messages/count'),
                self._get('info/version'),
                self._get('info/ftl'),
                now,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise PiholeError(f'unexpected API response: {error!r}') from error

    def close(self):
        if not self.sid:
            return
        try:
            self._request('DELETE', 'auth')
        except PiholeError as error:
            log.warning('Logout failed: %s', error)
        self.sid = None

    def _get(self, path):
        if not self.sid:
            self._login()
        status, body = self._request('GET', path)
        if status == 401:
            self.sid = None
            self._login()
            status, body = self._request('GET', path)
        if status != 200:
            raise PiholeError(f'GET {path} returned {status}')
        return body

    def _login(self):
        if not self.password_file:
            return
        try:
            password = self.password_file.read_text().strip()
        except OSError as error:
            raise PiholeError(f'cannot read {self.password_file}: {error}') from error
        status, body = self._request('POST', 'auth', {'password': password})
        session = (body or {}).get('session') or {}
        if status != 200 or not session.get('valid'):
            raise PiholeError(f'login returned {status}')
        self.sid = session.get('sid')

    def _request(self, method, path, body=None):
        request = urllib.request.Request(
            f'{self.api_url}/{path}',
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={'Content-Type': 'application/json'},
        )
        if self.sid:
            request.add_header('X-FTL-SID', self.sid)
        try:
            with self.opener(request, timeout=self.timeout) as response:
                return response.status, _decode(response.read())
        except urllib.error.HTTPError as error:
            return error.code, _decode(error.read())
        except (OSError, ValueError) as error:
            raise PiholeError(f'{method} {path} failed: {error}') from error


def _decode(payload):
    return json.loads(payload) if payload else None
