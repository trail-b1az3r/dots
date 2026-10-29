#!/usr/bin/env python3
"""The super battery saver: `halcyon saver`.

    halcyon saver            on or off, and what it changed
    halcyon saver on|off|toggle
    halcyon saver kick       reconnect Wi-Fi once, if the saver is on and it is down (boot, wake, lock, unlock)

On, it:
  * draws the screen at most 12 times a second (hyprland-plus's plus:max_fps; with plain Hyprland that part is
    skipped), and turns off animations, blur and shadows (saver.lua, read with the rest of the config);
  * sets the screen to 20% brightness;
  * sets the power-saver power profile;
  * stops Wi-Fi reconnecting by itself: NetworkManager's autoconnect goes off for every Wi-Fi network. It still
    connects after boot, waking from suspend, locking and unlocking (`kick`, run from those), and whenever you pick
    a network yourself.

Off puts back exactly what it found: the brightness, the profile, and autoconnect on the networks that had it.
What it found is kept in ~/.local/state/halcyon/saver.json, which is also how saver.lua and the shell know it is on.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "halcyon"
FILE = STATE / "saver.json"
BRIGHTNESS = "20%"
MAX_FPS = 12
WIRELESS = "802-11-wireless"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def is_on() -> bool:
    return FILE.is_file()


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(data: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_name(FILE.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, FILE)


# ── Wi-Fi ─────────────────────────────────────────────────────────────────────

def wifi_autoconnecting() -> list[str]:
    """UUIDs of the Wi-Fi connections NetworkManager would join by itself."""
    if not have("nmcli"):
        return []
    out = run(["nmcli", "-t", "-f", "UUID,TYPE,AUTOCONNECT", "connection", "show"]).stdout
    uuids = []
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == WIRELESS and parts[2] == "yes":
            uuids.append(parts[0])
    return uuids


def set_autoconnect(uuids: list[str], on: bool) -> None:
    for uuid in uuids:
        run(["nmcli", "connection", "modify", uuid, "connection.autoconnect", "yes" if on else "no"])


def network_up() -> bool:
    return run(["nmcli", "-t", "-f", "STATE", "general", "status"]).stdout.strip() == "connected"


# ── Brightness and power profile ──────────────────────────────────────────────

def brightness() -> str:
    """The screen's brightness as brightnessctl can set it back ("1234"), or "" without brightnessctl."""
    if not have("brightnessctl"):
        return ""
    return run(["brightnessctl", "-m", "-c", "backlight", "get"]).stdout.strip()


def set_brightness(value: str) -> None:
    if value and have("brightnessctl"):
        run(["brightnessctl", "-q", "-c", "backlight", "set", value])


def profile() -> str:
    return run(["powerprofilesctl", "get"]).stdout.strip() if have("powerprofilesctl") else ""


def set_profile(value: str) -> None:
    if value and have("powerprofilesctl"):
        run(["powerprofilesctl", "set", value])


# ── The compositor ────────────────────────────────────────────────────────────

def reload_compositor() -> None:
    """saver.lua reads saver.json when the config loads, so a reload applies (or drops) the compositor part."""
    if have("hyprctl") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        run(["hyprctl", "reload"])


def notify(body: str) -> None:
    if have("notify-send"):
        run(["notify-send", "-a", "Halcyon", "-i", "battery-profile-powersave", "Super battery saver", body])


# ── Commands ──────────────────────────────────────────────────────────────────

def turn_on() -> int:
    if is_on():
        return 0
    found = {"brightness": brightness(), "profile": profile(), "autoconnect": wifi_autoconnecting(),
             "max_fps": MAX_FPS}
    save(found)
    set_brightness(BRIGHTNESS)
    set_profile("power-saver")
    set_autoconnect(found["autoconnect"], False)
    reload_compositor()
    notify(f"On: {MAX_FPS} fps, {BRIGHTNESS} brightness, power saver, and Wi-Fi only reconnects when you wake, "
           "lock or unlock the computer, or pick a network.")
    return 0


def turn_off() -> int:
    if not is_on():
        return 0
    found = load()
    FILE.unlink(missing_ok=True)
    set_autoconnect(found.get("autoconnect") or [], True)
    set_brightness(found.get("brightness") or "")
    set_profile(found.get("profile") or "")
    reload_compositor()
    notify("Off: everything is as it was.")
    return 0


def kick() -> int:
    """After boot, waking, locking or unlocking: Wi-Fi comes back once, since it no longer does by itself."""
    if not is_on() or not have("nmcli") or network_up():
        return 0
    subprocess.Popen([str(HERE / "wifi-reconnect")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return 0


def status() -> int:
    if not is_on():
        print("super battery saver  off")
        return 0
    found = load()
    print("super battery saver  on")
    print(f"  screen             at most {found.get('max_fps', MAX_FPS)} fps, {BRIGHTNESS} brightness")
    print(f"  put back when off  brightness {found.get('brightness') or '(unknown)'}, "
          f"profile {found.get('profile') or '(none)'}, "
          f"autoconnect on {len(found.get('autoconnect') or [])} Wi-Fi network(s)")
    return 0


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "status"
    if command == "on":
        return turn_on()
    if command == "off":
        return turn_off()
    if command == "toggle":
        return turn_off() if is_on() else turn_on()
    if command == "kick":
        return kick()
    if command == "status":
        return status()
    print("usage: halcyon saver [status | on | off | toggle | kick]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
