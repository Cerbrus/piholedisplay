#!/bin/bash
set -euo pipefail

BRANCH=deploy

main() {
    local dir owner
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    owner="$(stat -c %U "$dir")"

    if [ "$(id -u)" -ne 0 ]; then
        echo "Run with sudo: sudo ./install.sh" >&2
        exit 1
    fi

    apt-get update
    apt-get install -y git python3-pil python3-spidev python3-rpi-lgpio

    raspi-config nonint do_spi 0
    usermod -aG pihole,spi,gpio,video "$owner"

    runuser -u "$owner" -- git -C "$dir" fetch --quiet origin "$BRANCH"
    runuser -u "$owner" -- git -C "$dir" checkout --quiet -B "$BRANCH" "origin/$BRANCH"

    "$dir/deploy/install-units.sh"
    systemctl enable --now pihole-display.service pihole-display-update.timer

    echo "Installed. Follow the display with: journalctl -fu pihole-display"
}

main "$@"
