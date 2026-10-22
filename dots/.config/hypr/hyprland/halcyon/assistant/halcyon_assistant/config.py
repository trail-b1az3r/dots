"""Settings (Settings > Halcyon > Assistant) and credentials."""

import json
import os
import shutil
import subprocess
from pathlib import Path

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")
RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/halcyon-{os.getuid()}")

SHELL_CONFIG = CONFIG / "illogical-impulse/config.json"
ASSISTANT_STATE = STATE / "halcyon/assistant"
VENV = ASSISTANT_STATE / "venv"
MODELS = ASSISTANT_STATE / "models"
LOG = ASSISTANT_STATE / "assistant.log"
SOCKET = RUNTIME / "halcyon-assistant.sock"
if len(str(SOCKET)) > 100:  # Unix socket paths are limited to ~108 bytes
    SOCKET = Path(f"/tmp/halcyon-assistant-{os.getuid()}.sock")

VOICES = ("auto", "piper", "kokoro", "command", "fish", "drama3", "ai", "espeak", "system")
PROVIDERS = ("auto", "claude", "claude-code", "gemini", "ollama", "lmstudio", "hypernix", "t1", "openai")
DEFAULTS = {
    "enable": True,          # start the assistant with Hyprland
    # auto: Claude API key, else Claude plan (Claude Code), else Gemini, else a T1 server with a key, else
    # whichever of Ollama, LM Studio and HyperNix is on this machine.
    "provider": "auto",
    "model": "",             # "" = the provider's default below
    "endpoint": "",          # for "openai" (any OpenAI-compatible server), "ollama", "lmstudio" and "hypernix"
    "t1Server": "",          # a HyperNix T1 server, e.g. http://127.0.0.1:8000 (its key: `key t1 T1_...`)
    "keyId": "",             # which stored key "openai" uses (e.g. "mistral", "openrouter")
    "wakeWord": False,       # listen continuously for the wake phrase (local, offline)
    "wakePhrase": "hey halcyon",
    "speechModel": "base",   # Whisper size: tiny, base, small
    "language": "",          # "" = detect
    "speak": True,           # read replies aloud
    # Which voice reads them. auto: your own command if one is set, else Kokoro if set up, else Piper, else an AI
    # voice if a Gemini or OpenAI key is stored, else espeak-ng, else speech-dispatcher. piper, kokoro, command, ai,
    # espeak, system (speech-dispatcher): that one first.
    "voice": "auto",
    "aiVoiceProvider": "auto",  # auto (Gemini if its key is stored, else OpenAI), gemini, openai
    "aiVoice": "",              # "" = Kore on Gemini, alloy on OpenAI
    "aiVoiceModel": "",         # "" = gemini-2.5-flash-preview-tts, or gpt-4o-mini-tts
    "aiVoiceEndpoint": "",      # an OpenAI-compatible voice server, e.g. http://127.0.0.1:8880/v1 (Kokoro)
    "sidebarSpeak": True,       # read the AI sidebar's replies aloud too
    "piperVoice": "",           # a Piper voice's key (en_GB-alba-medium) or path; "" = the built-in one
    "piperSpeaker": "",         # for a voice with several speakers: a name or number; "" = its first
    "kokoroVoice": "",          # a Kokoro voice (af_heart, bf_emma, am_adam...); "" = af_heart
    "ttsCommand": "",           # a voice program of your own: text on stdin, plays it or writes a WAV to stdout
    # Big local voice models, each on a server of its own (voice_servers.py): Fish Audio S2 Pro and drama3-small.
    "fishEndpoint": "",         # "" = the one setup runs, http://127.0.0.1:8090
    "fishReference": "",        # a voice saved on the Fish Speech server (reference id); "" = its own
    "drama3Endpoint": "",       # "" = the one setup runs, http://127.0.0.1:8091
    "drama3Reference": "",      # a 10-30 s recording of the voice drama3-small clones (WAV)
    "drama3ReferenceText": "",  # what that recording says
    "allowActions": True,    # let it control the desktop (volume, apps, themes...)
    # Where Claude Code keeps its login, as the terminal saw it at sign-in.
    # Hyprland starts this daemon without that terminal's environment, so the
    # daemon needs it written down. "" = the default, ~/.claude.
    "claudeConfigDir": "",
}
DEFAULT_MODELS = {
    "claude": "claude-opus-5",
    "claude-code": "",       # "" = whatever your plan's Claude Code uses
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.2",
    "openai": "gpt-4o-mini",
    "lmstudio": "",          # "" = what LM Studio has loaded, else the first model it has
    "hypernix": "",          # "" = the newest model in ~/.hypernix/models
    "t1": "",                # "" = what the T1 server's runner has loaded
}
DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai": "https://api.openai.com/v1",
    "lmstudio": "http://127.0.0.1:1234",
    "hypernix": "http://127.0.0.1:8080",
}
KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "t1": "T1_API_KEY",
}


def read_shell_config():
    try:
        return json.loads(SHELL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def settings(config=None):
    """Assistant settings, validated, with defaults for anything missing."""
    stored = ((config if config is not None else read_shell_config()).get("halcyon") or {}).get("assistant") or {}
    result = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = stored.get(key) if isinstance(stored, dict) else None
        if isinstance(value, type(default)):
            result[key] = value
    if result["provider"] not in PROVIDERS:
        result["provider"] = "auto"
    if result["voice"] not in VOICES:
        result["voice"] = "auto"
    if result["aiVoiceProvider"] not in ("auto", "gemini", "openai"):
        result["aiVoiceProvider"] = "auto"
    if result["speechModel"] not in ("tiny", "base", "small", "tiny.en", "base.en", "small.en"):
        result["speechModel"] = "base"
    return result


def write_setting(key, value):
    if key not in DEFAULTS:
        raise KeyError(key)
    data = read_shell_config()
    data.setdefault("halcyon", {}).setdefault("assistant", {})[key] = value
    SHELL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = SHELL_CONFIG.with_name(SHELL_CONFIG.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, SHELL_CONFIG)


# ---------------------------------------------------------------------------
# API keys. illogical-impulse's AI sidebar keeps its keys as JSON in the
# keyring ({"apiKeys": {"gemini": "...", ...}}); the assistant reads the same
# entry, so a key entered in the sidebar works here too.
# ---------------------------------------------------------------------------

KEYRING_ATTRS = ["application", "illogical-impulse"]


def _keyring_data():
    if not shutil.which("secret-tool"):
        return None
    try:
        out = subprocess.run(["secret-tool", "lookup", *KEYRING_ATTRS],
                             capture_output=True, text=True, timeout=10).stdout
        return json.loads(out) if out.strip() else {}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def api_key(key_id):
    """A key from the environment or the keyring, or None."""
    env = KEY_ENV.get(key_id)
    if env and os.environ.get(env):
        return os.environ[env]
    data = _keyring_data() or {}
    value = (data.get("apiKeys") or {}).get(key_id)
    return value or None


def store_api_key(key_id, value):
    """Store a key in the same keyring entry the AI sidebar uses."""
    if not shutil.which("secret-tool"):
        raise RuntimeError("secret-tool (libsecret) is not installed")
    data = _keyring_data()
    if data is None:
        data = {}
    data.setdefault("apiKeys", {})[key_id] = value.strip()
    subprocess.run(["secret-tool", "store", "--label=Halcyon Safe Storage", *KEYRING_ATTRS],
                   input=json.dumps(data), text=True, check=True, timeout=30)
