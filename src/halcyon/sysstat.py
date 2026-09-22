"""System load, read from the kernel rather than from another tool.

Waybar supplied CPU, memory and temperature to the old bar. The Ultra
Bar is ours, so these come from `/proc` and `/sys` directly: no polling
subprocess, no parsing of another program's human-readable output, and
nothing to install.

CPU utilisation is a rate, not a level, so it needs two samples to mean
anything. `CpuSampler` holds the previous reading; a single call to
`snapshot()` on a fresh sampler reports `None` for CPU rather than
inventing a number from one sample.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

PROC = "/proc"
SYS = "/sys"


# ── CPU ────────────────────────────────────────────────────────────────


@dataclass
class CpuTimes:
    total: int
    idle: int


def _read_cpu_times() -> CpuTimes | None:
    """Aggregate jiffies from /proc/stat's first line."""
    try:
        with open(os.path.join(PROC, "stat"), "r", encoding="utf-8") as handle:
            line = handle.readline()
    except OSError:
        return None
    if not line.startswith("cpu "):
        return None
    fields = line.split()[1:]
    try:
        values = [int(v) for v in fields]
    except ValueError:
        return None
    if len(values) < 5:
        return None
    # user nice system idle iowait irq softirq steal …
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return CpuTimes(total=sum(values), idle=idle)


class CpuSampler:
    """Turns successive /proc/stat readings into a percentage."""

    def __init__(self) -> None:
        self._previous: CpuTimes | None = None

    def sample(self) -> float | None:
        current = _read_cpu_times()
        if current is None:
            return None
        return self._compare(current)

    def _compare(self, current: CpuTimes) -> float | None:
        previous, self._previous = self._previous, current
        if previous is None:
            return None
        total_delta = current.total - previous.total
        idle_delta = current.idle - previous.idle
        if total_delta <= 0:
            # The counters wrapped or did not advance; one sample is not
            # worth reporting a spike over.
            return None
        busy = (total_delta - idle_delta) / total_delta
        return round(max(0.0, min(1.0, busy)) * 100.0, 1)


def cpu_count() -> int:
    return os.cpu_count() or 1


def load_average() -> tuple[float, float, float] | None:
    try:
        return os.getloadavg()
    except (OSError, AttributeError):
        return None


# ── Memory ─────────────────────────────────────────────────────────────


def _meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        with open(os.path.join(PROC, "meminfo"), "r", encoding="utf-8") as handle:
            for line in handle:
                name, _, rest = line.partition(":")
                parts = rest.split()
                if parts:
                    try:
                        values[name] = int(parts[0])  # kB
                    except ValueError:
                        continue
    except OSError:
        return {}
    return values


@dataclass
class Memory:
    total_kb: int = 0
    available_kb: int = 0
    used_kb: int = 0
    percent: float = 0.0
    swap_total_kb: int = 0
    swap_used_kb: int = 0
    swap_percent: float = 0.0


def memory() -> Memory:
    info = _meminfo()
    total = info.get("MemTotal", 0)
    # MemAvailable is the kernel's own estimate of what a new allocation
    # could get. It is a far better "free" than MemFree, which counts
    # reclaimable cache as used and makes every Linux box look full.
    available = info.get("MemAvailable", info.get("MemFree", 0))
    used = max(0, total - available)
    swap_total = info.get("SwapTotal", 0)
    swap_free = info.get("SwapFree", 0)
    swap_used = max(0, swap_total - swap_free)
    return Memory(
        total_kb=total,
        available_kb=available,
        used_kb=used,
        percent=round(used / total * 100.0, 1) if total else 0.0,
        swap_total_kb=swap_total,
        swap_used_kb=swap_used,
        swap_percent=round(swap_used / swap_total * 100.0, 1) if swap_total else 0.0,
    )


# ── Temperature ────────────────────────────────────────────────────────

#: hwmon names worth showing, best first. A machine exposes a dozen
#: thermal zones and most of them are not the one a person means by
#: "temperature"; these are the CPU package sensors by driver.
_CPU_SENSORS = ("k10temp", "coretemp", "zenpower", "cpu_thermal", "acpitz")


