"""`halcyon doctor` — is this installation actually working?

Checks the things that silently break a desktop: a Hyprland that rejects
the generated config, a Quickshell that is not running, two power daemons
fighting, a theme that was never generated. Every finding names the fix.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

from . import __version__, environment, hyprland, paths, power, shell
from . import settings as settings_module


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    fix: str = ""
    severity: str = "error"  # error | warning | info

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    version: str = __version__
    checks: list[Check] = field(default_factory=list)

    def add(self, *args: Any, **kwargs: Any) -> None:
        self.checks.append(Check(*args, **kwargs))

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and c.severity == "error"]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and c.severity == "warning"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "ok": not self.failures,
            "checks": [c.as_dict() for c in self.checks],
        }


def collect() -> Report:
    report = Report()

    _check_settings(report)
    _check_generated(report)
    _check_hyprland(report)
    _check_shell(report)
    _check_waybar(report)
    _check_power(report)
    _check_assistant(report)
    _check_hypernix(report)
    _check_graphics(report)

    return report


def _check_settings(report: Report) -> None:
    try:
        settings = settings_module.load()
    except settings_module.SettingsError as exc:
        report.add(
            "Settings", False, str(exc),
            fix=f"Fix or move aside {paths.SETTINGS_FILE}",
        )
        return
    report.add(
        "Settings", True,
        f"{paths.SETTINGS_FILE} ({len(settings)} sections, schema v{settings.get('version')})",
    )


def _check_generated(report: Report) -> None:
    expected = {
        "theme.json": paths.THEME_JSON,
        "hypr-theme.lua": paths.HYPR_THEME_LUA,
        "hypr-animations.lua": paths.HYPR_ANIM_LUA,
        "hypr-keybinds.lua": paths.GENERATED_DIR / "hypr-keybinds.lua",
        "hypr-runtime.lua": paths.GENERATED_DIR / "hypr-runtime.lua",
        "waybar-colors.css": paths.WAYBAR_CSS,
        "waybar-config.jsonc": paths.GENERATED_DIR / "waybar-config.jsonc",
    }
    missing = [name for name, path in expected.items() if not os.path.isfile(str(path))]
    if missing:
        report.add(
            "Generated files", False,
            f"missing: {', '.join(missing)}",
            fix="Run: halcyon theme apply",
        )
    else:
        report.add("Generated files", True, f"all {len(expected)} present in {paths.GENERATED_DIR}")


def _check_hyprland(report: Report) -> None:
    if not hyprland.available():
        report.add(
            "Hyprland", False, "hyprctl is not on PATH",
            fix="Install Hyprland 0.56 or newer",
        )
        return

    version = hyprland.version()
    if version is None:
        report.add("Hyprland", False, "hyprctl did not report a version", severity="warning")
    elif _older_than(version, (0, 56, 0)):
        report.add(
            "Hyprland", False,
            f"version {version}",
            fix="Halcyon's config uses the Lua API introduced in 0.53 and "
                "options added in 0.56; upgrade Hyprland.",
        )
    else:
        report.add("Hyprland", True, f"version {version}")

    if not hyprland.running():
        report.add(
            "Hyprland session", False, "not running (checked from outside a session)",
            severity="info",
        )
        return

    errors = hyprland.config_errors()
    if errors:
        report.add(
            "Hyprland config", False,
            "\n      ".join(errors[:8]),
            fix="Fix the reported lines, then run: hyprctl reload",
        )
    else:
        report.add("Hyprland config", True, "hyprctl configerrors reports nothing")

    table, source = hyprland.options()
    report.add(
        "Hyprland options", True,
        f"{len(table)} known options (from {source})",
        severity="info",
    )


def _older_than(version: str, minimum: tuple[int, int, int]) -> bool:
    try:
        parts = tuple(int(part) for part in version.split(".")[:3])
    except ValueError:
        return False
    return parts < minimum


def _check_shell(report: Report) -> None:
    binary = shell.binary()
    if binary is None:
        report.add(
            "Quickshell", False, "neither `qs` nor `quickshell` is on PATH",
            fix="Install Quickshell 0.3 or newer. Waybar keeps working without it, "
                "but Spotlight, Control Center and the assistant UI will not.",
        )
        return

    config = paths.XDG_CONFIG_HOME / "quickshell" / shell.CONFIG_NAME / "shell.qml"
    if not config.is_file():
        report.add(
            "Quickshell config", False, f"{config} is missing",
            fix="Re-run ./install.sh",
        )
    elif shell.running():
        report.add("Quickshell", True, f"{binary} · running the {shell.CONFIG_NAME} config")
    else:
        report.add(
            "Quickshell", False, f"{binary} is installed but not running",
            fix="Start it with: halcyon shell start",
            severity="warning",
        )


def _check_waybar(report: Report) -> None:
    if shutil.which("waybar") is None:
        report.add(
            "Waybar", False, "not installed",
            fix="Install waybar. Quickshell keeps working without it.",
            severity="warning",
        )
        return
    style = paths.XDG_CONFIG_HOME / "waybar" / "style.css"
    if not style.is_file():
        report.add("Waybar style", False, f"{style} is missing", fix="Re-run ./install.sh")
    else:
        report.add("Waybar", True, "installed, stylesheet present")


def _check_power(report: Report) -> None:
    conflicts = power.conflicts()
    if conflicts:
        report.add(
            "Power management", False,
            f"more than one daemon is running: {', '.join(conflicts)}",
            fix="Disable all but one, e.g. "
                "`systemctl disable --now tlp` if you keep power-profiles-daemon. "
                "Two of them fight over the CPU governor.",
        )
        return

    backend = power.detect_backend(
        settings_module.load().get("power", {}).get("backend", "auto")
    )
    if backend == "none":
        report.add(
            "Power management", False, "no power daemon installed",
            fix="Install power-profiles-daemon for CPU-level profiles. "
                "Halcyon's own graphics and idle policy works without it.",
            severity="warning",
        )
    else:
        state = power.battery_state()
        detail = backend
        if state.present:
            detail += f" · battery {state.percentage:.0f}%"
            detail += " (charging)" if state.charging else (" (on AC)" if state.plugged else " (on battery)")
        report.add("Power management", True, detail)


def _check_assistant(report: Report) -> None:
    from .assistant import client as assistant_client
    from .assistant import providers as assistant_providers

    settings = settings_module.load()
    if not settings.get("assistant", {}).get("enabled", True):
        report.add("AI assistant", True, "disabled in settings", severity="info")
        return

    for entry in assistant_providers.describe_all(settings):
        report.add(
            f"Assistant · {entry['title']}",
            bool(entry["ok"]),
            str(entry["status"]),
            severity="info" if entry["ok"] else "warning",
        )

    info = assistant_client.status(settings)
    report.add(
        "Assistant daemon",
        bool(info["running"]),
        f"state: {info['state']}",
        fix="" if info["running"] else "Start it with: halcyon assistant start",
        severity="warning",
    )


def _check_hypernix(report: Report) -> None:
    from . import hypernix as hypernix_module

    settings = settings_module.load()
    info = hypernix_module.status(settings)
    if not info["enabled"]:
        report.add("HyperNix", True, "integration disabled", severity="info")
        return
    report.add(
        "HyperNix",
        bool(info["installed"]),
        str(info.get("summary", "")),
        fix=str(info.get("hint", "")),
        severity="info",
    )


def _check_graphics(report: Report) -> None:
    hardware = environment.detect_hardware()
    detail = ", ".join(hardware.gpus) or "none detected"
    if hardware.nvidia_proprietary:
        detail += " (NVIDIA proprietary driver loaded)"
    report.add("Graphics", True, detail, severity="info")

    if hardware.multi_gpu:
        report.add(
            "Multiple GPUs", True,
            "Halcyon does not pick one for you; set AQ_DRM_DEVICES if the "
            "default is wrong.",
            severity="info",
        )


def run(*, json_output: bool = False) -> int:
    report = collect()

    if json_output:
        json.dump(report.as_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if not report.failures else 1

    symbols = {"error": "✗", "warning": "!", "info": "·"}
    print(f"Halcyon {report.version}\n")
    for check in report.checks:
        mark = "✓" if check.ok else symbols.get(check.severity, "✗")
        print(f" {mark} {check.name}")
        if check.detail:
            print(f"      {check.detail}")
        if not check.ok and check.fix:
            print(f"      → {check.fix}")

    print()
    if report.failures:
        print(f"{len(report.failures)} problem(s) need attention.")
    elif report.warnings:
        print(f"Everything essential works; {len(report.warnings)} optional piece(s) missing.")
    else:
        print("Everything checks out.")
    return 1 if report.failures else 0
