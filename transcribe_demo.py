#!/usr/bin/env uv run
"""Simple demo script to transcribe an audio file using OpenAI Whisper.

Usage:
  uv run python transcribe_demo.py path/to/audio.m4a

This script avoids importing mic-related packages and prints actionable
errors if the environment is not configured (missing packages, incompatible
NumPy, etc.).
"""
import sys
from pathlib import Path


def abort(msg: str, code: int = 1):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(code)


def main():
    if len(sys.argv) < 2:
        abort("usage: transcribe_demo.py path/to/audio.m4a")

    audio = Path(sys.argv[1])
    if not audio.exists():
        abort(f"audio file not found: {audio}")

    try:
        import whisper
    except Exception as e:
        abort(f"failed to import whisper: {e}\nInstall with: uv run python -m pip install git+https://github.com/openai/whisper.git@main")

    # check API
    if not hasattr(whisper, "load_model"):
        abort("installed 'whisper' package does not provide 'load_model' (conflicting package).\nInstall OpenAI Whisper: uv run python -m pip install git+https://github.com/openai/whisper.git@main")

    try:
        print("Loading tiny model (CPU)...")
        model = whisper.load_model("tiny")
    except Exception as e:
        abort(f"failed to load whisper model: {e}\nTip: ensure compatible torch/numpy are installed (see README)")

    try:
        res = model.transcribe(str(audio))
    except Exception as e:
        abort(f"transcription failed: {e}")

    print("--- TRANSCRIPT ---")
    print(res.get("text", ""))


if __name__ == "__main__":
    main()
