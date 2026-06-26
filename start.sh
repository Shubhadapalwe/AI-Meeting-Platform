#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Launch the AI Meeting Platform (HTTPS, cross-device)
# Usage:  chmod +x start.sh && ./start.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

# ── 1. Detect Mac WiFi IP ─────────────────────────────────────────────────────
detect_ip() {
  for iface in en0 en1 en2 wlan0; do
    ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
    if [[ -n "$ip" ]]; then echo "$ip"; return; fi
  done
  ifconfig | awk '/inet / && !/127\.0\.0\.1/ {print $2; exit}'
}

HOST_IP=$(detect_ip)
if [[ -z "$HOST_IP" ]]; then
  echo "❌  Could not detect WiFi IP. Connect to WiFi and try again."
  exit 1
fi
export HOST_IP

# ── 2. Install mkcert if missing ──────────────────────────────────────────────
if ! command -v mkcert &>/dev/null; then
  echo "Installing mkcert via Homebrew..."
  brew install mkcert
fi

# ── 3. Generate HTTPS certs for this IP (only if missing or IP changed) ───────
mkdir -p certs

# Install local CA (only needed once — safe to re-run)
mkcert -install 2>/dev/null || true

CERT_IP_FILE="certs/.last_ip"
LAST_IP=$(cat "$CERT_IP_FILE" 2>/dev/null || echo "")

if [[ ! -f "certs/cert.pem" || ! -f "certs/key.pem" || "$LAST_IP" != "$HOST_IP" ]]; then
  echo "Generating new certs for ${HOST_IP}..."
  mkcert -cert-file certs/cert.pem -key-file certs/key.pem \
    "${HOST_IP}" localhost 127.0.0.1
  echo "${HOST_IP}" > "$CERT_IP_FILE"
else
  echo "✅  Reusing existing certs for ${HOST_IP}"
fi

# Copy rootCA so user can import it into Firefox on Android
CAROOT=$(mkcert -CAROOT)
cp "${CAROOT}/rootCA.pem" certs/rootCA.pem

echo "✅  Certs generated for ${HOST_IP}"
echo "    rootCA.pem is at: $(pwd)/certs/rootCA.pem"

# ── 4. Write livekit.yaml with correct node_ip ────────────────────────────────
# LiveKit WebSocket is proxied through Vite (wss://HOST_IP:5173/livekit)
# so we don't need LiveKit to advertise the host IP for signaling.
# We still set node_ip so ICE candidates (WebRTC UDP) use the right IP.
cat > livekit.yaml <<EOF
port: 7880
bind_addresses:
  - 0.0.0.0

keys:
  devkey: devsecret

rtc:
  use_external_ip: false
  node_ip: ${HOST_IP}
  udp_port: 7882
  tcp_port: 7881

logging:
  level: info

development: true
EOF

echo "✅  livekit.yaml written with node_ip=${HOST_IP}"

# ── 5. LiveKit public URL — proxied through Vite (WSS same origin) ───────────
# Browser: wss://HOST_IP:5173/livekit  →  Vite proxy  →  ws://livekit:7880
export LIVEKIT_PUBLIC_URL="wss://${HOST_IP}:5173/livekit"

# ── 6. Print access info ──────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          AI Meeting Platform — HTTPS Cross-Device Mode       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf  "║  Mac IP           : %-40s ║\n" "${HOST_IP}"
printf  "║  Open on Mac      : https://%-33s ║\n" "${HOST_IP}:5173"
printf  "║  Open on Android  : https://%-33s ║\n" "${HOST_IP}:5173"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  ANDROID SETUP (one-time):                                   ║"
printf  "║  1. Open https://%-43s ║\n" "${HOST_IP}:5173 → Accept cert"
printf  "║  2. Download http://%-40s ║\n" "${HOST_IP}:8000/rootca"
echo "║     Install: Android Settings → Security → Install cert      ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  AUTO SPEAKER DETECTION (pyannote — one-time setup):         ║"
echo "║  1. Free token: huggingface.co/join                          ║"
echo "║  2. Accept licenses:                                         ║"
echo "║     huggingface.co/pyannote/speaker-diarization-3.1          ║"
echo "║     huggingface.co/pyannote/segmentation-3.0                 ║"
echo "║  3. Add HUGGINGFACE_TOKEN=hf_xxx to .env                     ║"
echo "║  Without token: both participants must record separately.     ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  EMAIL SETUP (one-time):                                     ║"
echo "║  cp .env.example .env  → fill in Gmail SMTP credentials      ║"
echo "║  Gmail: enable 2FA → myaccount.google.com/apppasswords       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 7. Ensure .env exists (SMTP is optional — app works without it) ──────────
if [[ ! -f ".env" ]]; then
  echo "# SMTP credentials (optional). See .env.example for instructions." > .env
  echo "Creating blank .env — copy .env.example and fill in SMTP to enable email."
fi

# ── 8. Stop old containers ────────────────────────────────────────────────────
echo "Stopping old containers..."
docker-compose down 2>/dev/null || true

# ── 9. Build & start ──────────────────────────────────────────────────────────
echo "Building and starting services..."
docker-compose build
docker-compose up
