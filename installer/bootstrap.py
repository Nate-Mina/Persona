#!/usr/bin/env python3
"""
Sabrina — first-run bootstrap.

Downloads and installs everything Sabrina needs, fully offline-capable after the
first successful run:
  1) a standalone embedded Python (python-3.11.x-embed) if none is present
  2) a venv + the exact pinned dependency set (requirements.txt order matters)
  3) the Coqui XTTS v2 model (2 GB) via huggingface_hub
  4) Ollama (the brain) for Windows, launched locally

Idempotent: re-running skips steps that are already done. Safe to run again.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(HERE, "app"))
INSTALL_DIR = os.path.abspath(os.path.join(HERE, ".."))  # install root = parent of installer/
DATA_DIR = os.path.join(INSTALL_DIR, "data")
XTTS_DIR = os.path.join(DATA_DIR, "xtts_v2")
VENV_DIR = os.path.join(INSTALL_DIR, "venv")
PY_DIR = os.path.join(INSTALL_DIR, "python")
STATE_FILE = os.path.join(INSTALL_DIR, "install_state.json")

PY_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
OLLAMA_URL = "https://ollama.com/download/ollama-windows-amd64.zip"


def log(msg):
    print(f"[sabrina-setup] {msg}", flush=True)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except Exception:
        pass


def run(cmd, **kw):
    log("> " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, **kw)


def download(url, dest, label="file"):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        log(f"{label} already present, skip download")
        return dest
    log(f"downloading {label}: {url}")
    urllib.request.urlretrieve(url, dest)
    log(f"saved {dest} ({os.path.getsize(dest)} bytes)")
    return dest


# --------------------------------------------------------------------------- #
def ensure_python():
    state = load_state()
    if state.get("python") and os.path.exists(os.path.join(PY_DIR, "python.exe")):
        log("embedded Python present")
        return os.path.join(PY_DIR, "python.exe")
    download(PY_URL, os.path.join(INSTALL_DIR, "python-embed.zip"), "embedded Python")
    log(f"extracting Python -> {PY_DIR}")
    if os.path.exists(PY_DIR):
        shutil.rmtree(PY_DIR)
    os.makedirs(PY_DIR, exist_ok=True)
    with zipfile.ZipFile(os.path.join(INSTALL_DIR, "python-embed.zip")) as z:
        z.extractall(PY_DIR)
    # embed python can't 'pip install' to user site by default; enable.
    pth = os.path.join(PY_DIR, "python311._pth")
    if os.path.exists(pth):
        with open(pth, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if "import site" not in lines:
            lines.append("import site")
        with open(pth, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    # get pip
    getpip = os.path.join(PY_DIR, "get-pip.py")
    download("https://bootstrap.pypa.io/get-pip.py", getpip, "get-pip.py")
    run([os.path.join(PY_DIR, "python.exe"), getpip], check=True)
    state["python"] = True
    save_state(state)
    return os.path.join(PY_DIR, "python.exe")


def ensure_venv(python_exe):
    state = load_state()
    py = os.path.join(VENV_DIR, "Scripts", "python.exe")
    pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    if state.get("venv") and os.path.exists(pip):
        log("venv present")
        return py, pip
    if not os.path.exists(VENV_DIR):
        run([python_exe, "-m", "venv", VENV_DIR], check=True)
    # install deps in the exact order from requirements.txt
    req = os.path.join(INSTALL_DIR, "requirements.txt")
    log("installing torch (CPU wheel)...")
    run([pip, "install", "torch==2.4.1+cpu", "torchaudio==2.4.1+cpu",
         "--extra-index-url", "https://download.pytorch.org/whl/cpu"], check=True)
    log("installing remaining deps...")
    run([pip, "install", "-r", req], check=True)
    # gruut must NOT drag numpy<2
    run([pip, "install", "gruut==2.2.3", "--no-deps"], check=True)
    state["venv"] = True
    save_state(state)
    return py, pip


def ensure_xtts():
    state = load_state()
    if state.get("xtts") and os.path.exists(os.path.join(XTTS_DIR, "model.pth")):
        log("XTTS v2 model present")
        return
    os.makedirs(XTTS_DIR, exist_ok=True)
    log("downloading XTTS v2 model (~2 GB, this is slow)...")
    run([os.path.join(VENV_DIR, "Scripts", "python.exe"),
         "-c",
         "from huggingface_hub import snapshot_download; "
         "snapshot_download('coqui/XTTS-v2', local_dir=r'" + XTTS_DIR.replace("'", "''") + "')"],
        check=True)
    state["xtts"] = True
    save_state(state)


def ensure_ollama():
    state = load_state()
    ollama_exe = os.path.join(INSTALL_DIR, "ollama", "ollama.exe")
    if state.get("ollama") and os.path.exists(ollama_exe):
        log("Ollama present")
        return ollama_exe
    dest = os.path.join(INSTALL_DIR, "ollama-windows.zip")
    download(OLLAMA_URL, dest, "Ollama")
    os.makedirs(os.path.join(INSTALL_DIR, "ollama"), exist_ok=True)
    with zipfile.ZipFile(dest) as z:
        z.extractall(os.path.join(INSTALL_DIR, "ollama"))
    state["ollama"] = True
    save_state(state)
    return ollama_exe


def main():
    log("=== Sabrina first-run setup ===")
    python_exe = ensure_python()
    py, pip = ensure_venv(python_exe)
    ensure_xtts()
    ollama_exe = ensure_ollama()
    log("=== setup complete ===")
    log(f"Ollama: {ollama_exe}")
    log(f"App:    {os.path.join(INSTALL_DIR, 'run.py')}")
    log("Run Launch Sabrina from the Start Menu, or run launcher.py")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"SETUP FAILED: {e}")
        input("Press Enter to close.")
        sys.exit(1)
