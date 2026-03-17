#!/usr/bin/env bash
# Magpie Resolution Scaler — installer for Linux Mint
set -e

echo "==> Installing Magpie Resolution Scaler..."

# Check for xrandr
if ! command -v xrandr &>/dev/null; then
    echo "Installing x11-xserver-utils (xrandr)..."
    sudo apt install -y x11-xserver-utils
fi

# Check for Python3 + GTK3 bindings
python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" 2>/dev/null || {
    echo "Installing python3-gi (GTK3 bindings)..."
    sudo apt install -y python3-gi gir1.2-gtk-3.0
}

# Copy app
sudo mkdir -p /opt/magpie-scaler
sudo cp magpie_scaler.py /opt/magpie-scaler/
sudo chmod +x /opt/magpie-scaler/magpie_scaler.py

# Install desktop launcher
sudo cp magpie-scaler.desktop /usr/share/applications/
sudo chmod 644 /usr/share/applications/magpie-scaler.desktop

# Also create a symlink so it's runnable from terminal
sudo ln -sf /opt/magpie-scaler/magpie_scaler.py /usr/local/bin/magpie-scaler

echo ""
echo "✓ Done! Launch from:"
echo "   • Menu → Preferences → Magpie Resolution Scaler"
echo "   • Or run:  magpie-scaler"
