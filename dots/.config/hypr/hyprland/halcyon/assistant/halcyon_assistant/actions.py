"""The things the assistant may do on the desktop. Nothing else.

Each action has a JSON schema the model sees, and a planner that turns
validated arguments into a fixed command. The model picks an action and
its arguments; it never supplies a command line, so there is no way to get
arbitrary code run. Planning is separate from running so it can be tested.
"""

import configparser
import os
import re
import shutil
import subprocess
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME_TOOL = HERE.parent.parent / "halcyon-theme"
THEMES = ["hyperneo", "hsr", "shattered-glass", "fractured-glass"]


def _schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": False}


ACTIONS = {
    "open_app": {
        "description": "Open an installed application by its name, e.g. 'Firefox', 'files', 'terminal'.",
        "parameters": _schema({"name": {"type": "string", "description": "Application name"}}, ["name"]),
    },
    "set_volume": {
        "description": "Set the output volume to a percentage.",
        "parameters": _schema({"percent": {"type": "integer", "minimum": 0, "maximum": 100}}, ["percent"]),
    },
    "change_volume": {
        "description": "Raise or lower the output volume by a number of percentage points.",
        "parameters": _schema({"delta": {"type": "integer", "minimum": -100, "maximum": 100}}, ["delta"]),
    },
    "toggle_mute": {
        "description": "Mute or unmute the speakers, or the microphone.",
        "parameters": _schema({"device": {"type": "string", "enum": ["speakers", "microphone"]}}, ["device"]),
    },
    "set_brightness": {
        "description": "Set the screen brightness to a percentage.",
        "parameters": _schema({"percent": {"type": "integer", "minimum": 1, "maximum": 100}}, ["percent"]),
    },
    "media": {
        "description": "Control the media player.",
        "parameters": _schema({"command": {"type": "string", "enum": ["play_pause", "next", "previous", "stop"]}},
                              ["command"]),
    },
    "switch_workspace": {
        "description": "Switch to a numbered workspace.",
        "parameters": _schema({"number": {"type": "integer", "minimum": 1, "maximum": 99}}, ["number"]),
    },
    "apply_theme": {
        "description": "Switch the Halcyon theme: hyperneo (macOS-style ember and neon), hsr (Star Rail), "
                       "shattered-glass, fractured-glass (Liquid Glass), or off (colours from the wallpaper).",
        "parameters": _schema({"theme": {"type": "string", "enum": THEMES + ["off"]}}, ["theme"]),
    },
    "set_effects": {
        "description": "Set how much visual effect the theme uses.",
        "parameters": _schema({"level": {"type": "string", "enum": ["full", "light", "off", "default"]}}, ["level"]),
    },
    "screenshot": {
        "description": "Take a screenshot of the whole screen, saved to Pictures/Screenshots and copied.",
        "parameters": _schema({}),
    },
    "lock_screen": {
        "description": "Lock the screen.",
        "parameters": _schema({}),
    },
    "web_search": {
        "description": "Search the web in the browser.",
        "parameters": _schema({"query": {"type": "string"}}, ["query"]),
    },
}


class ActionError(Exception):
    pass


def validate(name, args):
    if name not in ACTIONS:
        raise ActionError(f"unknown action '{name}'")
    if not isinstance(args, dict):
        raise ActionError("arguments must be an object")
    schema = ACTIONS[name]["parameters"]
    for key in schema["required"]:
        if key not in args:
            raise ActionError(f"missing '{key}'")
    for key, value in args.items():
        spec = schema["properties"].get(key)
        if spec is None:
            raise ActionError(f"unexpected argument '{key}'")
        if spec["type"] == "integer":
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ActionError(f"'{key}' must be a whole number")
            if not spec.get("minimum", value) <= value <= spec.get("maximum", value):
                raise ActionError(f"'{key}' out of range")
            args[key] = value
        elif spec["type"] == "string":
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ActionError(f"'{key}' must be a short text")
            if "enum" in spec and value not in spec["enum"]:
                raise ActionError(f"'{key}' must be one of {', '.join(spec['enum'])}")
    return args


# ---------------------------------------------------------------------------
# Finding applications: .desktop files in the XDG data dirs, matched by name.
# ---------------------------------------------------------------------------

def desktop_dirs():
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    return [Path(d) / "applications" for d in [data_home, *data_dirs.split(":")] if d]


