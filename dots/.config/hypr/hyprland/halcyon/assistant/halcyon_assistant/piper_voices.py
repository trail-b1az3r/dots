"""Piper voices: the ones on this computer, and the ones that can be added.

Three places voices come from, all listed together:

    built-in      the voice `halcyon assistant setup --piper` downloads (en_US-lessac-medium)
    Hugging Face  any voice in rhasspy/piper-voices, downloaded on request into the assistant's models folder and
                  checked against the catalogue's MD5
    AUR           the piper-voices-* packages (piper-voices-en-us, -de-de, ...), which install every voice of a
                  language into /usr/share/piper-voices; installed with your AUR helper

Any other Hugging Face repo that holds a Piper voice (a .onnx and its .onnx.json or config.json) can be downloaded too,
by name: `halcyon assistant voice get hf:systemofapwne/piper-en_US-glados-high`. The ones in FEATURED are listed with
the rest, so they can be picked from Settings.

A voice of your own (a .onnx with its .onnx.json) works too: put it in one of SEARCH_DIRS, or choose it by path.
The chosen voice is the `piperVoice` setting: a voice's key ("en_GB-alba-medium"), a path, or "" for the built-in
one (else the first voice found).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config

BUILTIN = "en_US-lessac-medium"
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
CATALOG_URL = HF_BASE + "voices.json"
AUR_SEARCH_URL = "https://aur.archlinux.org/rpc/v5/search/piper-voices?by=name"
CACHE_SECONDS = 7 * 24 * 3600
AUR_CACHE_SECONDS = 24 * 3600
HF_API = "https://huggingface.co/api/models/"

# Piper voices from other Hugging Face repos, listed beside rhasspy's. Key: the name it is saved under.
FEATURED = [
    {"key": "en_US-glados-high", "repo": "systemofapwne/piper-en_US-glados-high", "language": "en_US",
     "languageName": "English", "country": "United States", "quality": "high", "speakers": 1, "size": 113800584,
     "name": "GLaDOS (Portal)"},
]


def voices_dir() -> Path:
    return config.MODELS / "piper"


def search_dirs() -> list[Path]:
    """Where voices are looked for, the assistant's own folder first."""
    data = Path(os.environ.get("XDG_DATA_HOME") or config.HOME / ".local/share")
    return [voices_dir(), data / "piper-voices", data / "piper/voices", Path("/usr/share/piper-voices"),
            Path("/usr/local/share/piper-voices"), Path("/usr/share/piper/voices"), Path("/opt/piper-voices")]


class VoiceError(Exception):
    pass


# --- what is on this computer ---------------------------------------------------------------------------------

def describe(onnx: Path) -> dict | None:
    """A voice from its .onnx and the .onnx.json beside it; None without the JSON (Piper needs it)."""
    meta_path = onnx.with_name(onnx.name + ".json")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    language = meta.get("language") or {}
    speakers = meta.get("speaker_id_map") or {}
    return {
        "key": onnx.stem,
        "path": str(onnx),
        "language": language.get("code") or meta.get("espeak", {}).get("voice", ""),
        "languageName": language.get("name_english", ""),
        "quality": (meta.get("audio") or {}).get("quality", ""),
        "rate": int((meta.get("audio") or {}).get("sample_rate", 22050) or 22050),
        "speakers": sorted(speakers, key=lambda name: speakers[name]) if isinstance(speakers, dict) else [],
        "source": source_of(onnx),
    }


def source_of(onnx: Path) -> str:
    own = voices_dir()
    if onnx.parent == own:
        return "built-in" if onnx.stem == BUILTIN else "hugging face"
    if str(onnx).startswith(("/usr/share/piper-voices/", "/usr/local/share/piper-voices/")):
        return "aur"
    return "custom"


def installed() -> list[dict]:
    """Every voice on this computer, each key once (the first found wins), the assistant's own folder first."""
    seen, found = set(), []
    for directory in search_dirs():
        if not directory.is_dir():
            continue
        for onnx in sorted(directory.rglob("*.onnx")):
            if onnx.stem in seen:
                continue
            voice = describe(onnx)
            if voice:
                seen.add(onnx.stem)
                found.append(voice)
    return found


def resolve(choice: str = "") -> dict | None:
    """The voice to speak with: the chosen key or path, else the built-in one, else the first found."""
    choice = (choice or "").strip()
    if choice and ("/" in choice or choice.endswith(".onnx")):
        path = Path(os.path.expanduser(choice))
        return describe(path) if path.is_file() else None
    voices = installed()
    if choice:
        return next((v for v in voices if v["key"] == choice), None)
    return next((v for v in voices if v["key"] == BUILTIN), voices[0] if voices else None)


