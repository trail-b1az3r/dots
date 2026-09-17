#!/usr/bin/env bash
# Halcyon — building the components a distribution does not package.
#
# Two things drive the design here:
#
#   * Nothing is compiled that a package manager can supply. Building
#     Quickshell against the wrong Qt is a crash at startup, and building
#     Hyprland from source on a machine that has a perfectly good package
#     is forty minutes nobody asked for.
#   * Every build is pinned. An unpinned `git clone` of a fast-moving
#     project is a different program on every install, and "works on my
#     machine" becomes "worked on my machine that day".
#
# shellcheck shell=bash

if [[ -n "${HALCYON_BUILD_SH_LOADED:-}" ]]; then
	return 0
fi
HALCYON_BUILD_SH_LOADED=1

# shellcheck source=scripts/lib/packages.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/packages.sh"

# Versions Halcyon is developed and tested against. Raised deliberately,
# never automatically.
HALCYON_QUICKSHELL_REF="${HALCYON_QUICKSHELL_REF:-v0.3.1}"
HALCYON_QUICKSHELL_REPO="${HALCYON_QUICKSHELL_REPO:-https://github.com/quickshell-mirror/quickshell.git}"

HALCYON_BUILD_ROOT="${HALCYON_BUILD_ROOT:-$HALCYON_CACHE_DIR/build}"
HALCYON_PREFIX="${HALCYON_PREFIX:-$HOME/.local}"

build_prepare() {
	ensure_dir "$HALCYON_BUILD_ROOT" "$HALCYON_PREFIX/bin"
}

# fetch_source <name> <repo> <ref> — clone or update, then check out the
# pinned ref. Returns the source directory on stdout.
fetch_source() {
	local name="$1" repo="$2" ref="$3"
	local dir="$HALCYON_BUILD_ROOT/$name"

	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		printf '%s' "$dir"
		return 0
	fi

	if [[ -d "$dir/.git" ]]; then
		git -C "$dir" fetch --tags --depth 1 origin "$ref" >/dev/null 2>&1 ||
			git -C "$dir" fetch --tags origin >/dev/null 2>&1 || true
	else
		rm -rf "$dir"
		git clone --depth 1 --branch "$ref" "$repo" "$dir" >/dev/null 2>&1 ||
			git clone "$repo" "$dir" >/dev/null 2>&1 ||
			die "Could not clone $repo"
	fi

	git -C "$dir" checkout --detach "$ref" >/dev/null 2>&1 ||
		die "$name has no ref $ref"

	printf '%s' "$dir"
}

# build_quickshell — compile and install Quickshell into ~/.local.
#
# Quickshell links against private Qt APIs, so it has to be rebuilt after
# a Qt update or it will crash on an ABI mismatch. The installer records
# the Qt version it built against; `check-deps.sh` compares.
build_quickshell() {
	local qt_version
	qt_version="$(qt_version_string)"

	log_step "Building Quickshell $HALCYON_QUICKSHELL_REF (Qt $qt_version)"

	if ! has cmake || ! has ninja; then
		die "cmake and ninja are needed to build Quickshell; install the @build group first."
	fi

	build_prepare
	local source
	source="$(fetch_source quickshell "$HALCYON_QUICKSHELL_REPO" "$HALCYON_QUICKSHELL_REF")"

	local -a flags=(
		-GNinja
		-B "$source/build"
		-S "$source"
		-DCMAKE_BUILD_TYPE=RelWithDebInfo
		-DCMAKE_INSTALL_PREFIX="$HALCYON_PREFIX"
		-DDISTRIBUTOR="Halcyon dotfiles"
		-DINSTALL_QML_PREFIX=lib/qt6/qml
	)

	# Features whose dependencies are commonly missing. Quickshell refuses
	# to configure when a feature is enabled without its libraries, so the
	# honest thing is to disable what is not there and say which.
	local -a disabled=()
	pkg_has libpipewire-0.3 || { flags+=(-DSERVICE_PIPEWIRE=OFF); disabled+=(pipewire); }
	pkg_has libpam || [[ -e /usr/include/security/pam_appl.h ]] ||
		{ flags+=(-DSERVICE_PAM=OFF); disabled+=(pam); }
	pkg_has polkit-agent-1 || { flags+=(-DSERVICE_POLKIT=OFF); disabled+=(polkit); }
	pkg_has gbm || { flags+=(-DSCREENCOPY=OFF); disabled+=(screencopy); }
	pkg_has xcb || { flags+=(-DX11=OFF); disabled+=(x11); }
	has jemalloc-config || pkg_has jemalloc || { flags+=(-DUSE_JEMALLOC=OFF); disabled+=(jemalloc); }
	pkg_has cpptrace || { flags+=(-DCRASH_HANDLER=OFF); disabled+=(crash-handler); }

	if ((${#disabled[@]} > 0)); then
		log_warn "Quickshell features disabled (missing libraries): ${disabled[*]}"
		log_info "Install the @quickshell-dev package group and re-run to enable them."
	fi

	run cmake "${flags[@]}" || die "Configuring Quickshell failed."
	run cmake --build "$source/build" --parallel "$(nproc 2>/dev/null || echo 2)" ||
		die "Building Quickshell failed."
	run cmake --install "$source/build" || die "Installing Quickshell failed."

	if [[ -z "${HALCYON_DRY_RUN:-}" ]]; then
		ensure_dir "$HALCYON_STATE_DIR"
		printf 'quickshell %s\nqt %s\nbuilt %s\n' \
			"$HALCYON_QUICKSHELL_REF" "$qt_version" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
			>"$HALCYON_STATE_DIR/quickshell-build"
	fi

	verify_binary "$HALCYON_PREFIX/bin/quickshell" || verify_binary "$HALCYON_PREFIX/bin/qs"
}

pkg_has() {
	has pkg-config || return 1
	pkg-config --exists "$1" 2>/dev/null
}

qt_version_string() {
	local tool
	for tool in qmake6 qmake-qt6 qmake; do
		if has "$tool"; then
			"$tool" -query QT_VERSION 2>/dev/null && return 0
		fi
	done
	if has pkg-config && pkg-config --exists Qt6Core; then
		pkg-config --modversion Qt6Core
		return 0
	fi
	printf 'unknown'
}

# verify_binary <path> — a build that produced nothing runnable is a
# failed build, even when every command exited zero.
verify_binary() {
	local path="$1"
	if [[ -n "${HALCYON_DRY_RUN:-}" ]]; then
		log_info "would verify $path"
		return 0
	fi
	[[ -x "$path" ]] || {
		log_error "Expected $path to exist and be executable after the build."
		return 1
	}
	if ! "$path" --version >/dev/null 2>&1; then
		log_error "$path was built but will not run — check for a Qt version mismatch."
		return 1
	fi
	log_ok "Built $(basename "$path"): $("$path" --version 2>&1 | head -n1)"
}

# quickshell_needs_rebuild — true when Qt has moved since the last build.
quickshell_needs_rebuild() {
	local record="$HALCYON_STATE_DIR/quickshell-build"
	[[ -r "$record" ]] || return 1
	local built_qt current_qt
	built_qt="$(awk '/^qt /{print $2}' "$record")"
	current_qt="$(qt_version_string)"
	[[ -n "$built_qt" && -n "$current_qt" && "$built_qt" != "$current_qt" ]]
}
