"""Optional wake phrase ("hey halcyon"), spotted locally with Vosk.

Vosk runs a small offline model constrained to a grammar of just the wake
phrase and "[unk]", so it is cheap enough to leave running and never sends
audio anywhere. Off unless Settings > Halcyon > Assistant > Wake word is on.
"""

import json

from . import audio, config

MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"


def model_path():
    return config.MODELS / MODEL_NAME


def available():
    try:
        import vosk  # noqa: F401
    except ImportError:
        return False
    return model_path().is_dir()


def matches(text, phrase):
    words = text.lower().split()
    target = phrase.lower().split()
    return any(words[i:i + len(target)] == target for i in range(len(words) - len(target) + 1))


def listen(phrase, on_wake, should_stop, paused):
    """Block, calling on_wake() whenever the phrase is heard.

    The microphone is released before on_wake() runs, and while paused()
    is true, so the assistant can record the request itself.
    """
    import time
    import vosk
    vosk.SetLogLevel(-1)
    model = vosk.Model(str(model_path()))
    grammar = json.dumps([phrase.lower(), phrase.split()[-1].lower(), "[unk]"])
    while not should_stop():
        while paused() and not should_stop():
            time.sleep(0.2)
        recogniser = vosk.KaldiRecognizer(model, audio.RATE, grammar)
        woke = False
        with audio.Microphone() as mic:
            for frame in mic.frames():
                if should_stop() or paused():
                    break
                if recogniser.AcceptWaveform(frame):
                    if matches(json.loads(recogniser.Result()).get("text", ""), phrase):
                        woke = True
                        break
        if woke:
            on_wake()
