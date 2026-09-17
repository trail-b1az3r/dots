#!/usr/bin/env python3
"""Validate the Hyprland configuration without starting Hyprland.

Runs `hypr-config-probe.lua`, which loads the real configuration files
against a stand-in `hl` table, then checks everything it recorded against
Hyprland's option table — `hyprctl descriptions` when a compositor is
running, and the snapshot in deps/hyprland-options.json otherwise.

Catches the mistakes that only show up at login: an option that no longer
exists, a number outside its range, an animation leaf that is not in the
tree, a duplicated keybind.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from halcyon import hyprland  # noqa: E402

#: Hyprland's animation tree, from
#: src/config/shared/animation/AnimationTree.cpp.
ANIMATION_LEAVES = {
    "global", "windows", "windowsIn", "windowsOut", "windowsMove",
    "layers", "layersIn", "layersOut",
    "fade", "fadeIn", "fadeOut", "fadeSwitch", "fadeShadow", "fadeGlow",
    "fadeDim", "fadeLayers", "fadeLayersIn", "fadeLayersOut",
    "fadePopups", "fadePopupsIn", "fadePopupsOut", "fadeDpms",
    "border", "borderangle", "shadowangle", "glowangle",
    "workspaces", "workspacesIn", "workspacesOut",
    "specialWorkspace", "specialWorkspaceIn", "specialWorkspaceOut",
    "zoomFactor", "monitorAdded",
}

#: Window-rule effects, from LuaBindingsInternal.hpp.
WINDOW_RULE_EFFECTS = {
    "float", "tile", "fullscreen", "maximize", "center", "pseudo",
    "no_initial_focus", "pin", "fullscreen_state", "move", "size", "monitor",
    "workspace", "group", "suppress_event", "content", "no_close_for",
    "scrolling_width", "rounding", "border_size", "rounding_power",
    "scroll_mouse", "scroll_touchpad", "animation", "idle_inhibit", "opacity",
    "tag", "max_size", "min_size", "border_color", "persistent_size",
    "allows_input", "dim_around", "decorate", "focus_on_activate",
    "keep_aspect_ratio", "nearest_neighbor", "no_anim", "no_blur", "no_dim",
    "no_focus", "no_follow_mouse", "no_max_size", "no_shadow",
    "no_shortcuts_inhibit", "opaque", "force_rgbx", "sync_fullscreen",
    "immediate", "xray", "render_unfocused", "no_screen_share", "no_vrr",
    "no_auto_hdr", "stay_focused", "confine_pointer", "tonemap",
    "no_border", "no_rounding",
}

LAYER_RULE_EFFECTS = {
    "no_anim", "blur", "blur_popups", "ignore_alpha", "dim_around", "xray",
    "animation", "order", "above_lock", "no_screen_share",
}

#: Match properties, from src/desktop/rule/Rule.cpp.
MATCH_PROPERTIES = {
    "class", "title", "initial_class", "initial_title", "float", "tag",
    "xwayland", "fullscreen", "pin", "focus", "group", "modal",
    "fullscreen_state_internal", "fullscreen_state_client", "workspace",
    "content", "xdg_tag", "namespace",
}

WORKSPACE_RULE_FIELDS = {
    "workspace", "enabled", "monitor", "default", "persistent", "gaps_in",
    "gaps_out", "float_gaps", "border_size", "no_border", "no_rounding",
    "no_shadow", "decorate", "default_name", "on_created_empty", "layout",
    "layout_opts", "animation",
}

RULE_META = {"name", "enabled", "match"}


def probe(config_dir: str, generated_dir: str) -> dict:
    lua = shutil.which("lua5.4") or shutil.which("lua") or shutil.which("luajit")
    if lua is None:
        raise SystemExit("A Lua interpreter is needed to validate the config (lua5.4).")

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hypr-config-probe.lua")
    done = subprocess.run(
        [lua, script, config_dir, generated_dir],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if done.returncode != 0:
        raise SystemExit(f"The config probe failed:\n{done.stderr.strip()}")
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"The config probe produced invalid JSON: {exc}") from exc


def check(recorded: dict) -> list[str]:
    problems: list[str] = []

    for message in recorded.get("errors") or {}:
        problems.append(f"lua: {message}")

    options, source = hyprland.options()
    if not options:
        problems.append("no Hyprland option table available; skipped option checks")
    else:
        for path, value in (recorded.get("config") or {}).items():
            key = path.replace(".", ":")
            meta = options.get(key)
            if meta is None:
                problems.append(f"unknown option: {key}")
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            low, high = meta.get("min"), meta.get("max")
            if isinstance(low, (int, float)) and value < low:
                problems.append(f"{key} = {value} is below the minimum {low}")
            if isinstance(high, (int, float)) and value > high:
                problems.append(f"{key} = {value} is above the maximum {high}")

    curves = set((recorded.get("curves") or {}).keys())
    for animation in recorded.get("animations") or []:
        leaf = animation.get("leaf")
        if leaf not in ANIMATION_LEAVES:
            problems.append(f"unknown animation leaf: {leaf}")
        for field in ("bezier", "spring"):
            name = animation.get(field)
            if name and name not in curves:
                problems.append(f"animation {leaf!r} uses undefined curve {name!r}")

    for rule in recorded.get("window_rules") or []:
        _check_rule(rule, WINDOW_RULE_EFFECTS, "window", problems)
    for rule in recorded.get("layer_rules") or []:
        _check_rule(rule, LAYER_RULE_EFFECTS, "layer", problems)
    for rule in recorded.get("workspace_rules") or []:
        for key in rule:
            if key not in WORKSPACE_RULE_FIELDS:
                problems.append(f"workspace rule: unknown field {key!r}")

    seen: dict[str, str] = {}
    for bind in recorded.get("binds") or []:
        keys = str(bind.get("keys", ""))
        normalised = keys.upper().replace(" ", "")
        if not normalised:
            continue
        if normalised in seen:
            problems.append(
                f"duplicate keybind {keys!r} (also bound to {seen[normalised]})"
            )
        seen[normalised] = str(bind.get("dispatcher", "?"))

    return problems


def _check_rule(rule: dict, effects: set[str], kind: str, problems: list[str]) -> None:
    name = rule.get("name", "<unnamed>")
    for key, value in rule.items():
        if key in RULE_META:
            if key == "match" and isinstance(value, dict):
                for match_key in value:
                    if match_key not in MATCH_PROPERTIES:
                        problems.append(
                            f"{kind} rule {name!r}: unknown match property {match_key!r}"
                        )
            continue
        if key not in effects:
            problems.append(f"{kind} rule {name!r}: unknown effect {key!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=os.path.join(REPO_ROOT, "config", "hypr"),
        help="the hypr config directory to load",
    )
    parser.add_argument(
        "--generated",
        default=os.path.expanduser("~/.config/halcyon/generated"),
        help="the directory holding the generated Lua files",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    recorded = probe(args.config, args.generated)
    problems = check(recorded)

    if args.json:
        json.dump({"ok": not problems, "problems": problems}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1 if problems else 0

    counts = {
        "options": len(recorded.get("config") or {}),
        "binds": len(recorded.get("binds") or []),
        "animations": len(recorded.get("animations") or []),
        "window rules": len(recorded.get("window_rules") or []),
        "layer rules": len(recorded.get("layer_rules") or []),
        "workspace rules": len(recorded.get("workspace_rules") or []),
    }
    summary = ", ".join(f"{value} {name}" for name, value in counts.items())
    print(f"Loaded the configuration: {summary}.")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  ✗ {problem}")
        return 1

    print("No problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
