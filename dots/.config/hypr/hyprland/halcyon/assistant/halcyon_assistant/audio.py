"""Microphone capture and end-of-speech detection.

Capture goes through PipeWire's pw-record (arecord as a fallback) as raw
16 kHz mono 16-bit PCM, which is what Whisper and Vosk both want. Deciding
when you've stopped talking is a small energy detector with an adaptive
noise floor: no extra dependencies, and good enough for push-to-talk.
"""

import array
import math
import shutil
import subprocess

RATE = 16000
FRAME_MS = 30
FRAME_BYTES = RATE * FRAME_MS // 1000 * 2  # 16-bit mono


def recorder_command():
    if shutil.which("pw-record"):
        return ["pw-record", "--rate", str(RATE), "--channels", "1", "--format", "s16", "-"]
    if shutil.which("arecord"):
        return ["arecord", "-q", "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"]
    return None


class Microphone:
    """Context manager yielding 30 ms frames of raw PCM."""

    def __init__(self):
        self.process = None

    def __enter__(self):
        command = recorder_command()
        if command is None:
            raise RuntimeError("no recorder found: install pipewire (pw-record) or alsa-utils (arecord)")
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return self

    def frames(self):
        while True:
            chunk = self.process.stdout.read(FRAME_BYTES)
            if not chunk or len(chunk) < FRAME_BYTES:
                return
            yield chunk

    def __exit__(self, *_exc):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


def rms(frame):
    samples = array.array("h", frame)
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class EndOfSpeech:
    """Feed frames; tells you when an utterance has started and ended.

    The quietest of the first ~300 ms sets the noise floor, which is capped
    so it can't mistake a voice for noise. Speech is anything well above it;
    the utterance ends after `silence_ms` of quiet following speech, or at
    `max_ms`. If nobody speaks within `wait_ms`, it gives up.
    """

    def __init__(self, silence_ms=900, max_ms=15000, wait_ms=6000, calibrate_ms=300, min_level=300.0):
        self.silence_frames = silence_ms // FRAME_MS
        self.max_frames = max_ms // FRAME_MS
        self.wait_frames = wait_ms // FRAME_MS
        self.calibrate_frames = calibrate_ms // FRAME_MS
        self.min_level = min_level
        self.noise = None
        self.frames = 0
        self.quiet = 0
        self.heard = False
        self.buffer = bytearray()

    # The room's noise level is taken to be no louder than this. It keeps a
    # voice from being mistaken for background noise when someone starts
    # talking the moment they press the key.
    MAX_NOISE = 500.0

    @property
    def threshold(self):
        return max(min(self.noise or 0.0, self.MAX_NOISE) * 3.0, self.min_level)

    def feed(self, frame):
        """Returns "listening", "speech", "done" or "timeout"."""
        self.frames += 1
        level = rms(frame)
        if self.frames <= self.calibrate_frames:
            # The quietest moment so far is the room.
            self.noise = level if self.noise is None else min(self.noise, level)
        elif not self.heard:
            # Keep adapting to the room until speech starts.
            self.noise = 0.95 * self.noise + 0.05 * level
        loud = level > self.threshold
        if loud:
            self.heard = True
            self.quiet = 0
        if self.heard:
            self.buffer += frame
            if not loud:
                self.quiet += 1
            if self.quiet >= self.silence_frames or self.frames >= self.max_frames:
                return "done"
            return "speech"
        if self.frames >= self.wait_frames:
            return "timeout"
        # Keep a little audio from just before speech starts.
        self.buffer = (self.buffer + frame)[-FRAME_BYTES * 10:]
        return "listening"


def record_utterance(on_state=None, cancelled=lambda: False, **kwargs):
    """Record until end of speech. Returns PCM bytes, or None if nothing was said."""
    detector = EndOfSpeech(**kwargs)
    with Microphone() as mic:
        for frame in mic.frames():
            if cancelled():
                return None
            state = detector.feed(frame)
            if on_state:
                on_state(state)
            if state == "done":
                return bytes(detector.buffer)
            if state == "timeout":
                return None
    return bytes(detector.buffer) if detector.heard else None
