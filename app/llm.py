"""Minimal Ollama chat client (local, on the 6700XT).

Adds resilience: a connection failure to Ollama is retried a couple of times, and
if Ollama isn't running we attempt to auto-start it once (so a transient outage
or a reboot doesn't leave Sabrina hard-down). If it still can't connect, we raise
a clear OllamaUnavailable error the server turns into a friendly offline message.
"""

import json
import shutil
import subprocess
import time

import requests

from .config import (OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, TEMPERATURE, TOP_P,
                     REPEAT_PENALTY, FREQUENCY_PENALTY, PRESENCE_PENALTY)

# How long to keep the model resident on GPU between calls (avoids reload flapping).
KEEP_ALIVE = -1  # -1 = forever


class OllamaUnavailable(Exception):
    """Raised when Ollama cannot be reached after retries/auto-start."""


def _ollama_up() -> bool:
    """Quick liveness check (<= ~3s). Does NOT auto-start."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _try_autostart():
    """Best-effort: launch 'ollama serve' detached so it can come back on its own.
    Non-blocking — we don't wait for it to bind."""
    binpath = shutil.which("ollama")
    if not binpath:
        return
    try:
        subprocess.Popen([binpath, "serve"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x00000008)  # DETACHED_PROCESS
    except Exception:
        pass


def chat(messages, model: str = OLLAMA_MODEL, temperature: float = TEMPERATURE,
         top_p: float = TOP_P) -> str:
    """messages: list of {"role","content"}. Returns assistant text.

    On a connection failure we do a fast liveness check and (best-effort)
    trigger an Ollama auto-start in the background, but we return quickly with
    OllamaUnavailable rather than hanging — the server turns that into a clean
    offline message.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": REPEAT_PENALTY,
            "frequency_penalty": FREQUENCY_PENALTY,
            "presence_penalty": PRESENCE_PENALTY,
        },
    }
    last_err = None
    for attempt in range(2):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload,
                              timeout=OLLAMA_TIMEOUT)
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError as e:
            last_err = e
            if not _ollama_up():
                _try_autostart()           # fire-and-forget, don't block
                raise OllamaUnavailable(
                    f"Ollama at {OLLAMA_URL} is not running. Start it with: ollama serve") from e
            time.sleep(0.5)
        except requests.RequestException as e:
            last_err = e
            time.sleep(0.5)
    raise OllamaUnavailable(f"Ollama at {OLLAMA_URL} unavailable: {last_err}")


def generate(prompt: str, model: str = OLLAMA_MODEL, temperature: float = TEMPERATURE) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False,
               "keep_alive": KEEP_ALIVE,
               "options": {"temperature": temperature}}
    last_err = None
    for _ in range(2):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload,
                              timeout=OLLAMA_TIMEOUT)
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.exceptions.ConnectionError as e:
            last_err = e
            if not _ollama_up():
                _try_autostart()
                raise OllamaUnavailable(
                    f"Ollama at {OLLAMA_URL} is not running. Start it with: ollama serve") from e
            time.sleep(0.5)
        except requests.RequestException as e:
            last_err = e
    raise OllamaUnavailable(f"Ollama at {OLLAMA_URL} unavailable: {last_err}")
