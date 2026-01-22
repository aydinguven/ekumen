#!/bin/bash
# Ekumen - Install from GitHub
# Usage: curl -fsSL https://raw.githubusercontent.com/aydinguven/ekumen/main/install.sh | bash

set -e

# Default settings
INSTALL_DIR="${EKUMEN_INSTALL_DIR:-/opt/ekumen}"
SERVICE_NAME="ekumen"
USER_NAME="${SUDO_USER:-$USER}"
GROUP_NAME=$(id -gn "$USER_NAME")

# Check for root/sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

echo "Installing Ekumen to $INSTALL_DIR..."

# Clone repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR exists. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone --depth 1 https://github.com/aydinguven/ekumen.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment and install dependencies
echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Set ownership
chown -R "$USER_NAME:$GROUP_NAME" "$INSTALL_DIR"

# Create Systemd Service
echo "Creating Systemd service..."

cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Ekumen - Ansible Web Interface
After=network.target

[Service]
User=$USER_NAME
Group=$GROUP_NAME
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin"
Environment="ANSIBLE_SHUTTLE_HOST=0.0.0.0"
Environment="ANSIBLE_SHUTTLE_PORT=5000"
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload and Start Service
echo "Starting Ekumen service..."
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo ""
echo "✅ Ekumen installed and started successfully!"
echo ""
echo "Manage the service:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo systemctl restart $SERVICE_NAME"
echo "  sudo systemctl stop $SERVICE_NAME"
echo ""
echo "Access the interface at http://<server-ip>:5000"
