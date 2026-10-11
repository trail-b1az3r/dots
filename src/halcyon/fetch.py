"""`halcyon fetch`: a system summary beside the Halcyon mark, turning in 3D.

Every value shown is read from this machine when the command runs. A value
that cannot be read is left out rather than guessed, so the summary never
says something the machine does not support.

The mark is drawn by `logo3d`. Without `--spin` it prints one settled
frame; with `--spin` it turns for a few seconds in place and then settles.
Motion is never used when output is not a terminal, or when the user has
asked for reduced motion.
"""

from __future__ import annotations

import getpass
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, TextIO

from . import __version__, logo3d, sysstat

#: Gap between the mark and the text beside it, in columns.
GAP = 3

#: Angle the settled mark rests at, in radians: a three-quarter view.
SETTLED_YAW = 0.55

#: Turning speed while spinning, and how long a spin lasts.
SPIN_RATE = 1.7  # radians per second
SPIN_SECONDS = 3.0
FRAME_SECONDS = 1.0 / 15.0

# ANSI styling. Colour is only used on a terminal that has not asked for
# none; NO_COLOR is the convention that asks.
_LABEL = "\x1b[1;38;5;39m"
_RESET = "\x1b[0m"
_DIM = "\x1b[2m"


@dataclass
class Field:
    label: str
    value: str


# ── Reading the machine ────────────────────────────────────────────────


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def os_name() -> Optional[str]:
    text = _read("/etc/os-release")
    if not text:
        return None
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def host_model() -> Optional[str]:
    for path in ("/sys/devices/virtual/dmi/id/product_name", "/sys/firmware/devicetree/base/model"):
        text = _read(path)
        if text and text.strip().strip("\x00"):
            return text.strip().strip("\x00")
    return None


def cpu_model() -> Optional[str]:
    text = _read("/proc/cpuinfo")
    if not text:
        return None
    for line in text.splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def uptime_seconds() -> Optional[float]:
    text = _read("/proc/uptime")
    if not text:
        return None
    try:
        return float(text.split()[0])
    except (ValueError, IndexError):
        return None


def format_uptime(seconds: float) -> str:
    total = int(seconds)
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours or days:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    parts.append(f"{minutes} min")
    return ", ".join(parts)


def monitors() -> list[str]:
    """`WxH @ Hz` for each active Hyprland monitor, or [] when unavailable."""
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or not shutil.which("hyprctl"):
        return []
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True, text=True, timeout=1.5, check=False,
        )
        data = json.loads(result.stdout or "[]")
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        try:
            out.append(f"{int(item['width'])}x{int(item['height'])} @ {float(item['refreshRate']):.0f} Hz")
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _shell_name() -> Optional[str]:
    shell = os.environ.get("SHELL")
    return os.path.basename(shell) if shell else None


def _desktop() -> Optional[str]:
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland"
    return os.environ.get("XDG_CURRENT_DESKTOP") or None


def collect(now: Callable[[], float] = time.time) -> list[Field]:
    """Every field the summary can show on this machine, in display order."""
    fields: list[Field] = []

    try:
        user = getpass.getuser()
    except (KeyError, OSError):
        user = os.environ.get("USER", "user")
    fields.append(Field("", f"{user}@{socket.gethostname()}"))

    name = os_name()
    if name:
        fields.append(Field("OS", f"{name} {platform.machine()}"))
    model = host_model()
    if model:
        fields.append(Field("Host", model))
    fields.append(Field("Kernel", platform.release()))
    seconds = uptime_seconds()
    if seconds is not None:
        fields.append(Field("Uptime", format_uptime(seconds)))
    desktop = _desktop()
    if desktop:
        fields.append(Field("Desktop", desktop))
    for index, mode in enumerate(monitors()):
        fields.append(Field("Display" if index == 0 else "", mode))
    shell = _shell_name()
    if shell:
        fields.append(Field("Shell", shell))

    cpu = cpu_model()
    cores = sysstat.cpu_count()
    if cpu:
        fields.append(Field("CPU", f"{cpu} ({cores} threads)" if cores else cpu))
    memory = sysstat.memory()
    if memory.total_kb:
        used = sysstat.human_bytes(memory.used_kb * 1024)
        total = sysstat.human_bytes(memory.total_kb * 1024)
        fields.append(Field("Memory", f"{used} / {total} ({memory.percent:.0f}%)"))
    root = sysstat.disk("/")
    if root.total_bytes:
        used = sysstat.human_bytes(root.used_bytes)
        total = sysstat.human_bytes(root.total_bytes)
        fields.append(Field("Disk (/)", f"{used} / {total} ({root.percent:.0f}%)"))
    temperature = sysstat.cpu_temperature()
    if temperature is not None:
        fields.append(Field("Temp", f"{temperature:.0f} °C"))
    load = sysstat.load_average()
    if load:
        fields.append(Field("Load", f"{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}"))

    fields.append(Field("Halcyon", __version__))
    return fields


