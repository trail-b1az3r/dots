"""The keybind registry: one source of truth for every shortcut.

A binding is data, not a line of generated Lua. It carries everything
needed to decide whether it can work on *this* machine — what it runs,
what that needs, whether the shell has to be up, what to do instead when
it is not — so the generator can make that decision before writing a
file rather than leaving the user to discover a dead key.

Nothing here silently drops a binding. Every rejection produces a
`Diagnostic` naming the chord, the reason, the binding that owns it and
the file it came from.

Validation is deliberately split by severity:

* **error** — the binding cannot work, and we can prove it. An unknown
  action ID, an invalid modifier, a chord already taken.
* **warning** — the binding is suspect but might be fine. A keysym our
  table does not list, an executable not on PATH right now. These are
  reported and the binding is still emitted, because our tables describe
  one machine's idea of the world and the user's may differ. Treating a
  gap in our knowledge as proof of breakage is how an earlier version
  aborted an install over a config that was correct.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import actions as actions_module
from . import paths

SCHEMA_VERSION = 2


class CatalogError(ValueError):
    """The catalog itself is malformed — not one binding, the file."""


# ── Key tables ─────────────────────────────────────────────────────────

_KEY_TABLE: dict[str, Any] | None = None


def _key_table() -> dict[str, Any]:
    global _KEY_TABLE
    if _KEY_TABLE is not None:
        return _KEY_TABLE

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(here)), "deps", "hyprland-keys.json"),
        os.path.join(str(paths.DATA_DIR), "hyprland-keys.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(loaded, dict):
                _KEY_TABLE = loaded
                return _KEY_TABLE
    # No table: validation degrades to structural checks only.
    _KEY_TABLE = {"modifiers": [], "specialKeys": [], "keysyms": []}
    return _KEY_TABLE


def modifiers() -> set[str]:
    return {m.upper() for m in _key_table().get("modifiers", [])}


def keysyms() -> set[str]:
    """Keysym names, lowercased — Hyprland resolves case-insensitively."""
    return {k.lower() for k in _key_table().get("keysyms", [])}


def special_keys() -> set[str]:
    return {k.lower() for k in _key_table().get("specialKeys", [])}


_CODE_KEY = re.compile(r"^code:\d+$", re.I)
_MOUSE_KEY = re.compile(r"^mouse:(\d+)$", re.I)
_BARE_KEYCODE = re.compile(r"^\d+$")


# ── Model ──────────────────────────────────────────────────────────────


@dataclass
class Chord:
    """A parsed key combination."""

    mods: tuple[str, ...]
    key: str
    raw: str

    @property
    def normalised(self) -> str:
        """A canonical form, for collision detection.

        Modifiers are a set — `SUPER + SHIFT + S` and `SHIFT + SUPER + S`
        are the same chord and must collide. The key keeps its spelling
        but compares case-insensitively, as Hyprland resolves it.
        """
        return "+".join(sorted(self.mods) + [self.key.lower()])

    def __str__(self) -> str:
        return self.raw


def parse_chord(raw: str) -> Chord:
    """Split a chord the way Hyprland's parseKeyString does."""
    parts = [part.strip() for part in str(raw).split("+")]
    parts = [part for part in parts if part]
    if not parts:
        raise CatalogError(f"empty chord: {raw!r}")

    known = modifiers()
    mods: list[str] = []
    key = ""
    for index, part in enumerate(parts):
        upper = part.upper()
        # Everything but the last token is a modifier; the last is the
        # key, unless the chord is a bare modifier name.
        if index < len(parts) - 1:
            mods.append(upper)
        elif upper in known and len(parts) > 1:
            mods.append(upper)
        else:
            key = part
    if not key:
        key = parts[-1]
        if mods and mods[-1] == key.upper():
            mods.pop()
    return Chord(tuple(mods), key, str(raw).strip())


