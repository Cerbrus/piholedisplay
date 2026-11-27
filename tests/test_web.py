import urllib.error
import urllib.request

import pytest

from piholedisplay.web import PATH, REFRESH, FrameServer


def serve(produce):
    server = FrameServer(0, produce)
    return server, f'http://127.0.0.1:{server.port}'


def test_serves_the_produced_image():
    server, url = serve(lambda refresh: b'new' if refresh else b'png')
    try:
        with urllib.request.urlopen(f'{url}{PATH}?cache=1', timeout=5) as response:
            assert response.status == 200
            assert response.headers['Content-Type'] == 'image/png'
            assert response.read() == b'png'
    finally:
        server.close()


def test_refresh_asks_for_a_new_image():
    server, url = serve(lambda refresh: b'new' if refresh else b'png')
    try:
        with urllib.request.urlopen(f'{url}{PATH}?cache=1&{REFRESH}', timeout=5) as response:
            assert response.read() == b'new'
    finally:
        server.close()


def test_other_paths_are_not_found():
    server, url = serve(lambda refresh: b'png')
    try:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f'{url}/', timeout=5)
        assert error.value.code == 404
    finally:
        server.close()


def test_a_failed_render_answers_with_an_error():
    def fail(refresh):
        raise RuntimeError('broken')

    server, url = serve(fail)
    try:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f'{url}{PATH}', timeout=5)
        assert error.value.code == 500
    finally:
        server.close()
