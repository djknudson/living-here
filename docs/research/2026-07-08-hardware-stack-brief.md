# Aquarium Monitoring Station — 2026 Technical Research Brief

> Saved 2026-07-08. Sourced from a web-research pass. "Verify before relying" items noted at the end.

## Recency traps (old tutorials get these wrong)
| Area | Old (pre-2024) | Current 2026 |
|---|---|---|
| DS18B20 in ESPHome | `dallas:` hub + `platform: dallas` | `one_wire:` (`platform: gpio`) + `platform: dallas_temp`, linked by `one_wire_id` |
| ESP32 ADC attenuation | `attenuation: 11db` | `attenuation: 12db` (or `auto`) |
| ESP32 analog + WiFi | any ADC pin | ADC1 only (GPIO32–39); ADC2 dead with WiFi |
| ESPHome custom sensor | `platform: custom` + C++ | `template` sensor + `lambda`, or external components |
| OTA block | bare `ota:` | `ota: - platform: esphome` |
| Pi camera CLI | `raspivid`/`raspistill` | `rpicam-vid`/`rpicam-still` (libcamera) |
| Pi HW H.264 | all models | Pi 4 yes, **Pi 5 no** (software encode) |
| HA go2rtc | manual/add-on | bundled since HA 2024.11 (managed, ports 11984/18555) |

---

## 1. ESPHome on the Elegoo ESP-WROOM-32

### HA integration (native API + OTA)
- `api:` component → HA auto-discovers via mDNS (`<node>.local`), appears under Settings → Devices & Services in ~5 min. Protobuf-over-TCP, ~10× smaller than MQTT.
- Use an encryption key: `api: → encryption: → key:` (32-byte base64). HA prompts for it on adoption.
- OTA is now `ota: - platform: esphome`.
```yaml
api:
  encryption:
    key: "base64-32-byte-key-here"
ota:
  - platform: esphome
    password: "some-ota-password"
```

### DS18B20 — current `one_wire` + `dallas_temp` syntax
The old `dallas:` hub + `platform: dallas` were REMOVED (broke configs in 2025.x). Replacement:
```yaml
one_wire:
  - platform: gpio
    pin: GPIO4
    id: bus_a
sensor:
  - platform: dallas_temp
    one_wire_id: bus_a
    # address: 0x...   # only if >1 sensor on the bus
    name: "Water Temperature"
    resolution: 12
    update_interval: 30s
```
Discover address: flash with only the `one_wire:` bus, read logs (addresses printed on scan). 4.7 kΩ pull-up data→3.3V required by the bus — **BOJACK module already has it, don't add a second.**

### ESP32 ADC (pin choice, attenuation, calibration)
- **ADC2 is dead when WiFi is on.** Use ADC1 only: GPIO32–39. GPIO34/35/36/39 are input-only, clean analog inputs. Avoid ADC2/strapping pins (0/2/4/12–15/25–27).
- Attenuation: `12db` for a 0–2.3 V sensor (old tutorials say `11db`).
- Calibration via `filters:` — `calibrate_linear` (measured→actual points), `calibrate_polynomial`, or `lambda`. `samples:` for noise.
```yaml
sensor:
  - platform: adc
    pin: GPIO34
    name: "TDS raw voltage"
    attenuation: 12db
    samples: 20
    update_interval: 10s
    filters:
      - calibrate_linear:
          - 0.329 -> 3.0
          - 0.487 -> 90.0
```

### First flash then OTA
- First flash MUST be over USB (web.esphome.io / ESPHome Device Builder add-on / `esphome run`). OTA only after it's on WiFi once.
- Elegoo devkit = CP2102/CH340 serial; install driver if port doesn't show. Hold BOOT if it stalls at "Connecting…". Board: `esp32: board: esp32dev`, framework esp-idf (recommended) or arduino.

---

## 2. HiLetgo TDS Sensor (= clone of DFRobot Gravity Analog TDS / SEN0244)

### Specs
- Supply 3.3–5.5 V; analog out 0–2.3 V; 3–6 mA; range 0–1000 ppm, ±10% F.S. @25 °C. Analog (not I²C). Board must NOT be submerged — only the probe tip.

### Wiring to ESP32
- VCC → 5V (output swings 0–2.3 V). GND → GND. Signal → ADC1 pin e.g. GPIO34.
- **No divider needed at 5 V** (2.3 V < 3.3 V ADC ceiling at 12db). At 3.3 V supply output tops ~1.5 V (safer, lower resolution). Never exceed 3.3 V into the ADC.

### TDS formula + temp compensation (verified vs DFRobot GravityTDS lib)
```
compVoltage Vc = Vadc / (1 + 0.02*(T-25))
EC = (133.42*Vc^3 - 255.86*Vc^2 + 857.39*Vc) * kValue
TDS_ppm = EC * 0.5
```

### ESPHome (native template + lambda, avoids deprecated `custom`)
```yaml
sensor:
  - platform: dallas_temp
    one_wire_id: bus_a
    id: water_temp
    name: "Water Temperature"
  - platform: adc
    pin: GPIO34
    id: tds_voltage
    attenuation: 12db
    samples: 20
    update_interval: 10s
    filters:
      - sliding_window_moving_average: { window_size: 10, send_every: 2 }
  - platform: template
    name: "Water TDS"
    unit_of_measurement: "ppm"
    accuracy_decimals: 0
    update_interval: 10s
    lambda: |-
      float v = id(tds_voltage).state;
      float t = id(water_temp).has_state() ? id(water_temp).state : 25.0;
      float vc = v / (1.0 + 0.02 * (t - 25.0));
      return (133.42*vc*vc*vc - 255.86*vc*vc + 857.39*vc) * 0.5;
```
inventmarine/open-tds-meter-esphome adds a persisted K-value (`globals` + `restore_value`) calibratable from HA buttons.

