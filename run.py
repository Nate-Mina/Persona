"""Entry point: `python run.py` starts the Sabrina voice persona server on :8000."""
import sys
from pathlib import Path

# make `app` importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.server import main

if __name__ == "__main__":
    main()
