"""Speech-to-text via faster-whisper (local, CPU-friendly)."""

import functools

from .config import STT_MODEL

_model = None


@functools.lru_cache(maxsize=1)
def _get_model():
    from faster_whisper import WhisperModel
    # CPU int8 is fast enough for a persona game; set device="cuda" if you build a
    # ROCm torch and want GPU. compute_type "int8" keeps memory low.
    return WhisperModel(STT_MODEL, device="cpu", compute_type="int8")


def transcribe(path: str) -> str:
    """Transcribe an audio file (wav/mp3) -> text."""
    model = _get_model()
    segments, _ = model.transcribe(path, beam_size=5, vad_filter=True)
    return " ".join(s.text for s in segments).strip()


if __name__ == "__main__":
    import sys
    print(transcribe(sys.argv[1]))
