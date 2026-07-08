# fishbucket Pi — camera streaming

Raspberry Pi 4 (`fishbucket`, 10.0.10.38, Debian 13 trixie) with a Camera Module 3
(imx708). Streams the aquarium to Home Assistant via **go2rtc** + `rpicam-vid`.

## Pipeline
```
imx708 → rpicam-vid (Pi 4 hardware H.264) → go2rtc → RTSP :8554 → HA Generic Camera → WebRTC
```
`rpicam-vid` runs on-demand (only while something is watching).

## Install / redeploy
```bash
# 1. binary
sudo curl -fsSL -o /usr/local/bin/go2rtc \
  https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_arm64
sudo chmod +x /usr/local/bin/go2rtc

# 2. camera group access (fishbucket is already in video+render on Pi OS)
sudo usermod -aG video,render fishbucket

# 3. config + service (copy the files in this dir)
sudo mkdir -p /etc/go2rtc
sudo cp go2rtc.yaml /etc/go2rtc/go2rtc.yaml
sudo cp go2rtc.service /etc/systemd/system/go2rtc.service
sudo systemctl daemon-reload
sudo systemctl enable --now go2rtc
```

## Verify
- Web UI / test view: <http://10.0.10.38:1984>  → stream `aquarium`
- Grab video (proves the whole path): `curl -m 8 -o /tmp/out.mp4 "http://localhost:1984/api/stream.mp4?src=aquarium"`
- Service: `systemctl status go2rtc` · logs: `journalctl -u go2rtc -f`

## Home Assistant
Added via **Settings → Devices & Services → Generic Camera** with
Stream source `rtsp://10.0.10.38:8554/aquarium` → entity `camera.fishbucket_camera`.

## Tuning (edit `/etc/go2rtc/go2rtc.yaml`, then `sudo systemctl restart go2rtc`)
- Resolution/FPS: `--width/--height/--framerate`.
- Bitrate (default ~10 Mbps at 720p): add `--bitrate 4000000` for ~4 Mbps (kinder to Wi-Fi).
- Orientation: `--rotation 180`, `--hflip`, `--vflip` once the camera is mounted.
