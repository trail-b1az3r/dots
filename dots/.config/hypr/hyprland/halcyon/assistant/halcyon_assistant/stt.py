"""Speech to text with faster-whisper, locally. Loaded once and kept warm."""

from . import config

_model = None
_model_name = None


def available():
    try:
        import faster_whisper  # noqa: F401
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def load(name):
    global _model, _model_name
    if _model is None or _model_name != name:
        from faster_whisper import WhisperModel
        config.MODELS.mkdir(parents=True, exist_ok=True)
        _model = WhisperModel(name, device="cpu", compute_type="int8", download_root=str(config.MODELS / "whisper"))
        _model_name = name
    return _model


def transcribe(pcm, name="base", language=""):
    """16 kHz mono s16 PCM -> text."""
    import numpy as np
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _info = load(name).transcribe(
        audio, language=language or None, beam_size=1, vad_filter=True,
        condition_on_previous_text=False)
    return " ".join(segment.text.strip() for segment in segments).strip()
