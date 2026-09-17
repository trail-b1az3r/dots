"""The `halcyon` command.

Every keybind, every Waybar module and every button in the shell reaches
the system through this one entry point, which is what makes the desktop
configurable: change a setting, and the thing that reads it is the same
thing the keybind already calls.

Written against argparse and the standard library so it starts fast — a
keybind that takes 300 ms to spawn a Python interpreter feels broken, and
importing a CLI framework is most of that budget.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Sequence

from . import __version__

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def _print(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(message, file=stream)


def _result(ok: bool, message: str, *, quiet: bool = False) -> int:
    if message and not quiet:
        _print(message, error=not ok)
    return EXIT_OK if ok else EXIT_FAILED


def _json_out(payload: Any) -> int:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return EXIT_OK


# ── theme ──────────────────────────────────────────────────────────────


def cmd_theme(args: argparse.Namespace) -> int:
    from . import pipeline, render, settings as settings_module

    if args.theme_command == "list-presets":
        presets = settings_module.preset_files()
        for name in sorted(presets):
            preset = settings_module.load_preset(name)
            _print(f"{preset.get('name', name):<14} {preset.get('description', '')}")
        return EXIT_OK

    if args.theme_command == "preset":
        try:
            settings_module.apply_preset(args.name)
        except settings_module.SettingsError as exc:
            return _result(False, str(exc))
        result = pipeline.apply()
        return _result(True, f"Applied the {args.name} preset ({len(result.written)} files).")

    if args.theme_command == "toggle-mode":
        current = str(settings_module.get("appearance.mode"))
        # `auto` follows the wallpaper, so toggling out of it has to pick
        # the opposite of what is actually on screen, not the setting.
        if current == "auto":
            _settings, tokens = pipeline.build()
            current = tokens["mode"]
        new_mode = "light" if current == "dark" else "dark"
        settings_module.set_value("appearance.mode", new_mode)
        result = pipeline.apply()
        return _result(True, f"Switched to {result.mode} mode.")

    try:
        result = pipeline.apply(reload=not args.no_reload)
    except render.RenderError as exc:
        return _result(False, str(exc))

    if args.json:
        return _json_out(
            {
                "mode": result.mode,
                "accent": result.accent,
                "paletteSource": result.palette_source,
                "written": result.written,
                "reloaded": result.reloaded,
                "warnings": result.warnings,
            }
        )

    _print(f"Theme applied: {result.mode} mode, accent {result.accent} "
           f"(from the {result.palette_source}).")
    for path in result.written:
        _print(f"  wrote {path}")
    if result.reloaded:
        _print(f"  reloaded {', '.join(result.reloaded)}")
    for warning in result.warnings:
        _print(f"  ! {warning}", error=True)
    return EXIT_OK


# ── settings ───────────────────────────────────────────────────────────


def cmd_settings(args: argparse.Namespace) -> int:
    from . import pipeline, paths, settings as settings_module

    try:
        if args.settings_command == "get":
            value = settings_module.get(args.path)
            return _json_out(value) if args.json else _result(True, _render_value(value))

        if args.settings_command == "set":
            settings_module.set_value(args.path, args.value)
            if not args.no_apply:
                pipeline.apply()
            return _result(True, f"{args.path} = {settings_module.get(args.path)!r}")

        if args.settings_command == "unset":
            settings_module.unset(args.path)
            if not args.no_apply:
                pipeline.apply()
            return _result(True, f"{args.path} reset to its default.")

        if args.settings_command == "path":
            return _result(True, str(paths.SETTINGS_FILE))

        if args.settings_command == "list":
            merged = settings_module.load()
            if args.json:
                return _json_out(merged)
            for line in _flatten(merged):
                _print(line)
            return EXIT_OK

        if args.settings_command == "schema":
            return _json_out(settings_module.defaults())

    except settings_module.SettingsError as exc:
        return _result(False, str(exc))

    return EXIT_USAGE


def _render_value(value: Any) -> str:
    return json.dumps(value) if isinstance(value, (dict, list)) else str(value)


def _flatten(node: Any, prefix: str = "") -> list[str]:
    lines: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten(value, path))
    else:
        lines.append(f"{prefix} = {_render_value(node)}")
    return lines


# ── search ─────────────────────────────────────────────────────────────


def cmd_search(args: argparse.Namespace) -> int:
    from . import search as search_module, settings as settings_module

    settings = settings_module.load()
    results = search_module.search(
        args.query,
        settings,
        limit=args.limit,
        providers=args.provider or None,
    )

    if args.json:
        return _json_out([result.as_dict() for result in results])

    for result in results:
        _print(f"{result.category:<16} {result.title}")
        if result.subtitle:
            _print(f"{'':<16} {result.subtitle}")
    return EXIT_OK


def cmd_activate(args: argparse.Namespace) -> int:
    """Perform the `activate` payload attached to a search result."""
    from . import actions as actions_module, desktop, hypernix, hyprland
    from . import settings as settings_module, shell

    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        return _result(False, f"Not valid JSON: {exc}")
    if not isinstance(payload, dict):
        return _result(False, "Expected a JSON object.")

    kind = str(payload.get("type", ""))

    if kind == "action":
        invocation = actions_module.invoke(
            str(payload.get("action", "")),
            payload.get("params") or {},
            confirmed=bool(args.confirm),
        )
        if args.json:
            return _json_out(invocation.as_dict())
        return _result(invocation.ok, invocation.message)

    if kind == "dispatch":
        expression = str(payload.get("expression", ""))
        if not expression.startswith("hl.dsp."):
            return _result(False, "Only Hyprland dispatchers may be sent this way.")
        return _result(hyprland.dispatch(expression), "")

    if kind == "copy":
        text = str(payload.get("text", ""))
        import shutil
        import subprocess

        if shutil.which("wl-copy") is None:
            return _result(False, "wl-clipboard is not installed.")
        subprocess.run(["wl-copy", "--", text], timeout=5, check=False)
        return _result(True, "Copied.")

    if kind == "clipboard":
        import shutil
        import subprocess

        if shutil.which("cliphist") is None:
            return _result(False, "cliphist is not installed.")
        entry = str(payload.get("entry", ""))
        decoded = subprocess.run(
            ["cliphist", "decode", entry], capture_output=True, timeout=5, check=False
        ).stdout
        subprocess.run(["wl-copy"], input=decoded, timeout=5, check=False)
        return _result(True, "Copied from history.")

    if kind == "assistant":
        ok, message = shell.call("assistant", "ask", [str(payload.get("prompt", ""))])
        if ok:
            return _result(True, "")
        from .assistant import client as assistant_client

        return _result(*assistant_client.ask_detached(str(payload.get("prompt", ""))))

    if kind == "hypernix":
        settings = settings_module.load()
        command = str(payload.get("command", "launch"))
        if command == "launch":
            return _result(*hypernix.launch(settings))
        return _result(*desktop.open_terminal(settings, command.split()))

    return _result(False, f"Unknown activation type {kind!r}.")


# ── actions ────────────────────────────────────────────────────────────


def cmd_action(args: argparse.Namespace) -> int:
    from . import actions as actions_module

    if args.list:
        return _json_out(actions_module.catalog())

    params: dict[str, Any] = {}
    for pair in args.params:
        key, sep, value = pair.partition("=")
        if not sep:
            return _result(False, f"Expected name=value, got {pair!r}")
        params[key] = value

    invocation = actions_module.invoke(args.id, params, confirmed=args.confirm)
    if args.json:
        return _json_out(invocation.as_dict())
    return _result(invocation.ok, invocation.message)


# ── hardware shortcuts ─────────────────────────────────────────────────


def cmd_audio(args: argparse.Namespace) -> int:
    from . import desktop, shell

    if args.audio_command == "volume":
        value = args.value
        if value.startswith(("+", "-")):
            ok, message = desktop.adjust_volume(int(value))
        else:
            ok, message = desktop.set_volume(int(value))
        _show_osd("volume")
        return _result(ok, message, quiet=True) if ok else _result(ok, message)

    if args.audio_command == "mute":
        ok, message = desktop.mute_output(args.state)
        _show_osd("volume")
        return _result(ok, message, quiet=ok)

    if args.audio_command == "mic":
        ok, message = desktop.mute_input(args.state)
        _show_osd("microphone")
        return _result(ok, message, quiet=ok)

    if args.audio_command == "status":
        return _json_out(
            {"output": desktop.volume_state(), "input": desktop.microphone_state()}
        )
    return EXIT_USAGE


def cmd_backlight(args: argparse.Namespace) -> int:
    from . import desktop

    if args.value == "status":
        return _json_out(desktop.backlight_state())
    if args.value.startswith(("+", "-")):
        ok, message = desktop.adjust_backlight(int(args.value))
    else:
        ok, message = desktop.set_backlight(int(args.value))
    _show_osd("brightness")
    return _result(ok, message, quiet=ok)


def _show_osd(kind: str) -> None:
    """Ask the shell to show its HUD. Silent when the shell is absent."""
    from . import shell

    shell.call("osd", "show", [kind])


def cmd_media(args: argparse.Namespace) -> int:
    from . import desktop

    if args.media_command == "status":
        return _json_out(desktop.media_status())
    ok, message = desktop.media(args.media_command)
    return _result(ok, message, quiet=ok)


def cmd_screenshot(args: argparse.Namespace) -> int:
    from . import desktop, settings as settings_module

    ok, message = desktop.screenshot(args.mode, settings_module.load())
    return _result(ok, message if not ok else f"Saved to {message}")


def cmd_record(args: argparse.Namespace) -> int:
    from . import desktop, settings as settings_module

    ok, message = desktop.record(args.record_command, settings_module.load())
    return _result(ok, message)


def cmd_window(args: argparse.Namespace) -> int:
    from . import windows

    if args.window_command == "minimize":
        return _result(*windows.minimise())
    if args.window_command == "hide":
        return _result(*windows.hide_application())
    if args.window_command == "restore":
        return _result(*windows.restore())
    if args.window_command == "list":
        return _json_out(windows.minimised())
    return EXIT_USAGE


def cmd_open(args: argparse.Namespace) -> int:
    from . import apps, desktop, settings as settings_module

    settings = settings_module.load()
    applications = settings.get("applications", {})

    if args.target == "terminal":
        return _result(*desktop.open_terminal(settings))

    if args.target in ("files", "file-manager"):
        name = str(applications.get("fileManager", "")).strip()
        return _result(*_open_named(name or "nautilus", settings))

    if args.target == "browser":
        name = str(applications.get("browser", "")).strip()
        if name:
            return _result(*_open_named(name, settings))
        return _result(*desktop.open_path("https://duckduckgo.com"))

    if args.target == "editor":
        name = str(applications.get("editor", "")).strip()
        if not name:
            return _result(False, "No editor is configured (Settings → Applications).")
        return _result(*_open_named(name, settings))

    return _result(*desktop.open_path(args.target))


def _open_named(name: str, settings: dict[str, Any]):
    from . import apps, desktop

    application = apps.find(name)
    if application is None:
        return False, f"{name!r} is not installed."
    if application.terminal:
        return desktop.open_terminal(settings, application.exec_argv)
    ok, message = desktop._spawn(application.exec_argv)
    return ok, (f"Opening {application.name}" if ok else message)


# ── wallpaper, power, notifications ────────────────────────────────────


def cmd_wallpaper(args: argparse.Namespace) -> int:
    from . import wallpaper as wallpaper_module

    if args.wallpaper_command == "set":
        return _result(*wallpaper_module.set_wallpaper(args.path, monitor=args.monitor))
    if args.wallpaper_command == "next":
        return _result(*wallpaper_module.next_wallpaper())
    if args.wallpaper_command == "current":
        return _result(True, wallpaper_module.current() or "(none)")
    if args.wallpaper_command == "list":
        return _json_out(wallpaper_module.library())
    if args.wallpaper_command == "watch":
        wallpaper_module.watch()
        return EXIT_OK
    return EXIT_USAGE


def cmd_power(args: argparse.Namespace) -> int:
    from . import pipeline, power as power_module, settings as settings_module

    settings = settings_module.load()
    backend = power_module.detect_backend(settings.get("power", {}).get("backend", "auto"))

    if args.power_command == "status":
        return _json_out(
            {
                "backend": backend,
                "available": power_module.available_backends(),
                "conflicts": power_module.conflicts(),
                "profile": power_module.current_profile(backend),
                "battery": power_module.battery_state().as_dict(),
                "policy": power_module.decide(settings).as_dict(),
            }
        )

    if args.power_command == "profile":
        ok, message = power_module.set_profile(args.name, backend)
        settings_module.set_value("power.profile", args.name)
        pipeline.apply(outputs=("theme", "hypr-theme", "waybar-css"))
        from . import state

        state.refresh_waybar("power")
        return _result(ok or backend == "none", message)

    if args.power_command == "cycle":
        order = list(power_module.PROFILES)
        current = power_module.current_profile(backend) or settings.get("power", {}).get(
            "profile", "balanced"
        )
        index = order.index(current) if current in order else 1
        target = order[(index + 1) % len(order)]
        ok, message = power_module.set_profile(target, backend)
        settings_module.set_value("power.profile", target)
        pipeline.apply(outputs=("theme", "hypr-theme", "waybar-css"))
        from . import desktop, state

        state.refresh_waybar("power")
        desktop.notify("Power profile", target.replace("-", " ").title())
        return _result(ok or backend == "none", message)

    if args.power_command == "watch":
        return _power_watch()

    return EXIT_USAGE


def _power_watch() -> int:
    """Apply the adaptive effects policy as the battery state changes."""
    from . import desktop, pipeline, power as power_module, settings as settings_module
    from . import state

    def on_change(policy: power_module.Policy, battery: power_module.BatteryState) -> None:
        settings = settings_module.load()
        # The policy is applied as an override on top of the user's
        # settings, never written back into them: unplugging must not
        # permanently rewrite someone's chosen blur quality.
        overridden = json.loads(json.dumps(settings))
        overridden["graphics"]["blurQuality"] = policy.blur_quality
        overridden["graphics"]["shadowQuality"] = policy.shadow_quality
        overridden["graphics"]["animationQuality"] = policy.animation_quality
        overridden["graphics"]["lowPowerGraphics"] = policy.low_power_graphics

        pipeline.apply(settings=overridden, outputs=("theme", "hypr-theme", "hypr-animations"))
        state.write("power", {"policy": policy.as_dict(), "battery": battery.as_dict()})

        critical = float(
            settings.get("power", {}).get("adaptive", {}).get("criticalThreshold", 10)
        )
        if battery.present and not battery.plugged and battery.percentage <= critical:
            desktop.notify(
                "Battery critically low",
                f"{battery.percentage:.0f}% remaining — effects reduced.",
                urgency="critical",
            )

    try:
        power_module.watch(settings_module.load, on_change)
    except KeyboardInterrupt:
        return EXIT_OK
    return EXIT_OK


def cmd_notify(args: argparse.Namespace) -> int:
    from . import settings as settings_module, shell, state

    if args.notify_command == "dnd":
        current = bool(settings_module.get("notifications.doNotDisturb"))
        value = (not current) if args.state == "toggle" else args.state == "on"
        settings_module.set_value("notifications.doNotDisturb", value)
        shell.call("notifications", "setDoNotDisturb", ["true" if value else "false"])
        payload = state.read("notifications", {"count": 0})
        payload["dnd"] = value
        state.write("notifications", payload)
        return _result(True, f"Do Not Disturb {'on' if value else 'off'}")

    if args.notify_command == "send":
        from . import desktop

        return _result(
            desktop.notify(args.summary, args.body or ""), "", quiet=True
        )

    if args.notify_command == "state":
        # Written by the shell, read by the bar. The shell owns the
        # notification list; this is how it tells Waybar the count moved
        # without Waybar having to ask.
        state.write(
            "notifications",
            {"count": max(0, int(args.count)), "dnd": args.dnd == "on"},
        )
        return EXIT_OK

    return EXIT_USAGE


# ── status (Waybar) ────────────────────────────────────────────────────


def cmd_status(args: argparse.Namespace) -> int:
    from . import hypernix, power as power_module, settings as settings_module, state

    settings = settings_module.load()

    if args.what == "power":
        payload = power_module.waybar_status(settings)
    elif args.what == "gpu":
        payload = _gpu_status()
    elif args.what == "hypernix":
        payload = hypernix.waybar_status(settings)
    elif args.what == "assistant":
        payload = _assistant_status(settings)
    elif args.what == "notifications":
        payload = _notification_status(settings)
    elif args.what == "battery":
        payload = power_module.battery_state().as_dict()
    else:
        return EXIT_USAGE

    if args.waybar:
        return _json_out(payload)
    _print(json.dumps(payload, indent=2))
    return EXIT_OK


def _gpu_status() -> dict[str, Any]:
    """GPU load, when the vendor makes it readable without root."""
    from . import environment

    hardware = environment.detect_hardware()

    # AMD exposes utilisation in sysfs; no tool needed.
    for card in sorted(os.listdir("/sys/class/drm")) if os.path.isdir("/sys/class/drm") else []:
        busy = f"/sys/class/drm/{card}/device/gpu_busy_percent"
        if os.path.isfile(busy):
            try:
                percent = int(open(busy, encoding="ascii").read().strip())
            except (OSError, ValueError):
                continue
            return {
                "text": f"󰢮 {percent}%",
                "tooltip": f"GPU load {percent}%",
                "class": "active" if percent > 50 else "idle",
            }

    import shutil
    import subprocess

    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=4, check=False,
            ).stdout.strip()
            usage, temperature = (part.strip() for part in out.split(",")[:2])
            return {
                "text": f"󰢮 {usage}%",
                "tooltip": f"GPU load {usage}%  ·  {temperature}°C",
                "class": "active" if int(usage) > 50 else "idle",
            }
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass

    return {
        "text": "󰢮",
        "tooltip": f"GPU: {', '.join(hardware.gpus) or 'unknown'}\n"
                   "No readable load counter on this driver",
        "class": "idle",
    }


def _assistant_status(settings: dict[str, Any]) -> dict[str, Any]:
    from .assistant import client as assistant_client

    if not settings.get("assistant", {}).get("enabled", True):
        return {"text": "", "tooltip": "", "class": "disabled"}

    info = assistant_client.status(settings)
    icons = {
        "listening": "󰍬",
        "thinking": "󰧑",
        "speaking": "󰔊",
        "idle": "󰚩",
        "offline": "󰚩",
    }
    return {
        "text": icons.get(info["state"], "󰚩"),
        "tooltip": info["tooltip"],
        "class": info["state"],
        "alt": info["state"],
    }


def _notification_status(settings: dict[str, Any]) -> dict[str, Any]:
    from . import state

    payload = state.read("notifications", {"count": 0, "dnd": False})
    count = int(payload.get("count", 0))
    dnd = bool(payload.get("dnd") or settings.get("notifications", {}).get("doNotDisturb"))

    if dnd:
        return {
            "text": "󰂛",
            "tooltip": f"Do Not Disturb is on · {count} in history",
            "class": "dnd",
        }
    if count:
        return {
            "text": f"󰂚 {count}",
            "tooltip": f"{count} notification(s)",
            "class": "unread",
        }
    return {"text": "󰂜", "tooltip": "No notifications", "class": "idle"}


def cmd_refresh(args: argparse.Namespace) -> int:
    from . import state

    return _result(state.refresh_waybar(args.module), "", quiet=True)


# ── shell, session, hypernix ───────────────────────────────────────────


def cmd_shell(args: argparse.Namespace) -> int:
    from . import shell

    if args.target == "start":
        return _result(*shell.start())
    if args.target == "stop":
        return _result(*shell.stop())

    # Surfaces with a standalone stand-in use it when the shell is down,
    # so a keybind still does something. The rest fail quietly: a panel
    # that cannot open should not pop an error at someone who pressed a
    # key by accident.
    ok, message = shell.call_or_fallback(args.target, args.function, args.args)
    if sys.stdout.isatty():
        return _result(ok, message)
    return _result(ok, message, quiet=True)


def cmd_session(args: argparse.Namespace) -> int:
    from . import desktop, pipeline, shell

    if args.session_command == "lock":
        return _result(*desktop.lock())
    if args.session_command == "suspend":
        return _result(*desktop.suspend())
    if args.session_command == "hibernate":
        return _result(*desktop.hibernate())
    if args.session_command == "reboot":
        return _result(*desktop.reboot())
    if args.session_command == "shutdown":
        return _result(*desktop.shutdown())
    if args.session_command == "logout":
        return _result(*desktop.logout())
    if args.session_command == "reload":
        result = pipeline.apply()
        shell.call("shell", "reload", [])
        return _result(True, f"Reloaded ({', '.join(result.reloaded) or 'nothing running'}).")
    return EXIT_USAGE


def cmd_hypernix(args: argparse.Namespace) -> int:
    from . import hypernix as hypernix_module, settings as settings_module

    settings = settings_module.load()

    if args.hypernix_command == "status":
        payload = (
            hypernix_module.waybar_status(settings)
            if args.waybar
            else hypernix_module.status(settings)
        )
        return _json_out(payload)
    if args.hypernix_command == "launch":
        return _result(*hypernix_module.launch(settings))
    if args.hypernix_command == "devices":
        devices = hypernix_module.devices(settings)
        if devices is None:
            return _result(False, "HyperNix is not installed or would not answer.")
        return _json_out(devices)
    return EXIT_USAGE


def cmd_assistant(args: argparse.Namespace) -> int:
    from .assistant import cli as assistant_cli

    return assistant_cli.dispatch(args)


def cmd_doctor(args: argparse.Namespace) -> int:
    from . import doctor

    return doctor.run(json_output=args.json)


def cmd_version(_args: argparse.Namespace) -> int:
    _print(f"halcyon {__version__}")
    return EXIT_OK


# ── Parser ─────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="halcyon",
        description="Halcyon desktop control.",
    )
    parser.add_argument("--version", action="version", version=f"halcyon {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    theme = sub.add_parser("theme", help="regenerate and apply the theme")
    theme_sub = theme.add_subparsers(dest="theme_command")
    apply_cmd = theme_sub.add_parser("apply", help="regenerate every theme artefact")
    apply_cmd.add_argument("--no-reload", action="store_true")
    apply_cmd.add_argument("--json", action="store_true")
    theme_sub.add_parser("list-presets", help="list the glass presets")
    preset = theme_sub.add_parser("preset", help="apply a glass preset")
    preset.add_argument("name")
    theme_sub.add_parser("toggle-mode", help="switch between light and dark")
    theme.set_defaults(func=cmd_theme, theme_command="apply", no_reload=False, json=False)

    settings_parser = sub.add_parser("settings", help="read and write settings")
    settings_sub = settings_parser.add_subparsers(dest="settings_command", required=True)
    get = settings_sub.add_parser("get")
    get.add_argument("path")
    get.add_argument("--json", action="store_true")
    set_cmd = settings_sub.add_parser("set")
    set_cmd.add_argument("path")
    set_cmd.add_argument("value")
    set_cmd.add_argument("--no-apply", action="store_true")
    unset_cmd = settings_sub.add_parser("unset")
    unset_cmd.add_argument("path")
    unset_cmd.add_argument("--no-apply", action="store_true")
    list_cmd = settings_sub.add_parser("list")
    list_cmd.add_argument("--json", action="store_true")
    settings_sub.add_parser("path")
    settings_sub.add_parser("schema")
    settings_parser.set_defaults(func=cmd_settings, json=False, no_apply=False)

    search_parser = sub.add_parser("search", help="run a Spotlight query")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--provider", action="append")
    search_parser.add_argument("--json", action="store_true")
    search_parser.set_defaults(func=cmd_search)

    activate = sub.add_parser("activate", help="perform a search result's action")
    activate.add_argument("payload")
    activate.add_argument("--confirm", action="store_true")
    activate.add_argument("--json", action="store_true")
    activate.set_defaults(func=cmd_activate)

    action = sub.add_parser("action", help="invoke a desktop action")
    action.add_argument("id", nargs="?", default="")
    action.add_argument("params", nargs="*")
    action.add_argument("--confirm", action="store_true")
    action.add_argument("--list", action="store_true")
    action.add_argument("--json", action="store_true")
    action.set_defaults(func=cmd_action)

    audio = sub.add_parser("audio", help="volume and microphone")
    audio_sub = audio.add_subparsers(dest="audio_command", required=True)
    volume = audio_sub.add_parser("volume")
    volume.add_argument("value")
    mute = audio_sub.add_parser("mute")
    mute.add_argument("state", nargs="?", default="toggle", choices=["on", "off", "toggle"])
    mic = audio_sub.add_parser("mic")
    mic.add_argument("state", nargs="?", default="toggle", choices=["on", "off", "toggle"])
    audio_sub.add_parser("status")
    audio.set_defaults(func=cmd_audio)

    backlight = sub.add_parser("backlight", help="screen brightness")
    backlight.add_argument("value")
    backlight.set_defaults(func=cmd_backlight)

    media = sub.add_parser("media", help="media playback")
    media.add_argument(
        "media_command",
        choices=["play-pause", "play", "pause", "next", "previous", "stop", "status"],
    )
    media.set_defaults(func=cmd_media)

    screenshot = sub.add_parser("screenshot", help="capture the screen")
    screenshot.add_argument("mode", choices=["screen", "region", "window"], default="screen", nargs="?")
    screenshot.set_defaults(func=cmd_screenshot)

    record = sub.add_parser("record", help="screen recording")
    record.add_argument("record_command", choices=["start", "stop", "toggle"], default="toggle", nargs="?")
    record.set_defaults(func=cmd_record)

    window = sub.add_parser("window", help="minimise, hide and restore windows")
    window.add_argument("window_command", choices=["minimize", "hide", "restore", "list"])
    window.set_defaults(func=cmd_window)

    open_parser = sub.add_parser("open", help="open an app, file or URL")
    open_parser.add_argument("target")
    open_parser.set_defaults(func=cmd_open)

    wallpaper = sub.add_parser("wallpaper", help="the wallpaper system")
    wallpaper_sub = wallpaper.add_subparsers(dest="wallpaper_command", required=True)
    set_wallpaper = wallpaper_sub.add_parser("set")
    set_wallpaper.add_argument("path")
    set_wallpaper.add_argument("--monitor", default=None)
    wallpaper_sub.add_parser("next")
    wallpaper_sub.add_parser("current")
    wallpaper_sub.add_parser("list")
    wallpaper_sub.add_parser("watch")
    wallpaper.set_defaults(func=cmd_wallpaper, monitor=None)

    power = sub.add_parser("power", help="power profiles and the battery policy")
    power_sub = power.add_subparsers(dest="power_command", required=True)
    profile = power_sub.add_parser("profile")
    profile.add_argument("name", choices=["performance", "balanced", "battery-saver"])
    power_sub.add_parser("cycle")
    power_sub.add_parser("status")
    power_sub.add_parser("watch")
    power.set_defaults(func=cmd_power)

    notify = sub.add_parser("notify", help="notification control")
    notify_sub = notify.add_subparsers(dest="notify_command", required=True)
    dnd = notify_sub.add_parser("dnd")
    dnd.add_argument("state", nargs="?", default="toggle", choices=["on", "off", "toggle"])
    send = notify_sub.add_parser("send")
    send.add_argument("summary")
    send.add_argument("body", nargs="?", default="")
    notify_state = notify_sub.add_parser(
        "state", help="record the unread count for the bar (used by the shell)"
    )
    notify_state.add_argument("count", type=int)
    notify_state.add_argument("dnd", nargs="?", default="off", choices=["on", "off"])
    notify.set_defaults(func=cmd_notify)

    status = sub.add_parser("status", help="status payloads for the bar")
    status.add_argument(
        "what",
        choices=["power", "gpu", "hypernix", "assistant", "notifications", "battery"],
    )
    status.add_argument("--waybar", action="store_true")
    status.set_defaults(func=cmd_status)

    refresh = sub.add_parser("refresh", help="poke a Waybar module")
    refresh.add_argument("module", choices=sorted(["notifications", "assistant", "power"]))
    refresh.set_defaults(func=cmd_refresh)

    shell_parser = sub.add_parser("shell", help="talk to the Quickshell instance")
    shell_parser.add_argument("target")
    shell_parser.add_argument("function", nargs="?", default="")
    shell_parser.add_argument("args", nargs="*")
    shell_parser.set_defaults(func=cmd_shell)

    session = sub.add_parser("session", help="session control")
    session.add_argument(
        "session_command",
        choices=["lock", "suspend", "hibernate", "reboot", "shutdown", "logout", "reload"],
    )
    session.set_defaults(func=cmd_session)

    hypernix = sub.add_parser("hypernix", help="HyperNix integration")
    hypernix_sub = hypernix.add_subparsers(dest="hypernix_command", required=True)
    hypernix_status = hypernix_sub.add_parser("status")
    hypernix_status.add_argument("--waybar", action="store_true")
    hypernix_sub.add_parser("launch")
    hypernix_sub.add_parser("devices")
    hypernix.set_defaults(func=cmd_hypernix, waybar=False)

    from .assistant import cli as assistant_cli

    assistant_cli.add_parser(sub)

    doctor_parser = sub.add_parser("doctor", help="check the installation")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.set_defaults(func=cmd_doctor)

    version_parser = sub.add_parser("version")
    version_parser.set_defaults(func=cmd_version)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return EXIT_USAGE

    try:
        return handler(args)
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return EXIT_OK
    except Exception as exc:  # noqa: BLE001 — a CLI should not show a traceback
        if os.environ.get("HALCYON_DEBUG"):
            raise
        _print(f"halcyon: {exc}", error=True)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
