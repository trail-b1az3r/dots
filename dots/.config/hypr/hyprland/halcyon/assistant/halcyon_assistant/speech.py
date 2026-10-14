"""Reading replies aloud: Piper if a voice is set up, else espeak-ng, else speech-dispatcher.

Each engine that is installed is tried in turn, so one that fails (a missing voice file, an audio player that does
not take the stream) falls back to the next instead of leaving the reply silent. Why each one failed goes to the
assistant's log, and `halcyon assistant test-voice` runs the same thing and prints it.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile

from . import config, pcm

log = logging.getLogger("halcyon.speech")

DEFAULT_RATE = 22050


def piper_voice():
    voices = sorted((config.MODELS / "piper").glob("*.onnx"))
    return voices[0] if voices else None


def piper_rate(voice) -> int:
    """The voice's sample rate, from the .onnx.json beside it. Low-quality voices are 16 kHz, most 22.05 kHz."""
    try:
        data = json.loads(voice.with_name(voice.name + ".json").read_text(encoding="utf-8"))
        return int(data["audio"]["sample_rate"])
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_RATE


def piper_binary():
    """The piper program. Hyprland's PATH may not include the place setup put it, so look there too."""
    found = shutil.which("piper")
    if found:
        return found
    for candidate in (config.VENV / "bin/piper", config.HOME / ".local/bin/piper"):
        if candidate.exists():
            return str(candidate)
    return None


def engines():
    """The engines that are installed, best first."""
    found = []
    if piper_binary() and piper_voice():
        found.append("piper")
    if shutil.which("espeak-ng"):
        found.append("espeak-ng")
    elif shutil.which("espeak"):
        found.append("espeak")
    if shutil.which("spd-say"):
        found.append("spd-say")
    return found


def engine():
    """The engine that will be tried first, or None."""
    available = engines()
    return available[0] if available else None


def _wait(processes, should_stop):
    """Wait for the processes. Returns True if they were stopped early."""
    stopped = False
    while any(p.poll() is None for p in processes):
        if should_stop():
            stopped = True
            for p in processes:
                p.terminate()
            break
        try:
            processes[-1].wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
    for p in processes:
        p.wait()
    return stopped


def _speak_with_piper(text, should_stop):
    voice = piper_voice()
    player = pcm.player(piper_rate(voice))
    if player is None:
        return "no audio player (install pipewire, pulseaudio-utils or alsa-utils)"
    synth_errors = tempfile.TemporaryFile()
    play_errors = tempfile.TemporaryFile()
    try:
        synth = subprocess.Popen([piper_binary(), "--model", str(voice), "--output-raw"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=synth_errors)
        play = subprocess.Popen(player, stdin=synth.stdout, stderr=play_errors)
    except OSError as error:
        return f"could not start piper or {player[0]}: {error}"
    synth.stdout.close()  # piper gets a broken pipe if the player stops early
    try:
        synth.stdin.write(text.encode())
    except BrokenPipeError:
        pass
    finally:
        synth.stdin.close()
    stopped = _wait([synth, play], should_stop)
    problems = []
    for name, handle, proc in (("piper", synth_errors, synth), (player[0], play_errors, play)):
        handle.seek(0)
        output = handle.read().decode(errors="replace").strip()
        handle.close()
        if proc.returncode and not stopped:
            problems.append(f"{name} exited {proc.returncode}: {output[-300:] or 'no message'}")
    return "; ".join(problems) or None


def _speak_with(command, should_stop):
    try:
        proc = subprocess.Popen(command, stderr=subprocess.PIPE)
    except OSError as error:
        return f"could not start {command[0]}: {error}"
    stopped = _wait([proc], should_stop)
    if proc.returncode and not stopped:
        return f"{command[0]} exited {proc.returncode}: {proc.stderr.read().decode(errors='replace').strip()[-300:]}"
    return None


def speak_once(name, text, should_stop=lambda: False):
    """Speak with one engine. Returns None when it worked, else why not."""
    if name == "piper":
        return _speak_with_piper(text, should_stop)
    if name in ("espeak-ng", "espeak"):
        return _speak_with([name, "-s", "165", text], should_stop)
    if name == "spd-say":
        return _speak_with(["spd-say", "--wait", text], should_stop)
    return f"unknown engine {name}"


def say(text, should_stop=lambda: False):
    """Speak text with the best engine that works. Returns False if none did. Stops if asked."""
    if not text.strip():
        return True  # nothing to say is not a failure
    available = engines()
    if not available:
        log.error("no voice engine: install espeak-ng, or run `halcyon assistant setup --piper`")
        return False
    for name in available:
        problem = speak_once(name, text, should_stop)
        if problem is None:
            return True
        log.error("speaking with %s failed: %s", name, problem)
        if should_stop():
            return True
    return False
