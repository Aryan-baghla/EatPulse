#!/bin/bash
# CodeDeploy AfterInstall hook — install Python deps, update PgBouncer, run migrations.
set -euo pipefail
exec > >(tee -a /var/log/eatpulse-deploy.log) 2>&1

APP_DIR="/opt/eatpulse"
APP_USER="eatpulse"

echo "[CodeDeploy] Running install_dependencies.sh at $(date -u)"

# ── Install Python dependencies ────────────────────────────────────────────────
echo "[CodeDeploy] Installing Python dependencies..."
$APP_DIR/venv/bin/pip install --quiet --upgrade pip
$APP_DIR/venv/bin/pip install --quiet -r $APP_DIR/requirements.txt
echo "[CodeDeploy] Python dependencies installed"

# ── Re-sync secrets from Secrets Manager into .env ────────────────────────────
echo "[CodeDeploy] Syncing secrets from Secrets Manager..."
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
SECRET_ID=$(grep AWS_SECRETS_MANAGER_SECRET_ID $APP_DIR/.env | cut -d= -f2 || echo "eatpulse/prod")

SECRETS=$(aws secretsmanager get-secret-value \
    --region "$REGION" \
    --secret-id "$SECRET_ID" \
    --query SecretString \
    --output text 2>/dev/null || echo "{}")

if [ "$SECRETS" != "{}" ]; then
    {
      echo "AWS_SECRETS_MANAGER_SECRET_ID=$SECRET_ID"
      echo "AWS_REGION=$REGION"
      echo "$SECRETS" | jq -r 'to_entries[] | "\(.key)=\(.value)"'
    } > $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    echo "[CodeDeploy] Secrets synced"
fi

# ── Run Alembic migrations ─────────────────────────────────────────────────────
echo "[CodeDeploy] Running database migrations..."
cd $APP_DIR
# Migrations use AURORA_DIRECT_URL (bypasses PgBouncer for DDL)
$APP_DIR/venv/bin/alembic upgrade head && echo "[CodeDeploy] Migrations complete" || echo "[CodeDeploy] Migration warning (check if DB is reachable)"

# ── Fix ownership ──────────────────────────────────────────────────────────────
chown -R $APP_USER:$APP_USER $APP_DIR

echo "[CodeDeploy] install_dependencies.sh complete"
