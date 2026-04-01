#!/usr/bin/env bash
# ============================================================
# Generate UEM Root CA certificate
# Run once on initial server setup: bash pki/gen_ca.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA_DIR="$SCRIPT_DIR/ca"
mkdir -p "$CA_DIR"

# Only generate if CA doesn't already exist
if [ -f "$CA_DIR/ca.key" ] && [ -f "$CA_DIR/ca.crt" ]; then
    echo "✅ CA already exists at $CA_DIR - skipping"
    exit 0
fi

echo "Generating UEM Root CA..."

# Generate CA private key (4096-bit RSA)
openssl genrsa -out "$CA_DIR/ca.key" 4096

# Generate CA certificate (valid 10 years)
openssl req -new -x509 \
    -key "$CA_DIR/ca.key" \
    -out "$CA_DIR/ca.crt" \
    -days 3650 \
    -subj "/CN=UEM Root CA/O=UEM Platform/OU=Security/C=US" \
    -extensions v3_ca \
    -config <(cat /etc/ssl/openssl.cnf <(printf "\n[v3_ca]\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid:always"))

# Set permissions
chmod 600 "$CA_DIR/ca.key"
chmod 644 "$CA_DIR/ca.crt"

echo "✅ CA generated:"
echo "   Certificate: $CA_DIR/ca.crt"
echo "   Private key: $CA_DIR/ca.key (keep SECRET!)"
echo ""
echo "Certificate details:"
openssl x509 -in "$CA_DIR/ca.crt" -noout -subject -issuer -dates
