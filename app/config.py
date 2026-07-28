import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VOICES_DIR = DATA_DIR / "voices"
STATE_FILE = DATA_DIR / "state.json"

# Load .env if present (python-dotenv optional)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dolphin-mistral:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# TTS device: "cpu" is safest. If you installed the ROCm build of torch and want
# GPU TTS on the 6700XT, set TTS_DEVICE=cuda (XTTS will use ROCm if torch is the
# rocm wheel). CPU XTTS is ~2-4s per sentence which is fine for a persona game.
TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")
TTS_MODEL = os.getenv("TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")

STT_MODEL = os.getenv("STT_MODEL", "base")  # faster-whisper size: tiny/base/small

SEARCH_ENABLED = os.getenv("SEARCH_ENABLED", "true").lower() == "true"
SEARCH_RESULTS = int(os.getenv("SEARCH_RESULTS", "5"))

# Sampling — higher temperature + penalties to break repetitive outputs.
TEMPERATURE = float(os.getenv("TEMPERATURE", "1.0"))
TOP_P = float(os.getenv("TOP_P", "0.95"))
REPEAT_PENALTY = float(os.getenv("REPEAT_PENALTY", "1.18"))
FREQUENCY_PENALTY = float(os.getenv("FREQUENCY_PENALTY", "0.6"))
PRESENCE_PENALTY = float(os.getenv("PRESENCE_PENALTY", "0.4"))

VOICES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
