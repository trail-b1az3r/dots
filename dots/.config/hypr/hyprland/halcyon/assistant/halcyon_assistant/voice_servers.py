"""Voices from big local models, each run as a server on this computer that the assistant sends the text to:

    fish     Fish Audio S2 Pro (fishaudio/s2-pro, 4.5B, ~11 GB) on Fish Speech's API server. 80+ languages, and inline
             [tags] for tone ([whisper], [laughing], [excited]...). Needs a GPU with ~12 GB to run well.
             `halcyon assistant setup --fish-s2` installs Fish Speech and the weights. The weights are gated: accept
             the terms at https://huggingface.co/fishaudio/s2-pro and sign in (`hf auth login`) first. Licence: Fish
             Audio Research License, non-commercial use only.
    drama3   drama3-small (pentacoxian-dev/drama3-small-GGUF, ~10 GB), a compressed Fish Audio Drama 3 on a patched
             audio.cpp. Japanese and English, cloned from a 10-30 s recording of the voice you want (its path and
             transcript are settings). Needs an NVIDIA GPU with ~12 GB and the CUDA toolkit to build.
             `halcyon assistant setup --drama3` builds it and downloads the model. Licence: Fish Audio Community
             License v1.0.

Each runs as a systemd user service (halcyon-fish-speech, halcyon-drama3) that is started the first time the voice
is needed, not at login, since each holds ~10 GB of GPU memory while it runs; `halcyon assistant voice-server NAME
stop` frees it. Loading takes a minute or two, so the first reply after a start waits that long.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config, piper_voices


class ServerError(Exception):
    pass


SERVERS = {
    "fish": {"name": "Fish Audio S2 Pro", "unit": "halcyon-fish-speech.service", "port": 8090, "health": "/v1/health",
             "setting": "fishEndpoint"},
    "drama3": {"name": "drama3-small", "unit": "halcyon-drama3.service", "port": 8091, "health": "/health",
               "setting": "drama3Endpoint"},
}
START_WAIT = float(os.environ.get("HALCYON_VOICE_SERVER_WAIT", 240))   # seconds a model may take to load

FISH_REPO = "https://github.com/fishaudio/fish-speech"
FISH_WEIGHTS = "fishaudio/s2-pro"
AUDIOCPP_REPO = "https://github.com/JarodMica/audio.cpp"
AUDIOCPP_COMMIT = "9277495a"
DRAMA3_REPO = "pentacoxian-dev/drama3-small-GGUF"
DRAMA3_FILES = ("drama3-small-IQ3_XXS.gguf", "silence_codes.json", "drama3-small-audiocpp.patch")


def fish_dir() -> Path:
    return config.MODELS / "fish-speech"


def audiocpp_dir() -> Path:
    return config.MODELS / "audio.cpp"


def drama3_dir() -> Path:
    return config.MODELS / "drama3-small"


def unit_path(name: str) -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or config.HOME / ".config") / "systemd/user" / SERVERS[name]["unit"]


def installed(name: str) -> bool:
    """Set up with `halcyon assistant setup` (its service is written), so the voice can start it."""
    return unit_path(name).is_file()


def endpoint(name: str, settings) -> str:
    return (settings.get(SERVERS[name]["setting"]) or f"http://127.0.0.1:{SERVERS[name]['port']}").rstrip("/")


def _request(url: str, payload=None, timeout: float = 5):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                              "User-Agent": "halcyon-assistant"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def healthy(name: str, settings) -> bool:
    try:
        _request(endpoint(name, settings) + SERVERS[name]["health"], timeout=2)
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, check=False)


def ensure_running(name: str, settings, should_stop=lambda: False) -> None:
    """Start the voice's server if it isn't answering, and wait for its model to load."""
    if healthy(name, settings):
        return
    info = SERVERS[name]
    if not installed(name):
        raise ServerError(f"{info['name']} isn't answering at {endpoint(name, settings)}, and isn't set up here "
                          f"(halcyon assistant setup --{'fish-s2' if name == 'fish' else name})")
    systemctl("start", info["unit"])
    deadline = time.monotonic() + START_WAIT
    while time.monotonic() < deadline:
        if should_stop():
            raise ServerError("stopped")
        if healthy(name, settings):
            return
        if systemctl("is-failed", "--quiet", info["unit"]).returncode == 0:
            raise ServerError(f"{info['unit']} stopped while loading: journalctl --user -u {info['unit']}")
        time.sleep(1)
    raise ServerError(f"{info['name']} did not load within {int(START_WAIT)} s: journalctl --user -u {info['unit']}")


def _wav(data: bytes, who: str) -> bytes:
    if data[:4] != b"RIFF":
        raise ServerError(f"{who} did not send a WAV: {data[:200].decode(errors='replace')}")
    return data


def synthesize(name: str, text: str, settings, should_stop=lambda: False) -> bytes:
    """The WAV for text, from the voice's server (started if need be)."""
    ensure_running(name, settings, should_stop)
    url = endpoint(name, settings)
    try:
        if name == "fish":
            payload = {"text": text, "format": "wav", "normalize": True, "streaming": False}
            if settings.get("fishReference"):
                payload["reference_id"] = settings["fishReference"]
            return _wav(_request(url + "/v1/tts", payload, timeout=600), "Fish Speech")
        reference = os.path.expanduser(settings.get("drama3Reference") or "")
        if not reference or not Path(reference).is_file():
            raise ServerError("drama3-small clones a voice: set a 10-30 s recording of it (and what it says) in "
                              "Settings > Halcyon > Assistant > Voice")
        payload = {"model": "drama3-small", "input": text,
                   "voice_ref": {"type": "path", "path": reference},
                   "reference_text": settings.get("drama3ReferenceText") or "",
                   "options": {"max_pause_frames": "10", "silence_codes": str(drama3_dir() / "silence_codes.json")}}
        return _wav(_request(url + "/v1/audio/speech", payload, timeout=600), "audio.cpp")
    except urllib.error.HTTPError as error:
        raise ServerError(f"{SERVERS[name]['name']}: HTTP {error.code}: "
                          f"{error.read().decode(errors='replace')[:300]}") from None
    except (urllib.error.URLError, OSError) as error:
        raise ServerError(f"{SERVERS[name]['name']}: {getattr(error, 'reason', error)}") from None


