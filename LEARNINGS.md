- Keep deterministic CPU installs: commit `uv.lock` and `requirements-cpu.txt`.
  - Use `uv add --frozen --requirements requirements-cpu.txt` in CI and local setup to prevent GPU wheels.

- Avoid preloading model on import in dev servers; lazy-load with a `/health` endpoint so crashes become visible and the server can start before model load.

- Browser capture portability:
  - Not all browsers or contexts expose `navigator.mediaDevices.getUserMedia` (or require HTTPS). Feature-detect and provide a file-upload fallback or a helpful message.
  - Clients may return different sample rates; resample in-browser with `OfflineAudioContext` to 8000 Hz PCM16 for compact uploads and compatibility with telephone-band optimizations.

- Chunked transcription heuristics:
  - Overlap + naive string-trim works as a simple initial approach but will fail at boundaries; prefer timestamp/word-level trimming or streaming for robust results.

- Service management:
  - For simple deployments a systemd unit running the repo from the checked-out directory is fine for experiments. For production use a WSGI server (gunicorn/uvicorn) behind nginx with TLS.

- Debugging tips:
  - When model loading fails, return JSON error and 5xx instead of letting Flask return a raw 500 — makes it easier to automate health checks.
  - Add `/favicon.ico` handling to avoid noisy 404s in browser logs while developing UI features.

- Small helpers:
  - `bin/transcribe_b64.py` is handy for testing base64 JSON POSTs from CLI or automation.

- Follow-ups (next work to avoid repeating issues):
  - Implement streaming endpoint or use a streaming-capable model for lower-latency, more accurate incremental transcription.
  - Improve overlap-trimming to use timestamps from model segments if available.
  - Add CI job that installs with `uv add --frozen --requirements requirements-cpu.txt` and runs the test suite to ensure reproducible CI runs.
