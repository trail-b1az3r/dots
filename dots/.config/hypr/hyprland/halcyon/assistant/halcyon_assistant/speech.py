"""Reading replies aloud: Piper if a voice is set up, else espeak-ng.

When speaking fails, the reason goes to the assistant's log. The desktop
gives no other place to see it, and a reply that is silently dropped is
hard to diagnose.
"""

import logging
import shutil
import subprocess
import tempfile

from . import config

log = logging.getLogger("halcyon.speech")

PIPER_PLAYER = ["pw-play", "--rate", "22050", "--format", "s16", "--channels", "1", "-"]
ALSA_PLAYER = ["aplay", "-q", "-r", "22050", "-f", "S16_LE", "-c", "1", "-t", "raw"]


def piper_voice():
    voices = sorted((config.MODELS / "piper").glob("*.onnx"))
    return voices[0] if voices else None


def piper_binary():
    """The piper program. Hyprland's PATH may not include the place setup put it, so look there too."""
    found = shutil.which("piper")
    if found:
        return found
    for candidate in (config.VENV / "bin/piper", config.HOME / ".local/bin/piper"):
        if candidate.exists():
            return str(candidate)
    return None


def engine():
    if piper_binary() and piper_voice():
        return "piper"
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    return None


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
    player = PIPER_PLAYER if shutil.which("pw-play") else ALSA_PLAYER
    errors = tempfile.TemporaryFile()
    try:
        synth = subprocess.Popen([piper_binary(), "--model", str(piper_voice()), "--output-raw"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
        play = subprocess.Popen(player, stdin=synth.stdout, stderr=subprocess.DEVNULL)
    except OSError as error:
        log.error("could not start piper or the audio player: %s", error)
        errors.close()
        return False
    synth.stdout.close()  # piper gets a broken pipe if the player stops early
    try:
        synth.stdin.write(text.encode())
    except BrokenPipeError:
        pass
    finally:
        synth.stdin.close()
    stopped = _wait([synth, play], should_stop)
    errors.seek(0)
    problem = errors.read().decode(errors="replace").strip()
    errors.close()
    if not stopped and (synth.returncode or play.returncode):
        log.error("piper exited %s and the player %s: %s", synth.returncode, play.returncode, problem[-300:])
        return False
    return True


def _speak_with_espeak(text, should_stop):
    try:
        espeak = subprocess.Popen(["espeak-ng", "-s", "165", text], stderr=subprocess.DEVNULL)
    except OSError as error:
        log.error("could not start espeak-ng: %s", error)
        return False
    stopped = _wait([espeak], should_stop)
    if not stopped and espeak.returncode:
        log.error("espeak-ng exited %s", espeak.returncode)
        return False
    return True


def say(text, should_stop=lambda: False):
    """Speak text. Returns False if there is no engine or speaking failed. Stops if asked."""
    if not text.strip():
        return True  # nothing to say is not a failure
    which = engine()
    if which is None:
        log.error("no voice engine: run `halcyon assistant setup --piper`")
        return False
    if which == "piper":
        return _speak_with_piper(text, should_stop)
    return _speak_with_espeak(text, should_stop)
