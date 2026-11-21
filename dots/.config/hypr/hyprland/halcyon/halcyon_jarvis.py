#!/usr/bin/env python3
"""halcyon jarvis: Jarvis, a small offline voice assistant (github.com/DwizSharma/jarvis-linux, MIT).

Say "wake up Jarvis" (or "hey Jarvis"), wait for "Yes?", then one command: "open Firefox", "click Search",
"type hello into Search", "scroll down", "screenshot", "list controls". "Jarvis exit" stops it until the next login.
It hears with Vosk on this computer: no account, no API key, no network once it is installed, about 50 MB of memory.

    halcyon jarvis                   installed, on or off, and running
    halcyon jarvis install           its packages (pacman), Jarvis at the tested commit, the English speech model
    halcyon jarvis on | off          start it with every Hyprland login, or stop it
    halcyon jarvis wake "PHRASE"     the wake phrase (default: wake up jarvis)
    halcyon jarvis log               what it heard and did lately

Not the Halcyon assistant (Super + Shift + Space, "Hey Halcyon"), which talks to an AI model: Jarvis only runs the
desktop, with fixed commands, and never sends anything anywhere.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "https://github.com/DwizSharma/jarvis-linux.git"
# The commit Halcyon was tested with (its code was read before it was pinned). Moving it is a change to Halcyon.
COMMIT = "67a6c0a3790051c36434f64507804118765728e1"
MODEL = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL}.zip"
# Python's AT-SPI and GObject bindings (control apps, open them), speech-dispatcher and espeak-ng (it answers out
# loud), PortAudio (the microphone, for sounddevice), grim (screenshots on Wayland).
PACKAGES = ["git", "python-gobject", "python-atspi", "at-spi2-core", "speech-dispatcher", "espeak-ng", "portaudio",
            "grim"]
SERVICE = "halcyon-jarvis.service"

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
STATE_HOME = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")
CODE = DATA / "halcyon/jarvis-linux"
MODELS = HOME / ".local/share/jarvis"          # where jarvis-linux looks (it doesn't read XDG_DATA_HOME)
CONFIG = HOME / ".config/jarvis/config.toml"   # the same
ON = STATE_HOME / "halcyon/jarvis-on"
LOG = HOME / ".local/state/jarvis/jarvis.log"


class JarvisError(RuntimeError):
    pass


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, **kwargs)


def missing_packages() -> list[str]:
    if not shutil.which("pacman"):
        return []
    return [p for p in PACKAGES if run(["pacman", "-Q", p], capture_output=True).returncode != 0]


def installed() -> bool:
    return (CODE / ".venv/bin/python").exists() and (CODE / "run-jarvis").exists() and (MODELS / MODEL).is_dir()


def installed_commit() -> str:
    result = run(["git", "-C", str(CODE), "rev-parse", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def fetch_code() -> None:
    if not (CODE / ".git").is_dir():
        if CODE.exists():
            raise JarvisError(f"{CODE} is in the way (not a git checkout): move it, then install again")
        CODE.parent.mkdir(parents=True, exist_ok=True)
        if run(["git", "clone", "-q", REPO, str(CODE)]).returncode != 0:
            raise JarvisError("could not download Jarvis (git clone failed)")
    if installed_commit() != COMMIT:
        run(["git", "-C", str(CODE), "fetch", "-q", "origin"])
        if run(["git", "-C", str(CODE), "checkout", "-q", "--detach", COMMIT]).returncode != 0:
            raise JarvisError(f"could not check out Jarvis {COMMIT[:7]}")


def make_venv() -> None:
    venv = CODE / ".venv"
    python = venv / "bin/python"
    if not python.exists():
        # System site packages: the AT-SPI and GObject bindings come from pacman, not pip.
        if run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)]).returncode != 0:
            raise JarvisError("could not make Jarvis's Python environment")
    pip = [str(python), "-m", "pip", "install", "-q", "--disable-pip-version-check"]
    if run([*pip, "-e", str(CODE)]).returncode != 0:
        raise JarvisError("could not install Vosk and sounddevice (pip)")


def safe_extract(archive: zipfile.ZipFile, target: Path) -> None:
    root = target.resolve()
    for member in archive.namelist():
        dest = (target / member).resolve()
        if dest != root and root not in dest.parents:
            raise JarvisError(f"the speech model's zip has a bad path: {member}")
    archive.extractall(target)


def fetch_model() -> None:
    if (MODELS / MODEL).is_dir():
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    print(f"downloading the English speech model ({MODEL}, about 40 MB)")
    with tempfile.TemporaryDirectory(dir=MODELS) as tmp:
        zip_path = Path(tmp) / "model.zip"
        try:
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response, zip_path.open("wb") as out:
                shutil.copyfileobj(response, out)
        except OSError as exc:
            raise JarvisError(f"could not download the speech model: {exc}") from exc
        unpack = Path(tmp) / "unpacked"
        with zipfile.ZipFile(zip_path) as archive:
            safe_extract(archive, unpack)
        (unpack / MODEL).rename(MODELS / MODEL)


def write_config(wake: str | None = None) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists() and wake is None:
        return
    text = CONFIG.read_text(encoding="utf-8") if CONFIG.exists() else (
        '[voice]\n# english, hindi or hinglish (Halcyon installs the English model: halcyon jarvis install)\n'
        'language = "english"\nvariant = "male2"\nrate = -12\npitch = -18\nwake_phrase = "wake up jarvis"\n')
    if wake is not None:
        line = 'wake_phrase = "' + wake.replace("\\", "").replace('"', "") + '"'
        text, count = re.subn(r"(?m)^wake_phrase\s*=.*$", line, text)
        if not count:
            text = text.rstrip("\n") + "\n" + line + "\n"
    CONFIG.write_text(text, encoding="utf-8")


def systemctl(*args: str) -> int:
    if not shutil.which("systemctl"):
        return 1
    return run(["systemctl", "--user", *args], capture_output=True).returncode


def accessibility_on() -> None:
    # GTK apps and Firefox read this; Qt apps get QT_LINUX_ACCESSIBILITY_ALWAYS_ON from init.lua while Jarvis is on.
    if shutil.which("gsettings"):
        run(["gsettings", "set", "org.gnome.desktop.interface", "toolkit-accessibility", "true"], capture_output=True)


def install(yes: bool = False) -> int:
    missing = missing_packages()
    if missing:
        print("installing " + " ".join(missing))
        if run(["sudo", "pacman", "-S", "--needed", *(["--noconfirm"] if yes else []), *missing]).returncode != 0:
            raise JarvisError("pacman could not install: " + " ".join(missing))
    fetch_code()
    make_venv()
    fetch_model()
    write_config()
    (CODE / "run-jarvis").chmod(0o755)
    print("Jarvis is installed. Turn it on: halcyon jarvis on")
    return 0


def status() -> int:
    if not installed():
        print("Jarvis: not installed (halcyon jarvis install)")
        missing = missing_packages()
        if missing:
            print("  missing packages: " + " ".join(missing))
        return 0
    commit = installed_commit()
    running = systemctl("is-active", "--quiet", SERVICE) == 0
    print(f"Jarvis: installed ({commit[:7] or 'unknown'}), {'on' if ON.exists() else 'off'}, "
          f"{'listening' if running else 'not running'}")
    if commit and commit != COMMIT:
        print(f"  not the tested commit {COMMIT[:7]}: halcyon jarvis install puts it back")
    try:
        wake = re.search(r'(?m)^wake_phrase\s*=\s*"(.*)"', CONFIG.read_text(encoding="utf-8"))
        print(f'  wake phrase: "{wake.group(1) if wake else "wake up jarvis"}" (or "hey jarvis")')
    except OSError:
        pass
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon jarvis", description="Jarvis, the offline voice assistant")
    parser.add_argument("action", nargs="?", default="status",
                        choices=["status", "install", "on", "off", "wake", "log", "login"])
    parser.add_argument("phrase", nargs="?", help="the wake phrase (halcyon jarvis wake)")
    parser.add_argument("--yes", action="store_true", help="install without asking pacman's questions")
    a = parser.parse_args(argv)
    try:
        if a.action == "status":
            return status()
        if a.action == "install":
            return install(a.yes)
        if a.action == "on":
            if not installed():
                install(a.yes)
            ON.parent.mkdir(parents=True, exist_ok=True)
            ON.touch()
            accessibility_on()
            systemctl("daemon-reload")
            systemctl("restart", SERVICE)
            print('Jarvis is on: say "wake up Jarvis". Qt apps opened before now can be controlled after they restart.')
            return 0
        if a.action == "off":
            ON.unlink(missing_ok=True)
            systemctl("stop", SERVICE)
            print("Jarvis is off.")
            return 0
        if a.action == "wake":
            if not a.phrase or not a.phrase.strip():
                parser.error('say which phrase: halcyon jarvis wake "hey jarvis"')
            write_config(a.phrase.strip().lower())
            if ON.exists():
                systemctl("restart", SERVICE)
            print(f'Wake phrase: "{a.phrase.strip().lower()}"')
            return 0
        if a.action == "log":
            try:
                print("\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
            except OSError:
                print("no log yet")
            return 0
        # login (from init.lua at Hyprland's start): start it when it is on.
        if ON.exists() and installed():
            systemctl("restart", SERVICE)
        return 0
    except JarvisError as exc:
        print(f"halcyon jarvis: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
