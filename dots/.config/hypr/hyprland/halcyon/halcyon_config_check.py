#!/usr/bin/env python3
"""Checks the Hyprland and Halcyon configuration, and says how to fix what it finds.

    halcyon config-check            report problems
    halcyon config-check --json     the same, as JSON
    halcyon config-check --fix      also make the safe fixes (file permissions), after a backup

It looks for:
  - config errors Hyprland reports (invalid settings, unknown options, bad keybinds)
  - options the installed Hyprland does not have (Plus options without hyprland-plus)
  - Lua files that do not parse
  - keybind chords that are malformed, and chords two described binds both use
  - the same bind, rule or config line written twice in your custom files
  - plugins that are loaded from paths that do not exist
  - Plus Tiles settings that contradict each other
  - config files with wrong permissions, and Halcyon scripts that lost their executable bit

Your configuration is never rewritten. --fix only changes file permissions, and backs up ~/.config/hypr first.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HOME = Path.home()
HYPR = HOME / ".config" / "hypr"
HALCYON = HYPR / "hyprland" / "halcyon"
CUSTOM = HYPR / "custom"
STATE = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local" / "state")) / "halcyon"

MODIFIERS = {"SUPER", "MOD4", "WIN", "LOGO", "CTRL", "CONTROL", "ALT", "MOD1", "SHIFT", "CAPS", "MOD2", "MOD3", "MOD5", "META"}

# Halcyon's scripts that must stay executable.
EXECUTABLES = [
    "halcyon-theme", "halcyon-banner", "debug-snapshot", "drag-probe", "gpu-guard", "minimize-all", "resume",
    "sleep-hook", "update", "wifi-reconnect", "assistant/halcyon-assistant",
]

PLUS_ONLY_PREFIXES = ("plus:", "superposition:")


@dataclasses.dataclass
class Finding:
    severity: str  # error | warning | info
    area: str
    message: str
    fix: str = ""
    path: str = ""
    autofix: str = ""  # an action --fix can take: "chmod+x", "chmod-go-w"

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


# --- pure checks (tested in tests/test_halcyon_config_check.py) ---------------------------------------------------

def check_chord(chord: str) -> list[str]:
    """Problems with one hl.bind chord, like "SUPER + SHIFT + Q". Empty when it is fine."""
    if not isinstance(chord, str) or not chord.strip():
        return ["the chord is empty"]
    if chord.strip() == "catchall":
        return []
    parts = [p.strip() for p in chord.split("+")]
    if any(p == "" for p in parts):
        return ["the chord has an empty part (two + in a row, or a + at an end)"]
    problems = []
    seen_key = False
    for part in parts:
        if part.upper() in MODIFIERS:
            if seen_key:
                problems.append(f"modifier {part} comes after a key; modifiers must come first")
        else:
            if " " in part:
                problems.append(f"\"{part}\" has a space in it; did you forget a +?")
            if part == "Enter":
                problems.append("\"Enter\" is not a key name; use \"Return\"")
            seen_key = True
    if not seen_key:
        problems.append("the chord has only modifiers and no key")
    return problems


def find_duplicate_binds(binds: list[dict]) -> list[Finding]:
    """Chords that two binds with descriptions both use, in the same submap. Hyprland runs every bind on a chord,
    so both fire. Binds without a description are helpers (Halcyon's Super-tap companions) and are not counted."""
    groups: dict[tuple, list[dict]] = {}
    for b in binds:
        if not b.get("description"):
            continue
        if b.get("catch_all") or b.get("key") in ("SUPER_L", "SUPER_R"):
            continue
        key = (b.get("submap", ""), b.get("modmask", 0), str(b.get("key", "")).lower(), bool(b.get("release")), b.get("keycode", 0))
        groups.setdefault(key, []).append(b)

    findings = []
    for (submap, _mods, _key, _rel, _code), group in groups.items():
        actions = {(b.get("dispatcher"), b.get("arg")) for b in group}
        if len(group) < 2 or len(actions) < 2:
            continue
        names = "; ".join(b.get("description", "") for b in group)
        where = f" in submap {submap}" if submap else ""
        findings.append(Finding(
            "warning", "keybinds",
            f"{len(group)} binds share one chord{where}, and all of them run: {names}",
            "Give one of them another chord, in ~/.config/hypr/custom or the keys files (hypr_mode.lua, plus_keys.lua)."))
    return findings


def find_repeated_lines(path_text: dict[str, str]) -> list[Finding]:
    """The same hl.bind, hl.window_rule or hl.config line twice in one file."""
    findings = []
    for path, text in path_text.items():
        seen: dict[str, int] = {}
        for number, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line.startswith(("hl.bind(", "hl.window_rule(", "hl.config(", "hl.layer_rule(")):
                continue
            if line in seen:
                findings.append(Finding(
                    "warning", "duplicates", f"line {number} repeats line {seen[line]}: {line[:90]}",
                    "Delete one of the two lines.", path))
            else:
                seen[line] = number
    return findings


PLUGIN_RE = re.compile(r"""(?:hl\.plugin\.load|plugin\s*=|hyprctl\s+plugin\s+load)\s*\(?\s*["']?([^"')\s]+\.so)""")


def find_missing_plugins(path_text: dict[str, str]) -> list[Finding]:
    findings = []
    for path, text in path_text.items():
        for match in PLUGIN_RE.finditer(text):
            plugin = os.path.expanduser(os.path.expandvars(match.group(1)))
            if not Path(plugin).exists():
                findings.append(Finding(
                    "error", "plugins", f"a plugin is loaded from {plugin}, which does not exist",
                    "Install the plugin (hyprpm), fix the path, or remove the line.", path))
    return findings


def check_plus_options(opts: dict[str, object], plus_submap_binds: int | None = None) -> list[Finding]:
    """Plus Tiles settings that contradict each other. opts maps option names (plus:step, ...) to values."""
    findings = []

    def num(name: str) -> float | None:
        value = opts.get(name)
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    fine, step, coarse = num("plus:step_fine"), num("plus:step"), num("plus:step_coarse")
    if fine is not None and step is not None and fine > step:
        findings.append(Finding("warning", "plus", f"plus:step_fine ({fine:g}) is larger than plus:step ({step:g})",
                                "Make step_fine the smallest of the three steps."))
    if coarse is not None and step is not None and coarse < step:
        findings.append(Finding("warning", "plus", f"plus:step_coarse ({coarse:g}) is smaller than plus:step ({step:g})",
                                "Make step_coarse the largest of the three steps."))

    for axis in ("width", "height"):
        lo, hi = num(f"plus:min_{axis}"), num(f"plus:max_{axis}")
        if lo is not None and hi is not None and hi > 0 and lo > hi:
            findings.append(Finding("error", "plus", f"plus:min_{axis} ({lo:g}) is larger than plus:max_{axis} ({hi:g}), so no edge move can succeed",
                                    f"Lower plus:min_{axis}, or set plus:max_{axis} to 0 for no maximum."))

    submap = opts.get("plus:edit_submap")
    if isinstance(submap, str) and submap and plus_submap_binds == 0:
        findings.append(Finding("warning", "plus", f"plus:edit_submap is \"{submap}\", but no binds are defined in that submap",
                                "Move Edge then cannot select or move edges by keyboard. Define the submap (tiles.lua does) or set plus:edit_submap to \"\"."))

    if opts.get("plus:enabled") is False and opts.get("plus:all_tiled") is True:
        findings.append(Finding("info", "plus", "plus:all_tiled is on, but plus:enabled is off, so it has no effect"))

    size = num("superposition:size")
    if opts.get("superposition:reserve") is True and size is not None and size > 0.35:
        findings.append(Finding("warning", "plus", f"superposition:reserve takes {size:.0%} of the screen from the tiles",
                                "Use a smaller superposition:size, or reserve = false to draw the strip over the tiles."))
    return findings


def check_permissions(paths: list[Path], uid: int, executables: list[Path]) -> list[Finding]:
    findings = []
    for path in paths:
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_uid != uid:
            findings.append(Finding("error", "permissions", f"{path} belongs to another user (uid {st.st_uid})",
                                    f"sudo chown {os.environ.get('USER', '$USER')}: {path}", str(path)))
        if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            findings.append(Finding("warning", "permissions", f"{path} can be changed by other users",
                                    f"chmod go-w {path}", str(path), "chmod-go-w"))
        if not os.access(path, os.R_OK):
            findings.append(Finding("error", "permissions", f"{path} cannot be read", f"chmod u+r {path}", str(path)))
    for exe in executables:
        if exe.exists() and not os.access(exe, os.X_OK):
            findings.append(Finding("error", "permissions", f"{exe} is not executable, so the features that run it fail",
                                    f"chmod +x {exe}", str(exe), "chmod+x"))
    return findings


def classify_config_errors(errors: list[str], has_plus: bool, tiles: bool | None = None) -> list[Finding]:
    """has_plus: the running compositor is hyprland-plus. tiles: it is new enough for the plus:* options (None:
    assume it is when has_plus)."""
    tiles = has_plus if tiles is None else tiles
    findings = []
    for err in errors:
        err = err.strip()
        if not err:
            continue
        option = re.search(r"(?:option|variable)\s+[\"']?([a-z_]+:[a-z_.:0-9]+)", err)
        if option and option.group(1).startswith(PLUS_ONLY_PREFIXES) and has_plus and not tiles:
            findings.append(Finding("error", "version", f"{option.group(1)} is newer than the running hyprland-plus build: {err}",
                                    "Update hyprland-plus: sudo hyprctl-lite install update. Then log out and back in."))
        elif option and option.group(1).startswith(PLUS_ONLY_PREFIXES) and not has_plus:
            findings.append(Finding("error", "version", f"{option.group(1)} needs hyprland-plus, which is not the running compositor: {err}",
                                    "Install hyprland-plus (sudo hyprctl-lite install full), or move Plus settings behind the fork check (if hl.dsp.plus then ... end)."))
        elif re.search(r"bind|key|chord|keysym|modifier", err, re.I):
            findings.append(Finding("error", "keybinds", err, "Fix the bind at the file and line given."))
        else:
            findings.append(Finding("error", "config", err, "Fix the setting at the file and line given."))
    return findings


# --- gathering, from the running compositor and the files -----------------------------------------------------

def _run(argv: list[str], timeout: float = 5) -> str | None:
    if not shutil.which(argv[0]):
        return None
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _hyprctl_json(*args: str):
    text = _run(["hyprctl", "-j", *args])
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _option(name: str):
    data = _hyprctl_json("getoption", name)
    if not isinstance(data, dict):
        return None
    for key in ("int", "float", "str", "custom", "data"):
        if key in data:
            value = data[key]
            if key == "int" and name.split(":")[-1] in ("enabled", "all_tiled", "edit_preview", "auto_restore", "focus_preview", "reserve"):
                return bool(value)
            return value
    return None


def lua_files() -> list[Path]:
    files = []
    for base in (CUSTOM, HALCYON):
        if base.is_dir():
            files += sorted(base.rglob("*.lua"))
    return files


def gather(running: bool) -> list[Finding]:
    findings: list[Finding] = []

    has_plus = False
    if running:
        import halcyon_compositor
        info = halcyon_compositor.detect()
        has_plus, tiles = bool(info.get("plus")), bool(info.get("tiles"))
        findings.append(Finding("info", "version", "Running " + halcyon_compositor.describe(info)))
        if has_plus and not tiles:
            findings.append(Finding("warning", "version", "This hyprland-plus build is from before Plus Tiles, so Move Edge, Fit to Neighbors and the plus:* settings are off",
                                    "Update it: sudo hyprctl-lite install update, then log out and back in."))
        errors = _run(["hyprctl", "configerrors"]) or ""
        lines = [l for l in errors.splitlines() if l.strip() and l.strip() != "no errors"]
        findings += classify_config_errors(lines, has_plus, tiles)
        has_plus = tiles

        binds = _hyprctl_json("binds") or []
        findings += find_duplicate_binds(binds)

        if has_plus:
            names = ["plus:enabled", "plus:all_tiled", "plus:edit_submap", "plus:step", "plus:step_fine", "plus:step_coarse",
                     "plus:min_width", "plus:min_height", "plus:max_width", "plus:max_height", "superposition:size", "superposition:reserve"]
            opts = {n: _option(n) for n in names}
            submap = opts.get("plus:edit_submap")
            in_submap = sum(1 for b in binds if b.get("submap") == submap) if isinstance(submap, str) and submap else None
            findings += check_plus_options(opts, in_submap)
    else:
        findings.append(Finding("info", "config", "Hyprland is not running here, so only the files were checked",
                                "Run this inside the Hyprland session for the full check."))

    # Lua syntax
    luac = shutil.which("luac") or shutil.which("luac5.4") or shutil.which("luac5.5")
    for path in lua_files():
        if luac:
            out = subprocess.run([luac, "-p", str(path)], capture_output=True, text=True, check=False)
            if out.returncode != 0:
                findings.append(Finding("error", "lua", out.stderr.strip() or "does not parse", "Fix the syntax error at the line given.", str(path)))

    texts = {}
    for path in lua_files():
        if path.is_relative_to(CUSTOM):
            try:
                texts[str(path)] = path.read_text()
            except OSError:
                pass
    findings += find_repeated_lines(texts)
    findings += find_missing_plugins(texts)

    # Chords in the keys files people edit
    for name in ("plus_keys.lua", "hypr_mode.lua"):
        for path in (CUSTOM / name, HALCYON / name):
            if not path.exists():
                continue
            text = path.read_text()
            for chord in re.findall(r'"([A-Za-z0-9_ ]+(?:\s*\+\s*[A-Za-z0-9_:]+)+)"', text):
                for problem in check_chord(chord):
                    findings.append(Finding("error", "keybinds", f"\"{chord}\": {problem}", "Fix the chord in this file.", str(path)))
            break  # the user's copy wins; the shipped one is not read when it exists

    paths = [p for p in HYPR.rglob("*") if p.is_file()] if HYPR.is_dir() else []
    findings += check_permissions(paths, os.getuid(), [HALCYON / e for e in EXECUTABLES])
    return findings


def backup() -> Path:
    STATE.joinpath("backups").mkdir(parents=True, exist_ok=True)
    target = STATE / "backups" / f"config-check-{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"
    with tarfile.open(target, "w:gz") as tar:
        tar.add(HYPR, arcname="hypr")
    return target


def apply_fixes(findings: list[Finding]) -> list[str]:
    done = []
    for f in findings:
        if not f.autofix or not f.path:
            continue
        path = Path(f.path)
        try:
            mode = path.stat().st_mode
            if f.autofix == "chmod+x":
                path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            elif f.autofix == "chmod-go-w":
                path.chmod(mode & ~(stat.S_IWGRP | stat.S_IWOTH))
            done.append(f"{f.autofix} {path}")
        except OSError as e:
            done.append(f"could not fix {path}: {e}")
    return done


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon config-check", description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    parser.add_argument("--fix", action="store_true", help="make the safe fixes (permissions) after a backup")
    args = parser.parse_args(argv)

    running = bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) and shutil.which("hyprctl") is not None
    findings = gather(running)

    fixed: list[str] = []
    backup_path = None
    if args.fix and any(f.autofix for f in findings):
        backup_path = backup()
        fixed = apply_fixes(findings)

    if args.json:
        print(json.dumps({"findings": [f.as_dict() for f in findings], "fixed": fixed, "backup": str(backup_path) if backup_path else None}, indent=2))
    else:
        order = {"error": 0, "warning": 1, "info": 2}
        for f in sorted(findings, key=lambda f: order.get(f.severity, 3)):
            where = f" ({f.path})" if f.path else ""
            print(f"{f.severity:7} {f.area:12} {f.message}{where}")
            if f.fix:
                print(f"{'':20} fix: {f.fix}")
        errors = sum(f.severity == "error" for f in findings)
        warnings = sum(f.severity == "warning" for f in findings)
        print(f"\n{errors} error(s), {warnings} warning(s).")
        if backup_path:
            print(f"Backed up ~/.config/hypr to {backup_path}")
        for line in fixed:
            print(f"fixed: {line}")
        if not args.fix and any(f.autofix for f in findings):
            print("Run with --fix to make the permission fixes. Nothing else is changed automatically.")

    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