@dataclass
class Binding:
    id: str
    chord: str
    description: str
    category: str = "general"
    #: `{"exec": "..."}`, `{"dsp": "hl.dsp...."}` or `{"action": "id"}`.
    action: dict[str, Any] = field(default_factory=dict)
    #: Executables or capabilities this needs: `shell`, or a binary name.
    requires: list[str] = field(default_factory=list)
    destructive: bool = False
    #: True when the binding is useless without the Quickshell instance.
    requires_shell: bool = False
    #: Used when `requires_shell` is set and the shell is not running.
    fallback: dict[str, Any] | None = None
    enabled: bool = True
    #: False when this surface has no sensible non-graphical stand-in.
    #: Recorded with a reason rather than left as an unexplained gap.
    degrades: bool = True
    degrades_reason: str = ""
    mouse: bool = False
    flags: dict[str, bool] = field(default_factory=dict)
    #: Where this came from, for diagnostics.
    source: str = "catalog"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chord": self.chord,
            "description": self.description,
            "category": self.category,
            "action": self.action,
            "requires": list(self.requires),
            "destructive": self.destructive,
            "requiresShell": self.requires_shell,
            "fallback": self.fallback,
            "enabled": self.enabled,
            "degrades": self.degrades,
            "degradesReason": self.degrades_reason,
            "mouse": self.mouse,
            "flags": dict(self.flags),
        }


@dataclass
class Diagnostic:
    """Something worth telling the user about one binding."""

    severity: str  # "error" | "warning"
    binding: str  # the binding id
    chord: str
    message: str
    source: str = "catalog"
    #: For a collision: the id that already holds the chord.
    owner: str | None = None
    #: What we did instead.
    resolution: str = ""

    def format(self) -> str:
        mark = "✗" if self.severity == "error" else "!"
        line = f"{mark} {self.binding} ({self.chord}): {self.message}"
        if self.owner:
            line += f"\n    already bound to: {self.owner}"
        if self.resolution:
            line += f"\n    {self.resolution}"
        line += f"\n    source: {self.source}"
        return line


@dataclass
class Registry:
    bindings: list[Binding] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == "warning"]

    def active(self) -> list[Binding]:
        return [b for b in self.bindings if b.enabled]

    def by_id(self, bind_id: str) -> Binding | None:
        for binding in self.bindings:
            if binding.id == bind_id:
                return binding
        return None

    def by_chord(self, chord: str) -> Binding | None:
        target = parse_chord(chord).normalised
        for binding in self.active():
            if parse_chord(binding.chord).normalised == target:
                return binding
        return None


# ── Emergency bindings ─────────────────────────────────────────────────
#
# These exist so that a machine whose generated configuration is broken
# is still a machine you can fix. They are deliberately boring: no shell,
# no halcyon binary, nothing that can itself be missing. Hyprland's own
# dispatchers and a terminal are the whole dependency list.

EMERGENCY_TERMINALS = (
    "kitty", "foot", "alacritty", "wezterm", "ghostty",
    "gnome-terminal", "konsole", "xterm",
)


def emergency_bindings() -> list[Binding]:
    """The minimum needed to recover a broken desktop.

    Required capabilities, per the desktop's own contract: open a
    terminal, close a window, open settings, reload, and get out.
    """
    terminal_chain = " || ".join(EMERGENCY_TERMINALS)
    return [
        Binding(
            id="emergency.terminal",
            chord="SUPER + Return",
            description="Open a terminal",
            category="emergency",
            action={"exec": terminal_chain},
            source="emergency",
        ),
        Binding(
            id="emergency.close",
            chord="SUPER + W",
            description="Close the focused window",
            category="emergency",
            action={"dsp": "hl.dsp.window.close()"},
            source="emergency",
        ),
        Binding(
            id="emergency.settings",
            chord="SUPER + comma",
            description="Open Halcyon settings",
            category="emergency",
            # No shell needed: this opens the settings file in whatever
            # the system considers an editor, which is the one thing that
            # still works when the shell is down.
            action={"exec": "xdg-open ${XDG_CONFIG_HOME:-$HOME/.config}/halcyon/settings.json"},
            source="emergency",
        ),
        Binding(
            id="emergency.reload",
            chord="SUPER + CTRL + R",
            description="Reload Halcyon",
            category="emergency",
            action={"dsp": "hl.dsp.reload_config()"},
            source="emergency",
        ),
        Binding(
            id="emergency.exit",
            chord="SUPER + CTRL + Escape",
            description="Exit Hyprland",
            category="emergency",
            action={"dsp": "hl.dsp.exit()"},
            destructive=True,
            source="emergency",
        ),
    ]


