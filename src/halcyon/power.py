"""Power profiles, battery state, and the adaptive effects policy.

Three rules shape this module:

* Exactly one power-management daemon is ever driven. power-profiles-daemon,
  TLP and tuned all want to own the CPU governor, and running two of them
  produces a laptop that fights itself. `detect_backend` picks one and
  `conflicts()` reports the rest so the installer can warn instead of
  making it worse.
* Battery state is read from sysfs, not by shelling out. `upower` is not
  installed everywhere and spawning a process every few seconds to learn
  a percentage is exactly the kind of waste this desktop is supposed to
  avoid.
* The adaptive policy only ever *reduces* effects. It never silently
  turns something back on that the user switched off.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any, Iterator

POWER_SUPPLY = "/sys/class/power_supply"

#: Halcyon's three profiles, and what each backend calls them.
PROFILES = ("performance", "balanced", "battery-saver")

_PPD_NAMES = {
    "performance": "performance",
    "balanced": "balanced",
    "battery-saver": "power-saver",
}
_TUNED_NAMES = {
    "performance": "throughput-performance",
    "balanced": "balanced",
    "battery-saver": "powersave",
}


@dataclass
class BatteryState:
    present: bool = False
    percentage: float = 100.0
    charging: bool = False
    plugged: bool = True
    status: str = "unknown"
    time_to_empty: int | None = None
    power_draw: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Battery ────────────────────────────────────────────────────────────


def _read(path: str) -> str | None:
    try:
        with open(path, "r", encoding="ascii", errors="ignore") as handle:
            return handle.read().strip()
    except OSError:
        return None


def _read_int(path: str) -> int | None:
    value = _read(path)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _battery_dirs() -> Iterator[str]:
    try:
        entries = sorted(os.listdir(POWER_SUPPLY))
    except OSError:
        return
    for entry in entries:
        directory = os.path.join(POWER_SUPPLY, entry)
        if _read(os.path.join(directory, "type")) == "Battery":
            yield directory


def _ac_online() -> bool | None:
    try:
        entries = sorted(os.listdir(POWER_SUPPLY))
    except OSError:
        return None
    for entry in entries:
        directory = os.path.join(POWER_SUPPLY, entry)
        if _read(os.path.join(directory, "type")) == "Mains":
            online = _read_int(os.path.join(directory, "online"))
            if online is not None:
                return bool(online)
    return None


def battery_state() -> BatteryState:
    """Aggregate every battery in the machine into one state.

    Laptops with two packs report them separately; a user thinks in terms
    of "how much charge do I have", so the packs are summed by energy
    rather than averaged by percentage.
    """
    state = BatteryState()
    total_now = 0.0
    total_full = 0.0
    draw_total = 0.0
    statuses: list[str] = []

    for directory in _battery_dirs():
        state.present = True
        statuses.append(_read(os.path.join(directory, "status")) or "unknown")

        now = _read_int(os.path.join(directory, "energy_now"))
        full = _read_int(os.path.join(directory, "energy_full"))
        if now is None or full is None:
            now = _read_int(os.path.join(directory, "charge_now"))
            full = _read_int(os.path.join(directory, "charge_full"))

        if now is not None and full:
            total_now += now
            total_full += full
        else:
            capacity = _read_int(os.path.join(directory, "capacity"))
            if capacity is not None:
                total_now += capacity
                total_full += 100

        power = _read_int(os.path.join(directory, "power_now"))
        if power is None:
            # Some drivers expose current and voltage instead of power.
            current = _read_int(os.path.join(directory, "current_now"))
            voltage = _read_int(os.path.join(directory, "voltage_now"))
            if current is not None and voltage is not None:
                power = int(current * voltage / 1_000_000)
        if power:
            draw_total += power

    if not state.present:
        state.percentage = 100.0
        state.plugged = True
        state.status = "ac"
        return state

    if total_full:
        state.percentage = round(min(100.0, max(0.0, total_now / total_full * 100.0)), 1)

    state.status = next(
        (s for s in statuses if s in ("Charging", "Discharging", "Full")),
        statuses[0] if statuses else "unknown",
    )
    state.charging = state.status == "Charging"

    online = _ac_online()
    state.plugged = online if online is not None else state.status != "Discharging"

    if draw_total:
        state.power_draw = round(draw_total / 1_000_000, 2)
        if not state.plugged and total_full:
            hours = (total_now / draw_total) if draw_total else 0
            state.time_to_empty = int(hours * 3600)

    return state


def on_battery() -> bool:
    state = battery_state()
    return state.present and not state.plugged


# ── Backends ───────────────────────────────────────────────────────────


def _service_active(unit: str) -> bool:
    if shutil.which("systemctl") is None:
        return False
    try:
        done = subprocess.run(
            ["systemctl", "is-active", "--quiet", unit],
            timeout=4,
            check=False,
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def available_backends() -> list[str]:
    """Every power daemon that looks installed, running ones first."""
    running = []
    installed = []
    for name, unit, binary in (
        ("power-profiles-daemon", "power-profiles-daemon.service", "powerprofilesctl"),
        ("tlp", "tlp.service", "tlp"),
        ("tuned", "tuned.service", "tuned-adm"),
    ):
        if _service_active(unit):
            running.append(name)
        elif shutil.which(binary):
            installed.append(name)
    return running + installed


def detect_backend(preferred: str = "auto") -> str:
    """The one backend Halcyon will drive.

    An explicit setting wins if that backend is actually present; `auto`
    prefers power-profiles-daemon because it is the only one of the three
    with a real per-profile switching API rather than a config file.
    """
    backends = available_backends()
    if preferred and preferred != "auto":
        return preferred if preferred in backends else "none"
    for candidate in ("power-profiles-daemon", "tuned", "tlp"):
        if candidate in backends:
            return candidate
    return "none"


def conflicts() -> list[str]:
    """Daemons that are running alongside each other and should not be."""
    running = [
        name
        for name, unit in (
            ("power-profiles-daemon", "power-profiles-daemon.service"),
            ("tlp", "tlp.service"),
            ("tuned", "tuned.service"),
        )
        if _service_active(unit)
    ]
    return running if len(running) > 1 else []


def current_profile(backend: str | None = None) -> str | None:
    backend = backend or detect_backend()
    if backend == "power-profiles-daemon" and shutil.which("powerprofilesctl"):
        out = _run(["powerprofilesctl", "get"])
        if out is None:
            return None
        name = out.strip()
        for halcyon_name, ppd_name in _PPD_NAMES.items():
            if ppd_name == name:
                return halcyon_name
        return name or None
    if backend == "tuned" and shutil.which("tuned-adm"):
        out = _run(["tuned-adm", "active"])
        if not out:
            return None
        name = out.rsplit(":", 1)[-1].strip()
        for halcyon_name, tuned_name in _TUNED_NAMES.items():
            if tuned_name == name:
                return halcyon_name
        return name or None
    if backend == "tlp":
        # TLP has no notion of a profile to read back; it switches on
        # AC/battery by itself. Report what that implies instead of
        # pretending we set something.
        return "battery-saver" if on_battery() else "balanced"
    return None


def set_profile(profile: str, backend: str | None = None) -> tuple[bool, str]:
    """Switch the system power profile. Returns `(ok, message)`."""
    if profile not in PROFILES:
        return False, f"Unknown profile {profile!r}; expected one of {', '.join(PROFILES)}"

    backend = backend or detect_backend()

    if backend == "power-profiles-daemon" and shutil.which("powerprofilesctl"):
        target = _PPD_NAMES[profile]
        if _run(["powerprofilesctl", "set", target]) is None:
            return False, f"powerprofilesctl could not select {target}"
        return True, f"power-profiles-daemon → {target}"

    if backend == "tuned" and shutil.which("tuned-adm"):
        target = _TUNED_NAMES[profile]
        if _run(["tuned-adm", "profile", target]) is None:
            return False, f"tuned-adm could not select {target}"
        return True, f"tuned → {target}"

    if backend == "tlp":
        return (
            False,
            "TLP switches profiles automatically on AC/battery and has no "
            "runtime profile API. Halcyon recorded your choice and will "
            "still apply its own graphics and idle policy.",
        )

    return (
        False,
        "No power-management daemon is installed. Halcyon will still apply "
        "its graphics and idle policy; install power-profiles-daemon for "
        "CPU-level control.",
    )


def _run(argv: list[str], timeout: float = 6.0) -> str | None:
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


# ── Adaptive policy ────────────────────────────────────────────────────


@dataclass
class Policy:
    """What the desktop should look like given the current power state."""

    profile: str = "balanced"
    blur_quality: str = "high"
    shadow_quality: str = "high"
    animation_quality: str = "high"
    low_power_graphics: bool = False
    reason: str = "on AC power"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide(settings: dict[str, Any], state: BatteryState | None = None) -> Policy:
    """Work out the effects policy for the current battery state.

    Deliberately conservative: this only ever steps effects *down* from
    what the user chose. Someone who set blur to "low" on a desktop does
    not want a policy raising it.
    """
    state = state or battery_state()
    power = settings.get("power", {})
    graphics = settings.get("graphics", {})
    adaptive = power.get("adaptive", {})

    policy = Policy(
        profile=str(power.get("profile", "balanced")),
        blur_quality=str(graphics.get("blurQuality", "high")),
        shadow_quality=str(graphics.get("shadowQuality", "high")),
        animation_quality=str(graphics.get("animationQuality", "high")),
        low_power_graphics=bool(graphics.get("lowPowerGraphics", False)),
    )

    if not state.present or state.plugged:
        policy.reason = "on AC power" if state.present else "no battery present"
        return policy

    if not adaptive.get("enabled", True):
        policy.reason = "on battery; adaptive power policy is disabled"
        return policy

    policy.reason = "on battery"

    threshold = float(adaptive.get("batteryThreshold", 25))
    critical = float(adaptive.get("criticalThreshold", 10))
    reduce_effects = bool(adaptive.get("reduceEffectsOnBattery", True))

    order = ["off", "low", "medium", "high", "ultra"]

    def step_down(value: str, steps: int) -> str:
        try:
            index = order.index(value)
        except ValueError:
            index = len(order) - 2
        return order[max(0, index - steps)]

    if state.percentage <= critical:
        policy.blur_quality = "off"
        policy.shadow_quality = "off"
        policy.animation_quality = "low"
        policy.low_power_graphics = True
        policy.profile = "battery-saver"
        policy.reason = f"battery at {state.percentage:.0f}% — below the critical threshold"
    elif reduce_effects and state.percentage <= threshold:
        policy.blur_quality = step_down(policy.blur_quality, 2)
        policy.shadow_quality = step_down(policy.shadow_quality, 1)
        policy.animation_quality = step_down(policy.animation_quality, 1)
        policy.low_power_graphics = True
        policy.profile = "battery-saver"
        policy.reason = f"battery at {state.percentage:.0f}% — below the reduced-effects threshold"
    elif reduce_effects:
        # Even with plenty of charge, running off the battery is a good
        # reason to stop paying for the most expensive blur pass.
        policy.blur_quality = step_down(policy.blur_quality, 1)
        policy.reason = f"battery at {state.percentage:.0f}%"

    return policy


def refresh_interval(settings: dict[str, Any], state: BatteryState | None = None) -> int:
    state = state or battery_state()
    intervals = settings.get("power", {}).get("refreshIntervals", {})
    if state.present and not state.plugged:
        return max(2, int(intervals.get("batterySeconds", 15)))
    return max(1, int(intervals.get("acSeconds", 5)))


def waybar_status(settings: dict[str, Any]) -> dict[str, Any]:
    """The JSON a Waybar custom module expects."""
    state = battery_state()
    policy = decide(settings, state)
    backend = detect_backend(settings.get("power", {}).get("backend", "auto"))
    active = current_profile(backend) or policy.profile

    icons = {
        "performance": "󰓅",
        "balanced": "󰾅",
        "battery-saver": "󰌪",
    }
    labels = {
        "performance": "Performance",
        "balanced": "Balanced",
        "battery-saver": "Battery Saver",
    }

    tooltip = [f"Power profile: {labels.get(active, active)}"]
    if backend == "none":
        tooltip.append("No power-management daemon installed")
    else:
        tooltip.append(f"Backend: {backend}")
    tooltip.append(f"Effects: {policy.reason}")

    return {
        "text": icons.get(active, "󰾅"),
        "tooltip": "\n".join(tooltip),
        "class": active,
        "alt": active,
    }


# ── The watcher ────────────────────────────────────────────────────────


def watch(settings_loader, on_change, *, stop_after: float | None = None) -> None:
    """Poll battery state and call `on_change(policy, state)` on changes.

    Polling rather than subscribing to UPower over D-Bus keeps this free
    of dependencies, and the interval is the user's to set: 5 seconds on
    AC, 15 on battery by default. Two file reads at that rate is noise
    next to anything else on the system, and — unlike a busy loop — it
    lets the CPU idle properly between ticks.
    """
    previous: str | None = None
    started = time.monotonic()

    while True:
        settings = settings_loader()
        state = battery_state()
        policy = decide(settings, state)

        fingerprint = json.dumps(policy.as_dict(), sort_keys=True)
        if fingerprint != previous:
            previous = fingerprint
            on_change(policy, state)

        if stop_after is not None and time.monotonic() - started >= stop_after:
            return
        time.sleep(refresh_interval(settings, state))