ALIASES = {"terminal": ["terminal", "konsole", "kitty", "foot"], "files": ["files", "file manager", "dolphin", "nautilus"],
           "browser": ["web browser", "firefox", "chrome", "chromium", "zen"], "settings": ["settings"]}


def find_app(name, dirs=None):
    """Best-matching desktop entry id for a spoken name, or None."""
    wanted = name.lower().strip()
    candidates = []
    for directory in dirs or desktop_dirs():
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.desktop"):
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(path, encoding="utf-8")
                entry = parser["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if entry.get("NoDisplay", "false").lower() == "true" or entry.get("Type", "Application") != "Application":
                continue
            app_id = str(path.relative_to(directory)).replace("/", "-")[:-len(".desktop")]
            names = [entry.get("Name", ""), entry.get("GenericName", ""), app_id,
                     *entry.get("Keywords", "").split(";")]
            candidates.append((app_id, [n.lower() for n in names if n]))
    terms = [wanted] + ALIASES.get(wanted, [])
    for term in terms:           # exact name first
        for app_id, names in candidates:
            if term in names:
                return app_id
    for term in terms:           # then a name containing the term
        for app_id, names in candidates:
            if any(term in n for n in names):
                return app_id
    return None


# ---------------------------------------------------------------------------
# Planning and running
# ---------------------------------------------------------------------------

def plan(name, args):
    """Validated action -> (list of argv commands, what to tell the model)."""
    args = validate(name, dict(args))
    if name == "open_app":
        app = find_app(args["name"])
        if app is None:
            raise ActionError(f"no installed application matches '{args['name']}'")
        return [["gtk-launch", app]], f"opened {app}"
    if name == "set_volume":
        return [["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{args['percent']}%"]], f"volume {args['percent']}%"
    if name == "change_volume":
        delta = args["delta"]
        step = f"{abs(delta)}%{'+' if delta >= 0 else '-'}"
        return [["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", step]], f"volume changed by {delta}"
    if name == "toggle_mute":
        target = "@DEFAULT_AUDIO_SINK@" if args["device"] == "speakers" else "@DEFAULT_AUDIO_SOURCE@"
        return [["wpctl", "set-mute", target, "toggle"]], f"{args['device']} mute toggled"
    if name == "set_brightness":
        return [["brightnessctl", "set", f"{args['percent']}%"]], f"brightness {args['percent']}%"
    if name == "media":
        command = {"play_pause": "play-pause", "next": "next", "previous": "previous", "stop": "stop"}[args["command"]]
        return [["playerctl", command]], f"media {command}"
    if name == "switch_workspace":
        return [["hyprctl", "dispatch", "workspace", str(args["number"])]], f"workspace {args['number']}"
    if name == "apply_theme":
        if args["theme"] == "off":
            return [[str(THEME_TOOL), "off"]], "theme off"
        return [[str(THEME_TOOL), "apply", args["theme"]]], f"applying {args['theme']}"
    if name == "set_effects":
        return [[str(THEME_TOOL), "effects", args["level"]]], f"effects {args['level']}"
    if name == "screenshot":
        script = ('d="$(xdg-user-dir PICTURES)/Screenshots"; mkdir -p "$d"; '
                  'f="$d/Screenshot_$(date +%Y-%m-%d_%H.%M.%S).png"; grim "$f" && wl-copy < "$f"')
        return [["sh", "-c", script]], "screenshot saved"
    if name == "lock_screen":
        return [["loginctl", "lock-session"]], "locked"
    if name == "web_search":
        url = "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(args["query"])
        return [["xdg-open", url]], f"searching for {args['query']}"
    raise ActionError(f"no plan for '{name}'")


def run(name, args):
    """Do it. Returns a short result for the model; never raises."""
    try:
        commands, result = plan(name, args)
    except ActionError as error:
        return f"error: {error}"
    for argv in commands:
        if not shutil.which(argv[0]) and not Path(argv[0]).is_file():
            return f"error: {argv[0]} is not installed"
        # Themes take a few seconds; don't make the conversation wait for them.
        detach = argv[0] == str(THEME_TOOL) and argv[1] in ("apply", "off")
        try:
            if detach:
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            else:
                subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
        except (OSError, subprocess.SubprocessError) as error:
            message = re.sub(r"\s+", " ", str(error))[:200]
            return f"error: {message}"
    return result