# ── Loading ────────────────────────────────────────────────────────────


def _migrate_v1(entry: dict[str, Any], *, mouse: bool = False) -> dict[str, Any]:
    """Turn a v1 catalog entry into the v2 shape.

    v1 used `default` for the chord, `title` for the description and had
    no notion of dependencies or fallbacks. Everything it could express
    is still expressible, so migration is lossless.
    """
    migrated: dict[str, Any] = {
        "id": entry.get("id", ""),
        "chord": entry.get("default", ""),
        "description": entry.get("title") or entry.get("description") or "",
        "category": entry.get("category", "general"),
        "action": dict(entry.get("run") or {}),
        "enabled": True,
        "mouse": mouse,
    }
    if entry.get("flags"):
        migrated["flags"] = dict(entry["flags"])
    command = migrated["action"].get("exec", "")
    # A v1 entry that shells out to `halcyon shell ...` needs the shell;
    # nothing in v1 recorded that, so infer it from the command.
    if isinstance(command, str) and command.startswith("halcyon shell "):
        migrated["requiresShell"] = True
    return migrated


def _binding_from(entry: dict[str, Any], source: str) -> Binding:
    bind_id = str(entry.get("id") or "").strip()
    if not bind_id:
        raise CatalogError(f"{source}: a binding has no id")
    chord = str(entry.get("chord") or "").strip()
    action = entry.get("action") or {}
    if not isinstance(action, dict):
        raise CatalogError(f"{source}: {bind_id} has a non-table action")

    return Binding(
        id=bind_id,
        chord=chord,
        description=str(entry.get("description") or ""),
        category=str(entry.get("category") or "general"),
        action=dict(action),
        requires=[str(r) for r in (entry.get("requires") or [])],
        destructive=bool(entry.get("destructive", False)),
        requires_shell=bool(entry.get("requiresShell", False)),
        fallback=entry.get("fallback") or None,
        enabled=bool(entry.get("enabled", True)),
        degrades=bool(entry.get("degrades", True)),
        degrades_reason=str(entry.get("degradesReason") or ""),
        mouse=bool(entry.get("mouse", False)),
        flags=dict(entry.get("flags") or {}),
        source=source,
    )


def load_catalog(catalog: dict[str, Any], *, source: str = "catalog") -> list[Binding]:
    """Read a catalog of either schema version into Binding objects."""
    version = int(catalog.get("version", 1))
    if version > SCHEMA_VERSION:
        raise CatalogError(
            f"{source}: catalog schema version {version} is newer than this "
            f"build understands ({SCHEMA_VERSION}). Refusing to guess."
        )

    out: list[Binding] = []
    if version < SCHEMA_VERSION:
        for entry in catalog.get("binds", []):
            out.append(_binding_from(_migrate_v1(entry), source))
        for entry in catalog.get("mouseBinds", []):
            out.append(_binding_from(_migrate_v1(entry, mouse=True), source))
    else:
        for entry in catalog.get("binds", []):
            out.append(_binding_from(entry, source))
    return out


