"""Text-to-speech with zero-shot voice cloning via Coqui XTTS v2 (local).

- Default voice: a recorded clone (saved under data/voices) or a built-in sample.
- Voice cloning: pass a reference wav (10-30s, clean speech) -> XTTS clones it.
- Output is a 24kHz wav.

We load the XTTS v2 model from a LOCAL directory (data/xtts_v2) so we avoid
Coqui's interactive Terms-of-Service prompt that blocks non-interactive runs.
Downloaded once via `huggingface_hub` (see README). Runs on CPU by default
(TTS_DEVICE=cpu). For the 6700XT set TTS_DEVICE=cuda with a ROCm torch wheel.
"""

import os
from pathlib import Path

from .config import TTS_DEVICE, VOICES_DIR, DATA_DIR

# Local XTTS v2 directory (downloaded via huggingface_hub). Override with
# XTTS_DIR env var. TTS's Synthesizer treats the passed model_path as the
# *checkpoint directory* and appends "model.pth" itself, so we point at the dir.
_XTTS_DIR = os.getenv("XTTS_DIR", str(DATA_DIR / "xtts_v2"))
_MODEL_PATH = _XTTS_DIR
_CONFIG_PATH = os.path.join(_XTTS_DIR, "config.json")

_tts = None
_DEFAULT_SPEAKER_WAV = None  # path to a wav used when no custom clone is set
_DEFAULT_SPEAKER = "Claribel Dervla"  # a bundled XTTS reference voice (used pre-clone)


def _get_tts():
    global _tts
    if _tts is not None:
        return _tts
    from TTS.api import TTS
    # Load directly from local files (no network ToS prompt).
    _tts = TTS(
        model_path=_MODEL_PATH,
        config_path=_CONFIG_PATH,
        gpu=(TTS_DEVICE != "cpu"),
    )
    return _tts


def list_voices() -> list:
    """List saved cloned voices (wav files in data/voices)."""
    return sorted(p.name for p in VOICES_DIR.glob("*.wav"))


def set_default_speaker(wav_path: str | None):
    global _DEFAULT_SPEAKER_WAV
    _DEFAULT_SPEAKER_WAV = wav_path


def synthesize(text: str, out_path: str, speaker_wav: str | None = None,
               language: str = "en") -> str:
    """Synthesize `text` to `out_path` (wav). speaker_wav enables voice cloning."""
    tts = _get_tts()
    spk = speaker_wav or _DEFAULT_SPEAKER_WAV
    if spk and os.path.exists(spk):
        tts.tts_to_file(text=text, speaker_wav=spk, language=language,
                        file_path=out_path)
    else:
        # No clone available: use XTTS's bundled reference speaker.
        tts.tts_to_file(text=text, speaker=_DEFAULT_SPEAKER, language=language,
                        file_path=out_path)
    return out_path


if __name__ == "__main__":
    import sys
    p = sys.argv[2] if len(sys.argv) > 2 else str(VOICES_DIR / "test.wav")
    print(synthesize(sys.argv[1] if len(sys.argv) > 1 else "Why would you do this for me?", p))
