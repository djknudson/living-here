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
| `sensordisplay` | 10.0.10.19 | Raspberry Pi Zero W (armv6, trixie), LAFVIN/Waveshare 2.13″ e-ink HAT | `ssh sensordisplay` |

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
  TDS signal → **D34/GPIO34** (ADC1 — **ADC2 is dead when Wi-Fi is on**), VCC → **VIN (5V)**, GND;
  BMP280 (I²C, `bmp280_i2c` @ 0x76): SDA → **D21/GPIO21**, SCL → **D22/GPIO22**, VCC → 3V3, GND.
- BOJACK DS18B20 module has its **own pull-up** — don't add one.
- **6-pin BMP280 gotcha:** `CSB` must be tied HIGH (3V3) for I²C or it stays in SPI mode
  and the I²C scan shows "found no devices." `SDO` low = 0x76, high = 0x77.

### Pi camera — `fishbucket/pi/`
- **go2rtc** systemd service driving `rpicam-vid`. Config `go2rtc.yaml`, unit `go2rtc.service`
  (deployed at `/etc/go2rtc/`). See `fishbucket/pi/README.md`.
- This rpicam-apps build reports **`libav:0`** → use native `--codec h264` (Pi 4 hardware
  encoder), NOT `--codec libav`. rpicam-vid runs **on-demand** (only while watched).
- Test: <http://10.0.10.38:1984> (stream `aquarium`). Restart: `ssh fishbucket 'sudo systemctl restart go2rtc'`.

### Pi Zero e-ink display — `sensordisplay/`
- `dashboard.py` (deployed to `~/display/` on the Pi) fetches the 4 sensor states from
  the **HA REST API** and renders a 250×122 1-bit image with Pillow → Waveshare
  `epd2in13_V4` panel. Refresh loop = `sensordashboard.timer` (every 5 min; e-ink can't
  full-refresh faster than ~3 min). Redeploy: copy `sensordisplay/` to the Pi, `bash setup.sh`.
- **HA token** lives at `~/display/ha_token` (0600, git-ignored) — a long-lived token.
  Install it without it hitting logs/repo: `pbpaste | ssh sensordisplay 'umask 077; cat > ~/display/ha_token'`.
- Icons = **Material Design Icons webfont** (`@mdi/font@7.4.47`) rendered as glyphs via
  `ImageFont.truetype` (crisp on 1-bit). Preview a render without the panel:
  `python3 -c "import dashboard; dashboard.render(dashboard.fetch()).resize((750,366)).save('preview.png')"`
  then `scp` it back and view — how I iterate on the look (I can't see the physical panel).
- Gotchas: on **trixie the Waveshare lib uses gpiozero+lgpio+spidev** (all apt, no
  RPi.GPIO/venv); try driver `epd2in13_V4`→V3→V2; the panel's **physical right edge clips
  a few px before 250** (values are width-capped to 78px); `GPIO busy` → add `dtoverlay=spi0-0cs`.

### Home Assistant — `homeassistant/`
- **Living Here** dashboard is **YAML mode** (`homeassistant/dashboards/living-here.yaml`,
  live at `/config/dashboards/living-here.yaml`, registered in `/config/configuration.yaml`).
- Editing dashboard content → just reload the browser. Adding a new dashboard or any
  `configuration.yaml` change → `ssh homeassistant 'ha core check && ha core restart'`
  (**always `ha core check` first** — bad config blocks startup).
- Entity IDs: `sensor.fishbucket_sensors_water_temperature`, `...water_tds`,
  `...tds_sensor_voltage`, `...air_temperature`, `...air_pressure`,
  `number.fishbucket_sensors_tds_calibration_k`, `camera.fishbucket_camera`.

## Gotchas (things that cost time once)
- **HAOS empty add-on store on first boot** → `ha supervisor repair` (or restart). "Check
  for updates" only git-pulls repos; it doesn't rebuild the Supervisor's add-on index.
- **TDS math** matches the DFRobot GravityTDS library order: cubic on the RAW voltage →
  `EC`, then normalize EC to 25 °C (`/(1+0.02*(T-25))`), then `×0.5` (NaCl factor). Do NOT
  temperature-compensate the voltage before the (nonlinear) cubic.
- **TDS calibration** is a separate, optional step (the `number.…_tds_calibration_k` knob,
  K=1.0 uncalibrated). Temperature *compensation* is automatic via the DS18B20.
- Temperatures display in **°F** (HA imperial unit system; ESPHome sends °C).
- **Replaced the ESP32 board?** A new board has a new MAC + likely a new DHCP IP, so HA's
  ESPHome config entry (keyed by the OLD mac, holding the OLD IP) won't auto-adopt it and the
  sensor entities go 404/unavailable. Fix without the UI: with HA stopped, edit both `"host"`
  (new IP) and `"unique_id"` (new MAC, lowercase) for the entry in
  `/config/.storage/core.config_entries`, then `ha core start` + reload the entry
  (`homeassistant.reload_config_entry`, `entry_id`). Matching unique_id→new MAC lets future IP
  changes self-heal via mDNS. Canonical alternative: delete the dead entry and re-adopt the
  rediscovered device (recreates the same entity_ids). A brownout boot-loop (flickering power
  LED, `E BOD: Brownout detector was triggered`) = power/regulator, not firmware — swap cable →
  wall charger → board.

## Current state / open items
- ESP32 runs on a battery that has died a couple of times → readings go `unavailable`
  until repowered (firmware auto-reconnects, no reflash needed).
- TDS uncalibrated (fine for testing). Camera not yet in a waterproof enclosure.
- No alerting/automations yet (out of scope for the prototype).