def apply_overrides(
    bindings: Iterable[Binding], overrides: dict[str, Any]
) -> list[Binding]:
    """Layer the user's `keybinds` settings over the shipped catalog.

    A string replaces the chord. `"none"` (or false) disables the
    binding — disabling is recorded rather than dropped, so Settings can
    still show it and offer it back.
    """
    out: list[Binding] = []
    for binding in bindings:
        override = overrides.get(binding.id, None)
        if override is None:
            out.append(binding)
            continue
        if override is False:
            binding.enabled = False
        elif isinstance(override, str):
            text = override.strip()
            if text.lower() in ("none", "unbound", "disabled", ""):
                binding.enabled = False
            else:
                binding.chord = text
                binding.source = "settings.json"
        elif isinstance(override, dict):
            if "chord" in override:
                binding.chord = str(override["chord"])
            if "enabled" in override:
                binding.enabled = bool(override["enabled"])
            binding.source = "settings.json"
        out.append(binding)
    return out


# ── Validation ─────────────────────────────────────────────────────────


#: Shell syntax that means "this is not one simple command".
_SHELL_METACHARACTERS = "$`|&;<>(){}*?[]~"


def _executable_of(command: str) -> str:
    """The program a shell command would run, for a PATH check.

    Only a single plain command is worth checking. Anything with shell
    syntax anywhere in it — a pipeline, a variable, a subshell, or an
    alternation like `kitty || foot || xterm` — has no one executable to
    look up, and guessing the first word would report the emergency
    terminal chain as missing whenever the first terminal in it is.
    """
    text = command.strip()
    if not text:
        return ""
    if any(ch in text for ch in _SHELL_METACHARACTERS):
        return ""
    return text.split()[0]


_SHELL_COMMAND = re.compile(r"^halcyon\s+shell\s+(\S+)\s+(\S+)")


def has_fallback(binding: Binding) -> bool:
    """Whether this binding still does something with the shell down.

    Two ways to qualify: the catalog declares a `fallback`, or the
    command is `halcyon shell <target> <function>` and the CLI already
    routes that pair to a standalone menu. The second case is the common
    one — `halcyon shell` goes through call_or_fallback, so most shell
    bindings degrade without the catalog having to say so.
    """
    if binding.fallback:
        return True
    command = str(binding.action.get("exec", ""))
    match = _SHELL_COMMAND.match(command.strip())
    if match is None:
        return False
    # Imported lazily: shell imports settings, which imports paths, and a
    # module-level import here would make the cycle real.
    from . import shell as shell_module

    return (match.group(1), match.group(2)) in shell_module.FALLBACKS


