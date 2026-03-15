#!/bin/bash
# EatPulse EC2 bootstrap — runs at first boot via UserData
# Downloads this script from S3 to avoid YAML escaping hell
set -euo pipefail
exec > /var/log/eatpulse-init.log 2>&1
echo "=== EatPulse bootstrap $(date -u) ==="

SECRET_ID="${1:-eatpulse/prod}"
REGION="${2:-ap-south-1}"
APP_DIR="/opt/eatpulse"
APP_USER="eatpulse"

# ── Packages ─────────────────────────────────────────────────────────────────
dnf update -y -q || true
dnf install -y python3.11 python3.11-pip python3.11-devel || true
dnf install -y nginx || true
dnf install -y git jq ruby wget gcc gcc-c++ || true

# ── CodeDeploy agent ──────────────────────────────────────────────────────────
wget -q "https://aws-codedeploy-${REGION}.s3.${REGION}.amazonaws.com/latest/install" \
    -O /tmp/cd-install && chmod +x /tmp/cd-install && /tmp/cd-install auto || true
systemctl enable codedeploy-agent && systemctl start codedeploy-agent || true

# ── App user + directories ────────────────────────────────────────────────────
id -u "$APP_USER" &>/dev/null || \
    useradd --system --no-create-home --shell /sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"
python3.11 -m venv "$APP_DIR/venv" || true

# ── Fetch secrets from Secrets Manager ───────────────────────────────────────
SECRETS=$(aws secretsmanager get-secret-value \
    --region "$REGION" --secret-id "$SECRET_ID" \
    --query SecretString --output text 2>/dev/null || echo '{}')
{
    echo "AWS_SECRETS_MANAGER_SECRET_ID=$SECRET_ID"
    echo "AWS_REGION=$REGION"
    echo "$SECRETS" | jq -r 'to_entries[] | "\(.key)=\(.value)"' 2>/dev/null || true
} > "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# ── Nginx: clean main config (no default server block) ───────────────────────
cat > /etc/nginx/nginx.conf << 'NGINXMAIN'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /run/nginx.pid;
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';
    access_log  /var/log/nginx/access.log  main;
    sendfile            on;
    tcp_nopush          on;
    keepalive_timeout   65;
    types_hash_max_size 4096;
    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;
    include /etc/nginx/conf.d/*.conf;
}
NGINXMAIN

# ── Nginx: site config ────────────────────────────────────────────────────────
mkdir -p /etc/nginx/conf.d
cat > /etc/nginx/conf.d/eatpulse.conf << 'SITECONF'
server {
    listen 80 default_server;

    location = /health {
        access_log off;
        return 200 "ok\n";
        add_header Content-Type text/plain;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        client_max_body_size 10M;
        proxy_read_timeout 60s;
    }
}
SITECONF

# Remove old default.conf if present
rm -f /etc/nginx/conf.d/default.conf

nginx -t && systemctl enable --now nginx || true

# ── Systemd service for FastAPI app ──────────────────────────────────────────
cat > /etc/systemd/system/eatpulse-api.service << 'SVCEOF'
[Unit]
Description=EatPulse FastAPI + Telegram Bot
After=network.target

[Service]
Type=exec
User=eatpulse
WorkingDirectory=/opt/eatpulse
EnvironmentFile=/opt/eatpulse/.env
ExecStart=/opt/eatpulse/venv/bin/uvicorn dashboard.api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable eatpulse-api

chown -R "$APP_USER":"$APP_USER" "$APP_DIR" 2>/dev/null || true
echo "=== Bootstrap complete ==="
