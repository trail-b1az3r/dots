#!/usr/bin/env bash
# Halcyon — set a random wallpaper.
#
# A one-shot version of the rotation service, for a cron job, a keybind,
# or a login hook. Re-derives the palette, so the whole desktop changes
# colour with the picture.

set -Eeuo pipefail
# shellcheck source=scripts/lib/common.sh
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/common.sh"

has halcyon || die "halcyon is not on PATH."
exec halcyon wallpaper next