def validate(
    bindings: Iterable[Binding],
    *,
    check_executables: bool = True,
) -> tuple[list[Binding], list[Diagnostic]]:
    """Check every binding; return the ones to emit and what was found.

    A binding with an **error** is not emitted — it cannot work. One with
    only warnings is emitted. Either way it produces a diagnostic, so
    nothing disappears without explanation.
    """
    known_mods = modifiers()
    known_keys = keysyms()
    known_special = special_keys()

    diagnostics: list[Diagnostic] = []
    accepted: list[Binding] = []
    # chord -> the binding that took it first.
    claimed: dict[str, Binding] = {}

    for binding in bindings:
        if not binding.enabled:
            continue

        fatal = False

        # — the chord itself —
        if not binding.chord.strip():
            diagnostics.append(Diagnostic(
                "error", binding.id, "(none)",
                "no key chord", binding.source,
                resolution="not bound",
            ))
            continue

        try:
            chord = parse_chord(binding.chord)
        except CatalogError as exc:
            diagnostics.append(Diagnostic(
                "error", binding.id, binding.chord, str(exc), binding.source,
                resolution="not bound",
            ))
            continue

        for mod in chord.mods:
            if known_mods and mod not in known_mods:
                diagnostics.append(Diagnostic(
                    "error", binding.id, binding.chord,
                    f"{mod!r} is not a modifier Hyprland knows. "
                    f"Valid: {', '.join(sorted(known_mods))}",
                    binding.source, resolution="not bound",
                ))
                fatal = True

        key = chord.key
        lowered = key.lower()
        mouse_match = _MOUSE_KEY.match(key)
        if mouse_match:
            if int(mouse_match.group(1)) < 272:
                diagnostics.append(Diagnostic(
                    "error", binding.id, binding.chord,
                    f"mouse button {mouse_match.group(1)} is below 272, which "
                    "Hyprland rejects (button codes start at BTN_LEFT = 272)",
                    binding.source, resolution="not bound",
                ))
                fatal = True
        elif _CODE_KEY.match(key) or _BARE_KEYCODE.match(key):
            pass  # A raw keycode; nothing to check it against.
        elif lowered in known_special:
            pass
        elif known_keys and lowered not in known_keys:
            # Our keysym table is one version of xkbcommon's. A name it
            # does not list may still resolve on the user's machine, so
            # this warns rather than blocks.
            diagnostics.append(Diagnostic(
                "warning", binding.id, binding.chord,
                f"{key!r} is not a keysym name in our table; it may still "
                "resolve on your keymap",
                binding.source, resolution="bound anyway",
            ))

        # — the action —
        action = binding.action
        if not action:
            diagnostics.append(Diagnostic(
                "error", binding.id, binding.chord,
                "no action: needs one of exec, dsp or action",
                binding.source, resolution="not bound",
            ))
            fatal = True
        elif "action" in action:
            action_id = str(action["action"])
            if action_id not in actions_module.REGISTRY:
                diagnostics.append(Diagnostic(
                    "error", binding.id, binding.chord,
                    f"action {action_id!r} is not in the action registry",
                    binding.source, resolution="not bound",
                ))
                fatal = True
        elif "dsp" in action:
            expression = str(action["dsp"]).strip()
            if not expression.startswith("hl.dsp."):
                diagnostics.append(Diagnostic(
                    "error", binding.id, binding.chord,
                    f"dispatcher must start with 'hl.dsp.', got {expression!r}",
                    binding.source, resolution="not bound",
                ))
                fatal = True
        elif "exec" in action:
            command = str(action["exec"])
            if not command.strip():
                diagnostics.append(Diagnostic(
                    "error", binding.id, binding.chord,
                    "exec action has an empty command",
                    binding.source, resolution="not bound",
                ))
                fatal = True
            elif check_executables:
                program = _executable_of(command)
                # `halcyon` is installed by us and may not be on PATH at
                # generation time; the renderer resolves it separately.
                if program and program != "halcyon" and not _resolvable(program):
                    diagnostics.append(Diagnostic(
                        "warning", binding.id, binding.chord,
                        f"{program!r} is not on PATH; the binding will do "
                        "nothing until it is installed",
                        binding.source, resolution="bound anyway",
                    ))
        else:
            diagnostics.append(Diagnostic(
                "error", binding.id, binding.chord,
                f"unrecognised action keys: {', '.join(sorted(action))}",
                binding.source, resolution="not bound",
            ))
            fatal = True

        # — dependencies —
        for requirement in binding.requires:
            if requirement == "shell":
                continue  # Runtime state, not a generation-time fact.
            if check_executables and not _resolvable(requirement):
                diagnostics.append(Diagnostic(
                    "warning", binding.id, binding.chord,
                    f"requires {requirement!r}, which is not installed",
                    binding.source, resolution="bound anyway",
                ))

        # — a shell binding with no way to degrade —
        if binding.requires_shell and binding.degrades and not has_fallback(binding):
            diagnostics.append(Diagnostic(
                "warning", binding.id, binding.chord,
                "needs the shell but has no fallback; it will do nothing "
                "while the shell is down",
                binding.source,
                resolution=(
                    "add a `fallback` to the catalog entry, or a "
                    "(target, function) entry to shell.FALLBACKS"
                ),
            ))

        if fatal:
            continue

        # — collisions —
        key_form = chord.normalised
        owner = claimed.get(key_form)
        if owner is not None:
            diagnostics.append(Diagnostic(
                "error", binding.id, binding.chord,
                "chord is already bound",
                binding.source,
                owner=f"{owner.id} ({owner.description})" if owner.description else owner.id,
                resolution=(
                    f"kept {owner.id}; {binding.id} is not bound. "
                    f"Rebind with: halcyon settings set keybinds.{binding.id} "
                    '"<chord>"'
                ),
            ))
            continue

        claimed[key_form] = binding
        accepted.append(binding)

    return accepted, diagnostics


