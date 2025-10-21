# mini_transcriber

Minimal CPU-only transcription package (tiny footprint).

This repository is a compact, opinionated subset derived from the "Transcribe-and-Translate-Subtitles" project. It focuses on the essentials required to run a fast CPU transcription demo: environment setup, a CLI, and a small Flask server endpoint.

Credits
-------
This is based on work from the original repository: https://github.com/DakeQQ/Transcribe-and-Translate-Subtitles — this mini-repo is intentionally minimal and not a drop-in replacement for the full project.

Quick start
-----------
On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv git
./setup.sh
```

Then download model assets (tiny) and run the CLI.

If you have the project's `uv` helper installed, prefer it:

```bash
# Install deps from requirements.txt
uv add -r requirements.txt

# Download model and run the CLI
uv run python download_model.py --model tiny
uv run python cli.py path/to/audio.wav
```

If you don't have `uv` available, use the venv + pip fallback shown below:

```bash
source venv/bin/activate
python download_model.py --model tiny
python cli.py path/to/audio.wav
```

Run the Flask server with `uv` or the venv fallback:

```bash
uv run python app.py
# or with venv activated:
source venv/bin/activate
python app.py
# POST audio file to http://127.0.0.1:8080/transcribe
```

Avoiding accidental GPU (CUDA) downloads
---------------------------------------

This project is CPU-only by default. Installing `torch` or `torchaudio` without
explicit CPU wheel instructions can cause installers to fetch large GPU/CUDA
builds (nvidia-* packages). To avoid that, either skip installing `torch` when
you don't need it (tests don't require it), or install the CPU-only wheels:

```bash
# Example: install CPU-only PyTorch wheels into your active environment
python -m pip install --index-url https://download.pytorch.org/whl/cpu \
	torch==2.2.2+cpu torchaudio==2.2.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html
```

Quick test run (recommended, no GPU downloads)
---------------------------------------------

Use `uv` to set up a small test environment and run pytest without pulling heavy deps:

```bash
uv init
uv venv
uv add pytest flask numpy
PYTHONPATH=. uv run pytest -q
```

If you want to install everything from `requirements.txt` (including torch), opt in:

```bash
# opt into full install (may download large GPU packages)
INSTALL_FULL=1 ./setup.sh
```

What it includes
----------------
- `setup.sh` — installs system packages (FFmpeg), creates a Python venv and installs minimal Python deps.
- `requirements.txt` — CPU-friendly dependencies.
- `download_model.py` — helper to download small whisper model files to a local model cache.
- `cli.py` — transcribe local audio or system microphone (requires `sounddevice` for mic capture).
- `app.py` — Flask server with POST /transcribe to accept file uploads and return JSON text and timings.

Limitations & next steps
------------------------
- This is intentionally small and uses the openai/whisper PyTorch implementation on CPU for convenience. For production you may prefer onnxruntime or a GPU build.
- You may want to add concurrency/queueing for real server use, and containerize with resource limits.
