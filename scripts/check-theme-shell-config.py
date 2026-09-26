#!/usr/bin/env python3
"""Fail if a theme's shell_config names a setting the shell doesn't have.

The shell ignores unknown keys in config.json, so a typo in a theme would
silently do nothing. This reads the option tree out of Config.qml (nested
`property JsonObject name: JsonObject {` blocks and `property <type> name:`
leaves) and checks every dotted key against it, including the value's type.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_QML = ROOT / "dots/.config/quickshell/ii/modules/common/Config.qml"
THEMES = ROOT / "dots/.config/hypr/hyprland/halcyon/themes"

OBJECT = re.compile(r"^\s*property JsonObject (\w+): JsonObject \{")
LEAF = re.compile(r"^\s*property ([\w<>]+) (\w+):")
TYPES = {"bool": (bool,), "int": (int,), "real": (int, float), "string": (str,)}


STRINGS = re.compile(r'"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`')


def option_tree():
    """Map dotted option names under the JsonAdapter to their QML type."""
    options = {}
    stack = []      # names of the JsonObjects we are inside
    opened_at = []  # brace depth at which each of them opened
    depth = 0
    adapter_depth = None
    for line in CONFIG_QML.read_text(encoding="utf-8").splitlines():
        # Braces inside strings (the AI prompt has {DISTRO}) are not code.
        code = STRINGS.sub('""', line).split("//", 1)[0]
        if adapter_depth is None and re.match(r"^\s*JsonAdapter \{", code):
            adapter_depth = depth
        elif adapter_depth is not None:
            match = OBJECT.match(code)
            if match:
                stack.append(match.group(1))
                opened_at.append(depth)
            else:
                leaf = LEAF.match(code)
                if leaf and depth == adapter_depth + 1 + len(stack):
                    options[".".join(stack + [leaf.group(2)])] = leaf.group(1)
        depth += code.count("{") - code.count("}")
        while opened_at and depth <= opened_at[-1]:
            stack.pop()
            opened_at.pop()
        if adapter_depth is not None and depth <= adapter_depth and not code.strip().startswith("JsonAdapter"):
            break
    return options


def main():
    options = option_tree()
    if len(options) < 50:
        print(f"only found {len(options)} options in Config.qml; the parser needs updating", file=sys.stderr)
        return 1
    problems = []
    for path in sorted(THEMES.glob("*.json")):
        theme = json.loads(path.read_text(encoding="utf-8"))
        for key, value in (theme.get("shell_config") or {}).items():
            qml_type = options.get(key)
            if qml_type is None:
                problems.append(f"{path.name}: shell_config.{key} is not a shell option")
                continue
            expected = TYPES.get(qml_type)
            if qml_type.startswith("list"):
                expected = (list,)
            if expected and (not isinstance(value, expected) or (isinstance(value, bool) and bool not in expected)):
                problems.append(f"{path.name}: shell_config.{key} should be {qml_type}, got {value!r}")
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"ok: theme shell settings match Config.qml ({len(options)} options known)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
