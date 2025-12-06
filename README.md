# mini_transcriber

Minimal CPU-only transcription package (tiny footprint).

This repository is a compact, opinionated subset derived from the "Transcribe-and-Translate-Subtitles" project. It focuses on the essentials required to run a fast CPU transcription demo: environment setup, a CLI, and a small Flask server endpoint.

Credits
-------
This is based on work from the original repository: https://github.com/DakeQQ/Transcribe-and-Translate-Subtitles — this mini-repo is intentionally minimal and not a drop-in replacement for the full project.

Run directly with uvx (fastest)
-------------------------------

If you have `uv` installed, you can run the transcription server directly from GitHub without cloning:

```bash
# Run the server directly from GitHub
uvx --from git+https://github.com/raymondclowe/mini_transcriber mini-transcriber-server

# Run the CLI (requires PortAudio for mic recording)
uvx --from git+https://github.com/raymondclowe/mini_transcriber mini-transcriber-cli path/to/audio.wav

# Just print hello (test entry point)
uvx --from git+https://github.com/raymondclowe/mini_transcriber mini-transcriber
```

Available commands:
- `mini-transcriber` — prints hello (test that install works)
- `mini-transcriber-cli` — transcribe audio files or record from microphone
- `mini-transcriber-server` — start the Flask transcription server

Quick start
-----------

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv git
./setup.sh
```

### Windows

Prerequisites:
- Python 3.12+ from https://www.python.org/downloads/
- FFmpeg (optional, for audio conversion) from https://ffmpeg.org/download.html or via `winget install ffmpeg`

```powershell
# Run in PowerShell
.\setup.ps1

# Or from cmd.exe
setup.bat
```

For CPU-only install (default), the script installs minimal dependencies. Set `$env:INSTALL_FULL="1"` before running for full GPU-capable install.

**Note:** Models auto-download on first use. The tiny model (fastest, default) will download automatically when you first run the CLI or server. You can optionally pre-download models to avoid download time during first use.

If you have the project's `uv` helper installed, prefer it:

```bash
# Install deps from requirements.txt
uv add -r requirements.txt

# Run the CLI (tiny model auto-downloads on first use)
uv run python cli.py path/to/audio.wav

# Optional: Pre-download model to avoid download time during first use
uv run python download_model.py --model tiny
```

If you don't have `uv` available, use the venv + pip fallback shown below:

```bash
# Linux/macOS
source venv/bin/activate
# Run the CLI (tiny model auto-downloads on first use)
python cli.py path/to/audio.wav

# Optional: Pre-download model
python download_model.py --model tiny
```

```powershell
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Run the CLI (tiny model auto-downloads on first use)
python cli.py path\to\audio.wav

# Optional: Pre-download model
python download_model.py --model tiny
```

Run the Flask server with `uv` or the venv fallback:

```bash
uv run python app.py

# Linux/macOS with venv activated:
source venv/bin/activate
python app.py
# POST audio file to http://127.0.0.1:8080/transcribe
```

```powershell
# Windows with venv activated:
.\venv\Scripts\Activate.ps1
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

NO GPU / Deterministic CPU installs
----------------------------------

This repo enforces CPU-only, deterministic installs via `requirements-cpu.txt` and the
`uv.lock` lockfile. To reproduce the exact CPU-only environment we used in
CI and local testing, run:

```bash
# ensure `uv` is installed and available
uv add --frozen --requirements requirements-cpu.txt
uv run python -m pip check
```

This will install the exact pinned CPU packages (including `torch==2.2.2+cpu`) and
prevent any GPU/CUDA wheels (triton/nvidia) from being pulled. If you need GPU
capability intentionally, use `requirements-full.txt` or set `INSTALL_FULL=1` in
`setup.sh` on a machine that has proper GPU drivers.

Live transcription (chunking), minimal-quality audio, and examples
---------------------------------------------------------------

If you plan to use this service for live / low-latency transcription by repeatedly
POSTing small chunks (1-3s) and stitching results client-side, here are practical
tips, conversion commands and expected performance notes based on the environment
used while developing this repo.

1) Minimal-quality audio (telephone bandwidth)

These commands create compact, speech-friendly audio tuned for voice (300-3400 Hz)
and low sample-rate (8 kHz). Use WAV or a small m4a to keep uploads tiny.

```bash
# Telephone-bandwidth WAV (8 kHz mono, 300-3400 Hz)
ffmpeg -y -i audio.m4a -af "highpass=f=300, lowpass=f=3400" -ar 8000 -ac 1 -c:a pcm_s16le audio_8k_telephone.wav

# Small low-bitrate m4a (2s, 16 kb/s) useful for tiny uploads
ffmpeg -y -i audio.m4a -ar 16000 -ac 1 -c:a aac -b:a 16k sample_2s_16k.m4a

# Short WAV (1s, 16kHz) for slightly higher quality
ffmpeg -y -i audio.m4a -t 1 -ar 16000 -ac 1 -c:a pcm_s16le sample_1s_16k.wav
```

