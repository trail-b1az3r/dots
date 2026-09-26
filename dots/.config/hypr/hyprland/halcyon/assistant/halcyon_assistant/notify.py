"""Showing what the assistant is doing, through the shell's notifications.

One notification is updated in place (listening -> heard -> reply), so a
conversation doesn't pile up popups.
"""

import shutil
import subprocess

APP = "Halcyon Assistant"
_last_id = None


def show(summary, body="", icon="audio-input-microphone", urgency="normal", timeout_ms=8000):
    global _last_id
    if not shutil.which("notify-send"):
        return
    command = ["notify-send", "-a", APP, "-i", icon, "-u", urgency, "-t", str(timeout_ms), "-p"]
    if _last_id:
        command += ["-r", str(_last_id)]
    command += [summary, body]
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=5).stdout.strip()
        if out.isdigit():
            _last_id = int(out)
    except (OSError, subprocess.SubprocessError):
        pass


def reset():
    global _last_id
    _last_id = None


def chime(kind="start"):
    """A short soft tone: rising when listening starts, falling when it stops."""
    player = shutil.which("pw-play") or shutil.which("aplay")
    if not player:
        return
    import array
    import math
    rate = 22050
    notes = (660, 880) if kind == "start" else (880, 587)
    samples = array.array("h")
    for freq in notes:
        n = int(rate * 0.07)
        for i in range(n):
            envelope = math.sin(math.pi * i / n)
            samples.append(int(5000 * envelope * math.sin(2 * math.pi * freq * i / rate)))
    command = ["pw-play", "--rate", str(rate), "--format", "s16", "--channels", "1", "-"] if player.endswith("pw-play") \
        else ["aplay", "-q", "-r", str(rate), "-f", "S16_LE", "-c", "1", "-t", "raw"]
    try:
        subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL).communicate(samples.tobytes(), timeout=3)
    except (OSError, subprocess.SubprocessError):
        pass
