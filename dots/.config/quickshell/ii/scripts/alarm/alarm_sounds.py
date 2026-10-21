#!/usr/bin/env python3
"""The calendar alarm's sounds, made here from sine waves, so nothing recorded by someone else is shipped.

    alarm_sounds.py ensure DIR       write any of the sounds missing from DIR (the shell runs this at start)
    alarm_sounds.py write DIR        write them all again
    alarm_sounds.py path DIR NAME    where NAME is (ensuring it first)

    smoke    a smoke alarm: a piercing 3.1 kHz tone in the temporal-three pattern smoke alarms use
             (three half-second beeps, a second and a half of silence)
    tornado  an outdoor warning siren: a rotor's buzzy tone winding up from a growl to a wail and back down
    beep     a bedside alarm clock: four quick beeps, then a pause
    chime    three soft bell notes, falling

Each file is one cycle (a few seconds) of 16-bit mono WAV at 44.1 kHz (the smoke alarm's overtones need it); the player loops it. They are written
at full scale, so the volume is your volume: they play through the default output at its current level.
"""

from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path

RATE = 44100
NAMES = ("smoke", "tornado", "beep", "chime")


def clip(x: float) -> float:
    return max(-1.0, min(1.0, x))


def envelope(t: float, length: float, attack: float = 0.004, release: float = 0.01) -> float:
    """A short fade at each end of a beep, so it doesn't click."""
    if t < attack:
        return t / attack
    if t > length - release:
        return max(0.0, (length - t) / release)
    return 1.0


def smoke() -> list[float]:
    # T3: on 0.5 s, off 0.5 s, on, off, on, then 1.5 s off: four seconds a cycle.
    freq = 3150.0
    out = []
    beeps = [(0.0, 0.5), (1.0, 1.5), (2.0, 2.5)]
    for i in range(int(4.0 * RATE)):
        t = i / RATE
        value = 0.0
        for start, end in beeps:
            if start <= t < end:
                local = t - start
                # A piezo horn is nearly a square wave: the fundamental with odd harmonics.
                tone = (math.sin(2 * math.pi * freq * t) + 0.33 * math.sin(2 * math.pi * 3 * freq * t)
                        + 0.2 * math.sin(2 * math.pi * 5 * freq * t))
                value = 0.72 * tone * envelope(local, end - start)
        out.append(clip(value))
    return out


def tornado() -> list[float]:
    # Wind up from ~180 Hz to ~650 Hz over 4.5 s, hold, wind down over 3 s: an eight-second cycle. The rotor's
    # chopping makes the tone buzzy, so it is built from a fundamental and a stack of harmonics, with a slow wobble.
    up, hold, down = 4.5, 0.8, 3.0
    length = up + hold + down
    low, high = 180.0, 650.0
    out = []
    phase = 0.0
    for i in range(int(length * RATE)):
        t = i / RATE
        if t < up:
            k = 1 - (1 - t / up) ** 2              # winds up fast, then slower near the top
        elif t < up + hold:
            k = 1.0
        else:
            k = (1 - (t - up - hold) / down) ** 1.6
        freq = low + (high - low) * k * (1 + 0.006 * math.sin(2 * math.pi * 5.5 * t))
        phase += 2 * math.pi * freq / RATE
        tone = (math.sin(phase) + 0.55 * math.sin(2 * phase) + 0.4 * math.sin(3 * phase)
                + 0.22 * math.sin(4 * phase) + 0.15 * math.sin(5 * phase))
        loud = 0.35 + 0.65 * k                     # quieter while it is still a growl
        edge = min(1.0, t / 0.05, (length - t) / 0.05)
        out.append(clip(0.42 * tone * loud * edge))
    return out


def beep() -> list[float]:
    freq = 2000.0
    out = []
    for i in range(int(2.0 * RATE)):
        t = i / RATE
        value = 0.0
        for n in range(4):
            start = n * 0.16
            if start <= t < start + 0.09:
                value = 0.6 * math.sin(2 * math.pi * freq * t) * envelope(t - start, 0.09)
        out.append(clip(value))
    return out


def chime() -> list[float]:
    notes = [(0.0, 1046.5), (0.45, 880.0), (0.9, 698.5)]    # C6, A5, F5
    out = []
    for i in range(int(3.2 * RATE)):
        t = i / RATE
        value = 0.0
        for start, freq in notes:
            if t >= start:
                local = t - start
                decay = math.exp(-local * 2.4)
                value += 0.3 * decay * (math.sin(2 * math.pi * freq * local)
                                        + 0.3 * math.sin(2 * math.pi * 2.76 * freq * local)) * min(1.0, local / 0.003)
        out.append(clip(value))
    return out


MAKERS = {"smoke": smoke, "tornado": tornado, "beep": beep, "chime": chime}


def write(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with wave.open(str(tmp), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in samples))
    tmp.replace(path)


def ensure(directory: Path, names=NAMES, force: bool = False) -> list[Path]:
    written = []
    for name in names:
        path = directory / f"{name}.wav"
        if force or not path.is_file():
            write(path, MAKERS[name]())
            written.append(path)
    return written


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] in ("ensure", "write"):
        for path in ensure(Path(argv[1]).expanduser(), force=argv[0] == "write"):
            print(path)
        return 0
    if len(argv) == 3 and argv[0] == "path" and argv[2] in MAKERS:
        directory = Path(argv[1]).expanduser()
        ensure(directory, [argv[2]])
        print(directory / f"{argv[2]}.wav")
        return 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
