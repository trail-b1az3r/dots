"""`halcyon fetch`: a system summary beside the Halcyon mark, turning in 3D.

Every value shown is read from this machine when the command runs. A value
that cannot be read is left out rather than guessed, so the summary never
says something the machine does not support.

The mark is drawn by `logo3d`. Without `--spin` it prints one settled
frame; with `--spin` it turns for a few seconds in place and then settles.
A key pressed while it turns settles it at once, and the key is left for the
shell, so a new terminal can be typed in straight away.
Motion is never used when output is not a terminal, or when the user has
asked for reduced motion.
"""

from __future__ import annotations

import getpass
import json
import math
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Optional, Sequence, TextIO

import fetch_mark as logo3d

__version__ = "1.0.0"

#: Gap between the mark and the text beside it, in columns.
GAP = 3

#: The mark's size in characters: 96 wide and 52 tall.
FRAME_COLS = 96
FRAME_ROWS = 52

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


def _meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in (_read("/proc/meminfo") or "").splitlines():
        name, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[name] = int(parts[0])  # kB
    return values


def _human(value: float) -> str:
    amount = float(value)
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(amount) < 1024.0 or unit == "TB":
            return f"{amount:.1f} {unit}" if abs(amount) < 10.0 and unit != "B" else f"{amount:.0f} {unit}"
        amount /= 1024.0
    return f"{amount:.0f} TB"


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
    cores = os.cpu_count()
    if cpu:
        fields.append(Field("CPU", f"{cpu} ({cores} threads)" if cores else cpu))
    meminfo = _meminfo()
    total_kb = meminfo.get("MemTotal", 0)
    if total_kb:
        available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used_kb = max(0, total_kb - available_kb)
        percent = used_kb / total_kb * 100.0
        fields.append(Field("Memory", f"{_human(used_kb * 1024)} / {_human(total_kb * 1024)} ({percent:.0f}%)"))
    try:
        stats = os.statvfs("/")
        total = stats.f_blocks * stats.f_frsize
        free = stats.f_bavail * stats.f_frsize
        if total:
            used = total - free
            fields.append(Field("Disk (/)", f"{_human(used)} / {_human(total)} ({used / total * 100:.0f}%)"))
    except OSError:
        pass
    try:
        load = os.getloadavg()
        fields.append(Field("Load", f"{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}"))
    except OSError:
        pass

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


# ── Output ─────────────────────────────────────────────────────────────


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def fastfetch_lines() -> Optional[list[str]]:
    """fastfetch's own summary, without its logo, as plain text lines.

    None when fastfetch is not installed or does not run, so the caller can
    fall back to the built-in summary rather than show nothing.
    """
    exe = shutil.which("fastfetch")
    if not exe:
        return None
    try:
        result = subprocess.run([exe, "--logo", "none"], capture_output=True, text=True,
                                timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    # Colour codes are stripped so each line's width can be measured for
    # placing the mark beside it.
    return [_ANSI.sub("", line) for line in result.stdout.splitlines() if line.strip()]


def print_static(fields: Sequence[Field], out: TextIO, *, colour: bool,
                 text: Optional[list[str]] = None) -> None:
    frame = logo3d.render_frame(SETTLED_YAW, cols=FRAME_COLS, rows=FRAME_ROWS)
    info = text if text is not None else info_lines(fields, colour=colour)
    for line in compose(frame, info):
        out.write(line + "\n")
    out.flush()


def spin(
    fields: Sequence[Field],
    out: TextIO,
    *,
    colour: bool,
    seconds: Optional[float] = None,
    sleep: Callable[[float], None] = time.sleep,
    text: Optional[list[str]] = None,
    key_pressed: Optional[Callable[[float], bool]] = None,
) -> None:
    """Turn the mark in a loop, redrawing in place: for `seconds`, or until
    interrupted when `seconds` is None. Assumes `out` is a terminal.

    `key_pressed(timeout)` waits up to `timeout` seconds between frames and says
    whether a key came in; when one does, the mark settles straight away."""
    info = text if text is not None else info_lines(fields, colour=colour)
    height = max(FRAME_ROWS, len(info))
    total = None if seconds is None else max(1, int(seconds / FRAME_SECONDS))

    def draw(yaw: float, again: bool) -> None:
        lines = compose(logo3d.render_frame(yaw, cols=FRAME_COLS, rows=FRAME_ROWS), info)
        if again:
            out.write(f"\x1b[{height}A\r")
        out.write("\n".join(line + "\x1b[K" for line in _pad(lines, height)) + "\n")
        out.flush()

    out.write("\x1b[?25l")  # hide the cursor while the mark moves
    try:
        step = 0
        while total is None or step < total:
            # One full turn every 2π / SPIN_RATE seconds, so the loop is seamless.
            draw((step * SPIN_RATE * FRAME_SECONDS) % (2 * math.pi), step > 0)
            step += 1
            if key_pressed is None:
                sleep(FRAME_SECONDS)
            elif key_pressed(FRAME_SECONDS):
                draw(SETTLED_YAW, True)
                break
    finally:
        out.write("\x1b[?25h")
        out.flush()


@contextmanager
def _watch_keys(stream: TextIO) -> Iterator[Optional[Callable[[float], bool]]]:
    """While the mark turns, notice a key without taking it: the terminal is put
    in non-canonical, no-echo mode (Ctrl+C still works), polled, and set back
    without flushing, so the key stays queued for the shell's prompt."""
    try:
        import select
        import termios
        fd = stream.fileno()
        if not os.isatty(fd):
            raise OSError
        saved = termios.tcgetattr(fd)
    except (ImportError, OSError, ValueError, AttributeError):
        yield None
        return
    quiet = termios.tcgetattr(fd)
    quiet[3] &= ~(termios.ICANON | termios.ECHO)
    quiet[6][termios.VMIN] = 1
    quiet[6][termios.VTIME] = 0
    try:
        termios.tcsetattr(fd, termios.TCSANOW, quiet)
    except termios.error:
        yield None
        return

    def key_pressed(timeout: float) -> bool:
        try:
            return bool(select.select([fd], [], [], timeout)[0])
        except (OSError, ValueError):
            time.sleep(timeout)
            return False

    try:
        yield key_pressed
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSANOW, saved)  # TCSANOW: keep what was typed
        except termios.error:
            pass


def _pad(lines: list[str], height: int) -> list[str]:
    return lines + [""] * (height - len(lines))


def run(*, spin_seconds: Optional[float], as_json_out: bool, reduce_motion: bool = False,
        use_fastfetch: bool = False, out: TextIO = sys.stdout, keys: Optional[TextIO] = None) -> int:
    fields = collect()
    if as_json_out:
        out.write(json.dumps(as_json(fields), ensure_ascii=False, indent=2) + "\n")
        return 0
    text: Optional[list[str]] = None
    if use_fastfetch:
        text = fastfetch_lines()
        if text is None:
            print("halcyon fetch: fastfetch is not available, showing the built-in summary",
                  file=sys.stderr)
    colour = _colour_enabled(out)
    # spin_seconds of 0 means loop until interrupted; None means not to spin.
    if spin_seconds is not None and out.isatty() and not reduce_motion:
        with _watch_keys(keys if keys is not None else sys.stdin) as key_pressed:
            spin(fields, out, colour=colour, seconds=(spin_seconds or None), text=text,
                 key_pressed=key_pressed)
    else:
        print_static(fields, out, colour=colour, text=text)
    return 0
