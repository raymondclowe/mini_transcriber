#!/usr/bin/env bash
set -euo pipefail

echo "Installing system packages (you may need sudo)..."
sudo apt update
# Basic runtime + build deps for native wheels (cmake/pkg-config for sentencepiece, build-essential/python3-dev for compiling)
sudo apt install -y ffmpeg python3-venv git pkg-config cmake build-essential python3-dev libsndfile1-dev libffi-dev

echo "Creating venv (if you want a local virtualenv)..."
python3 -m venv venv || true
echo "If you use the project's 'uv' helper, prefer using it to install/run packages."

# Optional: check python version against pyproject requires-python to help users
if [ -f pyproject.toml ]; then
	REQ_PY=$(grep -Po 'requires-python = "\K[^"]+' pyproject.toml || true)
	if [ -n "$REQ_PY" ]; then
		echo "pyproject requires-python: $REQ_PY"
	python3 - <<'PY' || true
import sys
print('current python:', sys.version)
PY
	fi
fi

# By default install a minimal, safe set of Python deps to avoid pulling GPU builds of
# heavy packages like torch. Set INSTALL_FULL=1 to opt into installing the full
# requirements-full.txt (not recommended on machines without GPU-specific needs).
INSTALL_FULL=${INSTALL_FULL:-0}

if command -v uv >/dev/null 2>&1; then
	echo "Detected 'uv' - using 'uv add' to install dependencies..."
		# Prefer a frozen CPU-only install and DO NOT remove uv.lock automatically.
		# This enforces deterministic, NO-GPU installs for all contributors.
		if [ -f uv.lock ]; then
			echo "uv.lock detected — performing a frozen CPU-only install (deterministic, NO GPU wheels)"
			if uv add --frozen --requirements requirements-cpu.txt; then
				echo "Installed from uv.lock (frozen)"
			else
				echo "uv add --frozen failed. If you intentionally updated requirements, run:"
				echo "  uv add -r requirements-cpu.txt --index-strategy unsafe-best-match && uv add --frozen --requirements requirements-cpu.txt"
			fi
		else
			# No lockfile present: create a deterministic CPU-only lock from requirements-cpu.txt
			echo "No uv.lock present — creating a CPU-only lock from requirements-cpu.txt and freezing it"
			# Resolve CPU-only wheels; allow unsafe-best-match to mix the PyTorch CPU index when needed
			if ! uv add -r requirements-cpu.txt --index-strategy unsafe-best-match; then
				echo "uv add -r requirements-cpu.txt failed. Try running: uv add -r requirements-cpu.txt --index-strategy unsafe-best-match"
			fi
			# Freeze the resolved environment into uv.lock for reproducible installs
			if ! uv add --frozen --requirements requirements-cpu.txt; then
				echo "uv add --frozen failed. Re-run: uv add -r requirements-cpu.txt && uv add --frozen --requirements requirements-cpu.txt"
			fi
		fi
	if [ "$INSTALL_FULL" -eq 1 ]; then
		echo "Installing full requirements from requirements-full.txt (user opted-in) via uv"
		if uv add -r requirements-full.txt; then
			echo "Dependencies installed with 'uv add -r requirements-full.txt'"
		else
			echo "ERROR: 'uv add -r requirements-full.txt' failed. Fix the uv environment or run with INSTALL_FULL=1 on a machine configured for full installs."
			exit 1
		fi
	else
		echo "Defaulting to CPU-only install via uv: installing packages from requirements-cpu.txt"
		# Try to add pinned CPU requirements via uv; if it fails, fall back to unpinned uv add
		if uv add -r requirements-cpu.txt; then
			echo "Dependencies installed with 'uv add -r requirements-cpu.txt'"
		else
			echo "Warning: 'uv add -r requirements-cpu.txt' failed. Falling back to unpinned uv add for essential packages."
			if ! uv add pytest flask numpy whisper; then
				echo "ERROR: 'uv add pytest flask numpy whisper' also failed. Please check your uv installation or run 'uv add' manually." 
				exit 1
			fi
			# Ensure pip is available inside the uv-managed environment before running uv run pip installs
			echo "Ensuring pip is available inside uv environment..."
			uv run python -m ensurepip --upgrade || true
			# Preferred uv-only CPU install sequence:
			echo "Installing CPU-only torch/torchaudio via uv (PyTorch CPU index)..."
			# Do not remove uv.lock - prefer reproducible installs. If uv.lock is stale or broken
			# the user should update it intentionally by running 'uv add' locally.
			# Install exact CPU-only torch/torchaudio wheels used in the repro
			uv add --index https://download.pytorch.org/whl/cpu \
				-f https://download.pytorch.org/whl/cpu/torch_stable.html \
				torch==2.2.2+cpu torchaudio==2.2.2+cpu || true
			# Install numba/llvmlite which openai-whisper may require for fast decoding
			echo "Installing numba and llvmlite into the uv venv (required by whisper)" || true
			uv pip install numba llvmlite || true
			# Now install the rest of the runtime deps; allow selecting versions from PyPI if needed
			echo "Installing runtimedeps (flask, numpy, soundfile, etc) with uv using unsafe-best-match so PyPI versions are considered when appropriate..."
			uv add --index-strategy unsafe-best-match flask numpy soundfile sounddevice tqdm regex tiktoken requests || true
			# Finally, ensure openai-whisper (the loader) is available via uv pip without pulling optional compiled deps
			echo "Installing openai-whisper package code (no-deps) into uv venv..."
			# install the OpenAI whisper code without pulling optional compiled deps
			uv pip install --no-deps git+https://github.com/openai/whisper.git@main || true
			# Verification - quick smoke checks
			echo "Verifying torch and whisper imports inside uv venv..."
			uv run python -c "import importlib,sys; print('python',sys.executable); importlib.import_module('torch'); print('torch OK'); importlib.import_module('whisper'); print('whisper OK')" || true
		fi
	fi
	echo "Run scripts with: uv run python <script>"
else
	echo "'uv' not found - installing minimal deps into venv with pip fallback"
	source venv/bin/activate
	python3 -m pip install --upgrade pip
	# Detect NVIDIA GPU presence
	if command -v nvidia-smi >/dev/null 2>&1; then
		echo "NVIDIA GPU detected on this machine. INSTALL_FULL=1 will install full requirements (GPU builds possible)."
	fi
	if [ "$INSTALL_FULL" -eq 1 ]; then
		python3 -m pip install -r requirements-full.txt
	else
		python3 -m pip install --upgrade pip
		echo "Installing CPU-only PyTorch and torchaudio (no CUDA) into venv..."
		python3 -m pip install --index-url https://download.pytorch.org/whl/cpu \
			torch==2.2.2+cpu torchaudio==2.2.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html || true
			echo "Installing numba/llvmlite (whisper dependencies) into venv..."
			python3 -m pip install llvmlite numba || true
			echo "Installing openai-whisper (no-deps) and CPU runtime requirements into venv..."
			# prefer the openai repository implementation; avoid pulling heavy optional deps
			python3 -m pip install --no-deps git+https://github.com/openai/whisper.git@main || true
			python3 -m pip install -r requirements-cpu.txt || python3 -m pip install pytest flask numpy
			# Verification
			echo "Verifying torch and whisper imports inside venv..."
			python3 -c "import importlib,sys; print('python',sys.executable); importlib.import_module('torch'); print('torch OK'); importlib.import_module('whisper'); print('whisper OK')" || true
	fi
	echo "Setup complete. Activate with: source venv/bin/activate"
fi
