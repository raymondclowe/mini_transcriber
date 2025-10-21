#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root to install systemd unit files. Use sudo." >&2
  exit 1
fi

NAME="mini-transcriber"
SERVICE_DIR="/etc/systemd/system"

echo "Installing systemd unit files to ${SERVICE_DIR} ..."
cp ${NAME}.service ${SERVICE_DIR}/${NAME}.service

echo "Reloading systemd daemon and enabling service..."
systemctl daemon-reload
systemctl enable ${NAME}.service
systemctl start ${NAME}.service

echo "Service installed and started. Check status: systemctl status ${NAME}.service"
