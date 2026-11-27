#!/bin/bash
set -euo pipefail

BRANCH=deploy

main() {
    local dir owner
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    owner="$(stat -c %U "$dir")"

    as_owner() {
        runuser -u "$owner" -- git -C "$dir" "$@"
    }

    as_owner fetch --quiet origin "$BRANCH"
    if [ "$(as_owner rev-parse HEAD)" = "$(as_owner rev-parse "origin/$BRANCH")" ]; then
        exit 0
    fi

    as_owner reset --quiet --hard "origin/$BRANCH"
    echo "Updated to $(as_owner rev-parse --short HEAD)"
    "$dir/deploy/install-units.sh"
    systemctl restart pihole-display.service
    exit 0
}

main "$@"