def as_json(fields: Sequence[Field]) -> dict[str, str]:
    """Labelled fields as a dictionary, for `--json`. Unlabelled lines are
    keyed by their position so none are dropped."""
    out: dict[str, str] = {}
    for index, field in enumerate(fields):
        key = field.label or ("user" if index == 0 else f"line{index}")
        out[key] = field.value
    return out


# ── Composing the frame ────────────────────────────────────────────────


def _style(text: str, code: str, colour: bool) -> str:
    return f"{code}{text}{_RESET}" if colour and text else text


def info_lines(fields: Sequence[Field], *, colour: bool) -> list[str]:
    labels = [f.label for f in fields if f.label]
    width = max((len(label) for label in labels), default=0)
    lines = []
    for field in fields:
        if not field.label:
            lines.append(_style(field.value, "\x1b[1m", colour) if colour else field.value)
            continue
        label = field.label.ljust(width)
        lines.append(f"{_style(label, _LABEL, colour)}  {field.value}")
    rule = "─" * min(max(len(f.value) for f in fields) + width + 2, 48) if fields else ""
    if colour:
        rule = _style(rule, _DIM, colour)
    # A rule after the title line, as fastfetch draws it.
    if lines:
        lines.insert(1, rule)
    return lines


def compose(frame: Sequence[str], info: Sequence[str]) -> list[str]:
    """The mark on the left, the info on the right, one row each."""
    mark_width = logo3d.frame_width(frame)
    height = max(len(frame), len(info))
    top = max(0, (height - len(frame)) // 2)
    rows = []
    for row in range(height):
        index = row - top
        mark = frame[index] if 0 <= index < len(frame) else ""
        text = info[row] if row < len(info) else ""
        rows.append(f"{mark.ljust(mark_width)}{' ' * GAP}{text}".rstrip())
    return rows


def _colour_enabled(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return stream.isatty()


def _settings_reduce_motion() -> bool:
    try:
        from . import settings

        return bool(settings.load().get("motion", {}).get("reducedMotion", False))
    except Exception:  # noqa: BLE001 - a broken settings file must not stop fetch
        return False


# ── Output ─────────────────────────────────────────────────────────────


def print_static(fields: Sequence[Field], out: TextIO, *, colour: bool) -> None:
    frame = logo3d.render_frame(SETTLED_YAW)
    for line in compose(frame, info_lines(fields, colour=colour)):
        out.write(line + "\n")
    out.flush()


def spin(
    fields: Sequence[Field],
    out: TextIO,
    *,
    colour: bool,
    seconds: float = SPIN_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Turn the mark for `seconds`, redrawing in place, then settle on the
    resting angle. Assumes `out` is a terminal."""
    info = info_lines(fields, colour=colour)
    frames = max(1, int(seconds / FRAME_SECONDS))
    height = max(len(logo3d.render_frame(0.0)), len(info))
    out.write("\x1b[?25l")  # hide the cursor while the mark moves
    try:
        for step in range(frames + 1):
            if step == frames:
                yaw = SETTLED_YAW
            else:
                yaw = step * SPIN_RATE * FRAME_SECONDS
            lines = compose(logo3d.render_frame(yaw), info)
            if step:
                out.write(f"\x1b[{height}A\r")
            out.write("\n".join(line + "\x1b[K" for line in _pad(lines, height)) + "\n")
            out.flush()
            if step < frames:
                sleep(FRAME_SECONDS)
    finally:
        out.write("\x1b[?25h")
        out.flush()


def _pad(lines: list[str], height: int) -> list[str]:
    return lines + [""] * (height - len(lines))


def run(*, spin_seconds: Optional[float], as_json_out: bool, out: TextIO = sys.stdout) -> int:
    fields = collect()
    if as_json_out:
        out.write(json.dumps(as_json(fields), ensure_ascii=False, indent=2) + "\n")
        return 0
    colour = _colour_enabled(out)
    if spin_seconds and out.isatty() and not _settings_reduce_motion():
        spin(fields, out, colour=colour, seconds=spin_seconds)
    else:
        print_static(fields, out, colour=colour)
    return 0
