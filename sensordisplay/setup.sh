#!/usr/bin/env bash
# Living Here — sensordisplay e-ink dashboard installer. Run ON the Pi Zero
# (from this repo dir copied to the Pi), e.g.:  bash setup.sh
set -euo pipefail
DIR=/home/sensordisplay/display
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== enable SPI (reboot required if it was off) =="
sudo raspi-config nonint do_spi 0

echo "== apt deps (prebuilt armv6 — avoids slow pip builds / PEP-668) =="
sudo apt-get update
sudo apt-get install -y python3-pil python3-numpy python3-spidev \
  python3-gpiozero python3-lgpio libopenjp2-7 fonts-dejavu-core git curl

echo "== Waveshare 2.13\" V4 driver (gpiozero+lgpio backend, current on trixie) =="
mkdir -p "$DIR/waveshare_epd"
BASE=https://raw.githubusercontent.com/waveshareteam/e-Paper/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd
for f in epdconfig.py epd2in13_V4.py epd2in13_V3.py epd2in13_V2.py; do
  curl -fsSL -o "$DIR/waveshare_epd/$f" "$BASE/$f"
done
touch "$DIR/waveshare_epd/__init__.py"

echo "== Material Design Icons webfont (pinned 7.4.47) =="
curl -fsSL -o "$DIR/materialdesignicons-webfont.ttf" \
  https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/fonts/materialdesignicons-webfont.ttf

echo "== app + service =="
cp "$HERE/dashboard.py" "$DIR/dashboard.py"
sudo cp "$HERE/sensordashboard.service" /etc/systemd/system/
sudo cp "$HERE/sensordashboard.timer"   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sensordashboard.timer

if [ ! -f "$DIR/ha_token" ]; then
  echo
  echo "!! MISSING: $DIR/ha_token"
  echo "   Create a Home Assistant long-lived token (Profile -> Security ->"
  echo "   Long-lived access tokens) and install it WITHOUT it hitting your shell history:"
  echo "     (on the token dialog, click Copy)  then from your Mac:"
  echo "     pbpaste | ssh sensordisplay 'umask 077; cat > ~/display/ha_token'"
else
  echo "== first refresh =="
  sudo systemctl start sensordashboard.service
fi
echo "Done."
