#!/usr/bin/env bash
# Canonical Halcyon source-archive builder. CI and local releases use this
# exact script so release archives have the same layout and metadata.
# Usage: ./.build.sh <version> <outdir>
set -euo pipefail
label="${1:?usage: .build.sh <version> <outdir>}"
outdir="${2:?usage: .build.sh <version> <outdir>}"
case "$label" in ""|*[!A-Za-z0-9._-]*) echo "build: invalid version '$label'" >&2; exit 2;; esac
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$outdir"
outdir="$(cd "$outdir" && pwd)"
stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT
mkdir "$stage/halcyon-$label"
tar -C "$root" --exclude=.git --exclude=.github --exclude=__pycache__ --exclude='*.pyc' -cf - . | tar -C "$stage/halcyon-$label" -xf -
# Embed build provenance for the updater and diagnostics.
printf '%s\n' "$label" > "$stage/halcyon-$label/BUILD_VERSION"
if git -C "$root" rev-parse HEAD >/dev/null 2>&1; then
  git -C "$root" rev-parse HEAD > "$stage/halcyon-$label/BUILD_COMMIT"
fi
tar -C "$stage" -czf "$outdir/halcyon-$label.tar.gz" "halcyon-$label"
(cd "$outdir" && sha256sum "halcyon-$label.tar.gz" > "halcyon-$label.tar.gz.sha256")
echo "$outdir/halcyon-$label.tar.gz"
