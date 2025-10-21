#!/usr/bin/env bash
set -euo pipefail

echo "Installing system packages (you may need sudo)..."
sudo apt update
sudo apt install -y ffmpeg python3-venv git

echo "Creating venv..."
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Activate with: source venv/bin/activate"
