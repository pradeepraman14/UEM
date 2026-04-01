#!/usr/bin/env bash
# ============================================================
# UEM Platform - Ubuntu 24 Server Setup Script
# Run as root or with sudo: bash scripts/setup_server.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo " UEM Platform - Server Setup"
echo " Ubuntu 24.04 LTS"
echo "================================================"

# ── System updates ────────────────────────────────
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# ── Install dependencies ──────────────────────────
echo "[2/8] Installing system dependencies..."
apt-get install -y -qq \
    curl \
    wget \
    git \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql-client \
    openssl \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban

# ── Install Docker ────────────────────────────────
echo "[3/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Install Docker Compose plugin
docker compose version &> /dev/null || apt-get install -y docker-compose-plugin

# ── Configure firewall ─────────────────────────────
echo "[4/8] Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ── Generate PKI ──────────────────────────────────
echo "[5/8] Generating PKI certificates..."
cd "$PROJECT_DIR"
bash pki/gen_ca.sh
SERVER_IP=$(hostname -I | awk '{print $1}')
bash pki/gen_server_cert.sh "$SERVER_IP"

# ── Setup environment ─────────────────────────────
echo "[6/8] Setting up environment..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    # Generate secure random secrets
    JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n')
    DB_PASS=$(openssl rand -base64 24 | tr -d '\n/+=')
    REDIS_PASS=$(openssl rand -base64 24 | tr -d '\n/+=')

    sed -i "s/change_me_very_long_random_secret_key/$JWT_SECRET/g" "$PROJECT_DIR/.env"
    sed -i "s/change_me_db_password/$DB_PASS/g" "$PROJECT_DIR/.env"
    sed -i "s/change_me_redis_password/$REDIS_PASS/g" "$PROJECT_DIR/.env"
    sed -i "s|https://your-server-ip-or-domain|https://$SERVER_IP|g" "$PROJECT_DIR/.env"

    echo "✅ .env file created with random secrets"
else
    echo "⚠️  .env file already exists - skipping"
fi

# ── Start services ─────────────────────────────────
echo "[7/8] Starting Docker services..."
cd "$PROJECT_DIR"
docker compose pull
docker compose up -d

# Wait for services to be healthy
echo "   Waiting for services to be ready..."
sleep 30

# Run database migrations
docker compose exec -T backend alembic upgrade head

# ── Configure fail2ban ─────────────────────────────
echo "[8/8] Configuring fail2ban..."
cat > /etc/fail2ban/jail.d/uem.conf << 'EOF'
[nginx-req-limit]
enabled = true
filter = nginx-req-limit
logpath = /var/log/nginx/uem_error.log
maxretry = 10
bantime = 3600
EOF
systemctl restart fail2ban

# ── Summary ────────────────────────────────────────
echo ""
echo "================================================"
echo " ✅ UEM Platform Setup Complete!"
echo "================================================"
echo ""
echo " Admin Console: https://$SERVER_IP"
echo " API Docs:      https://$SERVER_IP/api/docs"
echo ""
echo " Default admin credentials (CHANGE THESE):"
grep "INITIAL_ADMIN" "$PROJECT_DIR/.env" | head -2
echo ""
echo " To check service status:"
echo "   docker compose ps"
echo ""
echo " To view logs:"
echo "   docker compose logs -f"
echo "================================================"
