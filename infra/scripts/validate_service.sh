#!/bin/bash
# CodeDeploy ValidateService hook — confirm the app is healthy.
set -euo pipefail

MAX_ATTEMPTS=10
SLEEP=3

echo "[CodeDeploy] Validating service health..."

for i in $(seq 1 $MAX_ATTEMPTS); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "[CodeDeploy] Health check passed (attempt $i)"
        exit 0
    fi
    echo "[CodeDeploy] Health check attempt $i/$MAX_ATTEMPTS — got HTTP $STATUS, retrying..."
    sleep $SLEEP
done

echo "[CodeDeploy] Health check FAILED after $MAX_ATTEMPTS attempts"
systemctl status eatpulse-api --no-pager || true
journalctl -u eatpulse-api -n 50 --no-pager || true
exit 1
