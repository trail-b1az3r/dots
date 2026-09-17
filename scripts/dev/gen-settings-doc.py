#!/usr/bin/env python3
"""Generate `docs/settings.md` from the defaults, so it cannot drift.

Types and defaults come from `config/system/settings.default.json`;
only the prose lives here. `validate.sh` checks that every key has a
description and that no description names a key that is gone, so adding
a setting without documenting it fails the build.

    ./scripts/dev/gen-settings-doc.py            # write docs/settings.md
    ./scripts/dev/gen-settings-doc.py --check    # exit 1 if it is stale
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULTS = os.path.join(ROOT, "config", "system", "settings.default.json")
OUTPUT = os.path.join(ROOT, "docs", "settings.md")

#: Sections, in the order they should be read rather than alphabetically.
SECTIONS: list[tuple[str, str, str]] = [
    ("appearance", "Appearance", "Light and dark, the accent colour, fonts and cursors."),
    ("glass", "Glass", "The material every surface is made of."),
    ("motion", "Motion", "How things move, and how fast."),
    ("bar", "Bar", "The status bar's geometry and module layout."),
    ("workspaces", "Workspaces", "How many, where, and whether they persist."),
    ("input", "Input", "Keyboard, pointer, touchpad and gestures."),
    ("displays", "Displays", "Monitor modes, scaling and tearing."),
    ("graphics", "Graphics", "What the GPU is allowed to spend effort on."),
    ("wallpaper", "Wallpaper", "The image, how it is fitted, and rotation."),
    ("notifications", "Notifications", "Placement, timeouts and history."),
    ("power", "Power", "Profiles, the adaptive policy and idle behaviour."),
    ("assistant", "AI assistant", "Backends, voice, and what it is allowed to see."),
    ("hypernix", "HyperNix", "The optional HyperNix integration."),
    ("search", "Search", "Spotlight's providers and their scope."),
    ("applications", "Applications", "Default applications and capture directories."),
    ("accessibility", "Accessibility", "Overrides that take precedence over the theme."),
    ("privacy", "Privacy", "What is recorded locally."),
    ("keybinds", "Keybinds", "Per-binding overrides."),
]

DESCRIPTIONS: dict[str, str] = {
    "version": "Schema version. Halcyon refuses to load settings written by a newer version rather than guessing.",

    "appearance.mode": "`dark`, `light`, or `auto` to follow the time of day.",
    "appearance.followSunset": "With `mode: auto`, switch at local sunrise and sunset rather than fixed hours.",
    "appearance.accentSource": "`wallpaper` derives the accent from the current image; `fixed` uses `accentColor`.",
    "appearance.accentColor": "The accent when `accentSource` is `fixed`. Used exactly as given — a hand-picked colour is never clamped.",
    "appearance.iconTheme": "Icon theme name, as installed under `share/icons`.",
    "appearance.cursorTheme": "Cursor theme name. Applied to Hyprland, GTK and Qt together.",
    "appearance.cursorSize": "Cursor size in logical pixels.",
    "appearance.fontUi": "Interface typeface. Inter by default — an open font with the proportions this design wants.",
    "appearance.fontMono": "Monospace typeface for the terminal module and code surfaces.",
    "appearance.fontSizeScale": "Multiplies every type size at once. `accessibility.textScale` is applied on top.",
    "appearance.cornerStyle": "`continuous` for squircle-style corners, `circular` for plain radii.",

    "glass.preset": "Which shipped preset the other glass values started from. Changing a value by hand does not clear it.",
    "glass.opacity": "Base surface opacity, before per-elevation adjustment. Lower means more wallpaper.",
    "glass.blurStrength": "Scales the blur radius and pass count. The single biggest GPU cost in the desktop.",
    "glass.saturation": "Saturation boost applied to what shows through. Above 1.0 makes glass feel alive rather than grey.",
    "glass.tintStrength": "How much of the accent hue the glass carries.",
    "glass.borderOpacity": "Opacity of the hairline border that separates a surface from what is behind it.",
    "glass.cornerRadius": "Corner radius in logical pixels, shared by windows and shell surfaces.",
    "glass.shadowStrength": "Drop-shadow intensity. Feeds both Hyprland's shadow and the shell's.",
    "glass.panelPadding": "Interior padding inside panels.",
    "glass.widgetSpacing": "Gap between widgets within a panel.",
    "glass.specularStrength": "The highlight along a surface's top edge — what makes it read as glass rather than frosted plastic.",
    "glass.refraction": "How much the edge of a surface bends what is behind it.",
    "glass.noise": "A trace of grain over the material, which hides blur banding on large flat areas.",
    "glass.elevationSpread": "How far apart the elevation levels sit. Higher means a more pronounced depth hierarchy.",

    "motion.preset": "`macos`, `smooth`, `fast`, `minimal` or `disabled`. Sets the curves and base durations.",
    "motion.speedScale": "Multiplies every duration. Below 1.0 is faster.",
    "motion.reducedMotion": "Collapse movement to opacity fades. Implied by `accessibility.reducedMotion`.",
    "motion.overlayAnimations": "Animate shell overlays (Spotlight, Control Center) as well as windows.",

    "bar.enabled": "Whether Waybar runs at all. The shell works without it.",
    "bar.position": "`top` or `bottom`.",
    "bar.height": "Bar height in logical pixels.",
    "bar.sideMargin": "Horizontal inset when floating.",
    "bar.topMargin": "Vertical inset when floating.",
    "bar.floating": "Detach the bar from the screen edge so it reads as a surface rather than a strip.",
    "bar.showOnAllMonitors": "One bar per monitor, or only on the primary.",
    "bar.left": "Modules on the left, in order. Every name must have a definition in `config/waybar/modules.jsonc`.",
    "bar.center": "Modules in the centre, in order.",
    "bar.right": "Modules on the right, in order.",

    "workspaces.count": "How many workspaces get bindings and persistent rules (1–20).",
    "workspaces.perMonitor": "Give each monitor its own set rather than sharing one.",
    "workspaces.persistent": "Keep empty workspaces in the bar instead of hiding them.",
    "workspaces.wrapAround": "Next/previous wraps from the last workspace to the first.",
    "workspaces.names": "Map of workspace number to display name, e.g. `{\"1\": \"Mail\"}`.",
    "workspaces.smartGaps": "Drop gaps and the border when a workspace holds one window.",

    "input.keyboardLayout": "XKB layout, e.g. `us` or `gb,de`.",
    "input.keyboardVariant": "XKB variant, e.g. `dvorak`.",
    "input.keyboardOptions": "XKB options, e.g. `ctrl:nocaps`.",
    "input.repeatRate": "Key repeats per second.",
    "input.repeatDelay": "Milliseconds before repeating starts.",
    "input.followMouse": "Hyprland's focus-follows-mouse mode: 0 off, 1 full, 2 loose, 3 detached.",
    "input.sensitivity": "Pointer sensitivity, −1.0 to 1.0. 0 is the driver's own setting.",
    "input.accelProfile": "`adaptive` or `flat`. `flat` gives a fixed 1:1 mapping.",
    "input.naturalScroll": "Natural scrolling for the mouse wheel.",
    "input.touchpadNaturalScroll": "Natural scrolling for the touchpad, set separately because most people want them different.",
    "input.tapToClick": "Tap the touchpad to click.",
    "input.disableWhileTyping": "Ignore the touchpad while typing.",
    "input.scrollFactor": "Multiplies touchpad scroll distance.",
    "input.workspaceSwipe": "Swipe between workspaces on the touchpad.",
    "input.swipeFingers": "How many fingers that swipe takes.",

    "displays.monitors": "Per-monitor configuration. Each entry takes `name`, `mode`, `position`, `scale`, `transform`, `enabled`.",
    "displays.defaultScale": "Scale for monitors with no explicit entry. `auto` lets Hyprland decide.",
    "displays.vrr": "Variable refresh rate: 0 off, 1 on, 2 fullscreen only.",
    "displays.allowTearing": "Permit tearing for windows that ask for it. Games only; it is off by default for a reason.",

    "graphics.blurQuality": "`off`, `low`, `medium`, `high` or `ultra`. Sets blur radius and passes together.",
    "graphics.shadowQuality": "Shadow range and render power, on the same scale.",
    "graphics.animationQuality": "How much of the motion system runs, on the same scale.",
    "graphics.transparency": "Global multiplier on every surface's opacity. 1.0 leaves the theme as designed.",
    "graphics.lowPowerGraphics": "Drop the expensive passes regardless of battery state.",
    "graphics.renderUnfocusedFps": "Frame cap for windows that are not focused. The largest single saving on a laptop.",
    "graphics.gpuOverrides": "`auto` detects the GPU and sets only what that hardware needs. `none` writes nothing.",

    "wallpaper.path": "The current wallpaper. Empty leaves whatever is set; the shipped wallpapers are in `$HALCYON_WALLPAPER_DIR`.",
    "wallpaper.mode": "`fill`, `fit`, `stretch`, `center` or `tile`.",
    "wallpaper.dim": "Darken the wallpaper, 0.0 to 1.0, without editing the file.",
    "wallpaper.blur": "Blur radius applied to the wallpaper itself.",
    "wallpaper.perMonitor": "Map of monitor name to wallpaper path.",
    "wallpaper.rotation.enabled": "Cycle through a directory.",
    "wallpaper.rotation.directory": "Where to cycle through. Defaults to `$HALCYON_WALLPAPER_DIR`.",
    "wallpaper.rotation.intervalMinutes": "Minutes between changes.",
    "wallpaper.rotation.shuffle": "Random order rather than alphabetical.",
    "wallpaper.deriveColors": "Re-derive the palette when the wallpaper changes. Off keeps the accent fixed.",

    "notifications.enabled": "Whether the notification server runs.",
    "notifications.position": "`top-right`, `top-left`, `top-center`, `bottom-right`, `bottom-left`.",
    "notifications.doNotDisturb": "Suppress popups. Critical notifications still arrive; everything is kept in history.",
    "notifications.defaultTimeout": "Seconds a normal notification stays up.",
    "notifications.lowTimeout": "Seconds for low-urgency notifications.",
    "notifications.criticalTimeout": "Seconds for critical ones. 0 means they stay until dismissed.",
    "notifications.maxVisible": "How many popups stack before the rest queue.",
    "notifications.groupByApp": "Collapse several notifications from one application into a stack.",
    "notifications.historyLimit": "How many to keep in the notification centre.",
    "notifications.showOnLockScreen": "Show notification content while locked. Off by default — the lock screen is visible to whoever walks past.",

    "power.profile": "`performance`, `balanced` or `battery-saver`. Applied through whichever backend is active.",
    "power.backend": "`auto`, `power-profiles-daemon`, `tuned`, `tlp` or `none`. Only ever one.",
    "power.adaptive.enabled": "Let battery state change how expensive the desktop is.",
    "power.adaptive.reduceEffectsOnBattery": "Step effects down on battery even above the threshold.",
    "power.adaptive.batteryThreshold": "Percentage below which effects are reduced further.",
    "power.adaptive.criticalThreshold": "Percentage below which the expensive effects are switched off.",
    "power.adaptive.criticalAction": "`notify`, `suspend` or `hibernate` at the critical threshold.",
    "power.idle.enabled": "Whether hypridle runs.",
    "power.idle.acDimSeconds": "Seconds of idle on AC before dimming. 0 disables.",
    "power.idle.acScreenOffSeconds": "Seconds on AC before the screen turns off.",
    "power.idle.acLockSeconds": "Seconds on AC before locking.",
    "power.idle.acSuspendSeconds": "Seconds on AC before suspending. 0 by default — a plugged-in machine is usually doing something.",
    "power.idle.batteryDimSeconds": "Seconds on battery before dimming.",
    "power.idle.batteryScreenOffSeconds": "Seconds on battery before the screen turns off.",
    "power.idle.batteryLockSeconds": "Seconds on battery before locking.",
    "power.idle.batterySuspendSeconds": "Seconds on battery before suspending.",
    "power.idle.lockBeforeSleep": "Lock before suspending, so the machine never wakes unlocked.",
    "power.refreshIntervals.acSeconds": "How often polled bar modules refresh on AC.",
    "power.refreshIntervals.batterySeconds": "The same on battery. Longer, deliberately.",

    "assistant.enabled": "Whether the assistant daemon runs at all.",
    "assistant.provider": "`auto`, `nixorb` or `local`. `auto` prefers NixOrb when it answers.",
    "assistant.pushToTalkOnly": "Only listen while the key is held; never on a wake word.",
    "assistant.streaming": "Show the answer as it is generated rather than all at once.",
    "assistant.voice.enabled": "Speak answers aloud.",
    "assistant.voice.name": "Piper voice model name.",
    "assistant.voice.speed": "Speech rate multiplier.",
    "assistant.voice.volume": "Speech volume, relative to the system volume.",
    "assistant.microphone.device": "PipeWire source name, or `default`.",
    "assistant.microphone.respectMute": "Refuse to listen while the microphone is muted — the mute key means mute.",
    "assistant.wakeWord.enabled": "Listen for a wake phrase. Off by default; an always-listening microphone should be a choice.",
    "assistant.wakeWord.phrase": "The phrase to listen for.",
    "assistant.wakeWord.sensitivity": "Detection threshold, 0.0 to 1.0. Higher means more false positives.",
    "assistant.privacy.allowWebAccess": "Permit actions that reach the network (web search, currency rates). Off by default.",
    "assistant.privacy.allowScreenContext": "Permit the assistant to see the screen. Off by default; nothing is captured silently.",
    "assistant.privacy.allowClipboardContext": "Permit the assistant to read the clipboard. Off by default.",
    "assistant.privacy.storeConversations": "Keep history on disk. Off means the conversation lives only in memory.",
    "assistant.privacy.confirmDestructiveActions": "Ask before suspending, rebooting, shutting down or logging out.",
    "assistant.local.llmBackend": "`ollama` or `openai` for any OpenAI-compatible server.",
    "assistant.local.llmHost": "Base URL of that server.",
    "assistant.local.llmModel": "Model name to request.",
    "assistant.local.sttBackend": "`whisper-cpp` or `whisper`.",
    "assistant.local.sttModel": "Path to the speech model. Empty picks the best one installed.",
    "assistant.local.ttsBackend": "`piper` or `espeak`.",
    "assistant.local.ttsModel": "Path to the voice model. Empty uses `assistant.voice.name`.",
    "assistant.local.maxTokens": "Cap on answer length.",
    "assistant.local.temperature": "Sampling temperature.",
    "assistant.nixorb.autostart": "Start NixOrb with the session if it is not already running.",
    "assistant.nixorb.socketPath": "Override NixOrb's socket path. Empty means autodetect.",
    "assistant.historyLimit": "How many turns to keep.",

    "hypernix.enabled": "The whole integration. Off removes the widget, the Spotlight provider and the tray item.",
    "hypernix.showWidget": "Show the HyperNix widget in Control Center and on the desktop.",
    "hypernix.showInSpotlight": "Offer HyperNix commands in search results.",
    "hypernix.showInTray": "Show a tray item.",
    "hypernix.notifyOnJobs": "Notify when a job finishes.",
    "hypernix.pollSeconds": "How often to ask HyperNix for its state.",
    "hypernix.command": "The executable name, if it is not `hypernix` on `PATH`.",

    "search.maxResults": "Maximum results shown at once.",
    "search.providers": "Per-provider on/off. A provider switched off is never called.",
    "search.fileRoots": "Directories the file provider searches.",
    "search.fileDepth": "How deep below each root to look.",
    "search.webSearchUrl": "Search URL with `{query}` substituted.",
    "search.webSearchName": "What to call that engine in the results.",

    "applications.terminal": "Terminal for `Super + Return` and for actions that need a shell.",
    "applications.browser": "Browser for `Super + B`. Empty uses the XDG default.",
    "applications.fileManager": "File manager for `Super + Shift + Return`.",
    "applications.editor": "Editor for opening text files. Empty uses the XDG default.",
    "applications.screenshotDir": "Where screenshots are saved.",
    "applications.recordingDir": "Where recordings are saved.",

    "accessibility.reducedMotion": "Collapse all motion to fades. Overrides the motion preset.",
    "accessibility.highContrast": "Raise every contrast floor and make borders solid.",
    "accessibility.largeText": "Step every type size up.",
    "accessibility.textScale": "Fine text scaling, applied on top of `appearance.fontSizeScale`.",
    "accessibility.disableBlur": "Turn blur off everywhere, regardless of the glass settings.",
    "accessibility.disableAnimations": "Turn animation off entirely, not just reduce it.",
    "accessibility.minimumTransparency": "Floor on surface opacity, so nothing becomes unreadable however the theme is set.",
    "accessibility.focusRing": "Draw a visible focus ring on keyboard focus.",
    "accessibility.screenReaderLabels": "Emit accessible names from shell components.",

    "privacy.clipboardHistory": "Record clipboard history for Spotlight.",
    "privacy.clipboardHistoryLimit": "How many entries to keep.",
    "privacy.recentFiles": "Record recently opened files for search.",
    "privacy.telemetry": "Off, and there is nothing to send — no telemetry code ships in this repository.",

    "keybinds": "Per-binding overrides, keyed by the IDs in `config/system/keybinds.catalog.json`. Set one to `\"none\"` to unbind it.",
}

#: Containers documented as a whole rather than key by key.
OPAQUE = {
    "workspaces.names", "wallpaper.perMonitor", "search.providers",
    "displays.monitors", "search.fileRoots", "bar.left", "bar.center",
    "bar.right", "keybinds",
}

TYPE_NAMES = {
    bool: "bool", int: "int", float: "float",
    str: "string", list: "list", dict: "map",
}


def flatten(node: dict, prefix: str = "") -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and path not in OPAQUE:
            out.extend(flatten(value, path + "."))
        else:
            out.append((path, value))
    return out


def render(defaults: dict) -> str:
    rows = flatten(defaults)
    by_section: dict[str, list[tuple[str, object]]] = {}
    for path, value in rows:
        by_section.setdefault(path.split(".", 1)[0], []).append((path, value))

    lines = [
        "# Settings reference",
        "",
        "Every key in `~/.config/halcyon/settings.json`, with its type and",
        "default. Only your overrides are stored — anything you have not",
        "changed takes the value below.",
        "",
        "```sh",
        "halcyon settings get glass.opacity",
        "halcyon settings set glass.opacity 0.55",
        "halcyon settings unset glass.opacity   # back to the default",
        "halcyon settings list                  # only what you have changed",
        "halcyon settings path                  # where the file lives",
        "```",
        "",
        "Values are type-checked on the way in. An out-of-range number or an",
        "unknown key is refused with the reason rather than quietly coerced,",
        "and a change only reaches the desktop once `halcyon theme apply`",
        "has regenerated the files — which the Settings app does for you.",
        "",
        "<!-- Generated by scripts/dev/gen-settings-doc.py — do not edit. -->",
        "",
    ]

    for key, title, blurb in SECTIONS:
        entries = by_section.get(key)
        if not entries:
            continue
        lines += [f"## {title}", "", blurb, ""]
        lines += ["| Key | Type | Default | Meaning |", "|---|---|---|---|"]
        for path, value in entries:
            type_name = TYPE_NAMES.get(type(value), "value")
            shown = json.dumps(value)
            if len(shown) > 60:
                shown = shown[:57] + "…"
            description = DESCRIPTIONS[path].replace("|", "\\|")
            lines.append(
                f"| `{path}` | {type_name} | `{shown}` | {description} |"
            )
        lines.append("")

    version = by_section.get("version")
    if version:
        lines += [
            "## Schema",
            "",
            "| Key | Type | Default | Meaning |",
            "|---|---|---|---|",
            f"| `version` | int | `{json.dumps(version[0][1])}` | {DESCRIPTIONS['version']} |",
            "",
        ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if the file is stale or a key is undocumented")
    args = parser.parse_args()

    with open(DEFAULTS, encoding="utf-8") as handle:
        defaults = json.load(handle)

    paths = {path for path, _ in flatten(defaults)}
    undocumented = sorted(paths - set(DESCRIPTIONS))
    orphaned = sorted(set(DESCRIPTIONS) - paths)
    if undocumented or orphaned:
        for path in undocumented:
            print(f"undocumented setting: {path}", file=sys.stderr)
        for path in orphaned:
            print(f"documented setting no longer exists: {path}", file=sys.stderr)
        return 1

    content = render(defaults)

    if args.check:
        try:
            with open(OUTPUT, encoding="utf-8") as handle:
                current = handle.read()
        except OSError:
            current = ""
        if current != content:
            print(f"{OUTPUT} is out of date; run scripts/dev/gen-settings-doc.py",
                  file=sys.stderr)
            return 1
        return 0

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(content)
    print(f"wrote {OUTPUT} ({len(paths)} settings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
