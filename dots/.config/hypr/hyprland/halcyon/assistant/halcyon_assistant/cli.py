"""halcyon assistant: the command line."""

import getpass
import logging
import os
import subprocess
import sys
import time
import urllib.request
import zipfile

from . import audio, config, daemon, providers, speech, stt, wake

USAGE = """Halcyon's voice assistant.

    halcyon assistant listen        talk to it (Super + Shift + Space); again cancels
    halcyon assistant ask TEXT      ask in writing; prints the reply
    halcyon assistant cancel        stop whatever it is doing
    halcyon assistant doctor        what is set up and what isn't

    halcyon assistant setup         install speech recognition (one time, ~300 MB)
          --wake                    ...and the offline "hey halcyon" wake word model
          --piper                   ...and a natural Piper voice instead of espeak-ng
    halcyon assistant login         use your Claude Pro/Max plan instead of an API key
    halcyon assistant key ID [KEY]  store an API key: anthropic, gemini, openai, mistral...
    halcyon assistant set NAME VALUE  change a setting (provider, model, wakeWord, speak...)

    halcyon assistant daemon        run the assistant (Hyprland starts it for you)

Settings > Halcyon > Assistant has the same settings. Keys are shared with the
AI sidebar: a Gemini key entered there works here too.
"""

PIP_PACKAGES = ["faster-whisper", "numpy", "anthropic"]
PIPER_VOICE = "en_US-lessac-medium"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/"


def _ensure_daemon():
    if daemon.send("status") is not None:
        return True
    launcher = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "halcyon-assistant")
    config.ASSISTANT_STATE.mkdir(parents=True, exist_ok=True)
    with open(config.LOG, "a") as log:
        subprocess.Popen([launcher, "daemon"], stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    for _ in range(50):
        time.sleep(0.1)
        if daemon.send("status") is not None:
            return True
    return False


def _download(url, dest):
    print(f"downloading {url.rsplit('/', 1)[-1]}…")
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=60) as response, open(tmp, "wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.rename(dest)


def setup(args):
    venv_python = config.VENV / "bin/python"
    if not venv_python.exists():
        print(f"creating {config.VENV}")
        subprocess.run([sys.executable, "-m", "venv", str(config.VENV)], check=True)
    packages = list(PIP_PACKAGES)
    if "--wake" in args or config.settings()["wakeWord"]:
        packages.append("vosk")
    if "--piper" in args:
        packages.append("piper-tts")
    print("installing " + ", ".join(packages))
    subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "--quiet", *packages], check=True)

    config.MODELS.mkdir(parents=True, exist_ok=True)
    if "vosk" in packages and not wake.model_path().is_dir():
        archive = config.MODELS / f"{wake.MODEL_NAME}.zip"
        _download(wake.MODEL_URL, archive)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(config.MODELS)
        archive.unlink()
    if "--piper" in args:
        voices = config.MODELS / "piper"
        voices.mkdir(exist_ok=True)
        for suffix in (".onnx", ".onnx.json"):
            target = voices / f"{PIPER_VOICE}{suffix}"
            if not target.exists():
                _download(f"{PIPER_BASE}{PIPER_VOICE}{suffix}", target)
        piper_bin = config.VENV / "bin/piper"
        local_bin = config.HOME / ".local/bin/piper"
        if piper_bin.exists() and not local_bin.exists():
            local_bin.parent.mkdir(parents=True, exist_ok=True)
            local_bin.symlink_to(piper_bin)

    print(f"fetching the Whisper '{config.settings()['speechModel']}' model…")
    subprocess.run([str(venv_python), "-c",
                    "import sys; sys.path.insert(0, sys.argv[1]); from halcyon_assistant import stt; stt.load(sys.argv[2])",
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config.settings()["speechModel"]],
                   check=True)
    if daemon.send("status") is not None:
        daemon.send("quit")  # restart it so it picks up the new packages
    print("done. Press Super + Shift + Space and speak.")
    return 0


CLAUDE_CODE_INSTALLER = "https://claude.ai/install.sh"


