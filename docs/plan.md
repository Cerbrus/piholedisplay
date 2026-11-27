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
- The screen as a picture over HTTP, for a camera entity in Home Assistant. Drawn on request with fresh numbers, at most once per 2 minutes, with the refresh time against the right margin.

## Verified on the Pi (2026-11-27)

The Pi was reinstalled with Raspberry Pi OS Lite 32-bit (Debian 13, Python 3.13, Pillow 11.1) on a second SD card; the old card is the rollback. A `dnsmasq` on another Pi stood in on the Pi-hole's addresses meanwhile, so the house lost DNS for under 30 seconds each way.

- `install.sh` ran clean on the fresh system.
- The display draws, and signs in to the live API with the CLI password.
- The `deploy` job moves the `deploy` branch after every green run on `master`, and `deploy/update.sh` on the Pi picked up three deploys by itself.
- The "Stopped" frame shows on the panel when the service stops.
- After a reboot the network settings, Pi-hole, the display and the update timer come back by themselves.
- The query history of the old install was copied over and the queries of the new install merged into it.

Found on the real hardware and fixed:

- `rpi-lgpio` refuses to claim the SPI chip-select pin (GPIO 8) that the vendored `epdif.py` set up as an output, because the kernel's SPI driver owns it. The line is removed; the SPI driver toggles chip select by itself.
- The frame drawn right after a boot showed 0%: FTL answers before it has loaded its history. A frame drawn within 10 minutes after FTL started is now redrawn when those 10 minutes are over.
- The CLI password session is not strictly read-only: it can delete diagnostics messages.

## Not verified yet

- **The "No data" and "Blocking off" overlays on the real panel.** Seen as PNG only.

## Later

- **Panel wear at the edges.** The panel shows degradation around the edges, most where the old layout drew a black border for years. The new layout has no border, but its three lines, the icons and the footer also never move. To look into: a full clearing cycle (all white, all black, all red) once a night, shifting the whole picture by a pixel now and then, and whether the damage is reversible with a few clearing cycles at all.