2) How to POST chunks to the REST endpoint

You can POST as a regular multipart file (recommended) or as base64 in JSON. The
server accepts either. Examples:

```bash
# multipart/form-data file upload
curl -F "file=@sample_1s_16k.wav" http://127.0.0.1:8085/transcribe

# JSON with base64 payload (safe for programmatic clients)
base64 -w0 sample_1s_16k.wav | jq -Rs --arg m "audio/wav" '{b64: ., mimetype: $m}' \
	| curl -H "Content-Type: application/json" -d @- http://127.0.0.1:8085/transcribe

# Data URI variant
b64=$(base64 -w0 sample_1s_16k.wav)
curl -H "Content-Type: application/json" -d "{\"b64\":\"data:audio/wav;base64,$b64\"}" http://127.0.0.1:8085/transcribe
```

3) Expected performance (approximate, CPU-only environment)

- Cold start: the first request may be slower because the model must load. That
	can take many seconds depending on the machine and model size. We register a
	lazy load in the server to avoid failures, but expect a noticeably longer
	latency for the very first request.
- Steady-state latency (observed while developing on the CPU environment used
	here): for short chunks (0.5–2s) the `whisper` tiny model produced responses in
	roughly 0.5–1.0 seconds of processing time (the server returns a JSON with
	field `duration_s` that contains the measured processing time).
- Memory: we observed ~=150MB RSS for the running service in this environment.
- Throughput: if you POST sequential small chunks, factor in processing time +
	network + client work. With 1s chunks you can expect ~0.5–1.5s end-to-end
	latency per chunk on a modest CPU, so overlapping uploads and buffering on the
	client helps keep the UI smooth.

4) Advice for stitching partial transcripts (basic approach)

- Send short overlapping chunks (for example 1s chunks with 200–500ms overlap).
- Drop overlap time from the beginning of each new chunk's transcript to avoid
	duplicating words — use timestamps or simple "best-effort" trimming at word
	boundaries.
- If you need lower latency and more accurate incremental decoding, move to a
	streaming approach (WebSocket or server-sent events) and a model/decoder that
	exposes partial results. This repo's HTTP endpoint is a simple, stateless
	POST and works well for quick experiments.

5) Example client loop (pseudocode)

- Record N seconds, upload as multipart or base64, append the returned text to a
	local buffer. Optionally apply a small heuristic to remove overlap duplicates:

	- Keep the last M characters from the previous response and skip them when
		appending the new text if they match the start of the new text.

6) When to switch to streaming / production

- If you need sub-second end-to-end latency for interactive voice, use a
	streaming-capable model and transport (WebSocket) and a smaller decoder (or
	an optimized runtime). For low-security, low-scale experiments this POST-based
	approach works fine.

If you'd like, I can:
- Add a tiny client script `bin/transcribe_b64.py` that encodes a file and POSTs
	it and prints the transcript (ready-made for your loop).
- Add a `/health` endpoint that returns 200 so an external monitor can probe the
	service quickly.

Quick test run (recommended, no GPU downloads)
---------------------------------------------

Use `uv` to set up a small test environment and run pytest without pulling heavy deps:

```bash
# Linux/macOS
uv init
uv venv
uv add pytest flask numpy
PYTHONPATH=. uv run pytest -q
```

```powershell
# Windows (PowerShell)
uv init
uv venv
uv add pytest flask numpy
$env:PYTHONPATH="."; uv run pytest -q
```

If you want to install everything from `requirements.txt` (including torch), opt in:

```bash
# Linux/macOS - opt into full install (may download large GPU packages)
INSTALL_FULL=1 ./setup.sh
```

```powershell
# Windows (PowerShell)
$env:INSTALL_FULL="1"; .\setup.ps1
```

What it includes
----------------
- `setup.sh` — Linux/macOS setup: installs system packages (FFmpeg), creates a Python venv and installs minimal Python deps.
- `setup.ps1` — Windows PowerShell setup script (equivalent to setup.sh).
- `setup.bat` — Windows batch file wrapper for setup.ps1.
- `requirements.txt` — CPU-friendly dependencies.
- `download_model.py` — optional helper to pre-download whisper models. Models auto-download on first use, so this is only needed to avoid download time during initial run.
- `cli.py` — transcribe local audio or system microphone (requires `sounddevice` for mic capture).
- `app.py` — Flask server with POST /transcribe to accept file uploads and return JSON text and timings.

Limitations & next steps
------------------------
- This is intentionally small and uses the openai/whisper PyTorch implementation on CPU for convenience. For production you may prefer onnxruntime or a GPU build.
- ~~You may want to add concurrency/queueing for real server use, and containerize with resource limits.~~ **✓ IMPLEMENTED** — See "Concurrency & Queue Management" section below.

