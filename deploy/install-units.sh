#!/bin/bash
set -euo pipefail

main() {
    local dir owner unit
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    owner="$(stat -c %U "$dir")"

    for unit in pihole-display.service pihole-display-update.service pihole-display-update.timer; do
        sed -e "s|@DIR@|$dir|g" -e "s|@USER@|$owner|g" "$dir/deploy/$unit" > "/etc/systemd/system/$unit"
    done
    systemctl daemon-reload
}

main "$@"
