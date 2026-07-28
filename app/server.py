"""FastAPI backend for the Sabrina voice persona game (fully local)."""

import io
import json
import os
import tempfile
import uuid

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import subprocess

from . import engine, tts
from .config import BASE_DIR, VOICES_DIR

try:
    import uvicorn
except ImportError:
    uvicorn = None


def _to_wav(src: str, dst: str) -> str:
    """Convert any audio file to 16k mono wav via ffmpeg (browser sends webm/opus)."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", dst],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return dst
    except Exception:
        return src

app = FastAPI(title="Sabrina — The Guarded Survivor")

INDEX = BASE_DIR / "app" / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX.read_text(encoding="utf-8")


@app.get("/state")
def state():
    from . import sabrina
    s = sabrina.load_state()
    return {"trust": s["trust"], "turns": s["turns"],
            "last_emotion": s["last_emotion"], "hooks": s["hooks"]}


@app.get("/persona")
def get_persona():
    from . import sabrina
    return {"text": sabrina.load_persona()}


@app.post("/persona")
async def set_persona(payload: dict):
    text = (payload or {}).get("text", "").strip()
    from . import sabrina
    sabrina.save_persona(text)
    return {"ok": True, "chars": len(text)}


@app.get("/reset")
def reset():
    engine.reset()
    return {"ok": True}


@app.get("/voices")
def voices():
    return {"voices": tts.list_voices()}


@app.post("/chat")
async def chat(payload: dict):
    text = (payload or {}).get("text", "").strip()
    if not text:
        return JSONResponse({"error": "empty"}, status_code=400)
    try:
        result = engine.respond(text)
    except Exception as e:
        # Most likely Ollama is down. Return a clean, in-character offline notice
        # (HTTP 200 so the UI can render it gracefully) instead of a 500.
        from .llm import OllamaUnavailable
        offline = isinstance(e, OllamaUnavailable)
        return JSONResponse(
            {
                "reply": (
                    "…Nate? You there? I can't… I can't reach you. Everything's gone quiet. "
                    "Wait for me. I'll come back when the line's open."
                    if offline else
                    "Something's wrong with my head right now. Give me a second."
                ),
                "emotion": "fear",
                "flashback": "",
                "hook": "",
                "offline": offline,
                "error": str(e) if not offline else None,
            },
            status_code=200,
        )
    return result


@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    data = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(data)
        tmp = f.name
    wav = tmp + ".wav"
    wav = _to_wav(tmp, wav)
    try:
        from . import stt as sttmod
        text = sttmod.transcribe(wav)
    finally:
        for p in (tmp, wav):
            try:
                os.remove(p)
            except Exception:
                pass
    return {"text": text}


@app.post("/tts")
async def synth(payload: dict):
    text = (payload or {}).get("text", "").strip()
    voice = (payload or {}).get("voice")  # optional voice filename
    if not text:
        return JSONResponse({"error": "empty"}, status_code=400)
    spk = None
    if voice:
        cand = VOICES_DIR / voice
        if cand.exists():
            spk = str(cand)
    out = tempfile.mktemp(suffix=".wav")
    path = tts.synthesize(text, out, speaker_wav=spk)
    return FileResponse(path, media_type="audio/wav", filename="sabrina.wav")


@app.post("/clone")
async def clone(file: UploadFile = File(...), name: str = Form("sabrina")):
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty upload"}, status_code=400)
    name = name.strip() or "sabrina"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(data)
        tmp = f.name
    wav = VOICES_DIR / f"{name}.wav"
    _to_wav(tmp, str(wav))
    try:
        os.remove(tmp)
    except Exception:
        pass
    tts.set_default_speaker(str(wav))
    return {"ok": True, "voice": wav.name, "voices": tts.list_voices()}


def main():
    if uvicorn is None:
        raise SystemExit("uvicorn not installed")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
