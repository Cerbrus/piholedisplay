import io
import json
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from piholedisplay.pihole import PiholeClient, PiholeError, parse_stats, parse_update, queries_per_minute

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'pihole.json').read_text())
NOW = datetime(2026, 11, 27, 12, 0)


def stats(**overrides):
    data = {**FIXTURE, **overrides}
    return parse_stats(data['stats/summary'], data['history'], data['dns/blocking'], data['info/messages/count'], data['info/version'], NOW)


def test_parse_stats_reads_the_summary():
    parsed = stats()

    assert parsed.blocked == 12431
    assert parsed.total == 67512
    assert round(parsed.percent_blocked, 1) == 18.4
    assert parsed.clients == 23
    assert parsed.blocklist_size == 1243118
    assert parsed.blocklist_updated == datetime.fromtimestamp(1795316342)
    assert parsed.messages == 1
    assert parsed.blocking
    assert parsed.blocking_until is None
    assert parsed.update is None


def test_parse_stats_keeps_history_in_time_order():
    reversed_history = {'history': list(reversed(FIXTURE['history']['history']))}

    assert stats(history=reversed_history).history == stats().history
    assert len(stats().history) == 145
    first = FIXTURE['history']['history'][0]
    assert stats().history[0] == (first['total'], first['blocked'])


def test_queries_per_minute_uses_the_last_complete_bucket():
    history = [
        {'timestamp': 0, 'total': 999},
        {'timestamp': 600, 'total': 470},
        {'timestamp': 1200, 'total': 3},
    ]

    assert queries_per_minute(history) == 47
    assert queries_per_minute(history[:1]) == 0


def test_blocking_timer_becomes_a_time():
    parsed = stats(**{'dns/blocking': {'blocking': 'disabled', 'timer': 900}})

    assert not parsed.blocking
    assert parsed.blocking_until == NOW + timedelta(minutes=15)


def test_update_is_the_remote_version_of_the_first_outdated_component():
    version = {
        'core': {'local': {'version': 'v6.6'}, 'remote': {'version': 'v6.6'}},
        'web': {'local': {'version': 'v6.6.1'}, 'remote': {'version': 'v6.7'}},
        'ftl': {'local': {'version': 'v6.9'}, 'remote': {'version': 'v6.10'}},
        'docker': {'local': None, 'remote': None},
    }

    assert parse_update(version) == 'v6.7'
    assert parse_update(FIXTURE['info/version']['version']) is None
    assert parse_update({'core': {'local': {'version': 'v6.6'}, 'remote': {'version': None}}}) is None


class Response:
    def __init__(self, status, body):
        self.status = status
        self.payload = json.dumps(body).encode() if body is not None else b''

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeApi:
    def __init__(self):
        self.calls = []
        self.valid_sids = set()
        self.logins = 0

    def __call__(self, request, timeout):
        path = request.full_url.split('/api/', 1)[1]
        sid = request.get_header('X-ftl-sid')
        self.calls.append((request.get_method(), path, sid))
        if path == 'auth' and request.get_method() == 'POST':
            assert json.loads(request.data) == {'password': 'secret'}
            self.logins += 1
            sid = f'sid-{self.logins}'
            self.valid_sids.add(sid)
            return Response(200, {'session': {'valid': True, 'sid': sid}})
        if sid not in self.valid_sids:
            raise urllib.error.HTTPError(request.full_url, 401, 'Unauthorized', {}, io.BytesIO(b'{"error": {"key": "unauthorized"}}'))
        if path == 'auth':
            self.valid_sids.discard(sid)
            return Response(204, None)
        return Response(200, FIXTURE[path])


@pytest.fixture
def password_file(tmp_path):
    path = tmp_path / 'cli_pw'
    path.write_text('secret\n')
    return path


def test_client_logs_in_once_and_reuses_the_session(password_file):
    api = FakeApi()
    client = PiholeClient('http://localhost/api/', password_file, opener=api)

    client.fetch(NOW)
    client.fetch(NOW)

    assert api.logins == 1
    assert {sid for _, path, sid in api.calls if path != 'auth'} == {'sid-1'}


def test_client_logs_in_again_when_the_session_expired(password_file):
    api = FakeApi()
    client = PiholeClient('http://localhost/api', password_file, opener=api)
    client.fetch(NOW)
    api.valid_sids.clear()

    assert client.fetch(NOW).total == 67512
    assert api.logins == 2


def test_client_logs_out_on_close(password_file):
    api = FakeApi()
    client = PiholeClient('http://localhost/api', password_file, opener=api)
    client.fetch(NOW)

    client.close()

    assert api.calls[-1] == ('DELETE', 'auth', 'sid-1')
    assert not api.valid_sids
    assert client.sid is None


def test_client_reports_an_unreachable_api(password_file):
    def refuse(request, timeout):
        raise urllib.error.URLError('connection refused')

    with pytest.raises(PiholeError):
        PiholeClient('http://localhost/api', password_file, opener=refuse).fetch(NOW)


def test_client_reports_a_missing_password_file(tmp_path):
    with pytest.raises(PiholeError):
        PiholeClient('http://localhost/api', tmp_path / 'missing', opener=FakeApi()).fetch(NOW)


def test_client_reports_an_unexpected_response(password_file):
    api = FakeApi()

    def broken(request, timeout):
        response = api(request, timeout)
        if request.full_url.endswith('stats/summary'):
            return Response(200, {'queries': {}})
        return response

    with pytest.raises(PiholeError):
        PiholeClient('http://localhost/api', password_file, opener=broken).fetch(NOW)
