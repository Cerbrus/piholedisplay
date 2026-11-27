# CLAUDE.md

Renders Pi-hole and system statistics to a Waveshare 2.13 inch three-colour (black, white, red) e-paper HAT on a Raspberry Pi Zero W. `README.md` covers installing it on the Pi, `docs/configuration.md` documents every `config.json` setting, `docs/plan.md` holds the decisions behind the rebuild and what is still unverified.

## Running

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
python -m piholedisplay --demo docs            # redraw docs/screens, docs/icons, docs/icons.md
python -m piholedisplay --preview preview.png  # one frame with live Pi-hole data, no display
python -m piholedisplay                        # the real thing, on the Pi only
```

Tests, linter and the demo render run anywhere with Python 3.11+ and Pillow. Only the bare `python -m piholedisplay` needs the Pi (SPI, GPIO).

## Layout

```
piholedisplay/__main__.py  command line: run, --preview, --demo
piholedisplay/app.py       App: refresh loop, retry while Pi-hole is down, overlays, "Stopped" frame on exit
piholedisplay/pihole.py    PiholeClient: v6 API session, parse_stats turns responses into PiholeStats
piholedisplay/system.py    host, IP, memory, disk, temperature, uptime, WiFi, under-voltage from /proc and /sys
piholedisplay/screen.py    render(frame): the whole layout, number formats, chart bucketing
piholedisplay/canvas.py    Canvas: a black and a red 1-bit image, text, icons, RGB export
piholedisplay/icons.py     9 x 9 icon bitmaps with their meaning
piholedisplay/model.py     PiholeStats, SystemStats, Overlay, Frame
piholedisplay/display.py   EpaperDisplay (the HAT) and PngDisplay (a file)
piholedisplay/demo.py      fake frames for every state, icon legend generator
piholedisplay/config.py    config.json with config.local.json laid over it
piholedisplay/lib/         Waveshare driver (epd2in13b.py, epdif.py): vendored, leave alone
piholedisplay/fonts/       DejaVu Sans Mono, bundled so every machine renders the same
deploy/                    systemd unit templates, update.sh (timer), install-units.sh
install.sh                 one-time setup on the Pi
tests/                     pytest; tests/fixtures/pihole.json has real v6 response shapes with made-up numbers
```

## How it works

- `App.run` loops: read the config, fetch Pi-hole statistics, draw when the interval has passed or when Pi-hole went down or came back, then wait. While Pi-hole does not answer it retries every `retry_seconds` without redrawing: an e-paper refresh takes about 15 seconds of flashing.
- `render(frame)` is a pure function from a `Frame` to a `Canvas`. Everything on screen is addressed as `'black'` or `'red'`; the two 1-bit layers must never share a pixel (a test checks this).
- Every second refresh has `frame.alternate` set, which swaps the two lower grid rows.
- Overlays, in order of precedence: "Stopped" (on exit), "No data" (fetch failed), "Blocking off".
- The canvas is landscape, 212 x 104. `EpaperDisplay` rotates it for the portrait panel; `draw_inverted` picks the direction.
- Deploy is pull-based: CI fast-forwards the `deploy` branch after a green run on `master`, `deploy/update.sh` on the Pi resets the checkout to it and restarts the service.

## Things to know before changing code

- **GPIO goes through `rpi-lgpio`**, the `RPi.GPIO` stand-in on current Raspberry Pi OS. It refuses pins the kernel already owns: the vendored `epdif.py` differs from upstream by one removed line, the setup of the SPI chip-select pin.
- **Python 3.11+, Pillow 9.4+** (what Raspberry Pi OS Bookworm ships). There are no other runtime dependencies; HTTP goes through `urllib`.
- **Pi-hole API is v6**: `POST /api/auth` with the password from `/etc/pihole/cli_pw`, then `stats/summary`, `history`, `dns/blocking`, `info/messages/count`, `info/version` with the `X-FTL-SID` header. Pi-hole allows 16 sessions: the client keeps one, logs in again on a 401 and logs out on exit.
- **Layout is pixel-exact and was agreed in mockup rounds.** After a change to `screen.py` or `icons.py`, run `--demo docs` and look at the pictures.
- Fonts load with Pillow's basic layout engine. With Raqm (the default on Linux) the same text is up to 8% wider than on Windows and the layout overflows; a test pins the advances.
- A new icon needs a `meaning`; `docs/icons.md` and `docs/icons/` are generated from it, and a test fails when they are stale.
- A phrase has to fit next to the blocked count; `phrase_fits` filters at draw time.
- `config.json` is replaced on every deploy. Machine-specific values go in `config.local.json` (gitignored).
- A changed or added setting is documented in `docs/configuration.md` in the same change.
- The shell scripts wrap their body in `main`, so bash has read the whole file before `update.sh` replaces it.