# --- setup --------------------------------------------------------------------------------------------------------

def _run(argv, cwd=None, progress=print) -> None:
    progress("+ " + " ".join(str(a) for a in argv))
    done = subprocess.run([str(a) for a in argv], cwd=cwd, check=False)
    if done.returncode != 0:
        raise ServerError(f"{Path(str(argv[0])).name} failed (exit {done.returncode})")


def _clone(repo: str, target: Path, progress, commit: str | None = None) -> None:
    if (target / ".git").is_dir():
        _run(["git", "-C", target, "fetch", "--quiet", "origin"], progress=progress)
        if not commit:
            _run(["git", "-C", target, "pull", "--ff-only", "--quiet"], progress=progress)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--quiet", repo, target], progress=progress)
    if commit:
        _run(["git", "-C", target, "checkout", "--quiet", commit], progress=progress)


def write_unit(name: str, exec_start: str, workdir: Path, environment: dict | None = None) -> Path:
    lines = ["[Unit]", f"Description=Halcyon assistant voice: {SERVERS[name]['name']}", "",
             "[Service]", f"WorkingDirectory={workdir}", f"ExecStart={exec_start}"]
    lines += [f"Environment={key}={value}" for key, value in (environment or {}).items()]
    lines += ["Restart=no", ""]
    path = unit_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    systemctl("daemon-reload")
    return path


def gpu() -> str:
    """The NVIDIA GPU's name and memory, or "" without one."""
    if not shutil.which("nvidia-smi"):
        return ""
    out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True, check=False).stdout.strip()
    return out.splitlines()[0] if out else ""


