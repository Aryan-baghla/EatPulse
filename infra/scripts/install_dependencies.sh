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

# ── Update PgBouncer config with Aurora endpoint ────────────────────────────────
echo "[CodeDeploy] Updating PgBouncer config..."
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
SECRET_ID=$(grep AWS_SECRETS_MANAGER_SECRET_ID $APP_DIR/.env | cut -d= -f2)

SECRETS=$(aws secretsmanager get-secret-value \
    --region "$REGION" \
    --secret-id "$SECRET_ID" \
    --query SecretString \
    --output text 2>/dev/null || echo "{}")

# Get Aurora endpoint from Secrets Manager (added during CF deploy)
AURORA_HOST=$(echo "$SECRETS" | jq -r '.AURORA_HOST // empty')
DB_USER="eatpulse"
DB_PASS=$(echo "$SECRETS" | jq -r '.DB_PASSWORD // empty')

if [ -n "$AURORA_HOST" ]; then
    # Update PgBouncer database config
    sed -i "s|host=.*port=5432 dbname=eatpulse|host=${AURORA_HOST} port=5432 dbname=eatpulse|" \
        /etc/pgbouncer/pgbouncer.ini

    # Update PgBouncer userlist with hashed password
    # PgBouncer scram-sha-256 requires the password in plain or md5 form in userlist
    echo "\"${DB_USER}\" \"${DB_PASS}\"" > /etc/pgbouncer/userlist.txt
    chmod 600 /etc/pgbouncer/userlist.txt

    systemctl restart pgbouncer || true
    echo "[CodeDeploy] PgBouncer updated with Aurora host: $AURORA_HOST"

    # Update DATABASE_URL in .env
    DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/eatpulse"
    AURORA_DIRECT_URL="postgresql://${DB_USER}:${DB_PASS}@${AURORA_HOST}:5432/eatpulse"

    # Update .env
    sed -i '/^DATABASE_URL=/d' $APP_DIR/.env
    sed -i '/^AURORA_DIRECT_URL=/d' $APP_DIR/.env
    echo "DATABASE_URL=${DATABASE_URL}" >> $APP_DIR/.env
    echo "AURORA_DIRECT_URL=${AURORA_DIRECT_URL}" >> $APP_DIR/.env
fi

# ── Run Alembic migrations ─────────────────────────────────────────────────────
echo "[CodeDeploy] Running database migrations..."
cd $APP_DIR
# Migrations use AURORA_DIRECT_URL (bypasses PgBouncer for DDL)
$APP_DIR/venv/bin/alembic upgrade head && echo "[CodeDeploy] Migrations complete" || echo "[CodeDeploy] Migration warning (check if DB is reachable)"

# ── Fix ownership ──────────────────────────────────────────────────────────────
chown -R $APP_USER:$APP_USER $APP_DIR

echo "[CodeDeploy] install_dependencies.sh complete"