### Calibration
- Known standard: 707 ppm (1413 µS/cm) @25 °C. Submerge, settle, solve kValue (or two-point linear — better at low freshwater ppm). Keep electrodes clean.

---

## 3. BOJACK DS18B20 Module
- Waterproof stainless probe + 3-pin breakout. **Includes the 4.7 kΩ pull-up** — don't add another.
- Red=VCC, Black=GND, Yellow=DATA. Supply 3.0–5.25 V → runs at 3.3 V for ESP32. Red→3V3, Yellow→GPIO4, Black→GND. Resolution 9–12 bit.

---

## 4. Pi Camera Module 3 → Home Assistant (Pi 4, Bookworm, rpicam/libcamera)

### Architecture options
- **(a) `rpicam-vid` → go2rtc/MediaMTX on the Pi (BEST).** Re-serves RTSP + WebRTC; sub-second latency in HA.
- (b) HA bundled go2rtc consuming a Pi RTSP URL (simplest).
- (c) Plain RTSP systemd service (reliable; ~1–3 s latency unless upgraded to WebRTC).
- Recommendation: MediaMTX/go2rtc as a systemd service on the Pi feeding from `rpicam-vid`, exposed as RTSP, added to HA via Generic Camera; HA's go2rtc delivers WebRTC.

### Pi 4 is the better streaming host
- Pi 5 dropped the HW H.264 encoder (software encode). **Pi 4 has HW H.264** → 1080p30 at a few % CPU. Prefer native H.264 path over software libav.

### Commands (Bookworm)
```bash
# MPEG-TS over UDP into go2rtc/MediaMTX
rpicam-vid -t 0 -n --inline --width 1280 --height 720 --framerate 30 \
  --codec libav --libav-format mpegts -o "udp://127.0.0.1:8555?pkt_size=1316"
# TCP-listen (no extra server)
rpicam-vid -t 0 -n --inline --codec libav --libav-format mpegts -o "tcp://0.0.0.0:8554?listen=1"
```
`-t 0` run forever, `-n` headless, `--inline` repeat SPS/PPS each keyframe. For lowest latency use the native H.264 encoder (omit `--codec libav`).

go2rtc.yaml on the Pi:
```yaml
streams:
  aquarium:
    - exec:rpicam-vid -t 0 -n --inline --codec libav --libav-format mpegts -o -#backchannel=0
```

### Into HA
- HA bundles go2rtc since 2024.11 (managed; ports 11984/18555; don't hand-edit its file).
- Easiest: Settings → Devices & Services → Add → Generic Camera, Stream Source URL = `rtsp://<pi-ip>:8554/aquarium`.
- To point HA at a separate Pi go2rtc: `go2rtc: url: http://<pi-ip>:1984`.

### picamera2 alternative
Viable if you want programmatic frame access (motion/level detection). For pure livestream, rpicam-vid→go2rtc is less code / lower CPU.

---

## 5. HAOS SSH on x86 mini PC

### Add-on choice
- **Official "Terminal & SSH"**: sandboxed to add-on container + `/config` + `ha` CLI. Cannot install packages or be root on host.
- **Community "Advanced SSH & Web Terminal"** (hassio-addons/app-ssh): richer, supports disabling Protection mode for Docker/host access.
```yaml
ssh:
  username: root
  password: ""
  authorized_keys:
    - "ssh-ed25519 AAAA...yourkey... user@host"
  sftp: false
  compatibility_mode: false
zsh: true
```
Setting a `password` DISABLES key auth — pick one. Set exposed port in the add-on Network panel.

### Protection mode
- Not a YAML option — Supervisor toggle on the add-on Info page. Turn off + restart to reach Docker/host. Full system access when off (security exposure). `login` drops to the HAOS host shell.

### Port 22222 dev SSH
- Enabled by an `authorized_keys` file on a `CONFIG`-labeled partition/USB, imported at boot. Impractical on an installed x86 box (internal disk, needs physical USB + reboot). Reserve for recovery.

### Installing add-ons without UI
- Primary path is web UI. Programmatic via Supervisor REST API / `ha addons install|options|start <slug>` — but those run from an existing shell/token, so there's a bootstrap chicken-and-egg.

---

## Verify before relying
- The exact `calibrate_linear` reference points above are from one community build — re-derive against YOUR probe + known solution.
- The Pi 4 native-H.264 low-CPU claim assumes the hardware encoder path (drop `--codec libav`), not software libav.

## Primary sources
ESPHome: esphome.io/components/{sensor/dallas_temp, one_wire, sensor/adc, api, ota/esphome} · web.esphome.io ·
DFRobot TDS: wiki.dfrobot.com/sen0244 · github.com/DFRobot/GravityTDS · github.com/inventmarine/open-tds-meter-esphome ·
Pi camera: raspberrypi.com/documentation/computers/camera_software.html ·
HA go2rtc: home-assistant.io/integrations/go2rtc · github.com/AlexxIT/go2rtc ·
HA SSH: github.com/hassio-addons/app-ssh · developers.home-assistant.io/docs/operating-system/debugging
