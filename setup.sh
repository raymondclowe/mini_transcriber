#!/usr/bin/env bash
set -euo pipefail

echo "Installing system packages (you may need sudo)..."
sudo apt update
sudo apt install -y ffmpeg python3-venv git

echo "Creating venv (if you want a local virtualenv)..."
python3 -m venv venv || true
echo "If you use the project's 'uv' helper, prefer using it to install/run packages."

# By default install a minimal, safe set of Python deps to avoid pulling GPU builds of
# heavy packages like torch. Set INSTALL_FULL=1 to opt into installing the full
# requirements-full.txt (not recommended on machines without GPU-specific needs).
INSTALL_FULL=${INSTALL_FULL:-0}

if command -v uv >/dev/null 2>&1; then
	echo "Detected 'uv' - using 'uv add' to install dependencies..."
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
			echo "Installing CPU-only PyTorch and torchaudio (no CUDA) via uv run pip..."
			uv run python -m pip install --upgrade pip
			uv run python -m pip install --index-url https://download.pytorch.org/whl/cpu \
				torch==2.2.2+cpu torchaudio==2.2.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html || true
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
		echo "Installing whisper and CPU runtime requirements..."
		python3 -m pip install whisper || true
		python3 -m pip install -r requirements-cpu.txt || python3 -m pip install pytest flask numpy
	fi
	echo "Setup complete. Activate with: source venv/bin/activate"
fi