def login(_args):
    """Use a Claude Pro/Max plan, through Anthropic's own Claude Code."""
    print("Halcyon uses your Claude plan through Claude Code, Anthropic's official CLI.\n"
          "You sign in to Claude Code yourself; Halcyon never sees your login.\n"
          "Requests count against your plan's usage limits.\n")
    if not providers.shutil.which("claude"):
        print(f"Claude Code isn't installed. Anthropic's installer is:\n  curl -fsSL {CLAUDE_CODE_INSTALLER} | bash")
        if not sys.stdin.isatty() or input("Run it now? [y/N] ").strip().lower() != "y":
            print("Install it, then run `halcyon assistant login` again.")
            return 1
        subprocess.run(["bash", "-c", f"curl -fsSL {CLAUDE_CODE_INSTALLER} | bash"], check=False)
        local_bin = str(config.HOME / ".local/bin")
        os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")
        if not providers.shutil.which("claude"):
            print("Claude Code still isn't on PATH; open a new terminal and try again.")
            return 1
    if providers.claude_code_signed_in():
        print("Claude Code is already signed in.")
    else:
        env = {k: v for k, v in os.environ.items() if k not in providers.ClaudeCode.ENV_CREDENTIALS}
        # Without --console this signs in with a claude.ai (Pro/Max) account.
        if subprocess.run(["claude", "auth", "login"], env=env).returncode != 0 \
                or not providers.claude_code_signed_in():
            print("Sign-in didn't finish. Run `halcyon assistant login` to try again.")
            return 1
    config.write_setting("provider", "claude-code")
    daemon.send("reload")
    print("\nDone: the assistant now uses your Claude plan. Press Super + Shift + Space and speak.")
    return 0


def doctor(_args):
    settings = config.settings()
    rows = [
        ("microphone recorder", " ".join(audio.recorder_command() or ["missing: install pipewire"])[:40]),
        ("speech recognition", "ready" if stt.available() else "not set up: halcyon assistant setup"),
        ("wake word", ("on, " if settings["wakeWord"] else "off, ") +
         ("model ready" if wake.available() else "not set up (setup --wake)")),
        ("voice", speech.engine() or "none: install espeak-ng, or setup --piper"),
        ("daemon", "running" if daemon.send("status") is not None else "not running"),
    ]
    try:
        provider = providers.resolve(settings)
        rows.append(("AI", f"{provider.name}, model {provider.model}"))
    except providers.ProviderError as error:
        rows.append(("AI", f"not ready: {error}"))
    rows.append(("Claude plan", "signed in (Claude Code)" if providers.claude_code_signed_in() else
                 ("Claude Code installed, not signed in" if providers.shutil.which("claude") else
                  "-  (halcyon assistant login)")))
    for key_id in ("anthropic", "gemini", "openai", "mistral"):
        rows.append((f"{key_id} key", "set" if config.api_key(key_id) else "-"))
    width = max(len(r[0]) for r in rows)
    for name, value in rows:
        print(f"{name:<{width}}  {value}")
    return 0


def ask(args):
    text = " ".join(args).strip()
    if not text:
        print("usage: halcyon assistant ask TEXT", file=sys.stderr)
        return 2
    from .conversation import Conversation
    settings = config.settings()
    try:
        reply = Conversation(providers.resolve(settings), settings["allowActions"]).ask(
            text, on_action=lambda name, a: print(f"[{name} {a}]", file=sys.stderr))
    except providers.ProviderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(reply)
    return 0


def parse_value(key, raw):
    default = config.DEFAULTS[key]
    if isinstance(default, bool):
        if raw.lower() in ("true", "on", "yes", "1"):
            return True
        if raw.lower() in ("false", "off", "no", "0"):
            return False
        raise ValueError(f"{key} is on or off")
    return raw


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    command, args = argv[0], argv[1:]
    if command == "daemon":
        return daemon.Assistant().serve()
    if command == "autostart":
        # Hyprland runs this at startup: start only if it's turned on.
        return daemon.Assistant().serve() if config.settings()["enable"] else 0
    if command == "stop":
        print(daemon.send("quit") or "not running")
        return 0
    if command in ("listen", "cancel", "reload", "status"):
        if command == "listen" and not config.settings()["enable"]:
            print("the assistant is turned off in Settings > Halcyon > Assistant", file=sys.stderr)
            return 1
        if command in ("listen",) and not _ensure_daemon():
            print(f"couldn't start the assistant; see {config.LOG}", file=sys.stderr)
            return 1
        reply = daemon.send(command)
        print(reply if reply is not None else "not running")
        return 0
    if command == "ask":
        return ask(args)
    if command == "setup":
        return setup(args)
    if command == "login":
        return login(args)
    if command == "doctor":
        return doctor(args)
    if command == "key" and args:
        value = args[1] if len(args) > 1 else getpass.getpass(f"{args[0]} API key: ")
        config.store_api_key(args[0], value)
        print(f"stored the {args[0]} key in the keyring")
        return 0
    if command == "set" and len(args) == 2 and args[0] in config.DEFAULTS:
        try:
            config.write_setting(args[0], parse_value(args[0], args[1]))
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        daemon.send("reload")
        print(f"{args[0]} = {config.settings()[args[0]]}")
        return 0
    print(USAGE, file=sys.stderr)
    return 2
