"""The small, concrete things a desktop has to be able to do.

Volume, brightness, media, radios, capture, session. Each function picks
whichever tool is actually installed, returns `(ok, message)` rather than
raising, and never runs a shell — every call is an argv list, so nothing
here can be turned into command injection by a filename or a voice
transcript.
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil
import subprocess
from typing import Any

from . import paths

Result = tuple[bool, str]


def _run(argv: list[str], *, timeout: float = 8.0) -> tuple[int, str, str]:
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError:
        return (127, "", f"{argv[0]} is not installed")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (1, "", str(exc))
    return (done.returncode, done.stdout.strip(), done.stderr.strip())


def _spawn(argv: list[str], *, cwd: str | None = None) -> Result:
    """Start a program and detach from it.

    start_new_session keeps the child alive when the caller is a keybind
    that exits immediately, and stops a crashing app from taking our
    terminal's process group with it.
    """
    try:
        subprocess.Popen(
            argv,
            cwd=cwd or None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        return False, f"{argv[0]} is not installed"
    except OSError as exc:
        return False, str(exc)
    return True, " ".join(argv[:2])


def _have(name: str) -> bool:
    return shutil.which(name) is not None


# ── Audio ──────────────────────────────────────────────────────────────

_SINK = "@DEFAULT_AUDIO_SINK@"
_SOURCE = "@DEFAULT_AUDIO_SOURCE@"


def volume_state() -> dict[str, Any]:
    """Current output volume and mute state, as a percentage."""
    if _have("wpctl"):
        code, out, _ = _run(["wpctl", "get-volume", _SINK])
        if code == 0 and out:
            # "Volume: 0.45 [MUTED]"
            parts = out.replace("Volume:", "").strip().split()
            try:
                level = float(parts[0])
            except (IndexError, ValueError):
                level = 0.0
            return {
                "volume": int(round(level * 100)),
                "muted": "MUTED" in out.upper(),
                "backend": "wireplumber",
            }
    if _have("pactl"):
        code, out, _ = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        percent = 0
        if code == 0:
            for token in out.split():
                if token.endswith("%"):
                    try:
                        percent = int(token.rstrip("%"))
                    except ValueError:
                        percent = 0
                    break
        code, out, _ = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
        return {
            "volume": percent,
            "muted": "yes" in out.lower(),
            "backend": "pulseaudio",
        }
    return {"volume": 0, "muted": False, "backend": "none"}


def set_volume(percent: int) -> Result:
    percent = max(0, min(150, int(percent)))
    if _have("wpctl"):
        # -l caps the ceiling so a stray command cannot blow an eardrum.
        code, _, err = _run(["wpctl", "set-volume", "-l", "1.5", _SINK, f"{percent}%"])
        return (code == 0, err or f"Volume set to {percent}%")
    if _have("pactl"):
        code, _, err = _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"])
        return (code == 0, err or f"Volume set to {percent}%")
    return False, "No PipeWire or PulseAudio control tool found"


def adjust_volume(delta: int) -> Result:
    delta = max(-100, min(100, int(delta)))
    sign = "+" if delta >= 0 else "-"
    if _have("wpctl"):
        code, _, err = _run(
            ["wpctl", "set-volume", "-l", "1.5", _SINK, f"{abs(delta)}%{sign}"]
        )
        return (code == 0, err or f"Volume {sign}{abs(delta)}%")
    if _have("pactl"):
        code, _, err = _run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{sign}{abs(delta)}%"]
        )
        return (code == 0, err or f"Volume {sign}{abs(delta)}%")
    return False, "No PipeWire or PulseAudio control tool found"


def _mute(target: str, state: str) -> Result:
    value = {"on": "1", "off": "0", "toggle": "toggle"}.get(state)
    if value is None:
        return False, f"Expected on, off or toggle; got {state!r}"
    if _have("wpctl"):
        code, _, err = _run(["wpctl", "set-mute", target, value])
        return (code == 0, err or f"Mute {state}")
    if _have("pactl"):
        device = "@DEFAULT_SINK@" if target == _SINK else "@DEFAULT_SOURCE@"
        code, _, err = _run(["pactl", f"set-{'sink' if target == _SINK else 'source'}-mute", device, value])
        return (code == 0, err or f"Mute {state}")
    return False, "No PipeWire or PulseAudio control tool found"


def mute_output(state: str = "toggle") -> Result:
    return _mute(_SINK, state)


def mute_input(state: str = "toggle") -> Result:
    return _mute(_SOURCE, state)


def microphone_state() -> dict[str, Any]:
    if _have("wpctl"):
        code, out, _ = _run(["wpctl", "get-volume", _SOURCE])
        if code == 0 and out:
            parts = out.replace("Volume:", "").strip().split()
            try:
                level = float(parts[0])
            except (IndexError, ValueError):
                level = 0.0
            return {"volume": int(round(level * 100)), "muted": "MUTED" in out.upper()}
    return {"volume": 0, "muted": False}


# ── Backlight ──────────────────────────────────────────────────────────


def backlight_state() -> dict[str, Any]:
    if _have("brightnessctl"):
        code, out, _ = _run(["brightnessctl", "--machine-readable", "info"])
        if code == 0 and out:
            # device,class,current,percent,max
            fields = out.splitlines()[0].split(",")
            if len(fields) >= 4:
                try:
                    return {
                        "device": fields[0],
                        "percent": int(fields[3].rstrip("%")),
                        "available": True,
                    }
                except ValueError:
                    pass
    # sysfs fallback: works without brightnessctl when the user has udev
    # rules granting write access.
    base = "/sys/class/backlight"
    try:
        devices = sorted(os.listdir(base))
    except OSError:
        devices = []
    for device in devices:
        try:
            current = int(open(f"{base}/{device}/brightness").read().strip())
            maximum = int(open(f"{base}/{device}/max_brightness").read().strip())
        except (OSError, ValueError):
            continue
        if maximum:
            return {
                "device": device,
                "percent": int(round(current / maximum * 100)),
                "available": True,
            }
    return {"device": "", "percent": 0, "available": False}


def set_backlight(percent: int) -> Result:
    percent = max(1, min(100, int(percent)))
    if _have("brightnessctl"):
        code, _, err = _run(["brightnessctl", "-q", "set", f"{percent}%"])
        return (code == 0, err or f"Brightness set to {percent}%")
    return False, "brightnessctl is not installed"


def adjust_backlight(delta: int) -> Result:
    delta = max(-100, min(100, int(delta)))
    if not _have("brightnessctl"):
        return False, "brightnessctl is not installed"
    # -e4 is a perceptual (gamma 4) curve; a linear step feels wrong at
    # the bottom of the range, where one percent is a visible jump.
    # -n2 keeps the panel from going fully dark.
    argument = f"{abs(delta)}%{'+' if delta >= 0 else '-'}"
    code, _, err = _run(["brightnessctl", "-q", "-e4", "-n2", "set", argument])
    return (code == 0, err or f"Brightness {argument}")


def keyboard_backlight(percent: int) -> Result:
    if not _have("brightnessctl"):
        return False, "brightnessctl is not installed"
    base = "/sys/class/leds"
    try:
        leds = [d for d in os.listdir(base) if "kbd_backlight" in d]
    except OSError:
        leds = []
    if not leds:
        return False, "This machine has no keyboard backlight"
    code, _, err = _run(
        ["brightnessctl", "-q", "-d", leds[0], "set", f"{max(0, min(100, int(percent)))}%"]
    )
    return (code == 0, err or f"Keyboard backlight set to {percent}%")


# ── Media ──────────────────────────────────────────────────────────────


def media(command: str) -> Result:
    allowed = {
        "play-pause": "play-pause",
        "play": "play",
        "pause": "pause",
        "next": "next",
        "previous": "previous",
        "stop": "stop",
    }
    action = allowed.get(command)
    if action is None:
        return False, f"Unknown media command {command!r}"
    if not _have("playerctl"):
        return False, "playerctl is not installed"
    code, _, err = _run(["playerctl", action])
    return (code == 0, err or f"Media: {action}")


def media_status() -> dict[str, Any]:
    if not _have("playerctl"):
        return {"status": "unavailable"}
    code, out, _ = _run(["playerctl", "status"])
    status = out.lower() if code == 0 else "stopped"
    info: dict[str, Any] = {"status": status}
    for key, fmt in (("title", "{{title}}"), ("artist", "{{artist}}"), ("album", "{{album}}")):
        code, out, _ = _run(["playerctl", "metadata", "--format", fmt])
        info[key] = out if code == 0 else ""
    return info


# ── Radios ─────────────────────────────────────────────────────────────


def wifi_state() -> dict[str, Any]:
    if _have("nmcli"):
        code, out, _ = _run(["nmcli", "-t", "radio", "wifi"])
        if code == 0:
            return {"enabled": out.strip() == "enabled", "backend": "networkmanager"}
    if _have("rfkill"):
        code, out, _ = _run(["rfkill", "list", "wlan"])
        if code == 0:
            return {"enabled": "Soft blocked: no" in out, "backend": "rfkill"}
    return {"enabled": False, "backend": "none"}


def set_wifi(state: str) -> Result:
    if state == "toggle":
        state = "off" if wifi_state()["enabled"] else "on"
    if state not in ("on", "off"):
        return False, f"Expected on, off or toggle; got {state!r}"
    if _have("nmcli"):
        code, _, err = _run(["nmcli", "radio", "wifi", state])
        return (code == 0, err or f"Wi-Fi {state}")
    if _have("rfkill"):
        code, _, err = _run(["rfkill", "unblock" if state == "on" else "block", "wlan"])
        return (code == 0, err or f"Wi-Fi {state}")
    return False, "Neither nmcli nor rfkill is installed"


def bluetooth_state() -> dict[str, Any]:
    if _have("bluetoothctl"):
        code, out, _ = _run(["bluetoothctl", "show"])
        if code == 0:
            return {"enabled": "Powered: yes" in out, "backend": "bluez"}
    if _have("rfkill"):
        code, out, _ = _run(["rfkill", "list", "bluetooth"])
        if code == 0:
            return {"enabled": "Soft blocked: no" in out, "backend": "rfkill"}
    return {"enabled": False, "backend": "none"}


def set_bluetooth(state: str) -> Result:
    if state == "toggle":
        state = "off" if bluetooth_state()["enabled"] else "on"
    if state not in ("on", "off"):
        return False, f"Expected on, off or toggle; got {state!r}"
    if _have("bluetoothctl"):
        code, _, err = _run(["bluetoothctl", "power", state])
        return (code == 0, err or f"Bluetooth {state}")
    if _have("rfkill"):
        code, _, err = _run(
            ["rfkill", "unblock" if state == "on" else "block", "bluetooth"]
        )
        return (code == 0, err or f"Bluetooth {state}")
    return False, "Neither bluetoothctl nor rfkill is installed"


def set_airplane_mode(state: str) -> Result:
    """Radios off. rfkill is the only tool that covers every radio."""
    if not _have("rfkill"):
        wifi = set_wifi(state)
        bluetooth = set_bluetooth(state)
        return (wifi[0] or bluetooth[0], f"{wifi[1]}; {bluetooth[1]}")
    if state == "toggle":
        state = "on" if wifi_state()["enabled"] else "off"
    code, _, err = _run(["rfkill", "block" if state == "on" else "unblock", "all"])
    return (code == 0, err or f"Airplane mode {state}")


# ── Capture ────────────────────────────────────────────────────────────


def _capture_dir(settings: dict[str, Any], key: str, default: str) -> str:
    configured = str(settings.get("applications", {}).get(key, "")).strip() or default
    directory = os.path.expanduser(configured)
    os.makedirs(directory, exist_ok=True)
    return directory


def screenshot(mode: str, settings: dict[str, Any]) -> Result:
    """Capture the screen, a region, or the focused window."""
    if not _have("grim"):
        return False, "grim is not installed"

    directory = _capture_dir(settings, "screenshotDir", "~/Pictures/Screenshots")
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    target = os.path.join(directory, f"Screenshot {stamp}.png")

    argv = ["grim"]
    if mode == "region":
        if not _have("slurp"):
            return False, "slurp is not installed, so a region cannot be selected"
        code, geometry, _ = _run(["slurp", "-d"], timeout=120)
        if code != 0 or not geometry:
            return False, "Region selection cancelled"
        argv += ["-g", geometry]
    elif mode == "window":
        geometry = _focused_window_geometry()
        if geometry is None:
            return False, "Could not determine the focused window's geometry"
        argv += ["-g", geometry]
    elif mode != "screen":
        return False, f"Unknown screenshot mode {mode!r}"

    argv.append(target)
    code, _, err = _run(argv, timeout=60)
    if code != 0:
        return False, err or "grim failed"

    if _have("wl-copy"):
        try:
            with open(target, "rb") as handle:
                subprocess.run(
                    ["wl-copy", "--type", "image/png"],
                    stdin=handle,
                    timeout=10,
                    check=False,
                )
        except (OSError, subprocess.TimeoutExpired):
            pass

    notify("Screenshot saved", os.path.basename(target), icon=target)
    return True, target


def _focused_window_geometry() -> str | None:
    if not _have("hyprctl"):
        return None
    import json as _json

    code, out, _ = _run(["hyprctl", "-j", "activewindow"])
    if code != 0:
        return None
    try:
        window = _json.loads(out)
        x, y = window["at"]
        width, height = window["size"]
    except (ValueError, KeyError, TypeError):
        return None
    return f"{x},{y} {width}x{height}"


def record(action: str, settings: dict[str, Any]) -> Result:
    """Start or stop a screen recording."""
    pidfile = paths.runtime_dir() / "halcyon-record.pid"

    if action == "stop":
        if not pidfile.exists():
            return False, "Nothing is recording"
        try:
            pid = int(pidfile.read_text().strip())
            os.kill(pid, 15)
        except (OSError, ValueError):
            pass
        pidfile.unlink(missing_ok=True)
        notify("Recording stopped", "Saved to your recordings folder")
        return True, "Recording stopped"

    if action == "toggle" and pidfile.exists():
        return record("stop", settings)

    tool = "wf-recorder" if _have("wf-recorder") else ("wl-screenrec" if _have("wl-screenrec") else None)
    if tool is None:
        return False, "Neither wf-recorder nor wl-screenrec is installed"

    directory = _capture_dir(settings, "recordingDir", "~/Videos/Recordings")
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    target = os.path.join(directory, f"Recording {stamp}.mp4")

    try:
        process = subprocess.Popen(
            [tool, "-f", target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return False, str(exc)

    pidfile.write_text(str(process.pid))
    notify("Recording started", os.path.basename(target))
    return True, target


def recording() -> bool:
    return (paths.runtime_dir() / "halcyon-record.pid").exists()


# ── Session ────────────────────────────────────────────────────────────


def lock() -> Result:
    """Lock the session, preferring the dedicated locker.

    hyprlock is first because it is a small, single-purpose program: if
    the shell has crashed, the lock still works. Quickshell's own lock
    surface is the fallback, and loginctl the last resort.
    """
    if _have("hyprlock"):
        return _spawn(["hyprlock"])

    from . import shell

    ok, message = shell.call("lock", "lock", [])
    if ok:
        return True, "Session locked"

    if _have("loginctl"):
        code, _, err = _run(["loginctl", "lock-session"])
        return (code == 0, err or "Session locked")
    return False, f"No lock screen available ({message})"


def suspend() -> Result:
    if _have("systemctl"):
        code, _, err = _run(["systemctl", "suspend"])
        return (code == 0, err or "Suspending")
    if _have("loginctl"):
        code, _, err = _run(["loginctl", "suspend"])
        return (code == 0, err or "Suspending")
    return False, "No way to suspend this system was found"


def hibernate() -> Result:
    if _have("systemctl"):
        code, _, err = _run(["systemctl", "hibernate"])
        return (code == 0, err or "Hibernating")
    return False, "No way to hibernate this system was found"


def reboot() -> Result:
    if _have("systemctl"):
        code, _, err = _run(["systemctl", "reboot"])
        return (code == 0, err or "Rebooting")
    return False, "No way to reboot this system was found"


def shutdown() -> Result:
    if _have("systemctl"):
        code, _, err = _run(["systemctl", "poweroff"])
        return (code == 0, err or "Shutting down")
    return False, "No way to power off this system was found"


def logout() -> Result:
    if _have("hyprctl"):
        code, _, _ = _run(["hyprctl", "dispatch", "hl.dsp.exit()"])
        if code == 0:
            return True, "Logging out"
    if _have("loginctl"):
        code, _, err = _run(["loginctl", "terminate-session", os.environ.get("XDG_SESSION_ID", "")])
        return (code == 0, err or "Logging out")
    return False, "No way to end the session was found"


# ── Notifications ──────────────────────────────────────────────────────


def notify(summary: str, body: str = "", *, icon: str = "", urgency: str = "normal") -> bool:
    if not _have("notify-send"):
        return False
    argv = ["notify-send", "-a", "Halcyon", "-u", urgency]
    if icon:
        argv += ["-i", icon]
    argv += [summary]
    if body:
        argv.append(body)
    code, _, _ = _run(argv, timeout=5)
    return code == 0


# ── Opening things ─────────────────────────────────────────────────────


def open_path(target: str) -> Result:
    """Hand a file or URL to the desktop's default handler."""
    expanded = os.path.expanduser(target)
    if os.path.exists(expanded):
        target = expanded
    elif "://" not in target:
        return False, f"No such file or folder: {target}"
    if not _have("xdg-open"):
        return False, "xdg-open is not installed"
    return _spawn(["xdg-open", target])


def open_terminal(settings: dict[str, Any], command: list[str] | None = None) -> Result:
    terminal = str(settings.get("applications", {}).get("terminal", "")).strip()
    candidates = [terminal] if terminal else []
    candidates += ["kitty", "alacritty", "foot", "wezterm", "ghostty", "xterm"]
    for candidate in candidates:
        if candidate and _have(candidate):
            argv = [candidate]
            if command:
                argv += ["-e", *command]
            return _spawn(argv)
    return False, "No terminal emulator was found"
