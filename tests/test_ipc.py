"""Every button and keybind that calls the shell must reach a real handler.

A call into `halcyon shell <target> <function>` that names a target or a
function the shell does not define does nothing, and nothing reports it.
That is how the bar's Settings button shipped dead. These tests read the
handlers out of shell.qml and the calls out of everything that makes one.
"""

from __future__ import annotations

import pathlib
import re
import unittest

from halcyon import pipeline

REPO = pathlib.Path(__file__).resolve().parent.parent
QML = REPO / "config" / "quickshell" / "halcyon"


def handlers() -> dict[str, set[str]]:
    """target -> function names, from every IpcHandler in shell.qml."""
    text = (QML / "shell.qml").read_text(encoding="utf-8")
    found: dict[str, set[str]] = {}
    for match in re.finditer(
        r'IpcHandler\s*\{\s*target:\s*"(\w+)"(.*?)\n    \}', text, re.S
    ):
        found[match.group(1)] = set(re.findall(r"function\s+(\w+)\s*\(", match.group(2)))
    return found


class TestHandlers(unittest.TestCase):
    def test_the_shell_defines_handlers(self) -> None:
        self.assertGreater(len(handlers()), 10)

    def test_every_handler_target_is_unique(self) -> None:
        text = (QML / "shell.qml").read_text(encoding="utf-8")
        targets = re.findall(r'IpcHandler\s*\{\s*target:\s*"(\w+)"', text)
        self.assertEqual(len(targets), len(set(targets)))


class TestUiCallsReachHandlers(unittest.TestCase):
    def test_every_qml_shell_call_has_a_handler(self) -> None:
        known = handlers()
        dead: list[str] = []
        for path in sorted(QML.rglob("*.qml")):
            text = path.read_text(encoding="utf-8")
            calls = re.findall(r'run\(\["shell",\s*"(\w+)",\s*"(\w+)"', text)
            calls += re.findall(r'"halcyon shell (\w+) (\w+)', text)
            for target, function in calls:
                if function not in known.get(target, set()):
                    dead.append(f"{path.relative_to(REPO)}: shell {target} {function}")
        self.assertEqual(dead, [], msg="dead buttons: no such IPC function")

    def test_the_bar_settings_button_is_wired(self) -> None:
        # The specific one that was dead, pinned so it cannot regress.
        self.assertIn("toggle", handlers()["settings"])


class TestKeybindCallsReachHandlers(unittest.TestCase):
    def test_every_bound_shell_command_has_a_handler(self) -> None:
        known = handlers()
        dead: list[str] = []
        for bind in pipeline.load_catalog()["binds"]:
            command = str(bind.get("action", {}).get("exec", ""))
            match = re.match(r"halcyon shell (\w+) (\w+)", command)
            if match and match.group(2) not in known.get(match.group(1), set()):
                dead.append(f"{bind['id']}: {command}")
        self.assertEqual(dead, [], msg="keybinds that call nothing")


if __name__ == "__main__":
    unittest.main()


class TestUiCommandsExist(unittest.TestCase):
    """Every `halcyon <subcommand>` the QML issues must be a real subcommand.

    Checked against the parser itself rather than `--help` text: the help
    does not list every special value (`backlight status` is one), so text
    matching both misses real commands and invents dead ones.
    """

    def subcommands(self) -> set[str]:
        import argparse

        from halcyon import cli

        parser = cli.build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                return set(action.choices)
        raise AssertionError("no subcommands found")

    def test_every_ui_halcyon_command_is_a_real_subcommand(self) -> None:
        known = self.subcommands()
        dead: list[str] = []
        for path in sorted(QML.rglob("*.qml")):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(
                r'(?:run|capture|command|Paths\.command)\(\[\s*"(\w+)"', text
            ):
                name = match.group(1)
                if name == "shell":
                    continue  # checked against the IPC handlers above
                if name not in known:
                    dead.append(f"{path.relative_to(REPO)}: halcyon {name}")
        self.assertEqual(dead, [], msg="UI calls a halcyon subcommand that does not exist")

    def test_the_brightness_reader_command_is_accepted(self) -> None:
        # The case the first version of this check got wrong.
        from halcyon import cli

        parser = cli.build_parser()
        args = parser.parse_args(["backlight", "status"])
        self.assertEqual(args.value, "status")
