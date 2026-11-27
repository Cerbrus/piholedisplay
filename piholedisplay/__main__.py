import argparse
import logging
import signal
import threading
from pathlib import Path

from .app import App
from .demo import write_demo
from .display import EpaperDisplay, PngDisplay


def main(argv=None):
    parser = argparse.ArgumentParser(prog='piholedisplay', description='Pi-hole statistics on a Waveshare 2.13 inch e-paper display')
    parser.add_argument('--config-dir', type=Path, default=Path(__file__).resolve().parent.parent, help='folder holding config.json')
    parser.add_argument('--preview', type=Path, metavar='FILE', help='render once with live data to a PNG file, without the display')
    parser.add_argument('--demo', type=Path, metavar='DIR', help='write demo screens, icon images and icons.md, without Pi-hole or display')
    args = parser.parse_args(argv)

    if args.demo:
        write_demo(args.demo)
        return

    logging.basicConfig(format='%(levelname)s %(name)s: %(message)s')
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())

    display = PngDisplay(args.preview) if args.preview else EpaperDisplay()
    App(args.config_dir, display, once=bool(args.preview), stop=stop).run()


if __name__ == '__main__':
    main()
