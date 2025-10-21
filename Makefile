PY=python3
UV=uv

.PHONY: help setup venv add-dev test run install-cpu-torch

help:
	@echo "Makefile targets:"
	@echo "  setup           - run ./setup.sh (safe CPU-first defaults)"
	@echo "  venv            - create uv venv (uv venv)"
	@echo "  add-dev         - install dev deps (pytest, flask, numpy) via uv"
	@echo "  test            - run pytest (PYTHONPATH=. uv run pytest -q)"
	@echo "  run             - run the app (uv run python app.py)"
	@echo "  install-cpu-torch - helper to install CPU-only PyTorch wheels"

setup:
	./setup.sh

venv:
	$(UV) venv

add-dev:
	$(UV) add pytest flask numpy

test:
	PYTHONPATH=. $(UV) run pytest -q

run:
	$(UV) run python app.py

install-cpu-torch:
	# Installs CPU-only PyTorch and torchaudio into the active environment
	@echo "Installing CPU-only PyTorch wheels..."
	$(UV) run python -m pip install --index-url https://download.pytorch.org/whl/cpu \
		torch==2.2.2+cpu torchaudio==2.2.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html
