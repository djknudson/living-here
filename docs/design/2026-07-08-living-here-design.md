# Living Here — Design Spec

> Status: prototype. Date: 2026-07-08.
> Goal (per owner): a testing/prototype aquarium monitoring station — a plastic tub
> outdoors with freshwater + goldfish. "Get all the parts functioning." No production
> alerting/HA automations required for v1.

## Machines

| Role | Host | IP | OS | Access |
|------|------|-----|-----|--------|
| HA hub "Living Here" | homeassistant | 10.0.10.90 | HAOS 2026.7.1 (Core, amd64), Intel N97, 16 GB | `ssh homeassistant` (root, Terminal & SSH add-on, key-only) + web UI :8123 |
| Aquarium node "fishbucket" | fishbucket | 10.0.10.38 | Debian 13 (trixie), Pi 4B, 8 GB | `ssh fishbucket` (key-only) |
| Sensor node | fishbucket-sensors | (DHCP) | ESPHome on Elegoo ESP-WROOM-32 | native HA API + OTA |

SSH aliases live in `~/.ssh/config` (key: `~/.ssh/id_ed25519`).

## Hardware inventory

- **Elegoo ESP-WROOM-32** dev board in a Freenove breakout, on USB to the Mac (first flash).
- **BOJACK DS18B20** waterproof temp probe + 3-pin module (on-board 4.7 kΩ pull-up — no external resistor).
- **HiLetgo TDS / conductivity sensor** = clone of DFRobot Gravity Analog TDS (SEN0244). Analog, 3.3–5.5 V in, 0–2.3 V out, 0–1000 ppm.
- **MECCANIXITY BMP280** (6-pin I²C) — ambient air temp + barometric pressure OUTSIDE the tank. Added 2026-07-09.
- **Raspberry Pi Camera Module 3** (imx708) on the Pi — to be dropped in the tub once a waterproof enclosure is built.

## Architecture

```
  ESP32 (ESPHome)                          Pi 4 "fishbucket" (picam3)
  ├─ DS18B20  → GPIO4  (1-Wire)            └─ rpicam-vid → go2rtc/MediaMTX
  └─ TDS      → GPIO34 (ADC1, 5V supply)         └─ RTSP / WebRTC
        │  Wi-Fi "<ssid>", native encrypted API            │  RTSP
        └──────────────┐              ┌──────────────────┘
                       ▼              ▼
                 Home Assistant (HAOS — the hub)
                 ├─ ESPHome integration (built-in)  → Water Temperature, Water TDS
                 ├─ go2rtc (built-in)               → camera live view
                 └─ Dashboard
```

## Components

### 1. ESP32 sensor firmware (`fishbucket/esp32/fishbucket-sensors.yaml`)
- ESPHome, `esp32dev` board, esp-idf framework. Built/flashed from the Mac with the
  `esphome` CLI (Homebrew). First flash over USB (`/dev/cu.usbserial-0001`), OTA after.
- Native encrypted API → HA auto-discovers the node (no MQTT broker).
- Entities: **Water Temperature** (`dallas_temp`, GPIO4), **Water TDS** (`ppm`,
  temperature-compensated), **TDS Sensor Voltage** (diagnostic), **TDS Calibration K**
  (`number`, HA-adjustable, persisted), **Air Temperature** + **Air Pressure**
  (`bmp280_i2c` @ 0x76 on GPIO21/22).
- Secrets (`secrets.yaml`, git-ignored): Wi-Fi, API key, OTA/AP passwords.

### 2. Pi camera stream (`fishbucket/pi/`) — DEPLOYED
- go2rtc systemd service on the Pi driving `rpicam-vid` (Pi 4 hardware H.264, native
  codec — this rpicam-apps build reports libav:0). Serves RTSP :8554 / WebRTC :8555 /
  web UI :1984, on-demand (encoder only runs while watched). Added to HA via Generic
  Camera → `camera.fishbucket_camera`; HA's bundled go2rtc serves low-latency WebRTC to
  the dashboard. Physical in-water placement awaits the waterproof enclosure.

### 3. Home Assistant (hub) — DEPLOYED
- ESPHome integration adopted the node (API encryption key entered once).
- Generic Camera integration → `camera.fishbucket_camera`.
- **Living Here** dashboard (YAML mode): live camera, temp + TDS gauges, 24 h
  trend graphs, sensor/calibration entities. Source in `homeassistant/dashboards/`.
- HA-side setup documented in `homeassistant/README.md`.

## Wiring (Freenove ESP32 breakout)

```
DS18B20:  RED → 3V3    BLACK → GND    YELLOW(DATA) → GPIO4
TDS:      VCC → 5V(VIN) GND → GND      A(signal)   → GPIO34
BMP280:   VCC → 3V3     GND → GND      SDA → GPIO21, SCL → GPIO22  (CSB→3V3 for I2C)
```
Rationale: GPIO34 is ADC1 + input-only (ADC2 is unusable with Wi-Fi on ESP32); TDS at 5 V
tops out ~2.3 V, under the 3.3 V ADC ceiling at `attenuation: 12db`, so no divider is needed.

## TDS calibration
Uncalibrated K=1.0. To calibrate: submerge the probe in a known solution (e.g. 707 ppm /
1413 µS/cm @ 25 °C), let it settle, then adjust **TDS Calibration K** in HA until "Water TDS"
reads the reference value. Two-point linear is more accurate at low freshwater ppm — revisit
if precision matters.

## Repo layout
```
living-here/
├── docs/            research brief + this design
├── fishbucket/      aquarium station
│   └── esp32/       ESPHome firmware (+ secrets, git-ignored)
└── .gitignore
```

## Out of scope for v1
Alerting/automations, camera-in-water, multi-sensor buses, pH/DO sensors, external access.
Reference: `docs/research/2026-07-08-hardware-stack-brief.md`.
