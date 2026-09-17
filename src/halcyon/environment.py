"""Deciding which environment variables this machine actually needs.

Copying a stranger's env block is how Hyprland setups end up broken:
`GBM_BACKEND=nvidia-drm` on a machine without the proprietary driver, a
VA-API driver name for hardware that is not there, a Qt platform theme
for a package that was never installed. Every variable here is gated on
something observable, and `explain()` says what that something was.

The NVIDIA set follows Hyprland's current guidance (only the two VA-API
and GLX vendor hints); the older `WLR_*` and `GBM_BACKEND` advice is no
longer correct for 0.5x and is deliberately absent.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Any

SYSFS_DRM = "/sys/class/drm"

_VENDOR_IDS = {
    "0x8086": "intel",
    "0x1002": "amd",
    "0x1022": "amd",
    "0x10de": "nvidia",
    "0x1af4": "virtio",
    "0x1b36": "virtio",
}


@dataclass
class Hardware:
    gpus: list[str] = field(default_factory=list)
    nvidia_proprietary: bool = False
    laptop: bool = False
    battery: bool = False

    @property
    def primary(self) -> str:
        if "nvidia" in self.gpus:
            return "nvidia"
        return self.gpus[0] if self.gpus else "unknown"

    @property
    def multi_gpu(self) -> bool:
        return len(self.gpus) > 1


def detect_hardware() -> Hardware:
    hardware = Hardware()

    try:
        entries = sorted(os.listdir(SYSFS_DRM))
    except OSError:
        entries = []

    for entry in entries:
        if not entry.startswith("card") or "-" in entry:
            continue
        vendor_file = os.path.join(SYSFS_DRM, entry, "device", "vendor")
        try:
            with open(vendor_file, "r", encoding="ascii") as handle:
                vendor_id = handle.read().strip().lower()
        except OSError:
            continue
        vendor = _VENDOR_IDS.get(vendor_id, "other")
        if vendor not in hardware.gpus:
            hardware.gpus.append(vendor)

    hardware.nvidia_proprietary = os.path.exists("/proc/driver/nvidia/version")

    try:
        chassis = open("/sys/class/dmi/id/chassis_type", encoding="ascii").read().strip()
        hardware.laptop = chassis in {"8", "9", "10", "11", "14", "30", "31", "32"}
    except OSError:
        pass

    power_supply = "/sys/class/power_supply"
    try:
        for entry in os.listdir(power_supply):
            type_file = os.path.join(power_supply, entry, "type")
            try:
                if open(type_file, encoding="ascii").read().strip() == "Battery":
                    hardware.battery = True
                    hardware.laptop = True
                    break
            except OSError:
                continue
    except OSError:
        pass

    return hardware


def _have(command: str) -> bool:
    return shutil.which(command) is not None


def build(
    settings: dict[str, Any], hardware: Hardware | None = None
) -> tuple[dict[str, str], list[str]]:
    """Return `(variables, notes)`.

    `notes` explains each hardware-specific decision so `halcyon
    diagnose` can show why a variable is or is not set.
    """
    hardware = hardware or detect_hardware()
    appearance = settings.get("appearance", {})
    graphics = settings.get("graphics", {})

    env: dict[str, str] = {}
    notes: list[str] = []

    cursor_theme = str(appearance.get("cursorTheme", "")).strip()
    cursor_size = int(appearance.get("cursorSize", 24))
    env["XCURSOR_SIZE"] = str(cursor_size)
    env["HYPRCURSOR_SIZE"] = str(cursor_size)
    if cursor_theme:
        env["XCURSOR_THEME"] = cursor_theme
        env["HYPRCURSOR_THEME"] = cursor_theme

    # Toolkit hints. These are safe everywhere: they only say "prefer
    # Wayland", which is the whole point of running Hyprland.
    env["QT_QPA_PLATFORM"] = "wayland;xcb"
    env["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    env["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"
    env["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    env["GDK_BACKEND"] = "wayland,x11"
    env["SDL_VIDEODRIVER"] = "wayland"
    env["CLUTTER_BACKEND"] = "wayland"
    env["MOZ_ENABLE_WAYLAND"] = "1"
    env["_JAVA_AWT_WM_NONREPARENTING"] = "1"

    # Only claim a platform theme when the package that implements it is
    # installed; otherwise every Qt app logs a warning at startup.
    if _have("qt6ct"):
        env["QT_QPA_PLATFORMTHEME"] = "qt6ct"
        notes.append("Qt platform theme set to qt6ct (found on PATH).")
    elif _have("qt5ct"):
        env["QT_QPA_PLATFORMTHEME"] = "qt5ct"
        notes.append("Qt platform theme set to qt5ct (qt6ct not installed).")
    else:
        notes.append(
            "No Qt platform theme set: neither qt6ct nor qt5ct is installed."
        )

    if os.path.exists("/etc/NIXOS"):
        env["NIXOS_OZONE_WL"] = "1"
        notes.append("NixOS detected: NIXOS_OZONE_WL enables Wayland for Electron apps.")
    else:
        env["ELECTRON_OZONE_PLATFORM_HINT"] = "auto"

    override = str(graphics.get("gpuOverrides", "auto")).lower()
    if override == "none":
        notes.append("graphics.gpuOverrides is 'none': no GPU variables applied.")
        return env, notes

    if hardware.nvidia_proprietary:
        # Hyprland's current NVIDIA guidance is exactly these two. The
        # GBM_BACKEND / WLR_* advice that circulates online predates 0.4x
        # and causes more breakage than it fixes.
        env["LIBVA_DRIVER_NAME"] = "nvidia"
        env["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
        notes.append(
            "NVIDIA proprietary driver is loaded (/proc/driver/nvidia/version): "
            "applied LIBVA_DRIVER_NAME and __GLX_VENDOR_LIBRARY_NAME."
        )
        if _have("nvidia-smi"):
            env["NVD_BACKEND"] = "direct"
            notes.append("NVD_BACKEND=direct set for the nvidia-vaapi-driver.")
    elif "nvidia" in hardware.gpus:
        notes.append(
            "An NVIDIA card is present but the proprietary driver is not "
            "loaded (nouveau); NVIDIA-specific variables were not applied."
        )

    if "intel" in hardware.gpus and not hardware.nvidia_proprietary:
        if os.path.exists("/usr/lib/dri/iHD_drv_video.so") or os.path.exists(
            "/usr/lib64/dri/iHD_drv_video.so"
        ):
            env["LIBVA_DRIVER_NAME"] = "iHD"
            notes.append("Intel media driver found: LIBVA_DRIVER_NAME=iHD.")
        else:
            notes.append(
                "Intel GPU found but intel-media-driver is not installed; "
                "leaving VA-API auto-detection alone."
            )

    if "amd" in hardware.gpus and not hardware.nvidia_proprietary:
        env["LIBVA_DRIVER_NAME"] = "radeonsi"
        notes.append("AMD GPU found: LIBVA_DRIVER_NAME=radeonsi.")

    if hardware.multi_gpu:
        notes.append(
            "More than one GPU is present ("
            + ", ".join(hardware.gpus)
            + "). Halcyon does not guess which one should drive the "
            "session — set AQ_DRM_DEVICES yourself if the default is wrong."
        )

    if graphics.get("lowPowerGraphics"):
        notes.append("Low Power Graphics is on: blur and shadow tiers are clamped.")

    return env, notes


def explain() -> str:
    """A human-readable summary, used by `halcyon diagnose`."""
    from . import settings as settings_module

    hardware = detect_hardware()
    env, notes = build(settings_module.load(), hardware)

    lines = [
        f"GPUs detected: {', '.join(hardware.gpus) or 'none'}",
        f"Primary: {hardware.primary}",
        f"NVIDIA proprietary driver loaded: {'yes' if hardware.nvidia_proprietary else 'no'}",
        f"Laptop: {'yes' if hardware.laptop else 'no'}  Battery: {'yes' if hardware.battery else 'no'}",
        "",
        "Environment variables:",
    ]
    lines += [f"  {key}={value}" for key, value in sorted(env.items())]
    if notes:
        lines += ["", "Notes:"] + [f"  - {note}" for note in notes]
    return "\n".join(lines)
