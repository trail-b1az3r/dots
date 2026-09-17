"""Reading, merging and writing Halcyon's settings.

There is exactly one user-editable settings file, `settings.json`, and
one shipped defaults file. The user's file only needs to contain what
differs from the defaults, so a hand-edited file stays small and a new
release can add options without rewriting anyone's configuration.

Writes are atomic (temp file plus rename): the shell watches this file,
and half a JSON document is worse than none.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from typing import Any

from . import SETTINGS_SCHEMA_VERSION, paths


class SettingsError(RuntimeError):
    """Raised when settings cannot be read or a value is rejected."""


def _read_json(path: os.PathLike[str] | str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise SettingsError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SettingsError(f"{path} must contain a JSON object")
    return data


def defaults() -> dict[str, Any]:
    """The shipped defaults.

    Falls back to the copy in the source tree so that the CLI works from
    a git checkout before `install.sh` has copied anything into place.
    """
    data = _read_json(paths.DEFAULTS_FILE)
    if data:
        return data

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback = os.path.join(
        os.path.dirname(here), "config", "system", "settings.default.json"
    )
    data = _read_json(fallback)
    if not data:
        raise SettingsError(
            "Cannot find settings.default.json — reinstall Halcyon or set "
            "HALCYON_DATA_DIR to the directory holding it."
        )
    return data


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively overlay one mapping onto a copy of another.

    Lists replace wholesale rather than merging element-wise: a user who
    reorders their bar modules means that order, not that order unioned
    with ours.
    """
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def user_settings() -> dict[str, Any]:
    """Just the user's overrides, with nothing merged in."""
    return _read_json(paths.SETTINGS_FILE)


def load() -> dict[str, Any]:
    """Defaults with the user's overrides applied."""
    base = defaults()
    overlay = user_settings()

    version = overlay.get("version", SETTINGS_SCHEMA_VERSION)
    if isinstance(version, int) and version > SETTINGS_SCHEMA_VERSION:
        raise SettingsError(
            f"{paths.SETTINGS_FILE} uses schema version {version}, but this "
            f"Halcyon understands up to {SETTINGS_SCHEMA_VERSION}. Upgrade "
            "Halcyon or move that file aside."
        )

    merged = deep_merge(base, overlay)
    merged["version"] = SETTINGS_SCHEMA_VERSION
    return merged


def save(overrides: dict[str, Any]) -> None:
    """Write the user's override document atomically."""
    paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(overrides)
    payload["version"] = SETTINGS_SCHEMA_VERSION

    fd, tmp = tempfile.mkstemp(
        dir=str(paths.CONFIG_DIR), prefix=".settings-", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, paths.SETTINGS_FILE)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── Dotted-path access ─────────────────────────────────────────────────


def get(path: str, settings: dict[str, Any] | None = None) -> Any:
    """Read `a.b.c` out of the merged settings."""
    node: Any = load() if settings is None else settings
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise SettingsError(f"No such setting: {path}")
        node = node[part]
    return node


def _coerce(path: str, value: Any, reference: Any) -> Any:
    """Make a string from the CLI match the type the default declares.

    Without this, `halcyon set glass.opacity 0.4` would store the string
    "0.4" and every consumer would have to defend against it.
    """
    if not isinstance(value, str):
        return value
    if isinstance(reference, bool):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "on", "1"):
            return True
        if lowered in ("false", "no", "off", "0"):
            return False
        raise SettingsError(f"{path} expects a boolean, got {value!r}")
    if isinstance(reference, int) and not isinstance(reference, bool):
        try:
            return int(value)
        except ValueError as exc:
            raise SettingsError(f"{path} expects an integer, got {value!r}") from exc
    if isinstance(reference, float):
        try:
            return float(value)
        except ValueError as exc:
            raise SettingsError(f"{path} expects a number, got {value!r}") from exc
    if isinstance(reference, (list, dict)):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise SettingsError(
                f"{path} expects JSON ({type(reference).__name__}), got {value!r}"
            ) from exc
    return value


def set_value(path: str, value: Any) -> dict[str, Any]:
    """Set `a.b.c` in the user's overrides and return the merged result.

    The path must already exist in the defaults. Refusing unknown keys
    turns a typo into an error message instead of a setting that silently
    never takes effect.
    """
    reference = get(path, defaults())
    value = _coerce(path, value, reference)

    overrides = user_settings()
    node = overrides
    parts = path.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value

    save(overrides)
    return load()


def unset(path: str) -> dict[str, Any]:
    """Drop an override so the default applies again."""
    overrides = user_settings()
    parts = path.split(".")
    node = overrides
    stack: list[tuple[dict[str, Any], str]] = []
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            return load()
        stack.append((node, part))
        node = child
    node.pop(parts[-1], None)

    # Prune containers we just emptied so the file does not accumulate
    # skeletons of settings the user reverted.
    for parent, key in reversed(stack):
        if isinstance(parent.get(key), dict) and not parent[key]:
            parent.pop(key)

    save(overrides)
    return load()


# ── Presets ────────────────────────────────────────────────────────────


def preset_files() -> dict[str, str]:
    """Map preset name to file path, searching install and source trees."""
    found: dict[str, str] = {}
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for directory in (str(paths.PRESETS_DIR), os.path.join(here, "themes")):
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith(".json"):
                found.setdefault(name[: -len(".json")], os.path.join(directory, name))
    return found


def load_preset(name: str) -> dict[str, Any]:
    files = preset_files()
    if name not in files:
        raise SettingsError(
            f"Unknown preset {name!r}. Available: {', '.join(sorted(files)) or 'none'}"
        )
    return _read_json(files[name])


def apply_preset(name: str) -> dict[str, Any]:
    """Merge a glass preset into the user's overrides."""
    preset = load_preset(name)
    patch = {k: v for k, v in preset.items() if k not in ("name", "description")}
    overrides = deep_merge(user_settings(), patch)
    save(overrides)
    return load()
