"""halcyon assistant: the command line."""

import getpass
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import zipfile

from . import audio, config, daemon, local_tts, localai, pcm, piper_voices, providers, speech, stt, wake

USAGE = """Halcyon's voice assistant.

    halcyon assistant listen        talk to it (Super + Shift + Space); again cancels
    halcyon assistant ask TEXT      ask in writing; prints the reply
    halcyon assistant say TEXT      read text aloud with the voice replies use (- reads it from stdin)
    halcyon assistant cancel        stop whatever it is doing
    halcyon assistant doctor        what is set up and what isn't
    halcyon assistant test-voice    say a sentence with each voice engine; says why one fails
    halcyon assistant test-mic      record 3 seconds and play them back
    halcyon assistant models        the LM Studio, HyperNix and T1 models it can use

    halcyon assistant voices [--all] [--json] [WORDS]
                                    the Piper voices here; --all adds Hugging Face's and the AUR's
    halcyon assistant voice         the Piper voice in use
    halcyon assistant voice use KEY|PATH [--speaker NAME]   speak with that voice (one here, or a .onnx file)
    halcyon assistant voice get KEY download a voice from Hugging Face (rhasspy/piper-voices) and use it
    halcyon assistant voice aur PACKAGE  install a piper-voices-* package with your AUR helper
    halcyon assistant voice remove KEY   delete a downloaded voice
    halcyon assistant voice preview KEY  say a sentence with a voice here, without choosing it

    halcyon assistant setup         install speech recognition (one time, ~300 MB)
          --wake                    ...and the offline "hey halcyon" wake word model
          --piper                   ...and a natural Piper voice instead of espeak-ng
          --kokoro                  ...and Kokoro, a local voice model with 54 voices (~340 MB)
    halcyon assistant login         use your Claude Pro/Max plan instead of an API key
    halcyon assistant key ID [KEY]  store an API key: anthropic, gemini, openai, mistral, t1...
    halcyon assistant set NAME VALUE  change a setting (provider, model, t1Server, wakeWord, speak...)
    halcyon assistant ensure lmstudio|hypernix [MODEL]
                                    start LM Studio's server or HyperNix's runtime with a model

Providers: claude, claude-code (your Claude plan), gemini, ollama, lmstudio (LM Studio), hypernix
(`hnx runtime serve` with a model from ~/.hypernix/models), t1 (a HyperNix T1 server: set t1Server and
`key t1 T1_...`), openai (any OpenAI-compatible server). The AI sidebar lists the same local models.

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
    if "--kokoro" in args:
        packages.append("kokoro-onnx")
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

    if "--kokoro" in args:
        local_tts.kokoro_download()
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
    # Always run the sign-in, even when a login file is there: the file can
    # outlive its session, and signing in again is what refreshes it.
    env = {k: v for k, v in os.environ.items() if k not in providers.ClaudeCode.ENV_CREDENTIALS}
    # Without --console this signs in with a claude.ai (Pro/Max) account.
    if subprocess.run(["claude", "auth", "login"], env=env).returncode != 0 \
            or not providers.claude_code_signed_in():
        print("Sign-in didn't finish. Run `halcyon assistant login` to try again.")
        return 1
    # The daemon doesn't see this terminal's environment, so it is told where
    # the login is, and the voice path uses the same directory.
    config.write_setting("claudeConfigDir", str(providers.claude_config_dir()))
    config.write_setting("provider", "claude-code")
    daemon.send("reload")
    print("\nDone: the assistant now uses your Claude plan. Press Super + Shift + Space and speak.")
    return 0


def doctor(_args):
    settings = config.settings()
    engines = speech.engines(settings)
    rows = [
        ("microphone recorder", " ".join(audio.recorder_command() or ["missing: install pipewire"])[:48]),
        ("audio player", " ".join(pcm.player(22050) or ["missing: install pipewire"])[:48]),
        ("speech recognition", "ready" if stt.available() else "not set up: halcyon assistant setup"),
        ("wake word", ("on, " if settings["wakeWord"] else "off, ") +
         ("model ready" if wake.available() else "not set up (setup --wake)")),
        ("voice", ", ".join(engines) + "  (test-voice tries them)" if engines
         else "none: install espeak-ng, setup --piper, or store a Gemini/OpenAI key"),
        ("voice setting", settings["voice"] + (f" (AI voice: {speech.tts_ai.provider(settings)})"
                                               if speech.tts_ai.provider(settings) else "")),
        ("speak replies", "on" if settings["speak"] else "off (Settings > Halcyon > Assistant)"),
        ("daemon", "running" if daemon.send("status") is not None else "not running"),
    ]
    try:
        provider = providers.resolve(settings)
        rows.append(("AI", f"{provider.name}, model {provider.model}"))
    except providers.ProviderError as error:
        rows.append(("AI", f"not ready: {error}"))
    rows.append(("Claude plan", "signed in (Claude Code)" if providers.claude_code_signed_in(settings["claudeConfigDir"]) else
                 ("Claude Code installed, not signed in" if providers.shutil.which("claude") else
                  "-  (halcyon assistant login)")))
    rows.append(("LM Studio", "running" if localai.reachable(localai.LMSTUDIO_URL) else
                 ("installed (`lms`), server off" if localai.lms_cli() else "-")))
    hnx_models = localai.hypernix_models()
    rows.append(("HyperNix", ("runtime serving " + ", ".join(localai.hypernix_served())) if localai.hypernix_served() else
                 (f"{len(hnx_models)} model(s) in ~/.hypernix/models" + ("" if localai.hnx_cli() else ", `hnx` missing"))
                 if hnx_models else ("installed, no models" if localai.hnx_cli() else "-")))
    rows.append(("T1 server", settings["t1Server"] or "-  (halcyon assistant set t1Server URL)"))
    for key_id in ("anthropic", "gemini", "openai", "mistral", "t1"):
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


def say(args):
    """Read text aloud: through the daemon when it runs (so `cancel` and the shortcut stop it), else here."""
    text = sys.stdin.read() if args == ["-"] else " ".join(args)
    if args[:1] == ["--"]:
        text = " ".join(args[1:])
    spoken = speech.plain(text)
    if not spoken:
        return 0
    settings = config.settings()
    if not settings["speak"]:
        print("speaking replies is off in Settings > Halcyon > Assistant", file=sys.stderr)
        return 0
    reply = daemon.send("say " + spoken)
    if reply in ("speaking", "busy"):
        return 0
    return 0 if speech.say(spoken, settings=settings) else 1


def _matches(entry, words):
    text = " ".join(str(entry.get(k, "")) for k in ("key", "name", "language", "languageName", "country",
                                                       "quality", "description")).lower()
    return all(word.lower() in text for word in words)


def voices(args):
    """The Piper voices: here, and with --all the ones Hugging Face and the AUR have."""
    as_json = "--json" in args
    everything = "--all" in args
    words = [a for a in args if not a.startswith("--")]
    settings = config.settings()
    current = piper_voices.resolve(settings["piperVoice"])
    result = {"current": current["key"] if current else "", "chosen": settings["piperVoice"],
              "speaker": settings["piperSpeaker"], "piper": bool(speech.piper_binary()),
              "aurHelper": piper_voices.aur_helper() or "",
              "installed": [v for v in piper_voices.installed() if _matches(v, words)], "errors": []}
    if everything:
        here = {v["key"] for v in result["installed"]}
        try:
            result["huggingface"] = [dict(v, installed=v["key"] in here)
                                     for v in piper_voices.catalog() if _matches(v, words)]
        except piper_voices.VoiceError as error:
            result["huggingface"], result["errors"] = [], result["errors"] + [f"Hugging Face: {error}"]
        try:
            result["aur"] = [p for p in piper_voices.aur_packages() if _matches(p, words)]
        except piper_voices.VoiceError as error:
            result["aur"], result["errors"] = [], result["errors"] + [f"AUR: {error}"]
    if as_json:
        print(json.dumps(result))
        return 0
    print("Here:" if result["installed"] else "No Piper voices here yet.")
    for v in result["installed"]:
        mark = "*" if v["key"] == result["current"] else " "
        extra = f", {len(v['speakers'])} speakers" if v["speakers"] else ""
        print(f" {mark} {v['key']:<34} {v['source']:<12} {v['languageName'] or v['language']}{extra}")
    if everything:
        print(f"\nOn Hugging Face ({len(result['huggingface'])}): halcyon assistant voice get KEY")
        for v in result["huggingface"]:
            print(f"   {v['key']:<34} {v['size'] // 1_000_000:>4} MB  {v['languageName']} ({v['country']})"
                  + ("  [here]" if v["installed"] else ""))
        print(f"\nIn the AUR ({len(result['aur'])}): halcyon assistant voice aur PACKAGE  (every voice of a language)")
        for p in result["aur"]:
            print(f"   {p['name']:<34} {p['version']:<10} " + ("[installed]" if p["installed"] else ""))
    for error in result["errors"]:
        print(f"note: {error}", file=sys.stderr)
    if not everything:
        print("\n--all lists the ones you can add, from Hugging Face and the AUR.")
    return 0


def voice(args):
    settings = config.settings()
    if not args:
        current = piper_voices.resolve(settings["piperVoice"])
        if current is None:
            print("no Piper voice: halcyon assistant voices --all, then voice get KEY")
            return 1
        print(f"{current['key']}  ({current['source']}, {current['path']})"
              + (f", speaker {settings['piperSpeaker']}" if settings["piperSpeaker"] else ""))
        return 0
    command, rest = args[0], args[1:]
    try:
        if command == "use" and rest:
            choice = rest[0]
            speaker = rest[rest.index("--speaker") + 1] if "--speaker" in rest[:-1] else ""
            found = piper_voices.resolve(choice)
            if found is None:
                print(f"{choice} is not here. `halcyon assistant voice get {choice}` downloads it from Hugging Face.",
                      file=sys.stderr)
                return 1
            if speaker and piper_voices.speaker_id(found, speaker) is None:
                print(f"{found['key']} has no speaker {speaker}: " + (", ".join(found["speakers"]) or "it has one voice"),
                      file=sys.stderr)
                return 1
            # A file outside the usual folders is kept by path, a voice in them by its key.
            keep = found["path"] if "/" in choice else found["key"]
            config.write_setting("piperVoice", "" if keep == piper_voices.BUILTIN else keep)
            config.write_setting("piperSpeaker", speaker)
            daemon.send("reload")
            print(f"speaking with {found['key']}" + (f", speaker {speaker}" if speaker else ""))
            return 0
        if command == "get" and len(rest) == 1:
            def progress(done, total):
                if total:
                    print(f"\r{rest[0]}: {done * 100 // total}% of {total // 1_000_000} MB", end="", flush=True)
            path = piper_voices.download(rest[0], progress)
            print(f"\nsaved {path}")
            return voice(["use", rest[0]])
        if command == "aur" and len(rest) == 1:
            helper_command = piper_voices.aur_install_command(rest[0])
            print("running: " + " ".join(helper_command))
            done = subprocess.run(helper_command, check=False)
            if done.returncode == 0:
                print("installed. Its voices are listed by: halcyon assistant voices")
            return done.returncode
        if command == "remove" and len(rest) == 1:
            print(f"removed {piper_voices.remove(rest[0])}")
            if settings["piperVoice"] == rest[0]:
                config.write_setting("piperVoice", "")
                daemon.send("reload")
            return 0
        if command == "preview" and rest:
            preview = dict(settings, piperVoice=rest[0], piperSpeaker=rest[1] if len(rest) > 1 else "")
            text = "Hello. This is how I sound."
            problem = speech.speak_once("piper", text, settings=preview)
            if problem:
                print(f"failed: {problem}", file=sys.stderr)
                return 1
            return 0
    except piper_voices.VoiceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("usage: halcyon assistant voice [use KEY|PATH [--speaker NAME] | get KEY | aur PACKAGE | remove KEY | preview KEY]",
          file=sys.stderr)
    return 2


def test_voice(args):
    """Speak with every installed engine, the way replies are spoken, and say what went wrong."""
    text = " ".join(args) or "Hello. This is Halcyon's voice."
    settings = config.settings()
    voice = speech.piper_voice(settings)
    player = pcm.player(speech.piper_rate(voice) if voice else speech.DEFAULT_RATE)
    if voice:
        print(f"Piper voice: {voice.stem} ({voice})")
    print(f"audio player: {' '.join(player) if player else 'none (install pipewire)'}")
    print(f"voice setting: {settings['voice']}" + (f", AI voice from {speech.tts_ai.provider(settings)}"
                                                    if speech.tts_ai.provider(settings) else ", no AI voice (no Gemini or OpenAI key)"))
    if pcm.pipewire_has_raw():
        print("PipeWire 1.2 or later: raw audio needs --raw, which Halcyon passes")
    engines = speech.engines(settings)
    if not engines:
        print("no voice engine: install espeak-ng, run `halcyon assistant setup --piper`, "
              "or store a key for an AI voice (`halcyon assistant key gemini`)")
        return 1
    worked = []
    for name in engines:
        print(f"{name}: speaking…", flush=True)
        problem = speech.speak_once(name, text, settings=settings)
        print(f"{name}: " + ("ok" if problem is None else f"failed: {problem}"))
        if problem is None:
            worked.append(name)
    if not config.settings()["speak"]:
        print("note: speaking replies is off in Settings > Halcyon > Assistant")
    if worked:
        print(f"replies will be spoken with {worked[0]}")
        return 0
    return 1


def test_mic(_args):
    """Record three seconds from the default microphone and play them back."""
    recorder, player = pcm.recorder(audio.RATE), pcm.player(audio.RATE)
    if not recorder or not player:
        print("missing a recorder or player: install pipewire (pw-record, pw-play)")
        return 1
    print(f"recording 3 s with: {' '.join(recorder)}")
    try:
        done = subprocess.run(recorder, capture_output=True, timeout=3.5)
        data = done.stdout
    except subprocess.TimeoutExpired as expired:
        data = expired.stdout or b""
    if not data:
        print("nothing was recorded: is a microphone connected and not muted? (pavucontrol, wpctl status)")
        return 1
    import array
    samples = array.array("h", data[: len(data) // 2 * 2])
    peak = max((abs(x) for x in samples), default=0)
    print(f"got {len(data) // 2 / audio.RATE:.1f} s, loudest {peak * 100 // 32768}% of full scale"
          + ("  (very quiet: check the input volume)" if peak < 600 else ""))
    print("playing it back…")
    subprocess.run(player, input=data, check=False)
    return 0


def models(args):
    """The local and T1 models. --sidebar prints them for the AI sidebar (JSON); --json as data."""
    settings = config.settings()
    found = localai.sidebar_models(settings["t1Server"], bool(config.api_key("t1")))
    if "--sidebar" in args or "--json" in args:
        print(json.dumps(found))
        return 0
    if not found:
        print("no LM Studio, HyperNix or T1 models found.\n"
              "  LM Studio: download a model in LM Studio (or `lms get MODEL`)\n"
              "  HyperNix:  put a .gguf in ~/.hypernix/models (or HyperLink / `hypernix download`)\n"
              "  T1:        halcyon assistant set t1Server http://HOST:PORT")
        return 0
    for entry in found.values():
        print(f"{entry['name']:<44} {entry['model']}")
    return 0


def ensure(args):
    """Start LM Studio's server or HyperNix's runtime with a model. The AI sidebar runs this before a request;
    with --sse-error a failure is printed as the error line its stream reader shows."""
    sse = "--sse-error" in args
    rest = [a for a in args if a != "--sse-error"]
    if not rest or rest[0] not in ("lmstudio", "hypernix"):
        print("usage: halcyon assistant ensure lmstudio|hypernix [MODEL]", file=sys.stderr)
        return 2
    model = rest[1] if len(rest) > 1 else ""
    try:
        ready = localai.lmstudio_ensure(model) if rest[0] == "lmstudio" else localai.hypernix_ensure(model)
    except localai.LocalAIError as error:
        if sse:
            print("data: " + json.dumps({"error": {"message": str(error)}}), flush=True)
        else:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(ready, file=sys.stderr if sse else sys.stdout)
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
    if command == "say":
        return say(args)
    if command == "voices":
        return voices(args)
    if command == "voice":
        return voice(args)
    if command == "test-voice":
        return test_voice(args)
    if command == "test-mic":
        return test_mic(args)
    if command == "models":
        return models(args)
    if command == "ensure":
        return ensure(args)
    if command == "key" and args:
        value = args[1] if len(args) > 1 else getpass.getpass(f"{args[0]} API key: ")
        config.store_api_key(args[0], value)
        print(f"stored the {args[0]} key in the keyring")
        return 0
    if command == "set" and len(args) == 2 and args[0] in config.DEFAULTS:
        if args[0] == "provider" and args[1] not in config.PROVIDERS:
            print(f"error: provider is one of {', '.join(config.PROVIDERS)}", file=sys.stderr)
            return 2
        if args[0] == "voice" and args[1] not in config.VOICES:
            print(f"error: voice is one of {', '.join(config.VOICES)}", file=sys.stderr)
            return 2
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
