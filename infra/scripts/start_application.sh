#!/bin/bash
# CodeDeploy ApplicationStart hook — start the application.
set -euo pipefail

echo "[CodeDeploy] Starting eatpulse-api..."
systemctl daemon-reload
systemctl start eatpulse-api
echo "[CodeDeploy] eatpulse-api started"

# Give it a moment to initialise before the next hook validates
sleep 3
