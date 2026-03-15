#!/bin/bash
# CodeDeploy BeforeInstall hook — stop the application gracefully.
set -euo pipefail

echo "[CodeDeploy] Stopping eatpulse-api..."
if systemctl is-active --quiet eatpulse-api; then
    systemctl stop eatpulse-api
    echo "[CodeDeploy] eatpulse-api stopped"
else
    echo "[CodeDeploy] eatpulse-api was not running"
fi
