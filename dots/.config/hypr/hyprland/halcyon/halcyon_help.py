"""The text of `halcyon help`, kept as data so it can be searched (`halcyon help auto`) and tested against the commands.

`halcyon` is the command you type: a link to halcyon-theme in ~/.local/bin (created when Hyprland starts), and an
alias in fish and zsh. Every line here works with either name.
"""

from __future__ import annotations

# (group, [(usage, what it does)]). A usage's first word is the command, which `halcyon help COMMAND` matches.
GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Themes", [
        ("list", "the themes, and which one is active"),
        ("apply NAME", "switch to a theme"),
        ("off", "back to colours from the wallpaper"),
        ("current", "the active theme's id, or 'none'"),
        ("menu", "pick a theme or effects level with fuzzel (Ctrl + Super + Shift + T)"),
        ("custom new [NAME]", "make your own theme from the active one, to edit"),
        ("custom list|duplicate ID|delete ID|open ID|path", "manage your own themes"),
        ("show [ID|all]", "list hidden built-in themes, or bring one back"),
        ("check", "validate every theme (used by CI)"),
        ("render NAME DIR [--effects LEVEL] [--native-blur]", "write what apply would, into DIR only"),
    ]),
    ("Schedules", [
        ("auto list", "scheduled themes (Settings > Halcyon, Auto-apply), with today's sun times"),
        ("auto sun", "today's sunrise and sunset, as JSON"),
        ("auto day [--json]", "today's sun and the next theme change (what the bar's sun dial shows)"),
        ("auto location [LAT,LON|clear]", "where the sun times are for; by default the bar's weather location"),
        ("auto", "apply what is due now (a timer runs this once a minute)"),
    ]),
    ("Effects, cursor and windows", [
        ("effects [full|light|off|default]", "show or set how much visual effect themes use"),
        ("effects flip", "mirror pointer effects vertically, if the glass lens trails the pointer upside down"),
        ("refresh", "re-apply Settings > Halcyon to the active theme"),
        ("cursor [on|off]", "the Halcyon Glass cursor, or upstream's"),
        ("cursor size N", "cursor size in pixels (16-96)"),
        ("placement [MODE|--list]", "where a new window opens: golden, cursor, stacked, side-by-side or mondrian"),
        ("settings", "open the Settings app"),
    ]),
    ("Plus Tiles and the config", [
        ("plus", "the Plus Tiles settings as Hyprland gets them (needs hyprland-plus to take effect)"),
        ("plus apply|status", "write the settings from Settings > Halcyon and reload, or report what is in use"),
        ("plus edit rules|keys", "open your copy of app_rules.lua or plus_keys.lua"),
        ("config-check [--fix] [--json]", "check the Hyprland and Halcyon config, and say how to fix it"),
        ("crashes [--since 2d] [--json]", "why apps closed: core dumps, memory kills, and shell restarts that took apps with them"),
        ("migrate", "bring a theme applied by an older Halcyon up to date (login and `update apply` do this)"),
        ("hyprland [--json]", "which Hyprland is running: stock, hyprland-plus, or a hyprland-plus too old for Plus Tiles"),
    ]),
    ("Text from the screen", [
        ("text", "pick a region of the screen and copy the text in it (Super + Shift + X does the same)"),
        ("text --window|--screen|--clipboard", "the focused window, the whole monitor, or the image in the clipboard"),
        ("text FILE [--print] [--join] [--lang eng+deu]", "read an image or a PDF (scanned or not); print it, rejoin lines, pick languages"),
    ]),
    ("Browsers and devices", [
        ("browsers [--json]", "the Firefox and Chromium themes that follow Halcyon's colours, and where they are"),
        ("browsers update", "write them now (applying a theme or a wallpaper does this)"),
        ("browsers off [firefox|chromium]", "take them out of the browsers again"),
        ("server on|off|status", "server mode: no suspend, no automatic lock or screen blanking (Settings > Halcyon has the button)"),
        ("usb [--json]", "why a browser can't find or open a USB, HID or serial device (WebUSB, WebHID, Web Serial)"),
        ("usb allow VID:PID ... | --all", "let you open those devices from the browser (a udev rule; asks for sudo)"),
        ("usb remove", "take that rule away again"),
    ]),
    ("Widgets, characters and extras", [
        ("revolver status", "whether the revolver is on and where, its games, and any error the shell logged for it"),
        ("revolver on|off", "show or hide it, on every theme"),
        ("revolver scan [--json]", "the revolver's games and their weights"),
        ("collapse arm AGE X Y R [CX CY] | disarm", "the Red Sun sequence: spin, eye, tape and rewind (the revolver runs this)"),
        ("revolver fire SOURCE ID", "start one of them"),
        ("starrail next|refresh|status", "Star Rail banner character: another one, download the index, what is showing"),
        ("banner NAME IMAGE [--title T] [--subtitle S]", "put character art on a theme's banner"),
        ("banner NAME [--clear]", "show what is set, or remove it"),
        ("fetch [--spin [S]] [--json] [--fastfetch]", "a system summary beside the turning Halcyon mark"),
        ("assistant ...", "the voice assistant ('halcyon assistant help')"),
    ]),
]

NOTES = """\
hyprland-plus is not a command. It is Hyprland itself, built with the Halcyon additions, and it replaces the
`Hyprland` program: start it the way you start Hyprland (pick Hyprland at your login screen). To see
whether you are running it, use `halcyon hyprland` (or `hyprctl version`, which says 'hyprland-plus'). Everything under
'Plus Tiles' needs it. On stock Hyprland those settings are saved and do nothing.

Where things are:
  Settings          Settings > Halcyon (themes, effects, glass, Plus Tiles, config check)
  Logs              ~/.local/state/halcyon/apply.log (theme apply), ~/.local/state/halcyon/ (the rest)
  Your themes       ~/.config/halcyon/themes/        Your Plus keys and rules  ~/.config/hypr/custom/
  Docs              https://trail-b1az3r.github.io/dots/
"""


def command_of(usage: str) -> str:
    return usage.split()[0]


def commands() -> set[str]:
    return {command_of(usage) for _group, rows in GROUPS for usage, _what in rows}


def render(topic: str | None = None, program: str = "halcyon", width: int = 100) -> str:
    """The whole help, or only the rows for one command. Unknown topics raise KeyError."""
    selected = []
    for group, rows in GROUPS:
        keep = [row for row in rows if topic is None or command_of(row[0]) == topic]
        if keep:
            selected.append((group, keep))
    if not selected:
        raise KeyError(topic)

    column = min(52, max(len(usage) for _group, rows in selected for usage, _what in rows) + len(program) + 3)
    lines = [f"{program}: themes, effects and the Plus Tiles settings for this desktop.", ""]
    if topic is None:
        lines += [f"Usage: {program} COMMAND [ARGUMENTS]", ""]
    for group, rows in selected:
        lines.append(f"{group}")
        for usage, what in rows:
            head = f"  {program} {usage}"
            if len(head) + 2 > column:
                lines.append(head)
                lines.append(" " * column + what)
            else:
                lines.append(head.ljust(column) + what)
        lines.append("")
    if topic is None:
        lines.append(NOTES.rstrip())
        lines.append("")
        lines.append(f"{program} help COMMAND shows one command. The full manual is in docs/halcyon/themes.md.")
    return "\n".join(lines).rstrip() + "\n"
