#!/usr/bin/env bash
# Halcyon — shared shell helpers.
#
# Sourced by every script in this repository. Provides logging, guarded
# execution (dry-run), and small predicates. It must stay dependency-free:
# the installer sources this before any packages have been installed.
#
# shellcheck shell=bash

# Guard against double-sourcing; every helper below is idempotent anyway,
# but re-running the readonly assignments would abort a `set -e` script.
if [[ -n "${HALCYON_COMMON_SH_LOADED:-}" ]]; then
	return 0
fi
HALCYON_COMMON_SH_LOADED=1

# ── Paths ──────────────────────────────────────────────────────────────

HALCYON_REPO_ROOT="${HALCYON_REPO_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}"
export HALCYON_REPO_ROOT

: "${XDG_CONFIG_HOME:=$HOME/.config}"
: "${XDG_DATA_HOME:=$HOME/.local/share}"
: "${XDG_STATE_HOME:=$HOME/.local/state}"
: "${XDG_CACHE_HOME:=$HOME/.cache}"
export XDG_CONFIG_HOME XDG_DATA_HOME XDG_STATE_HOME XDG_CACHE_HOME

HALCYON_CONFIG_DIR="${HALCYON_CONFIG_DIR:-$XDG_CONFIG_HOME/halcyon}"
HALCYON_DATA_DIR="${HALCYON_DATA_DIR:-$XDG_DATA_HOME/halcyon}"
HALCYON_STATE_DIR="${HALCYON_STATE_DIR:-$XDG_STATE_HOME/halcyon}"
HALCYON_CACHE_DIR="${HALCYON_CACHE_DIR:-$XDG_CACHE_HOME/halcyon}"
HALCYON_BACKUP_DIR="${HALCYON_BACKUP_DIR:-$HALCYON_STATE_DIR/backups}"
HALCYON_GENERATED_DIR="${HALCYON_GENERATED_DIR:-$HALCYON_CONFIG_DIR/generated}"
export HALCYON_CONFIG_DIR HALCYON_DATA_DIR HALCYON_STATE_DIR HALCYON_CACHE_DIR
export HALCYON_BACKUP_DIR HALCYON_GENERATED_DIR

# ── Output ─────────────────────────────────────────────────────────────

# Colour only when stdout is a terminal and the user has not opted out.
if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-dumb}" != "dumb" ]]; then
	C_RESET=$'\033[0m'
	C_DIM=$'\033[2m'
	C_BOLD=$'\033[1m'
	C_RED=$'\033[31m'
	C_GREEN=$'\033[32m'
	C_YELLOW=$'\033[33m'
	C_BLUE=$'\033[34m'
	C_CYAN=$'\033[36m'
else
	C_RESET='' C_DIM='' C_BOLD='' C_RED='' C_GREEN='' C_YELLOW='' C_BLUE='' C_CYAN=''
fi
export C_RESET C_DIM C_BOLD C_RED C_GREEN C_YELLOW C_BLUE C_CYAN

HALCYON_LOG_FILE="${HALCYON_LOG_FILE:-}"

_log_raw() {
	[[ -n "$HALCYON_LOG_FILE" ]] || return 0
	# Bash reports a failed redirection itself, before the command's own
	# stderr redirection can suppress it — so check the directory first
	# rather than trying to silence the message afterwards.
	[[ -d "$(dirname -- "$HALCYON_LOG_FILE")" ]] || return 0
	printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$HALCYON_LOG_FILE" 2>/dev/null || true
}

log_info() { printf '%s\n' "${C_BLUE}··${C_RESET} $*"; _log_raw "INFO  $*"; }
log_ok() { printf '%s\n' "${C_GREEN}✓${C_RESET}  $*"; _log_raw "OK    $*"; }
log_warn() { printf '%s\n' "${C_YELLOW}!${C_RESET}  $*" >&2; _log_raw "WARN  $*"; }
log_error() { printf '%s\n' "${C_RED}✗${C_RESET}  $*" >&2; _log_raw "ERROR $*"; }
log_step() { printf '\n%s\n' "${C_BOLD}${C_CYAN}▸ $*${C_RESET}"; _log_raw "STEP  $*"; }
log_debug() {
	[[ -n "${HALCYON_DEBUG:-}" ]] || return 0
	printf '%s\n' "${C_DIM}   $*${C_RESET}" >&2
	_log_raw "DEBUG $*"
}

die() {
	log_error "$*"
	exit 1
}

# ── Dry-run aware execution ────────────────────────────────────────────

# HALCYON_DRY_RUN=1 makes `run` print instead of execute. Every mutating
# action in the installer goes through this, which is what makes
# `./install.sh --dry-run` trustworthy rather than aspirational.
run() {
	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		printf '%s\n' "${C_DIM}   would run:${C_RESET} $*"
		return 0
	fi
	log_debug "run: $*"
	"$@"
}

# Same, but for shell snippets that need redirection or pipes.
run_sh() {
	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		printf '%s\n' "${C_DIM}   would run:${C_RESET} $*"
		return 0
	fi
	log_debug "run_sh: $*"
	bash -c "$*"
}

# ── Predicates ─────────────────────────────────────────────────────────

has() { command -v "$1" >/dev/null 2>&1; }

is_root() { [[ "$(id -u)" -eq 0 ]]; }

# Prefix for commands needing root. Empty when already root, `sudo` when
# available, and a hard failure otherwise — silently skipping privileged
# steps would leave a half-installed system.
sudo_prefix() {
	if is_root; then
		printf ''
	elif has sudo; then
		printf 'sudo'
	elif has doas; then
		printf 'doas'
	else
		return 1
	fi
}

confirm() {
	local prompt="${1:-Continue?}" reply
	if [[ -n "${HALCYON_ASSUME_YES:-}" ]]; then
		return 0
	fi
	if [[ ! -t 0 ]]; then
		log_warn "Not a terminal and --yes was not passed; assuming no for: $prompt"
		return 1
	fi
	read -r -p "$(printf '%s' "${C_BOLD}?${C_RESET} $prompt [y/N] ")" reply
	[[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

timestamp() { date +%Y%m%d-%H%M%S; }

# Ensure a directory exists, honouring dry-run.
ensure_dir() {
	local dir
	for dir in "$@"; do
		[[ -d "$dir" ]] && continue
		run mkdir -p "$dir"
	done
}

# Print the version of a tool in `major.minor.patch` form, or nothing.
tool_version() {
	local tool="$1"
	has "$tool" || return 1
	"$tool" --version 2>&1 | head -n1 |
		grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1
}

# Compare dotted versions: `version_ge 0.56.2 0.56` is true.
version_ge() {
	[[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]
}
