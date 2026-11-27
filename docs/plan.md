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

## Not verified yet

- **On the display.** Everything was rendered to PNG; the code has not run on the Pi. The vendored Waveshare driver is unchanged, and `rpi-lgpio` standing in for `RPi.GPIO` under it is untested.
- **Against the live API.** The client is tested against the response shapes read from the Pi-hole on 2026-11-27, not against the running API.
- **`install.sh` and `deploy/update.sh`.** They pass `shellcheck` in CI but have never run.
- **The `deploy` job.** Lint, tests and demo render ran green on the pull request; the fast-forward of `deploy` only runs on `master`.
- **CLI password sessions being read-only**, as the Pi-hole documentation describes them.

## Still to do

1. Push the branch, get CI green, merge to `master`; check that `deploy` appears.
2. Reinstall the Pi. Pi-hole on it is the only DNS server the modem hands out, so the whole house loses DNS while it is down:
   - Export a Teleporter backup and copy `/etc/pihole/pihole.toml` off the Pi.
   - Flash Raspberry Pi OS Lite 32-bit, same host name, same address (192.168.1.104 is bound in the modem), SSH key.
   - Install Pi-hole, import the Teleporter backup, check the `misc.dnsmasq_lines` split-horizon entries.
   - Clone this repository and run `sudo ./install.sh`.
3. Watch the first refreshes with `journalctl -fu pihole-display` and tick off the list above.
