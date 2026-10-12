#!/usr/bin/env bash
# Builds a Halcyon release archive: halcyon-<label>.tar.gz and halcyon-<label>.tar.gz.sha256 in <outdir>.
# Used by .github/workflows/stable.yml and nightly.yml, and runnable by hand.
#
#   scripts/release.sh <label> <outdir>
#
# <label> names the archive and the folder inside it, so it may only use letters, digits, '.', '_' and '-'.
# The archive holds the working tree as it is: the git history and the CI configuration are left out.
set -euo pipefail

label="${1:?usage: release.sh <label> <outdir>}"
outdir="${2:?usage: release.sh <label> <outdir>}"

case "$label" in
    ""|*[!A-Za-z0-9._-]*) echo "release.sh: bad label '$label'" >&2; exit 1 ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$outdir"
outdir="$(cd "$outdir" && pwd)"

stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT

mkdir "$stage/halcyon-$label"
tar -C "$root" --exclude=.git --exclude=.github --exclude=__pycache__ --exclude='*.pyc' -cf - . \
    | tar -C "$stage/halcyon-$label" -xf -

tar -C "$stage" -czf "$outdir/halcyon-$label.tar.gz" "halcyon-$label"
(cd "$outdir" && sha256sum "halcyon-$label.tar.gz" > "halcyon-$label.tar.gz.sha256")

echo "$outdir/halcyon-$label.tar.gz"
