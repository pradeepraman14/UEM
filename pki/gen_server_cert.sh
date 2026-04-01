#!/usr/bin/env bash
# ============================================================
# Generate UEM Server TLS certificate (signed by the CA)
# Usage: bash pki/gen_server_cert.sh [server-hostname-or-ip]
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA_DIR="$SCRIPT_DIR/ca"
SERVER_CN="${1:-uem-server}"

if [ ! -f "$CA_DIR/ca.key" ]; then
    echo "❌ CA not found. Run 'bash pki/gen_ca.sh' first."
    exit 1
fi

echo "Generating server certificate for: $SERVER_CN"

# Generate server private key
openssl genrsa -out "$CA_DIR/server.key" 2048
chmod 600 "$CA_DIR/server.key"

# Create SAN extension config
cat > /tmp/server_ext.cnf << EOF
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${SERVER_CN}
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

# Check if the CN looks like an IP address
if [[ "$SERVER_CN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    cat >> /tmp/server_ext.cnf << EOF
IP.2 = ${SERVER_CN}
EOF
fi

# Generate CSR
openssl req -new \
    -key "$CA_DIR/server.key" \
    -out /tmp/server.csr \
    -subj "/CN=${SERVER_CN}/O=UEM Platform/OU=Server/C=US" \
    -config /tmp/server_ext.cnf

# Sign with CA (valid 2 years)
openssl x509 -req \
    -in /tmp/server.csr \
    -CA "$CA_DIR/ca.crt" \
    -CAkey "$CA_DIR/ca.key" \
    -CAcreateserial \
    -out "$CA_DIR/server.crt" \
    -days 730 \
    -extensions v3_req \
    -extfile /tmp/server_ext.cnf

rm -f /tmp/server.csr /tmp/server_ext.cnf

chmod 644 "$CA_DIR/server.crt"

echo "✅ Server certificate generated:"
echo "   Certificate: $CA_DIR/server.crt"
echo "   Private key: $CA_DIR/server.key"
echo ""
echo "Certificate details:"
openssl x509 -in "$CA_DIR/server.crt" -noout -subject -issuer -dates -extensions v3_req 2>/dev/null || \
    openssl x509 -in "$CA_DIR/server.crt" -noout -subject -issuer -dates