_RESOLVE_CACHE: dict[str, bool] = {}


def _resolvable(program: str) -> bool:
    if program not in _RESOLVE_CACHE:
        if os.path.isabs(program):
            _RESOLVE_CACHE[program] = os.access(program, os.X_OK)
        else:
            _RESOLVE_CACHE[program] = shutil.which(program) is not None
    return _RESOLVE_CACHE[program]


def build(
    catalog: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    *,
    source: str = "keybinds.catalog.json",
    include_emergency: bool = False,
    check_executables: bool = True,
) -> Registry:
    """Catalog plus user overrides, validated, ready to render.

    Emergency bindings are deliberately **not** part of this set. They
    belong to the fallback configuration that runs when generation has
    failed, where they are the only bindings at all; mixing them in here
    would collide with the real bindings that already cover the same
    keys and say nothing useful. `emergency_coverage` checks the set
    reaches those capabilities instead.
    """
    bindings = load_catalog(catalog, source=source)
    bindings = apply_overrides(bindings, overrides or {})
    if include_emergency:
        bindings = bindings + emergency_bindings()

    accepted, diagnostics = validate(
        bindings, check_executables=check_executables
    )
    return Registry(bindings=accepted, diagnostics=diagnostics)


def report(diagnostics: Iterable[Diagnostic]) -> str:
    """A human-readable diagnostic block, or an empty string."""
    items = list(diagnostics)
    if not items:
        return ""
    errors = [d for d in items if d.severity == "error"]
    warnings = [d for d in items if d.severity == "warning"]
    lines: list[str] = []
    if errors:
        lines.append(f"{len(errors)} keybind error(s):")
        lines.extend(d.format() for d in errors)
    if warnings:
        if lines:
            lines.append("")
        lines.append(f"{len(warnings)} keybind warning(s):")
        lines.extend(d.format() for d in warnings)
    return "\n".join(lines)


# ── Emergency coverage ─────────────────────────────────────────────────

#: What a recoverable desktop must be able to do, and how to tell
#: whether a binding does it. Matched against the binding's action so a
#: renamed binding still counts, as long as it still does the job.
EMERGENCY_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "terminal": ("terminal.open", "app.terminal", "emergency.terminal"),
    "close-window": ("window.close", "emergency.close"),
    "settings": ("settings", "settings.open", "emergency.settings"),
    "reload": ("reload", "emergency.reload"),
    "exit": ("exit", "session.logout", "emergency.exit"),
}


def emergency_coverage(registry: Registry) -> dict[str, str | None]:
    """Which recovery capabilities the active bindings actually provide.

    Returns capability -> the binding id covering it, or None. A None
    here is worth shouting about: it means a user whose shell has died
    has no bound way to do that thing.
    """
    covered: dict[str, str | None] = {}
    active = {b.id: b for b in registry.active()}
    for capability, candidates in EMERGENCY_CAPABILITIES.items():
        found: str | None = None
        for candidate in candidates:
            binding = active.get(candidate)
            if binding is None:
                continue
            # The case being covered is "the shell is down", so a binding
            # counts only if it still does something then: either it
            # never needed the shell, or it has a stand-in that does not.
            if not binding.requires_shell or has_fallback(binding):
                found = candidate
                break
        covered[capability] = found
    return covered


def emergency_gaps(registry: Registry) -> list[str]:
    return [name for name, owner in emergency_coverage(registry).items() if owner is None]
