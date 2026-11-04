#!/usr/bin/env sh
# Which network tool Halcyon talks to: prints "nmxcli" or "nmcli", then "nexora" on Nexora.
#
# - nmx running (anywhere): nmxcli.
# - Nexora with nmx chosen (nmx.service enabled, so it is starting or restarting), or with NetworkManager not
#   running: nmxcli, so nothing in Halcyon needs NetworkManager, nmtui or KDE's network settings there.
# - Otherwise: nmcli (NetworkManager), as before.
os_release="${OS_RELEASE:-/etc/os-release}"
id=$(sed -n 's/^ID=//p' "$os_release" 2>/dev/null | tr -d "\"'" | head -n1)

tool=nmcli
if command -v nmxcli >/dev/null 2>&1; then
    if nmxcli -t -f RUNNING general 2>/dev/null | grep -qx running; then
        tool=nmxcli
    elif [ "$id" = nexora ]; then
        if systemctl is-enabled --quiet nmx.service 2>/dev/null \
            || ! systemctl is-active --quiet NetworkManager.service 2>/dev/null; then
            tool=nmxcli
        fi
    fi
fi
echo "$tool"
[ "$id" = nexora ] && echo nexora
exit 0
