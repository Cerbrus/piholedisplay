import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)

PATH = '/screen.png'
REFRESH = 'refresh=1'


def handler(produce):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path, _, query = self.path.partition('?')
            if path != PATH:
                self.send_error(404)
                return
            try:
                image = produce(REFRESH in query.split('&'))
            except Exception:
                log.exception('Could not render the screen')
                self.send_error(500)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(image)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(image)

        def log_message(self, format, *args):
            log.debug(format, *args)

    return Handler


class FrameServer:
    def __init__(self, port, produce):
        self.httpd = ThreadingHTTPServer(('', port), handler(produce))
        self.port = self.httpd.server_address[1]
        self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        log.info('Serving the screen on port %s', self.port)

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