def speaker_id(voice: dict, speaker: str) -> int | None:
    """A multi-speaker voice's speaker, by name or number; None for the voice's default."""
    speaker = (speaker or "").strip()
    if not speaker or not voice.get("speakers"):
        return None
    if speaker.isdigit():
        return int(speaker) if int(speaker) < len(voice["speakers"]) else None
    names = voice["speakers"]
    return names.index(speaker) if speaker in names else None


# --- Hugging Face ------------------------------------------------------------------------------------------------

def _fetch(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "halcyon-dots"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (urllib.error.URLError, OSError) as error:
        raise VoiceError(f"can't reach {url.split('/')[2]}: {getattr(error, 'reason', error)}") from None


def _cached(name: str, url: str, max_age: int, refresh: bool) -> bytes:
    cache = config.ASSISTANT_STATE / name
    fresh = cache.is_file() and time.time() - cache.stat().st_mtime < max_age
    if fresh and not refresh:
        return cache.read_bytes()
    try:
        data = _fetch(url)
    except VoiceError:
        if cache.is_file():
            return cache.read_bytes()   # offline: the last list is better than none
        raise
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(data)
    return data


def catalog(refresh: bool = False) -> list[dict]:
    """Every voice in rhasspy/piper-voices, from its voices.json (kept for a week)."""
    try:
        data = json.loads(_cached("piper-voices.json", CATALOG_URL, CACHE_SECONDS, refresh))
    except ValueError:
        raise VoiceError("the Hugging Face voice list is not JSON") from None
    voices = []
    for key, entry in sorted(data.items()):
        files = entry.get("files") or {}
        onnx = next((f for f in files if f.endswith(".onnx")), None)
        if not onnx:
            continue
        language = entry.get("language") or {}
        voices.append({
            "key": key,
            "language": language.get("code", ""),
            "languageName": language.get("name_english", ""),
            "country": language.get("country_english", ""),
            "quality": entry.get("quality", ""),
            "speakers": entry.get("num_speakers", 1),
            "size": files[onnx].get("size_bytes", 0),
            "files": {name: info.get("md5_digest", "") for name, info in files.items()
                      if name.endswith((".onnx", ".onnx.json"))},
        })
    have = {v["key"] for v in voices}
    voices += [dict(entry, files={}) for entry in FEATURED if entry["key"] not in have]
    return voices


def repo_of(choice: str) -> str | None:
    """"hf:OWNER/REPO", or a huggingface.co link to a repo, as OWNER/REPO; None for anything else."""
    choice = choice.strip()
    if choice.startswith("hf:"):
        repo = choice[3:]
    elif "huggingface.co/" in choice:
        repo = choice.split("huggingface.co/", 1)[1]
    else:
        return None
    parts = [p for p in repo.split("/") if p]
    return "/".join(parts[:2]) if len(parts) >= 2 else None


def repo_key(repo: str) -> str:
    """The name a repo's voice is saved under: the repo's name without a leading "piper-"."""
    name = repo.split("/")[-1]
    return name[len("piper-"):] if name.lower().startswith("piper-") else name


def download_repo(repo: str, progress=lambda done, total: None, key: str | None = None) -> Path:
    """Download the Piper voice in any Hugging Face repo: its .onnx, and the .onnx.json or config.json that describes
    it (saved as KEY.onnx.json, where Piper looks). Large files are checked against the SHA-256 Hugging Face keeps."""
    try:
        tree = json.loads(_fetch(HF_API + repo + "/tree/main?recursive=1"))
    except ValueError:
        raise VoiceError(f"Hugging Face's answer about {repo} is not JSON") from None
    if not isinstance(tree, list):
        raise VoiceError(f"no repo called {repo} on Hugging Face")
    files = {entry.get("path", ""): entry for entry in tree if entry.get("type") == "file"}
    onnx = sorted(path for path in files if path.endswith(".onnx"))
    if not onnx:
        raise VoiceError(f"{repo} has no .onnx file: it is not a Piper voice")
    model = onnx[0]
    meta = next((path for path in (model + ".json", str(Path(model).with_name("config.json")), "config.json")
                 if path in files), None)
    if meta is None:
        raise VoiceError(f"{repo} has {model} but no .onnx.json or config.json beside it; Piper needs one")
    key = key or repo_key(repo)
    target_dir = voices_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    targets = [(meta, target_dir / f"{key}.onnx.json"), (model, target_dir / f"{key}.onnx")]
    for remote, target in targets:
        sha = ((files[remote].get("lfs") or {}).get("oid") or "")
        _download_file(f"https://huggingface.co/{repo}/resolve/main/{remote}", target, "sha256", sha,
                       progress if remote == model else (lambda done, total: None),
                       files[remote].get("size", 0))
    return target_dir / f"{key}.onnx"


def _download_file(url: str, target: Path, algorithm: str, expected: str, progress, total: int) -> None:
    part = target.with_name(target.name + ".part")
    digest = hashlib.new(algorithm)
    request = urllib.request.Request(url, headers={"User-Agent": "halcyon-dots"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, open(part, "wb") as out:
            done = 0
            while chunk := response.read(1 << 20):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                progress(done, total)
    except (urllib.error.URLError, OSError) as error:
        part.unlink(missing_ok=True)
        raise VoiceError(f"downloading {target.name} failed: {getattr(error, 'reason', error)}") from None
    if expected and digest.hexdigest() != expected:
        part.unlink(missing_ok=True)
        raise VoiceError(f"{target.name} did not match its checksum; nothing was kept")
    part.replace(target)


def download(key: str, progress=lambda done, total: None, refresh: bool = False) -> Path:
    """Download a voice from Hugging Face into the assistant's folder, check it, and return its .onnx."""
    repo = repo_of(key)
    if repo:
        return download_repo(repo, progress)
    entry = next((v for v in catalog(refresh) if v["key"] == key), None)
    if entry is None:
        raise VoiceError(f"no voice called {key} on Hugging Face (halcyon assistant voices --all lists them)")
    if entry.get("repo"):
        return download_repo(entry["repo"], progress, key=entry["key"])
    target_dir = voices_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    total = entry["size"]
    for remote, md5 in sorted(entry["files"].items(), key=lambda item: item[0].endswith(".json")):
        target = target_dir / Path(remote).name
        part = target.with_name(target.name + ".part")
        digest = hashlib.md5()
        request = urllib.request.Request(HF_BASE + remote, headers={"User-Agent": "halcyon-dots"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, open(part, "wb") as out:
                done = 0
                while chunk := response.read(1 << 20):
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if remote.endswith(".onnx"):
                        progress(done, total)
        except (urllib.error.URLError, OSError) as error:
            part.unlink(missing_ok=True)
            raise VoiceError(f"downloading {Path(remote).name} failed: {getattr(error, 'reason', error)}") from None
        if md5 and digest.hexdigest() != md5:
            part.unlink(missing_ok=True)
            raise VoiceError(f"{Path(remote).name} did not match its checksum; nothing was kept")
        part.replace(target)
    return target_dir / f"{key}.onnx"


def remove(key: str) -> Path:
    """Delete a voice from the assistant's own folder. Ones from the AUR are removed with pacman instead."""
    onnx = voices_dir() / f"{key}.onnx"
    if not onnx.is_file():
        raise VoiceError(f"{key} is not in {voices_dir()}: voices from the AUR are removed with pacman")
    onnx.unlink()
    onnx.with_name(onnx.name + ".json").unlink(missing_ok=True)
    return onnx


# --- the AUR -----------------------------------------------------------------------------------------------------

def aur_packages(refresh: bool = False) -> list[dict]:
    """The piper-voices-* packages in the AUR (kept for a day), and whether each is installed."""
    try:
        data = json.loads(_cached("piper-voices-aur.json", AUR_SEARCH_URL, AUR_CACHE_SECONDS, refresh))
    except ValueError:
        raise VoiceError("the AUR's answer is not JSON") from None
    have = installed_packages()
    packages = []
    for entry in sorted(data.get("results") or [], key=lambda e: e.get("Name", "")):
        name = entry.get("Name", "")
        if not name.startswith("piper-voices-") or name == "piper-voices-common":
            continue
        packages.append({"name": name, "version": entry.get("Version", ""),
                         "description": entry.get("Description", ""), "installed": name in have})
    return packages


def installed_packages() -> set[str]:
    if not shutil.which("pacman"):
        return set()
    out = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, check=False).stdout
    return {line.strip() for line in out.splitlines() if line.startswith("piper-voices")}


def aur_helper() -> str | None:
    return next((h for h in ("paru", "yay", "pikaur", "trizen") if shutil.which(h)), None)


def aur_install_command(package: str) -> list[str]:
    if not package.startswith("piper-voices-"):
        raise VoiceError(f"{package} is not a Piper voice package (they are called piper-voices-LANG-REGION)")
    helper = aur_helper()
    if helper is None:
        raise VoiceError("no AUR helper (paru or yay) is installed; install one, or download the voice from Hugging Face")
    return [helper, "-S", "--needed", package]
