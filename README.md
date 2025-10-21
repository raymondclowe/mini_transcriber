# mini_transcriber

Minimal CPU-only transcription package (tiny footprint).

This repository is a compact, opinionated subset derived from the "Transcribe-and-Translate-Subtitles" project. It focuses on the essentials required to run a fast CPU transcription demo: environment setup, a CLI, and a small Flask server endpoint.

Credits
-------
This is based on work from the original repository: https://github.com/raymondclowe/Transcribe-and-Translate-Subtitles — this mini-repo is intentionally minimal and not a drop-in replacement for the full project.

Quick start
-----------
On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv git
./setup.sh
```

Then download model assets (tiny) and run the CLI:

```bash
source venv/bin/activate
python download_model.py --model tiny
python cli.py path/to/audio.wav
```

Run the Flask server:

```bash
source venv/bin/activate
python app.py
# POST audio file to http://127.0.0.1:8080/transcribe
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
