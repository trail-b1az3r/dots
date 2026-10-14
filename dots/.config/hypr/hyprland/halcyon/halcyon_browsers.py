#!/usr/bin/env python3
"""Firefox and Chromium themes that follow Halcyon: `halcyon browsers`.

    halcyon browsers                  what is themed, where
    halcyon browsers update           write both themes from the current colours (themes and wallpapers do this)
    halcyon browsers off [firefox|chromium]
    halcyon browsers --json

The colours are the shell's own (~/.local/state/quickshell/user/generated/colors.json), so the browsers match a
Halcyon theme, and the wallpaper's colours when no theme is on. Applying a theme or a wallpaper runs `update`.

Firefox    Every profile of Firefox, LibreWolf, Zen, Floorp and Waterfox gets chrome/halcyon.css (the toolbars, tabs,
           address bar, menus and sidebar) and chrome/halcyon-content.css (new tab and blank pages), imported from
           userChrome.css and userContent.css, and user.js turns on toolkit.legacyUserProfileCustomizations.stylesheets.
           Firefox reads them when it starts: restart it to see new colours.
Chromium   A theme extension in ~/.local/share/halcyon/chromium-theme, with the wallpaper on the new tab page.
           Chromium and Brave load it from their flags file (--load-extension). Google Chrome no longer takes that
           flag: load the folder once in chrome://extensions (Developer mode > Load unpacked), and it follows from
           then on. Chromium-based browsers re-read it when they start.

Everything Halcyon adds is marked, and `off` takes exactly that away.
"""

from __future__ import annotations

import argparse
import colorsys
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")

COLORS = STATE / "quickshell/user/generated/colors.json"
ACTIVE_THEME = STATE / "halcyon/active"
SHELL_CONFIG = CONFIG / "illogical-impulse/config.json"
CHROMIUM_THEME = DATA / "halcyon/chromium-theme"

# Where each Firefox-family browser keeps profiles.ini.
FIREFOX_ROOTS = [
    ("Firefox", HOME / ".mozilla/firefox"),
    ("Firefox", CONFIG / "mozilla/firefox"),        # Firefox 147+ on a fresh install: XDG paths
    ("LibreWolf", HOME / ".librewolf"),
    ("LibreWolf", CONFIG / "librewolf/librewolf"),
    ("Zen", HOME / ".zen"),
    ("Zen", CONFIG / "zen"),
    ("Floorp", HOME / ".floorp"),
    ("Waterfox", HOME / ".waterfox"),
    # Flatpaks keep their profiles in their own sandbox folder.
    ("Firefox", HOME / ".var/app/org.mozilla.firefox/.mozilla/firefox"),
    ("Firefox", HOME / ".var/app/org.mozilla.firefox/config/mozilla/firefox"),
    ("LibreWolf", HOME / ".var/app/io.gitlab.librewolf-community/.librewolf"),
    ("Zen", HOME / ".var/app/app.zen_browser.zen/.zen"),
]
# Chromium-based browsers whose Arch launcher reads a flags file.
CHROMIUM_FLAGS = [("Chromium", CONFIG / "chromium-flags.conf"), ("Brave", CONFIG / "brave-flags.conf")]

CSS_BEGIN, CSS_END = "/* halcyon-browsers: begin */", "/* halcyon-browsers: end */"
JS_BEGIN, JS_END = "// halcyon-browsers: begin", "// halcyon-browsers: end"

# Used when colors.json is missing a key (an old matugen template, or a theme that does not set it).
FALLBACK = {
    "background": "#141218", "surface": "#141218", "surface_container_lowest": "#0F0D13",
    "surface_container_low": "#1D1B20", "surface_container": "#211F26", "surface_container_high": "#2B2930",
    "surface_container_highest": "#36343B", "on_surface": "#E6E0E9", "on_surface_variant": "#CAC4D0",
    "outline": "#938F99", "outline_variant": "#49454F", "primary": "#D0BCFF", "on_primary": "#381E72",
    "primary_container": "#4F378B", "on_primary_container": "#EADDFF", "secondary_container": "#4A4458",
    "on_secondary_container": "#E8DEF8", "tertiary": "#EFB8C8", "error": "#F2B8B5",
}


