# Rebuild plan

Decided on 2026-11-27. The display had been dark since 2026-11-21, when Pi-hole was updated to v6 and the v5 API the old Python 2 code called disappeared.

## Decisions

1. **Target**: reinstall the Pi (a Pi Zero W, on end-of-life Raspbian 10) with current Raspberry Pi OS Lite 32-bit. The code targets Python 3.11 and newer only.
2. **Deploy**: no Docker; the board is ARMv6 with 430 MB of memory. A git checkout on the Pi follows the `deploy` branch through a systemd timer.
3. **CI**: GitHub Actions runs `ruff`, `pytest` and a demo render on every push and pull request. A green run on `master` fast-forwards `deploy`.
4. **Authentication**: a Pi-hole v6 API session with the CLI password from `/etc/pihole/cli_pw`. No secret is stored with the display.
5. **Service**: one systemd unit, logging to the journal, an update timer, `install.sh` for a fresh Pi, a "Stopped" frame on shutdown.
6. **Screen**: as much information as fits, icons in place of labels, state overlays on the chart. The layout was settled in eight mockup rounds; `docs/screens` shows the result.

## Deviation

Decision 2 named a Python virtual environment. There is none: Pillow, `spidev` and `rpi-lgpio` come from apt, and nothing else is needed at runtime. That avoids compiling Pillow on a Pi Zero.

## Done

- Python 3 package `piholedisplay` with the v6 API client, system statistics, renderer, refresh loop and PNG output.
- Tests, linter configuration and the GitHub Actions workflow.
- systemd units, `deploy/update.sh` and `install.sh`.
- Icon legend generated from the icon bitmaps.

## Verified on the Pi (2026-11-27)

The Pi was reinstalled with Raspberry Pi OS Lite 32-bit (Debian 13, Python 3.13, Pillow 11.1) on a second SD card; the old card is the rollback.

- `install.sh` ran clean on the fresh system.
- The display draws, and signs in to the live API with the CLI password.
- The `deploy` job created the `deploy` branch after the first green run on `master`.
- `rpi-lgpio` needed one change in the vendored driver: `epdif.py` set up the SPI chip-select pin (GPIO 8) as an output. The kernel's SPI driver owns that pin, and `lgpio` refuses to claim it where `RPi.GPIO` did not check. The line is removed; the SPI driver toggles chip select by itself.

## Not verified yet

- **`deploy/update.sh`.** It passes `shellcheck`; the first deploy after the reinstall is its first real run.
- **CLI password sessions being read-only**, as the Pi-hole documentation describes them.
- **The "Stopped" frame and the overlays on the real panel.** Seen as PNG only.

## Later

- **Panel wear at the edges.** The panel shows degradation around the edges, most where the old layout drew a black border for years. The new layout has no border, but its three lines, the icons and the footer also never move. To look into: a full clearing cycle (all white, all black, all red) once a night, shifting the whole picture by a pixel now and then, and whether the damage is reversible with a few clearing cycles at all.
