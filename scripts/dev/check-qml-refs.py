#!/usr/bin/env python3
"""Check QML against the singletons it uses.

`qmlformat` proves a file parses. It does not prove that `Assistant.busy`
exists, or that a file using `Process` imported `Quickshell.Io` — and
neither does anything else available offline, because qmllint cannot
resolve the Quickshell modules. Both mistakes produce a component that
loads to nothing at runtime, which on a bar means a module that silently
is not there.

So: read every singleton, collect the property, function and signal
names it declares, and flag any `Singleton.member` reference that does
not resolve. Then check that files using types from a Quickshell module
actually import it.

Comments and string literals are stripped first — "Processor" is not a
use of `Process`, and a filename in a string is not a reference.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parent.parent.parent
ROOT = REPO / "config" / "quickshell" / "halcyon"
SERVICES = ROOT / "Services"
#: Everything that consumes the singletons — which is the whole shell.
MODULES = ROOT

DECL = re.compile(
    r"^\s*(?:readonly\s+)?(?:required\s+)?property\s+\S+\s+(\w+)"
    r"|^\s*function\s+(\w+)"
    r"|^\s*signal\s+(\w+)",
    re.M,
)

# Singletons a module may touch, by the name it is used under.
singletons = {}
for path in SERVICES.glob("*.qml"):
    names = set()
    text = path.read_text()
    for match in DECL.finditer(text):
        names.add(next(g for g in match.groups() if g))
    singletons[path.stem] = names

# Config and Theme live in Config/.
for name in ("Config", "Theme", "Paths"):
    path = ROOT / "Config" / f"{name}.qml"
    if path.exists():
        names = set()
        for match in DECL.finditer(path.read_text()):
            names.add(next(g for g in match.groups() if g))
        singletons[name] = names

USE = re.compile(r"\b(" + "|".join(sorted(singletons)) + r")\.(\w+)")

# Qt built-ins reachable on any QObject.
UNIVERSAL = {"objectName", "destroy", "toString"}

problems = []
for path in sorted(MODULES.rglob("*.qml")):
    text = path.read_text()
    scrubbed = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    scrubbed = re.sub(r"//[^\n]*", " ", scrubbed)
    scrubbed = re.sub(r'"[^"\n]*"', '""', scrubbed)
    for match in USE.finditer(scrubbed):
        service, member = match.group(1), match.group(2)
        if member in UNIVERSAL:
            continue
        if member not in singletons[service]:
            line = scrubbed[: match.start()].count("\n") + 1
            problems.append(
                f"{path.relative_to(ROOT)}:{line}: {service}.{member} "
                f"is not declared in {service}"
            )

# Imports: a file using Process/StdioCollector needs Quickshell.Io.
NEEDS_IMPORT = {
    "Quickshell.Io": ("Process", "StdioCollector", "FileView", "IpcHandler",
                      "Socket", "SplitParser"),
    "Quickshell": ("Quickshell.", "SystemClock", "Variants", "PanelWindow",
                   "LazyLoader", "ShellRoot", "Singleton"),
    "Quickshell.Services.SystemTray": ("SystemTray",),
    "Quickshell.Hyprland": ("Hyprland",),
    "Quickshell.Wayland": ("WlrLayershell", "WlrLayer", "WlrKeyboardFocus"),
    "QtQuick.Layouts": ("RowLayout", "ColumnLayout", "Layout."),
}
for path in sorted(MODULES.rglob("*.qml")):
    text = path.read_text()
    # Strip imports, comments and string literals: "Processor" is not
    # a use of Process, and a filename in a string is not a reference.
    body = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("import")
    )
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    body = re.sub(r'"[^"\n]*"', '""', body)
    for module, tokens in NEEDS_IMPORT.items():
        used = [
            t for t in tokens
            if re.search(r"\b" + re.escape(t.rstrip(".")) + r"\b", body)
        ]
        if used and f"import {module}" not in text:
            problems.append(
                f"{path.relative_to(ROOT)}: uses {', '.join(used)} "
                f"but does not import {module}"
            )

if problems:
    print(f"{len(problems)} problem(s):")
    for problem in problems:
        print("  " + problem)
    sys.exit(1)

print(f"checked {len(list(MODULES.rglob('*.qml')))} QML file(s); references resolve")