def setup_fish(progress=print, cpu: bool = False) -> None:
    card = gpu()
    progress(f"GPU: {card or 'none found'}" + ("" if card or cpu else " (S2 Pro is very slow without one; --cpu to go on anyway)"))
    if not card and not cpu:
        raise ServerError("no NVIDIA GPU found")
    progress("Fish Audio S2 Pro is under the Fish Audio Research License: non-commercial use only.")
    base = fish_dir()
    _clone(FISH_REPO, base, progress)
    python = base / ".venv/bin/python"
    if not python.exists():
        _run(["python3", "-m", "venv", base / ".venv"], progress=progress)
    extra, index = ("cpu", "https://download.pytorch.org/whl/cpu") if cpu else ("cu129", "https://download.pytorch.org/whl/cu129")
    _run([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip", "huggingface_hub[cli]"], progress=progress)
    _run([python, "-m", "pip", "install", "--quiet", "--extra-index-url", index, "-e", f".[{extra}]"], cwd=base,
         progress=progress)
    weights = base / "checkpoints/s2-pro"
    progress(f"downloading {FISH_WEIGHTS} (~11 GB) into {weights}")
    try:
        _run([base / ".venv/bin/hf", "download", FISH_WEIGHTS, "--local-dir", weights], progress=progress)
    except ServerError:
        raise ServerError(f"the weights are gated: accept the terms at https://huggingface.co/{FISH_WEIGHTS}, sign in "
                          f"with `{base / '.venv/bin/hf'} auth login`, then run this again") from None
    port = SERVERS["fish"]["port"]
    write_unit("fish", f"{python} tools/api_server.py --listen 127.0.0.1:{port} --llama-checkpoint-path "
                       f"checkpoints/s2-pro --decoder-checkpoint-path checkpoints/s2-pro/codec.pth"
                       + (" --device cpu" if cpu else ""), base)
    config.write_setting("voice", "fish")
    progress("set up. The voice is now Fish Audio S2 Pro; its server starts the first time it speaks.")


def setup_drama3(progress=print) -> None:
    card = gpu()
    progress(f"GPU: {card or 'none found'}")
    if not card:
        raise ServerError("drama3-small runs on NVIDIA GPUs only (CUDA), and none was found")
    if not shutil.which("nvcc") and not Path("/opt/cuda/bin/nvcc").exists():
        raise ServerError("the CUDA toolkit is needed to build audio.cpp: sudo pacman -S cuda")
    progress("drama3-small is under the Fish Audio Community License v1.0.")
    models = drama3_dir()
    models.mkdir(parents=True, exist_ok=True)
    tree = {entry["path"]: entry for entry in json.loads(piper_voices._fetch(
        piper_voices.HF_API + DRAMA3_REPO + "/tree/main"))}
    for name in DRAMA3_FILES:
        target = models / name
        entry = tree.get(name, {})
        if target.is_file() and target.stat().st_size == entry.get("size", -1):
            continue
        progress(f"downloading {name} ({entry.get('size', 0) // 1_000_000} MB)")
        piper_voices._download_file(f"https://huggingface.co/{DRAMA3_REPO}/resolve/main/{name}", target, "sha256",
                                    (entry.get("lfs") or {}).get("oid", ""), lambda done, total: None, entry.get("size", 0))
    source = audiocpp_dir()
    _clone(AUDIOCPP_REPO, source, progress, commit=AUDIOCPP_COMMIT)
    patch = models / "drama3-small-audiocpp.patch"
    if subprocess.run(["git", "-C", source, "apply", "--check", patch], capture_output=True).returncode == 0:
        _run(["git", "-C", source, "apply", patch], progress=progress)
    else:
        progress("the drama3-small patch is already applied")
    _run(["bash", "scripts/build_linux.sh", "--cuda", "on", "--models", "fish_drama3"], cwd=source, progress=progress)
    server = next(iter(sorted(source.glob("build/*/bin/audiocpp_server"))), None)
    if server is None:
        raise ServerError(f"audiocpp_server was not built: look for errors above, in {source}")
    settings_file = models / "server.json"
    settings_file.write_text(json.dumps({
        "host": "127.0.0.1", "port": SERVERS["drama3"]["port"], "backend": "cuda", "lazy_load": False,
        "models": [{"id": "drama3-small", "family": "fish_drama3", "task": "clon", "mode": "offline",
                    "path": str(models / "drama3-small-IQ3_XXS.gguf"),
                    "session_options": {"fish_drama3.cpu_expert_layers": "0", "fish_drama3.context_length": "4096"}}],
    }, indent=2) + "\n", encoding="utf-8")
    write_unit("drama3", f"{server} --config {settings_file}", models,
               {"AUDIOCPP_DRAMA3_MAX_PAUSE_FRAMES": "10", "AUDIOCPP_DRAMA3_SILENCE_CODES": str(models / "silence_codes.json")})
    config.write_setting("voice", "drama3")
    progress("set up. Now set the voice to clone in Settings > Halcyon > Assistant > Voice: a 10-30 s recording "
             "and what it says. Its server starts the first time it speaks.")