Concurrency & Queue Management
------------------------------

The transcription service now includes built-in concurrency control and queue management to handle multiple simultaneous requests gracefully:

### Features

- **Thread-safe queue**: Requests are queued and processed by a configurable number of worker threads
- **Configurable limits**: Control concurrent transcriptions and queue size via environment variables
- **Graceful degradation**: Returns `503 Service Busy` with retry information when the queue is full
- **Both sync and async modes**: Support for immediate response (async) or wait-for-result (sync) operations
- **Queue status monitoring**: Check queue status via the `/health` endpoint

### Configuration

Set these environment variables to tune the behavior:

```bash
# Maximum concurrent transcriptions (default: 1 for CPU-only setups)
export MAX_CONCURRENT_TRANSCRIPTIONS=1

# Maximum queue size (default: 5)
export MAX_QUEUE_SIZE=5

# Estimated processing time per second of audio (default: 0.5)
export ESTIMATED_TIME_PER_SECOND_AUDIO=0.5
```

### Usage

**Synchronous mode (default)**: Client waits for transcription to complete

```bash
curl -F "file=@audio.wav" http://127.0.0.1:8080/transcribe
# Returns: {"text": "...", "duration_s": 1.23, ...}
```

**Asynchronous mode**: Get job ID immediately, poll for results

```bash
# Submit job
curl -F "file=@audio.wav" "http://127.0.0.1:8080/transcribe?async=true"
# Returns: {"job_id": "job_123_...", "status": "queued", ...}

# Poll for status
curl http://127.0.0.1:8080/transcribe/status/job_123_...
# Returns: {"status": "processing|complete", "result": {...}}
```

**Queue full response**: When the service is busy

```bash
curl -F "file=@audio.wav" http://127.0.0.1:8080/transcribe
# Returns 503 with:
{
  "error": "service_busy",
  "message": "Transcription service is currently busy. Please try again later.",
  "retry_after_seconds": 30,
  "queue_status": {
    "active_workers": 1,
    "queued_jobs": 5,
    "queue_capacity": 5
  },
  "backoff_strategy": {
    "type": "exponential",
    "initial_delay": 30,
    "max_delay": 300,
    "multiplier": 2
  }
}
```

### Monitoring

Check queue status via `/health`:

```bash
curl http://127.0.0.1:8080/health
# Returns:
{
  "status": "ok",
  "model_loaded": true,
  "loaded_models": ["tiny"],
  "queue": {
    "max_workers": 1,
    "active_workers": 1,
    "queued_jobs": 2,
    "processing_jobs": 1,
    "queue_size": 2,
    "queue_capacity": 5
  },
  "concurrency": {
    "max_concurrent_transcriptions": 1,
    "max_queue_size": 5
  }
}
```

### Recommendations

- **CPU-only setups**: Keep `MAX_CONCURRENT_TRANSCRIPTIONS=1` to avoid resource contention
- **Multi-core with GPU**: Increase to 2-4 depending on available memory and GPU resources
- **High-traffic scenarios**: Increase `MAX_QUEUE_SIZE` but be aware this increases memory usage
- **Client implementation**: Implement exponential backoff when receiving 503 responses

Recent changes (local development)
---------------------------------

- **NEW**: Added thread-safe queue management for concurrent transcription requests with configurable limits
- **NEW**: Added async transcription mode with job polling via `/transcribe/status/<job_id>`
- **NEW**: Added 503 "service busy" responses with retry-after headers and exponential backoff recommendations
- **NEW**: Enhanced `/health` endpoint to include queue status and concurrency metrics
- Added a small browser UI at `/` (served from `static/index.html`) that records overlapping chunks, resamples to 8 kHz WAV in the browser, and POSTs them to `/transcribe` for naive stitched live transcription.
- Added a `/health` endpoint to report whether the Whisper model has been loaded. Useful for service monitors.
- The server will now respond to `/favicon.ico` (returns `static/favicon.ico` if present or 204 otherwise) to avoid 404 noise in browser devtools.
- The UI now feature-detects `navigator.mediaDevices.getUserMedia` and disables the Start button with a helpful message in browsers where microphone capture is unavailable.
- A systemd unit (`mini-transcriber.service`) was added to run the Flask app as a service (defaults: `PORT=8085`, `HOST=0.0.0.0`) and a small helper script `bin/transcribe_b64.py` can POST base64-encoded audio to the server.

Reproducible, CPU-only installs
--------------------------------

This project intentionally enforces CPU-only installs. See `requirements-cpu.txt` and the checked-in `uv.lock` for the exact environment used during development. Use the `uv` helper with `--frozen` to reproduce the same CPU-only environment and avoid accidental GPU/CUDA wheel downloads.

If you maintain this repo, keep `uv.lock` and `requirements-cpu.txt` up-to-date when you change dependencies so CI and reproducible installs continue to work.
