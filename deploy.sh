#!/bin/bash
# Deploy PrepRight on Raspberry Pi
# Run: bash deploy.sh  (no sudo needed!)
# Works on a fresh Raspberry Pi OS (Bookworm or Bullseye)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CURRENT_USER="$(whoami)"

echo "=== PrepRight Deploy Script ==="

# ── 0. Ensure project directory is owned by current user ────────
echo "[0/7] Fixing file ownership..."
sudo chown -R $CURRENT_USER:$CURRENT_USER "$SCRIPT_DIR"

# ── 1. Install system prerequisites ─────────────────────────────
echo "[1/7] Installing system prerequisites..."
sudo apt-get update
sudo apt-get install -y \
    nodejs \
    npm \
    git \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev

# Ensure pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "  Installing pip3..."
    sudo apt-get install -y python3-pip
fi

# Add current user to dialout group (serial port access)
echo "  Adding '$CURRENT_USER' user to dialout group..."
sudo usermod -aG dialout $CURRENT_USER
echo "  NOTE: Reboot after deploy for dialout group to take effect."

# ── 2. Install Python dependencies ──────────────────────────────
echo "[2/7] Installing Python dependencies..."
cd "$SCRIPT_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# ── 3. Seed database ────────────────────────────────────────────
echo "[3/7] Seeding database..."
python seed.py
python seed_templates.py

# ── 4. Install root npm dependencies ────────────────────────────
echo "[4/7] Installing root npm dependencies..."
cd "$SCRIPT_DIR"
npm install

# ── 5. Install frontend and build ───────────────────────────────
echo "[5/7] Building frontend..."
cd "$SCRIPT_DIR/frontend"
# Detect Pi's IP for the API URL
PI_IP=$(hostname -I | awk '{print $1}')
export VITE_API_URL="http://$PI_IP:8000/api"
echo "  API URL set to: $VITE_API_URL"
# Clean slate to avoid permission issues
rm -rf node_modules dist
npm install
npm run build

# ── 6. Serve frontend via nginx ─────────────────────────────────
echo "[6/7] Setting up nginx for frontend..."
if ! command -v nginx &> /dev/null; then
    sudo apt-get install -y nginx
fi
sudo cp -r dist/* /var/www/html/
sudo systemctl enable nginx
sudo systemctl start nginx
echo "  Frontend served at: http://<pi-ip> (via nginx on port 80)"

# ── 7. Create systemd services ──────────────────────────────────
echo "[7/7] Creating systemd services..."

# Backend service
sudo tee /etc/systemd/system/prepright.service > /dev/null <<EOF
[Unit]
Description=PrepRight Backend
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/backend/.venv/bin/uvicorn prepright.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=$SCRIPT_DIR/backend/.venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prepright
sudo systemctl start prepright

# Serial receiver service
echo "  NOTE: Update the serial port below if yours is not /dev/ttyUSB0"
sudo tee /etc/systemd/system/prepright-serial.service > /dev/null <<EOF
[Unit]
Description=PrepRight Serial Receipt Receiver
After=network.target prepright.service
Wants=prepright.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/backend/.venv/bin/python3 serial_receiver.py --port /dev/ttyUSB0 --baud 9600 --host localhost --port-api 8000
Restart=always
RestartSec=5
Environment=PATH=$SCRIPT_DIR/backend/.venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prepright-serial
sudo systemctl start prepright-serial

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo "Backend API:    http://<pi-ip>:8000"
echo "API docs:       http://<pi-ip>:8000/docs"
echo "Dashboard:      http://<pi-ip>"
echo ""
echo "Services:"
echo "  sudo systemctl status prepright"
echo "  sudo systemctl status prepright-serial"
echo ""
echo "Logs:"
echo "  sudo journalctl -u prepright -f"
echo "  sudo journalctl -u prepright-serial -f"
echo ""
echo "NOTE: If your POS uses a different serial port or baud rate,"
echo "      edit ExecStart in /etc/systemd/system/prepright-serial.service"
echo "      then: sudo systemctl daemon-reload && sudo systemctl restart prepright-serial"
