#!/usr/bin/env bash
# Adds Halcyon's module to a NixOS configuration.nix, printing the result (the file itself is not touched):
#
#   edit-configuration.sh /etc/nixos/configuration.nix USER > new-configuration.nix
#
# The module goes first in the `imports = [` list (or into a new `imports` line when there is none), and
# `halcyon = { enable = true; user = "USER"; };` goes before the file's last closing brace. A file that already
# imports it comes out unchanged. Plain awk, since a fresh NixOS has no Python.
set -euo pipefail
file="$1"
user="$2"
if grep -q 'halcyon/halcyon\.nix' "$file"; then
  cat "$file"
  exit 0
fi
has_imports=0
grep -Eq '(^|[[:space:];{])imports[[:space:]]*=' "$file" && has_imports=1
last=$(grep -nE '^[[:space:]]*}[[:space:]]*$' "$file" | tail -1 | cut -d: -f1)
if [[ -z "$last" ]]; then
  echo "edit-configuration.sh: no closing brace on a line of its own in $file" >&2
  exit 1
fi
awk -v has_imports="$has_imports" -v last="$last" -v user="$user" '
  BEGIN { done = 0; waiting = 0 }
  {
    # The list may open on the line of `imports =` or on a later one (the default configuration.nix does that).
    if (has_imports && !done) {
      line = $0
      offset = 0
      if (!waiting && match(line, /imports[[:space:]]*=/)) {
        waiting = 1
        offset = RSTART + RLENGTH - 1
        line = substr(line, offset + 1)
      }
      if (waiting && (at = index(line, "[")) > 0) {
        at += offset
        $0 = substr($0, 1, at) " ./halcyon/halcyon.nix" substr($0, at + 1)
        done = 1
      }
    }
    if (NR == last) {
      print ""
      print "  # Halcyon (./setup install added this; see /etc/nixos/halcyon/halcyon.nix)."
      if (!has_imports) print "  imports = [ ./halcyon/halcyon.nix ];"
      print "  halcyon = { enable = true; user = \"" user "\"; };"
    }
    print
  }
' "$file"