def _hwmon_candidates() -> list[tuple[str, str]]:
    """(driver name, directory) for every hwmon device."""
    base = os.path.join(SYS, "class", "hwmon")
    out: list[tuple[str, str]] = []
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return out
    for entry in entries:
        directory = os.path.join(base, entry)
        try:
            with open(os.path.join(directory, "name"), "r", encoding="utf-8") as handle:
                name = handle.read().strip()
        except OSError:
            continue
        out.append((name, directory))
    return out


def _read_millidegrees(path: str) -> float | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return int(handle.read().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def cpu_temperature() -> float | None:
    """Celsius from the most CPU-like sensor present, or None."""
    devices = _hwmon_candidates()
    ordered = sorted(
        devices,
        key=lambda item: (
            _CPU_SENSORS.index(item[0]) if item[0] in _CPU_SENSORS else len(_CPU_SENSORS)
        ),
    )
    for name, directory in ordered:
        if name not in _CPU_SENSORS:
            continue
        # Prefer the package sensor where one is labelled.
        best: float | None = None
        try:
            files = sorted(os.listdir(directory))
        except OSError:
            continue
        for filename in files:
            if not re.fullmatch(r"temp\d+_input", filename):
                continue
            value = _read_millidegrees(os.path.join(directory, filename))
            if value is None:
                continue
            label_path = os.path.join(
                directory, filename.replace("_input", "_label")
            )
            label = ""
            try:
                with open(label_path, "r", encoding="utf-8") as handle:
                    label = handle.read().strip().lower()
            except OSError:
                pass
            if "package" in label or "tctl" in label or "tdie" in label:
                return round(value, 1)
            if best is None or value > best:
                best = value
        if best is not None:
            return round(best, 1)

    # No known CPU driver: fall back to thermal_zone0 if it looks sane.
    zone = os.path.join(SYS, "class", "thermal", "thermal_zone0", "temp")
    value = _read_millidegrees(zone)
    if value is not None and 0.0 < value < 150.0:
        return round(value, 1)
    return None


# ── Storage ────────────────────────────────────────────────────────────


@dataclass
class Disk:
    path: str = "/"
    total_bytes: int = 0
    free_bytes: int = 0
    used_bytes: int = 0
    percent: float = 0.0


def disk(path: str = "/") -> Disk:
    try:
        stats = os.statvfs(path)
    except OSError:
        return Disk(path=path)
    block = stats.f_frsize
    total = stats.f_blocks * block
    # f_bavail is what a non-root process can actually use, which is the
    # number a person cares about.
    free = stats.f_bavail * block
    used = max(0, total - free)
    return Disk(
        path=path,
        total_bytes=total,
        free_bytes=free,
        used_bytes=used,
        percent=round(used / total * 100.0, 1) if total else 0.0,
    )


# ── Network throughput ─────────────────────────────────────────────────


def _interface_bytes() -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    try:
        with open(os.path.join(PROC, "net", "dev"), "r", encoding="utf-8") as handle:
            lines = handle.readlines()[2:]
    except OSError:
        return out
    for line in lines:
        name, _, rest = line.partition(":")
        name = name.strip()
        if not name or name == "lo":
            continue
        parts = rest.split()
        if len(parts) < 9:
            continue
        try:
            out[name] = (int(parts[0]), int(parts[8]))
        except ValueError:
            continue
    return out


class NetSampler:
    """Bytes per second, from successive /proc/net/dev readings."""

    def __init__(self) -> None:
        self._previous: dict[str, tuple[int, int]] | None = None
        self._at: float = 0.0

    def sample(self) -> dict[str, float] | None:
        now = time.monotonic()
        current = _interface_bytes()
        previous, self._previous = self._previous, current
        elapsed, self._at = now - self._at, now
        if previous is None or elapsed <= 0:
            return None
        down = sum(
            max(0, current[name][0] - previous.get(name, (0, 0))[0])
            for name in current
        )
        up = sum(
            max(0, current[name][1] - previous.get(name, (0, 0))[1])
            for name in current
        )
        return {
            "downBytesPerSecond": round(down / elapsed, 1),
            "upBytesPerSecond": round(up / elapsed, 1),
        }


# ── Snapshot ───────────────────────────────────────────────────────────


@dataclass
class Snapshot:
    cpuPercent: float | None = None
    cpuCount: int = 1
    loadAverage: list[float] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    temperatureC: float | None = None
    disk: dict[str, Any] = field(default_factory=dict)
    network: dict[str, float] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


#: Module-level samplers, for a long-lived caller.
_CPU = CpuSampler()
_NET = NetSampler()

#: How stale a saved sample may be and still give a meaningful rate.
#: Beyond this the average is over so long a window that it says nothing
#: about now, and a fresh baseline is better than a misleading number.
_SAMPLE_TTL = 30.0


def _state_path() -> str:
    from . import paths

    return str(paths.CACHE_DIR / "sysstat.json")


def _load_state() -> dict[str, Any]:
    try:
        with open(_state_path(), "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    if time.time() - float(loaded.get("at", 0)) > _SAMPLE_TTL:
        return {}
    return loaded


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Written next to the target and renamed, so a bar polling this
        # file never reads a half-written one.
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        os.replace(temporary, path)
    except OSError:
        pass


def snapshot(
    *,
    include_network: bool = True,
    disk_path: str = "/",
    persist: bool = True,
) -> Snapshot:
    """One reading of the machine.

    CPU and network are rates, so they need a previous sample. Inside one
    process the module-level samplers hold it; across processes — which
    is how the bar polls, one `halcyon status system` per tick — it is
    carried in a small cache file. Without that every CLI call would
    report `null` for the two values people most want to see.
    """
    load = load_average()
    state = _load_state() if persist else {}
    new_state: dict[str, Any] = {"at": time.time()}

    cpu_percent: float | None
    current_cpu = _read_cpu_times()
    if current_cpu is not None:
        new_state["cpu"] = [current_cpu.total, current_cpu.idle]
    saved_cpu = state.get("cpu")
    if (
        persist
        and current_cpu is not None
        and isinstance(saved_cpu, list)
        and len(saved_cpu) == 2
    ):
        sampler = CpuSampler()
        sampler._previous = CpuTimes(int(saved_cpu[0]), int(saved_cpu[1]))
        cpu_percent = sampler._compare(current_cpu)
    else:
        cpu_percent = _CPU.sample()

    network: dict[str, float] | None = None
    if include_network:
        current_net = _interface_bytes()
        new_state["net"] = {k: list(v) for k, v in current_net.items()}
        saved_net = state.get("net")
        saved_at = float(state.get("at", 0))
        if persist and isinstance(saved_net, dict) and saved_at:
            elapsed = max(1e-3, time.time() - saved_at)
            previous = {
                k: (int(v[0]), int(v[1]))
                for k, v in saved_net.items()
                if isinstance(v, list) and len(v) == 2
            }
            network = _rate(previous, current_net, elapsed)
        else:
            network = _NET.sample()

    if persist:
        _save_state(new_state)

    return Snapshot(
        cpuPercent=cpu_percent,
        cpuCount=cpu_count(),
        loadAverage=[round(v, 2) for v in load] if load else [],
        memory=asdict(memory()),
        temperatureC=cpu_temperature(),
        disk=asdict(disk(disk_path)),
        network=network,
    )


def _rate(
    previous: dict[str, tuple[int, int]],
    current: dict[str, tuple[int, int]],
    elapsed: float,
) -> dict[str, float]:
    down = sum(
        max(0, current[name][0] - previous.get(name, (0, 0))[0]) for name in current
    )
    up = sum(
        max(0, current[name][1] - previous.get(name, (0, 0))[1]) for name in current
    )
    return {
        "downBytesPerSecond": round(down / elapsed, 1),
        "upBytesPerSecond": round(up / elapsed, 1),
    }


def human_bytes(value: float) -> str:
    """Bytes as a short human string: 1.4 GB, 812 MB, 3 kB."""
    amount = float(value)
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(amount) < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(amount)} B"
            if abs(amount) < 10.0:
                return f"{amount:.1f} {unit}"
            return f"{amount:.0f} {unit}"
        amount /= 1024.0
    return f"{amount:.0f} TB"
