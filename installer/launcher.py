#!/usr/bin/env python3
"""
Sabrina launcher — runs the game.

1) If first run (no install_state.json), runs bootstrap.py (auto-downloads deps,
   the 2 GB XTTS model, and Ollama).
2) Starts Ollama (local) and the FastAPI server on :8000.
3) Opens the browser to http://localhost:8000.

Windows-only (uses creationflags for detached processes).
"""

import os
import subprocess
import sys
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR = os.path.abspath(os.path.join(HERE, ".."))
VENV_PY = os.path.join(INSTALL_DIR, "python", "python.exe")
STATE_FILE = os.path.join(INSTALL_DIR, "install_state.json")
OLLAMA_EXE = os.path.join(INSTALL_DIR, "ollama", "ollama.exe")
RUN_PY = os.path.join(INSTALL_DIR, "run.py")

DETACHED = 0x00000008  # DETACHED_PROCESS

URL = "http://localhost:8000"


def log(m):
    print(f"[sabrina-launcher] {m}", flush=True)


def first_run_setup():
    if os.path.exists(STATE_FILE):
        return
    log("First run — running bootstrap (downloads ~2 GB model + deps)...")
    subprocess.run([VENV_PY, os.path.join(HERE, "bootstrap.py")], check=True)


def is_up(url, timeout=3):
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def start_ollama():
    if is_up("http://localhost:11434/api/tags"):
        log("Ollama already running")
        return
    if not os.path.exists(OLLAMA_EXE):
        log("Ollama not found — run setup again")
        return
    log("starting Ollama...")
    subprocess.Popen([OLLAMA_EXE, "serve"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=DETACHED)
    for _ in range(30):
        time.sleep(1)
        if is_up("http://localhost:11434/api/tags"):
            log("Ollama up")
            return
    log("Ollama did not come up in time")


def start_server():
    env = dict(os.environ)
    env["PYTHONPATH"] = INSTALL_DIR
    env["TTS_DEVICE"] = env.get("TTS_DEVICE", "cpu")
    log("starting Sabrina server on :8000 ...")
    subprocess.Popen([VENV_PY, RUN_PY],
                     cwd=INSTALL_DIR, env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=DETACHED)


def main():
    first_run_setup()
    start_ollama()
    start_server()
    # wait for UI
    for _ in range(40):
        time.sleep(1)
        if is_up(URL):
            break
    log(f"opening {URL}")
    webbrowser.open(URL)
    # keep launcher alive a moment so child processes are definitely spawned
    time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"LAUNCH FAILED: {e}")
        input("Press Enter to close.")
        sys.exit(1)
