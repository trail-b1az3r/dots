"""Reading replies aloud: Piper if a voice is set up, else espeak-ng."""

import shutil
import subprocess

from . import config


def piper_voice():
    voices = sorted((config.MODELS / "piper").glob("*.onnx"))
    return voices[0] if voices else None


def engine():
    if shutil.which("piper") and piper_voice():
        return "piper"
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    return None


def say(text, should_stop=lambda: False):
    """Speak text; returns False if there is no engine. Stops if asked."""
    which = engine()
    if which is None or not text.strip():
        return False
    if which == "piper":
        player = shutil.which("pw-play") and ["pw-play", "--rate", "22050", "--format", "s16", "--channels", "1", "-"] \
            or ["aplay", "-q", "-r", "22050", "-f", "S16_LE", "-c", "1", "-t", "raw"]
        synth = subprocess.Popen(["piper", "--model", str(piper_voice()), "--output-raw"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        play = subprocess.Popen(player, stdin=synth.stdout, stderr=subprocess.DEVNULL)
        synth.stdin.write(text.encode())
        synth.stdin.close()
        processes = [synth, play]
    else:
        processes = [subprocess.Popen(["espeak-ng", "-s", "165", text], stderr=subprocess.DEVNULL)]
    while any(p.poll() is None for p in processes):
        if should_stop():
            for p in processes:
                p.terminate()
            break
        try:
            processes[-1].wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
    return True
