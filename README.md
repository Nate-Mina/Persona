# Sabrina — The Guarded Survivor

A **fully local** AI voice-to-voice persona game. You talk to *Sabrina*, a guarded
trauma-survivor / true-crime obsessive, through your microphone. She talks back in a
**clonable** voice (record a sample → she speaks in it). Nothing leaves your machine.

## Stack (all local)
- **Brain**: [Ollama](https://ollama.com) running `gemma4:12b` on your **AMD 6700XT** (ROCm).
- **Ears**: `faster-whisper` (speech-to-text).
- **Voice**: `Coqui XTTS v2` — zero-shot voice cloning (record 10–30s, she adopts it).
- **Facts**: DuckDuckGo search for obscure true-crime / psychology / medical details.
- **UI**: a local web page with push-to-talk + **barge-in** (talk over her to interrupt).

## Quick start
```bash
# 1) Ollama must be running with a model (already on this machine):
ollama serve &
ollama pull dolphin-mistral:7b      # fast persona model on the 6700XT

# 2) The project venv is already built at .venv. To rebuild from scratch:
python -m venv .venv
.venv\Scripts\activate
pip install "torch==2.4.1+cpu" "torchaudio==2.4.1+cpu" --extra-index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
pip install "gruut==2.2.3" --no-deps          # critical: keeps numpy 2 (torch needs it)
# Download the XTTS v2 model locally (one-time, ~1.9GB), avoids Coqui's ToS prompt:
python -c "from huggingface_hub import snapshot_download; snapshot_download('coqui/XTTS-v2', local_dir='data/xtts_v2')"

# 3) Run:
python run.py
# open http://localhost:8000
```

## Playing
- **Push to Talk** the red button (hold), release to send. Or type in the box.
- **Barge-in**: while Sabrina speaks, start talking — she cuts off (VAD).
- **Clone a Voice** tab: record a sample, Save, then Test. Any TTS uses the active voice.
- **About** tab: how to build her trust vs. trigger a shutdown.

## How Sabrina works
- A fragile **trust meter** (starts at 20%). Intellectual topics (true crime, psychology,
  health, the YouTube channel) raise it and unlock `CALM/VULNERABLE`. Praise or emotional
  prying drops it and triggers a sharp defensive shutdown. Trust persists in `data/state.json`.
- **Trauma triggers**: mentioning *Tommy*, the *motel/room 214/trafficking*, or her *dad*
  forces a visceral sensory flashback, then an anger/fear retreat.
- **Narrative hooks**: she never lists options — she dangles open threads ("…room 214.
  Maybe stick to the Zodiac's medical history?") and branches on what you follow.

## Config
Copy `.env.example` to `.env`. Key knobs:
- `OLLAMA_MODEL`, `OLLAMA_URL`
- `TTS_DEVICE=cpu` → set `cuda` only with a ROCm torch wheel for GPU TTS.
- `STT_MODEL` (tiny/base/small), `SEARCH_ENABLED`, `TEMPERATURE`.

## Notes
- First XTTS load downloads the model (~1.8GB) and unpacks; subsequent runs are fast.
- CPU TTS is ~2–4s per sentence — fine for a persona game. GPU TTS is much faster.
- `data/` holds cloned voices and Sabrina's memory. Delete `data/state.json` to reset her.