# --- colours ----------------------------------------------------------------------------------------------------

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def load_colors(path: Path | None = None) -> dict[str, str]:
    try:
        data = json.loads((path or COLORS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    colors = dict(FALLBACK)
    for key, value in (data.items() if isinstance(data, dict) else []):
        if isinstance(value, str) and HEX_RE.match(value.strip()):
            colors[key] = value.strip().upper()
    return colors


def rgb(hex_colour: str) -> list[int]:
    value = hex_colour.lstrip("#")
    return [int(value[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a: str, b: str, amount: float) -> str:
    """a moved `amount` of the way to b."""
    ra, rb = rgb(a), rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * amount):02X}" for x, y in zip(ra, rb))


def luminance(hex_colour: str) -> float:
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgba(hex_colour: str, alpha: float) -> str:
    r, g, b = rgb(hex_colour)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def active_theme() -> str:
    try:
        return ACTIVE_THEME.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def shell_config() -> dict:
    try:
        data = json.loads(SHELL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def wallpaper() -> Path | None:
    """The wallpaper on screen now (the shell keeps its path in background.wallpaperPath)."""
    value = (shell_config().get("background") or {}).get("wallpaperPath") or ""
    path = Path(value).expanduser() if isinstance(value, str) and value else None
    if path is None or not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        return None
    return path


def settings() -> dict[str, bool]:
    stored = (shell_config().get("halcyon") or {}).get("browsers") or {}
    if not isinstance(stored, dict):
        stored = {}
    return {key: stored.get(key, True) is not False for key in ("firefox", "chromium")}


# --- Firefox ------------------------------------------------------------------------------------------------------

def firefox_css(c: dict[str, str], theme: str = "") -> str:
    """userChrome: Firefox's own colour variables, set from the shell's palette."""
    dark = luminance(c["surface"]) < 0.4
    frame = c["surface_container_lowest"] if dark else c["surface_container"]
    accent_line = c["primary"]
    extra = ""
    if theme == "red-sun":
        # The ring: an ember line under the selected tab, brightest in the middle.
        accent_line = f"linear-gradient(90deg, transparent, {c['primary']} 30%, {c['tertiary']} 50%, {c['primary']} 70%, transparent)"
        extra = f"""
.tab-background:is([selected], [multiselected]) {{
  box-shadow: 0 0 14px {rgba(c['primary'], 0.28)}, inset 0 0 0 1px {rgba(c['primary'], 0.35)} !important;
}}"""
    return f"""{CSS_BEGIN}
/* Written by `halcyon browsers update` from the Halcyon colours{f" ({theme})" if theme else ""}. Edits are replaced. */
:root, #navigator-toolbox, #main-window {{
  --lwt-accent-color: {frame} !important;
  --lwt-accent-color-inactive: {frame} !important;
  --lwt-text-color: {c['on_surface']} !important;
  --toolbar-bgcolor: {c['surface_container']} !important;
  --toolbar-color: {c['on_surface']} !important;
  --toolbarbutton-icon-fill: {c['on_surface_variant']} !important;
  --toolbarbutton-icon-fill-attention: {c['primary']} !important;
  --toolbarbutton-hover-background: {rgba(c['on_surface'], 0.08)} !important;
  --toolbarbutton-active-background: {rgba(c['on_surface'], 0.14)} !important;
  --toolbar-field-background-color: {c['surface_container_high']} !important;
  --toolbar-field-color: {c['on_surface']} !important;
  --toolbar-field-border-color: transparent !important;
  --toolbar-field-focus-background-color: {c['surface_container_highest']} !important;
  --toolbar-field-focus-color: {c['on_surface']} !important;
  --toolbar-field-focus-border-color: {c['primary']} !important;
  --urlbar-box-bgcolor: {c['surface_container_high']} !important;
  --urlbar-box-hover-bgcolor: {c['surface_container_highest']} !important;
  --urlbar-box-text-color: {c['on_surface']} !important;
  --tab-selected-bgcolor: {c['surface_container']} !important;
  --tab-selected-textcolor: {c['on_surface']} !important;
  --tab-hover-background-color: {rgba(c['on_surface'], 0.06)} !important;
  --tab-loading-fill: {c['primary']} !important;
  --tab-attention-icon-color: {c['primary']} !important;
  --focus-outline-color: {c['primary']} !important;
  --chrome-content-separator-color: {c['outline_variant']} !important;
  --arrowpanel-background: {c['surface_container']} !important;
  --arrowpanel-color: {c['on_surface']} !important;
  --arrowpanel-border-color: {c['outline_variant']} !important;
  --panel-separator-color: {c['outline_variant']} !important;
  --sidebar-background-color: {c['surface_container_low']} !important;
  --sidebar-text-color: {c['on_surface']} !important;
  --sidebar-border-color: {c['outline_variant']} !important;
  --button-primary-bgcolor: {c['primary']} !important;
  --button-primary-color: {c['on_primary']} !important;
  --color-accent-primary: {c['primary']} !important;
  --link-color: {c['primary']} !important;
  accent-color: {c['primary']} !important;
}}
#navigator-toolbox {{ background-color: {frame} !important; border-bottom-color: {c['outline_variant']} !important; }}
#TabsToolbar, #titlebar {{ background-color: {frame} !important; color: {c['on_surface']} !important; }}
#nav-bar, #PersonalToolbar {{ background-color: {c['surface_container']} !important; }}
.tab-background:is([selected], [multiselected]) {{ background: {c['surface_container']} !important; }}
.tab-background:is([selected], [multiselected])::before {{
  content: ""; position: absolute; inset: auto 12px 0 12px; height: 2px; border-radius: 2px;
  background: {accent_line};
}}
.tab-background {{ position: relative; }}
/* Set directly as well: Firefox's own rules for these do not all go through the variables above. */
#TabsToolbar, #nav-bar, #PersonalToolbar, #toolbar-menubar, #sidebar-box, #sidebar-main {{ color: {c['on_surface']} !important; }}
.tabbrowser-tab .tab-label {{ color: {c['on_surface_variant']} !important; }}
.tabbrowser-tab:is([selected], [multiselected]) .tab-label {{ color: {c['on_surface']} !important; }}
#personal-toolbar-empty-description, #PersonalToolbar .toolbarbutton-text {{ color: {c['on_surface_variant']} !important; }}
#urlbar-background, #searchbar {{
  background-color: {c['surface_container_high']} !important; border-color: transparent !important;
  border-radius: 999px !important;
}}
#urlbar:is([focused], [open]) > #urlbar-background, #urlbar[breakout-extend] > #urlbar-background {{
  background-color: {c['surface_container_highest']} !important;
  outline: 1px solid {c['primary']} !important; border-radius: 18px !important;
}}
#urlbar, #urlbar-input, .urlbar-input, #searchbar {{ color: {c['on_surface']} !important; }}
#urlbar-input::placeholder, .urlbar-input::placeholder, .searchbar-textbox::placeholder {{
  color: {c['on_surface_variant']} !important; opacity: 1 !important;
}}
.urlbarView {{ color: {c['on_surface']} !important; }}
.urlbarView-row[selected] {{ background-color: {c['secondary_container']} !important; color: {c['on_secondary_container']} !important; }}
.urlbarView-url, .urlbarView-action {{ color: {c['primary']} !important; }}
menupopup, panel {{ --panel-background: {c['surface_container']} !important; --panel-color: {c['on_surface']} !important; }}
menupopup > menuitem[_moz-menuactive], menupopup > menu[_moz-menuactive] {{
  background-color: {c['secondary_container']} !important; color: {c['on_secondary_container']} !important;
}}
::selection {{ background-color: {c['primary_container']} !important; color: {c['on_primary_container']} !important; }}{extra}
{CSS_END}
"""


def firefox_content_css(c: dict[str, str]) -> str:
    """userContent: the new tab, home and blank pages, where Firefox shows no website of its own."""
    return f"""{CSS_BEGIN}
@-moz-document url("about:newtab"), url("about:home"), url("about:blank"), url("about:privatebrowsing") {{
  :root {{
    --newtab-background-color: {c['surface']} !important;
    --newtab-background-color-secondary: {c['surface_container']} !important;
    --newtab-text-primary-color: {c['on_surface']} !important;
    --newtab-text-secondary-color: {c['on_surface_variant']} !important;
    --newtab-primary-action-background: {c['primary']} !important;
    --newtab-element-hover-color: {c['surface_container_high']} !important;
    --newtab-element-active-color: {c['surface_container_highest']} !important;
    --newtab-search-icon-color: {c['primary']} !important;
    --in-content-page-background: {c['surface']} !important;
    --in-content-page-color: {c['on_surface']} !important;
    --in-content-box-background: {c['surface_container']} !important;
    --in-content-primary-button-background: {c['primary']} !important;
    --in-content-primary-button-text-color: {c['on_primary']} !important;
    --in-content-link-color: {c['primary']} !important;
    --color-accent-primary: {c['primary']} !important;
    background-color: {c['surface']} !important;
  }}
  body {{ background-color: {c['surface']} !important; color: {c['on_surface']} !important; }}
}}
{CSS_END}
"""


def user_js(c: dict[str, str]) -> str:
    """The prefs: read userChrome.css at all, and use Firefox's dark (or light) base to match the palette. Without the
    second, a light system theme leaves Firefox's own text dark on Halcyon's dark toolbars."""
    mode = 0 if luminance(c["surface"]) < 0.4 else 1   # Firefox: 0 dark, 1 light
    return f"""{JS_BEGIN}
// Halcyon's Firefox theme lives in chrome/halcyon.css; Firefox only reads userChrome.css with this on.
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
// Firefox's own colours under it are {'dark' if mode == 0 else 'light'}, like the desktop's.
user_pref("ui.systemUsesDarkTheme", {1 - mode});
user_pref("browser.theme.toolbar-theme", {mode});
user_pref("browser.theme.content-theme", {mode});
{JS_END}
"""


def firefox_profiles(roots=None) -> list[tuple[str, Path]]:
    """(browser, profile folder) for every profile listed in a profiles.ini that exists."""
    found = []
    seen = set()
    for browser, root in roots if roots is not None else FIREFOX_ROOTS:
        ini = root / "profiles.ini"
        if not ini.is_file():
            continue
        parser = configparser.RawConfigParser()
        try:
            parser.read(ini, encoding="utf-8")
        except (configparser.Error, UnicodeDecodeError):
            continue
        for section in parser.sections():
            if not section.startswith("Profile") or not parser.has_option(section, "Path"):
                continue
            relative = parser.get(section, "IsRelative", fallback="1") == "1"
            path = (root / parser.get(section, "Path")) if relative else Path(parser.get(section, "Path"))
            if path.is_dir() and path.resolve() not in seen:
                seen.add(path.resolve())
                found.append((browser, path))
    return found


def _strip_block(text: str, begin: str, end: str) -> str:
    return re.sub(rf"\n?{re.escape(begin)}.*?{re.escape(end)}\n?", "\n", text, flags=re.S).strip("\n")


def _with_import(text: str, name: str) -> str:
    """The file with `@import url("name");` first (after any @charset), once."""
    line = f'@import url("{name}"); /* halcyon-browsers */'
    lines = [l for l in text.splitlines() if "halcyon-browsers" not in l or "@import" not in l]
    insert_at = 1 if lines and lines[0].lstrip().lower().startswith("@charset") else 0
    lines.insert(insert_at, line)
    return "\n".join(lines).rstrip("\n") + "\n"


def _without_import(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not ("@import" in l and "halcyon-browsers" in l)).strip("\n")


def write_if_changed(path: Path, text: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.halcyon-{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return True


def install_firefox(profile: Path, colors: dict[str, str], theme: str = "") -> bool:
    """Theme one profile. Returns whether anything changed (Firefox then needs a restart)."""
    chrome = profile / "chrome"
    changed = write_if_changed(chrome / "halcyon.css", firefox_css(colors, theme))
    changed |= write_if_changed(chrome / "halcyon-content.css", firefox_content_css(colors))
    for name, imported in (("userChrome.css", "halcyon.css"), ("userContent.css", "halcyon-content.css")):
        path = chrome / name
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        changed |= write_if_changed(path, _with_import(current, imported))
    prefs = profile / "user.js"
    current = prefs.read_text(encoding="utf-8") if prefs.is_file() else ""
    wanted = (_strip_block(current, JS_BEGIN, JS_END) + "\n\n" + user_js(colors)).lstrip("\n")
    changed |= write_if_changed(prefs, wanted)
    return changed


def remove_firefox(profile: Path) -> None:
    chrome = profile / "chrome"
    for name in ("halcyon.css", "halcyon-content.css"):
        (chrome / name).unlink(missing_ok=True)
    for name in ("userChrome.css", "userContent.css"):
        path = chrome / name
        if path.is_file():
            rest = _without_import(path.read_text(encoding="utf-8"))
            if rest.strip():
                path.write_text(rest + "\n", encoding="utf-8")
            else:
                path.unlink()
    user_js = profile / "user.js"
    if user_js.is_file():
        rest = _strip_block(user_js.read_text(encoding="utf-8"), JS_BEGIN, JS_END)
        if rest.strip():
            user_js.write_text(rest + "\n", encoding="utf-8")
        else:
            user_js.unlink()


# --- Chromium -----------------------------------------------------------------------------------------------------

def _hsl_tint(hex_colour: str) -> list[float]:
    r, g, b = (x / 255 for x in rgb(hex_colour))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return [round(h, 3), round(s, 3), round(l, 3)]


def chromium_manifest(c: dict[str, str], version: str, has_image: bool, theme: str = "") -> dict:
    dark = luminance(c["surface"]) < 0.4
    frame = c["surface_container_lowest"] if dark else c["surface_container"]
    colors = {
        "frame": rgb(frame),
        "frame_inactive": rgb(mix(frame, c["surface"], 0.5)),
        "frame_incognito": rgb(mix(frame, "#000000", 0.35)),
        "frame_incognito_inactive": rgb(mix(frame, "#000000", 0.45)),
        "toolbar": rgb(c["surface_container"]),
        "toolbar_text": rgb(c["on_surface"]),
        "toolbar_button_icon": rgb(c["on_surface_variant"]),
        "tab_text": rgb(c["on_surface"]),
        "tab_background_text": rgb(c["on_surface_variant"]),
        "tab_background_text_inactive": rgb(mix(c["on_surface_variant"], frame, 0.35)),
        "bookmark_text": rgb(c["on_surface"]),
        "omnibox_background": rgb(c["surface_container_high"]),
        "omnibox_text": rgb(c["on_surface"]),
        "button_background": [*rgb(c["primary"]), 0.0],
        "ntp_background": rgb(c["surface"]),
        "ntp_text": rgb(c["on_surface"]),
        "ntp_link": rgb(c["primary"]),
        "ntp_header": rgb(c["primary"]),
        "ntp_section": rgb(c["surface_container"]),
        "ntp_section_text": rgb(c["on_surface"]),
        "ntp_section_link": rgb(c["primary"]),
        "control_button_background": [*rgb(c["surface_container_high"]), 0.0],
    }
    manifest = {
        "manifest_version": 3,
        "name": f"Halcyon{' · ' + theme.replace('-', ' ').title() if theme else ''}",
        "description": "Follows the Halcyon desktop's colours. Written by `halcyon browsers update`.",
        "version": version,
        "theme": {
            "colors": colors,
            "tints": {"buttons": _hsl_tint(c["on_surface_variant"]),
                      "frame_inactive": [-1, -1, 0.55], "frame_incognito": [-1, 0.2, 0.35]},
            "properties": {"ntp_background_alignment": "center", "ntp_background_repeat": "no-repeat",
                           "ntp_logo_alternate": 1 if dark else 0},
        },
    }
    if has_image:
        manifest["theme"]["images"] = {"theme_ntp_background": "images/ntp.png"}
    return manifest


def version_now(now: float | None = None) -> str:
    """A version that grows every time: Chromium rebuilds a theme only when its version changes."""
    t = time.gmtime(now if now is not None else time.time())
    return f"{t.tm_year}.{t.tm_mon * 100 + t.tm_mday}.{t.tm_hour * 100 + t.tm_min}.{t.tm_sec}"


def ntp_image(source: Path | None, target: Path, width: int = 1600) -> bool:
    """The wallpaper as a PNG for the new tab page. Without Pillow there is no image, and the colour is used."""
    target.unlink(missing_ok=True)
    if source is None:
        return False
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((width, width))
            target.parent.mkdir(parents=True, exist_ok=True)
            img.save(target, optimize=True)
        return True
    except (OSError, ValueError):
        return False


def install_chromium(colors: dict[str, str], theme: str = "", folder: Path | None = None,
                     image: Path | None = None) -> bool:
    """Write the theme extension. Returns whether it changed: then the version is new, and Chromium rebuilds it."""
    folder = folder or CHROMIUM_THEME
    stamp_file = folder.with_name(folder.name + ".source.json")  # beside it: Chromium checks every file inside
    source = {"manifest": chromium_manifest(colors, "0", image is not None, theme),
              "image": [str(image), image.stat().st_mtime] if image is not None else None}
    try:
        if json.loads(stamp_file.read_text(encoding="utf-8")) == source and (folder / "manifest.json").is_file():
            return False  # same colours, same wallpaper: leave the version alone, so nothing is rebuilt
    except (OSError, ValueError):
        pass
    has_image = ntp_image(image, folder / "images/ntp.png")
    manifest = chromium_manifest(colors, version_now(), has_image, theme)
    folder.mkdir(parents=True, exist_ok=True)
    write_if_changed(folder / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    write_if_changed(stamp_file, json.dumps(source) + "\n")
    return True


def _flag_lines(text: str) -> list[str]:
    return text.splitlines()


def add_load_extension(text: str, folder: Path) -> str:
    """The flags file with --load-extension including the theme folder (merged into an existing one)."""
    lines = _flag_lines(text)
    for i, line in enumerate(lines):
        if line.strip().startswith("--load-extension="):
            paths = [p for p in line.strip().split("=", 1)[1].split(",") if p]
            if str(folder) not in paths:
                paths.append(str(folder))
            lines[i] = "--load-extension=" + ",".join(paths)
            return "\n".join(lines).rstrip("\n") + "\n"
    lines.append(f"--load-extension={folder}")
    return "\n".join(lines).strip("\n") + "\n"


def remove_load_extension(text: str, folder: Path) -> str:
    out = []
    for line in _flag_lines(text):
        if line.strip().startswith("--load-extension="):
            paths = [p for p in line.strip().split("=", 1)[1].split(",") if p and p != str(folder)]
            if not paths:
                continue
            line = "--load-extension=" + ",".join(paths)
        out.append(line)
    return "\n".join(out).strip("\n") + ("\n" if out else "")


def chromium_browsers() -> list[tuple[str, Path]]:
    """The flags files of the Chromium-based browsers that are installed."""
    commands = {"Chromium": ("chromium",), "Brave": ("brave", "brave-browser")}
    return [(name, path) for name, path in CHROMIUM_FLAGS
            if path.exists() or any(shutil.which(cmd) for cmd in commands[name])]


def chrome_installed() -> bool:
    return any(shutil.which(cmd) for cmd in ("google-chrome-stable", "google-chrome"))


# --- commands -----------------------------------------------------------------------------------------------------

def update(quiet: bool = False) -> dict:
    """Write both themes. One update at a time: a wallpaper change and a theme can both ask at once."""
    import fcntl
    lock_path = DATA / "halcyon/browsers.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _update(quiet)


def _update(quiet: bool) -> dict:
    wants = settings()
    colors = load_colors()
    theme = active_theme()
    report = {"firefox": [], "chromium": [], "chrome": chrome_installed(), "restart": []}
    first_time = []
    if wants["firefox"]:
        for browser, profile in firefox_profiles():
            if not (profile / "chrome/halcyon.css").is_file() and browser not in first_time:
                first_time.append(browser)
            changed = install_firefox(profile, colors, theme)
            report["firefox"].append({"browser": browser, "profile": str(profile), "changed": changed})
            if changed and browser not in report["restart"]:
                report["restart"].append(browser)
    if wants["chromium"]:
        changed = install_chromium(colors, theme, image=wallpaper())
        for name, flags in chromium_browsers():
            current = flags.read_text(encoding="utf-8") if flags.is_file() else ""
            write_if_changed(flags, add_load_extension(current, CHROMIUM_THEME))
            report["chromium"].append({"browser": name, "flags": str(flags)})
            if changed and name not in report["restart"]:
                report["restart"].append(name)
        if changed and report["chrome"] and "Google Chrome" not in report["restart"]:
            report["restart"].append("Google Chrome")
    if first_time and shutil.which("notify-send"):
        # Firefox reads its theme only when it starts, so the first time say so, or it looks like nothing happened.
        names = " and ".join(first_time)
        subprocess.run(["notify-send", "-a", "Halcyon", f"{names} theme installed",
                        f"Restart {names} to see Halcyon's colours. From now on they follow your theme."], check=False)
    if not quiet:
        print_report(report)
    return report


def off(which: str = "") -> int:
    if which in ("", "firefox"):
        for _browser, profile in firefox_profiles():
            remove_firefox(profile)
    if which in ("", "chromium"):
        for _name, flags in CHROMIUM_FLAGS:
            if flags.is_file():
                rest = remove_load_extension(flags.read_text(encoding="utf-8"), CHROMIUM_THEME)
                flags.write_text(rest, encoding="utf-8")
        if CHROMIUM_THEME.is_dir():
            shutil.rmtree(CHROMIUM_THEME)
        CHROMIUM_THEME.with_name(CHROMIUM_THEME.name + ".source.json").unlink(missing_ok=True)
    print("removed Halcyon's browser theme" + (f" from {which}" if which else "s") + "; restart the browser to see it go")
    return 0


def status() -> dict:
    profiles = firefox_profiles()
    return {
        "settings": settings(),
        "colors": str(COLORS),
        "firefox": [{"browser": b, "profile": str(p), "themed": (p / "chrome/halcyon.css").is_file()}
                    for b, p in profiles],
        "chromium_theme": str(CHROMIUM_THEME) if (CHROMIUM_THEME / "manifest.json").is_file() else "",
        "chromium": [{"browser": n, "flags": str(f),
                      "loads_theme": f.is_file() and str(CHROMIUM_THEME) in f.read_text(encoding="utf-8")}
                     for n, f in chromium_browsers()],
        "chrome": chrome_installed(),
    }


def print_report(report: dict) -> None:
    for item in report["firefox"]:
        print(f"{item['browser']:<10} {item['profile']}{'' if item['changed'] else '  (already up to date)'}")
    if not report["firefox"] and settings()["firefox"]:
        print("Firefox    no profiles found (start Firefox once, then run this again)")
    for item in report["chromium"]:
        print(f"{item['browser']:<10} loads {CHROMIUM_THEME} ({item['flags']})")
    if report["chrome"]:
        print(f"Chrome     load {CHROMIUM_THEME} once: chrome://extensions > Developer mode > Load unpacked")
    if report["restart"]:
        print("restart " + ", ".join(report["restart"]) + " to see the new colours")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon browsers", description="Firefox and Chromium themes that follow Halcyon.")
    parser.add_argument("action", nargs="?", default="status", choices=("status", "update", "off"))
    parser.add_argument("which", nargs="?", default="", choices=("", "firefox", "chromium"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "update":
        report = update(quiet=args.quiet or args.json)
        if args.json:
            print(json.dumps(report, indent=2))
        return 0
    if args.action == "off":
        return off(args.which)
    info = status()
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    for item in info["firefox"]:
        print(f"{item['browser']:<10} {'themed' if item['themed'] else 'not themed'}  {item['profile']}")
    if not info["firefox"]:
        print("Firefox    no profiles found")
    print(f"Chromium   theme {'at ' + info['chromium_theme'] if info['chromium_theme'] else 'not written yet'}")
    for item in info["chromium"]:
        print(f"{item['browser']:<10} {'loads it' if item['loads_theme'] else 'does not load it'} ({item['flags']})")
    if info["chrome"]:
        print(f"Chrome     load {CHROMIUM_THEME} once in chrome://extensions (Developer mode > Load unpacked)")
    if not all(info["settings"].values()):
        off_ones = [k for k, v in info["settings"].items() if not v]
        print("turned off in Settings > Halcyon: " + ", ".join(off_ones))
    print("`halcyon browsers update` writes them now; applying a theme or wallpaper does it too.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
