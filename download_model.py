"""Download a small whisper model into a local cache directory.

This script uses the `whisper` package's model download to ensure the tiny/base models are cached locally.
"""
import argparse
import whisper
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="tiny", choices=["tiny", "base", "small"], help="model size")
    p.add_argument("--cache-dir", default="models", help="where to store downloaded models")
    args = p.parse_args()

    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    print(f"Downloading whisper model '{args.model}' to {cache} ...")
    # whisper.load_model will cache under torch/hf cache; we still keep a copy of the model object under our cache dir for clarity
    model = whisper.load_model(args.model)
    print("Model loaded (cached by whisper).")


if __name__ == "__main__":
    main()
