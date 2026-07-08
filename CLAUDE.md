# Living Here — project guide

Home Assistant setup called **Living Here**. First station: **fishbucket**, an
aquarium monitor for a backyard freshwater tub with goldfish. Status: working
prototype — temp + TDS + camera all live in Home Assistant.

Parent conventions apply: see `~/Development/CLAUDE.md` (Conventional Commits,
trunk-based direct to `main`, atomic commits, "code like it ships").

## Machines & access (passwordless SSH is set up)
| Host | IP | What it is | Reach it |
|------|-----|-----------|----------|
| `homeassistant` | 10.0.10.90 | HAOS 2026.7.1, Intel N97, 16 GB | `ssh homeassistant` (root, Terminal & SSH add-on) · web `:8123` (user `<ha-user>`) |
| `fishbucket` | 10.0.10.38 | Raspberry Pi 4, Debian 13 (trixie), Camera Module 3 (imx708) | `ssh fishbucket` |
| `fishbucket-sensors` | DHCP (was .67) | ESP32 (Elegoo ESP-WROOM-32) running ESPHome | HA native API + wireless OTA |

SSH aliases live in `~/.ssh/config` (identity `~/.ssh/id_ed25519`). The `ssh homeassistant`
shell is the add-on container: `/config` + the `ha` CLI (not the host OS).

## Data flow
`ESP32 (DS18B20 + TDS) --Wi-Fi/encrypted ESPHome API--> HA`
`Camera Module 3 --rpicam-vid HW H.264--> go2rtc (Pi) --RTSP--> HA Generic Camera`

## Components & how to change them
### ESP32 sensor firmware — `fishbucket/esp32/`
- **ESPHome, not Arduino.** Firmware is `fishbucket-sensors.yaml`. Secrets (Wi-Fi, API
  key, OTA pass) in `secrets.yaml` — **git-ignored**; template is `secrets.example.yaml`.
- `esphome` CLI is installed via **Homebrew** (system Python is 3.14, which ESPHome
  doesn't support — don't try a venv). `export PATH="/opt/homebrew/bin:$PATH"`.
- Change + deploy (wireless, no USB after the first flash):
  ```bash
  cd fishbucket/esp32
  esphome run fishbucket-sensors.yaml --device fishbucket-sensors.local
  ```
- First-ever flash only: `--device /dev/cu.usbserial-0001` (USB).
- Pins (Elegoo silkscreen = `D<gpio>`): DS18B20 data → **D4/GPIO4**, 3V3, GND;
  TDS signal → **D34/GPIO34** (ADC1 — **ADC2 is dead when Wi-Fi is on**), VCC → **VIN (5V)**, GND.
- BOJACK DS18B20 module has its **own pull-up** — don't add one.

### Pi camera — `fishbucket/pi/`
- **go2rtc** systemd service driving `rpicam-vid`. Config `go2rtc.yaml`, unit `go2rtc.service`
  (deployed at `/etc/go2rtc/`). See `fishbucket/pi/README.md`.
- This rpicam-apps build reports **`libav:0`** → use native `--codec h264` (Pi 4 hardware
  encoder), NOT `--codec libav`. rpicam-vid runs **on-demand** (only while watched).
- Test: <http://10.0.10.38:1984> (stream `aquarium`). Restart: `ssh fishbucket 'sudo systemctl restart go2rtc'`.

### Home Assistant — `homeassistant/`
- **Living Here** dashboard is **YAML mode** (`homeassistant/dashboards/living-here.yaml`,
  live at `/config/dashboards/living-here.yaml`, registered in `/config/configuration.yaml`).
- Editing dashboard content → just reload the browser. Adding a new dashboard or any
  `configuration.yaml` change → `ssh homeassistant 'ha core check && ha core restart'`
  (**always `ha core check` first** — bad config blocks startup).
- Entity IDs: `sensor.fishbucket_sensors_water_temperature`, `...water_tds`,
  `...tds_sensor_voltage`, `number.fishbucket_sensors_tds_calibration_k`, `camera.fishbucket_camera`.

## Gotchas (things that cost time once)
- **HAOS empty add-on store on first boot** → `ha supervisor repair` (or restart). "Check
  for updates" only git-pulls repos; it doesn't rebuild the Supervisor's add-on index.
- **TDS math** matches the DFRobot GravityTDS library order: cubic on the RAW voltage →
  `EC`, then normalize EC to 25 °C (`/(1+0.02*(T-25))`), then `×0.5` (NaCl factor). Do NOT
  temperature-compensate the voltage before the (nonlinear) cubic.
- **TDS calibration** is a separate, optional step (the `number.…_tds_calibration_k` knob,
  K=1.0 uncalibrated). Temperature *compensation* is automatic via the DS18B20.
- Temperatures display in **°F** (HA imperial unit system; ESPHome sends °C).

## Current state / open items
- ESP32 runs on a battery that has died a couple of times → readings go `unavailable`
  until repowered (firmware auto-reconnects, no reflash needed).
- TDS uncalibrated (fine for testing). Camera not yet in a waterproof enclosure.
- No alerting/automations yet (out of scope for the prototype).
